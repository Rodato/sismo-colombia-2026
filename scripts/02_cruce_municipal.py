"""Cruza sacudida (ShakeMap) x poblacion (DANE) x vulnerabilidad (deficit habitacional).

Produce una tabla con un registro por municipio de Colombia y, para cada uno:

  - estadisticas de intensidad MMI dentro del poligono municipal
  - Vs30 medio (suelo blando amplifica; suelo rigido no)
  - poblacion proyectada 2026, total / cabecera / rural
  - % de hogares en deficit cualitativo (CNPV 2018) como proxy de vulnerabilidad
  - un indice de exposicion ponderada para priorizar donde mirar

NOTA METODOLOGICA: la poblacion municipal se reparte de forma uniforme sobre el
area del municipio. Es una aproximacion: subestima la concentracion urbana. Por
eso reportamos tambien MMI en cabecera y el rango de MMI dentro del municipio,
para saber en que municipios esa aproximacion importa (los grandes y de MMI
heterogenea) y en cuales es inocua (los pequenos y de MMI uniforme).

El indice NO es un modelo de perdidas ni una estimacion de muertos. Es un
ranking de tamizaje para priorizar donde buscar dano no reportado.
"""

import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "proc"

ANIO = 2026

# ------------------------------------------------------------------ ráster
print("cargando ShakeMap ...")
with rasterio.open(PROC / "shakemap.tif") as src:
    bandas = {src.descriptions[i]: src.read(i + 1) for i in range(src.count)}
    transform, shape, crs_r = src.transform, src.shape, src.crs
MMI, SVEL, PGA = bandas["MMI"], bandas["SVEL"], bandas["PGA"]
print(f"  {shape[0]}x{shape[1]}  MMI {MMI.min():.1f}–{MMI.max():.1f}")

# --------------------------------------------------------------- municipios
print("cargando municipios MGN 2023 ...")
mun = gpd.read_file(RAW / "mgn_mpio" / "MGN_ADM_MPIO_GRAFICO.shp").to_crs(crs_r)
mun["divipola"] = mun["mpio_cdpmp"].astype(str).str.zfill(5)
mun = mun[["divipola", "mpio_cnmbr", "dpto_cnmbr", "mpio_narea", "geometry"]].rename(
    columns={"mpio_cnmbr": "municipio", "dpto_cnmbr": "departamento", "mpio_narea": "area_km2"}
)
print(f"  {len(mun)} municipios")

# Recorta a los que tocan la huella del ShakeMap: fuera de ahí no hay dato.
oeste, sur, este, norte = (
    transform.c,
    transform.f + shape[0] * transform.e,
    transform.c + shape[1] * transform.a,
    transform.f,
)
huella = mun.cx[oeste:este, sur:norte]
print(f"  {len(huella)} dentro de la huella del ShakeMap")

# ---------------------------------------------------- zonal stats por rasterización
print("rasterizando municipios sobre el grid ...")
huella = huella.reset_index(drop=True)
idx = rasterize(
    ((geom, i + 1) for i, geom in enumerate(huella.geometry)),
    out_shape=shape,
    transform=transform,
    fill=0,
    dtype="int32",
)

filas = []
for i, r in huella.iterrows():
    m = idx == (i + 1)
    n = int(m.sum())
    if n == 0:
        # Municipio más pequeño que una celda: muestrea en el centroide.
        c = r.geometry.centroid
        col, fil = ~transform * (c.x, c.y)
        col, fil = int(col), int(fil)
        if not (0 <= fil < shape[0] and 0 <= col < shape[1]):
            continue
        vm, vs, vp = MMI[fil, col], SVEL[fil, col], PGA[fil, col]
        mmi_v, svel_v, pga_v, n = np.array([vm]), np.array([vs]), np.array([vp]), 1
        muestreo = "centroide"
    else:
        mmi_v, svel_v, pga_v = MMI[m], SVEL[m], PGA[m]
        muestreo = "celdas"

    filas.append(
        dict(
            divipola=r.divipola,
            municipio=r.municipio,
            departamento=r.departamento,
            area_km2=r.area_km2,
            celdas=n,
            muestreo=muestreo,
            mmi_max=float(mmi_v.max()),
            mmi_media=float(mmi_v.mean()),
            mmi_min=float(mmi_v.min()),
            pga_max=float(pga_v.max()),
            vs30_medio=float(svel_v.mean()),
            vs30_min=float(svel_v.min()),
            # fracción del área municipal en cada banda de intensidad
            frac_mmi6=float((mmi_v >= 6).mean()),
            frac_mmi7=float((mmi_v >= 7).mean()),
            frac_mmi8=float((mmi_v >= 8).mean()),
            # mismas bandas con la convención del USGS PAGER, que redondea al
            # entero: la banda VIII cubre 7.5–8.5, no 8.0+. Sin esto la
            # comparación contra sus cifras publicadas no es válida.
            frac_pager6=float((mmi_v >= 5.5).mean()),
            frac_pager7=float((mmi_v >= 6.5).mean()),
            frac_pager8=float((mmi_v >= 7.5).mean()),
            # peso de daño: nulo por debajo de MMI 5, crece rápido por encima
            peso_dano=float((np.clip(mmi_v - 5.0, 0, None) ** 2.5).mean()),
        )
    )

sac = pd.DataFrame(filas)
print(f"  {len(sac)} municipios con sacudida calculada")

# ------------------------------------------------------------------ población
print(f"cargando población DANE {ANIO} ...")
pob = pd.read_excel(
    RAW / "dane_poblacion_mun_2018_2042.xlsx", sheet_name="PobMunicipalxÁrea", skiprows=7
)
pob.columns = [str(c).strip() for c in pob.columns]
pob = pob.dropna(subset=["DPMP"])
pob["divipola"] = pob["MPIO"].astype(str).str.split(".").str[0].str.zfill(5)
pob["AÑO"] = pd.to_numeric(pob["AÑO"], errors="coerce")
pob = pob[pob["AÑO"] == ANIO]

area_col = "ÁREA GEOGRÁFICA"
piv = pob.pivot_table(index="divipola", columns=area_col, values="TOTAL", aggfunc="sum")
ren = {c: c for c in piv.columns}
for c in piv.columns:
    cl = str(c).lower()
    if cl.startswith("total"):
        ren[c] = "pob_total"
    elif "cabecera" in cl:
        ren[c] = "pob_cabecera"
    elif "rural" in cl or "poblados" in cl:
        ren[c] = "pob_rural"
piv = piv.rename(columns=ren).reset_index()
print(f"  {len(piv)} municipios con población {ANIO}")

# -------------------------------------------------------------- vulnerabilidad
print("cargando déficit habitacional CNPV 2018 ...")
d = pd.read_excel(
    RAW / "dane_deficit_hab_2018_cnpv.xlsx", sheet_name="Resumen Municipios", skiprows=9
)
d = d.iloc[1:]  # fila en blanco bajo el encabezado
d.columns = [str(c).strip() for c in d.columns]
cols = list(d.columns)
d = d.rename(
    columns={
        cols[2]: "divipola",
        cols[4]: "def_cuantitativo",
        cols[5]: "def_cualitativo",
        cols[6]: "def_habitacional",
    }
)
d["divipola"] = d["divipola"].astype(str).str.split(".").str[0].str.zfill(5)
d = d[["divipola", "def_cuantitativo", "def_cualitativo", "def_habitacional"]].dropna(
    subset=["divipola"]
)
for c in ["def_cuantitativo", "def_cualitativo", "def_habitacional"]:
    d[c] = pd.to_numeric(d[c], errors="coerce")
print(f"  {len(d)} municipios con déficit")

# ------------------------------------------------------------------- join
df = sac.merge(piv, on="divipola", how="left").merge(d, on="divipola", how="left")

falta_pob = df["pob_total"].isna().sum()
falta_def = df["def_cualitativo"].isna().sum()
print(f"\njoin: {len(df)} filas | sin población: {falta_pob} | sin déficit: {falta_def}")

# ------------------------------------------------------- índice de tamizaje
# Exposición: población x peso de daño medio del municipio.
#
# Vulnerabilidad: déficit habitacional TOTAL, no solo el cualitativo. La primera
# versión usaba el cualitativo y subestimaba gravemente al Chocó: allí la
# vivienda es tan precaria que el DANE la clasifica en déficit CUANTITATIVO
# (hay que reemplazarla) en vez de cualitativo (hay que mejorarla). En Alto
# Baudó el 96,6% del déficit es cuantitativo, así que mirar solo el cualitativo
# lo hacía aparecer con 3,0% de vulnerabilidad cuando su déficit real es 99,6%.
# Usar el total corrige el sesgo contra los municipios más precarios.
df["exposicion"] = df["pob_total"].fillna(0) * df["peso_dano"]
df["vulnerabilidad"] = 1 + df["def_habitacional"].fillna(df["def_habitacional"].median()) / 100
df["indice"] = df["exposicion"] * df["vulnerabilidad"]

# Población por banda de intensidad (reparto uniforme por área — ver nota arriba)
for b in (6, 7, 8):
    df[f"pob_mmi{b}"] = (df["pob_total"].fillna(0) * df[f"frac_mmi{b}"]).round().astype("int64")
    df[f"pob_pager{b}"] = (df["pob_total"].fillna(0) * df[f"frac_pager{b}"]).round().astype("int64")

df = df.sort_values("indice", ascending=False).reset_index(drop=True)
df["rank"] = df.index + 1

salida = PROC / "municipios_sismo.csv"
df.to_csv(salida, index=False)
print(f"escrito: {salida}")

# guarda también la geometría para el mapa
geo = huella.merge(df.drop(columns=["municipio", "departamento", "area_km2"]), on="divipola")
geo.to_file(PROC / "municipios_sismo.gpkg", driver="GPKG")
print(f"escrito: {PROC / 'municipios_sismo.gpkg'}")

# ------------------------------------------------------------------ chequeos
print("\n" + "=" * 78)
print("CONTRASTE CON LAS CIFRAS PUBLICADAS POR EL USGS (misma convención de bandas)")
print("=" * 78)
# PAGER publica por banda redondeada; acumulamos sus bandas para comparar umbrales.
pager_pub = {6: 5_507_652, 7: 5_163_899, 8: 1_218_340}
acum = {
    6: pager_pub[6] + pager_pub[7] + pager_pub[8],
    7: pager_pub[7] + pager_pub[8],
    8: pager_pub[8],
}
print(f"  {'umbral':<12}{'nuestro':>14}{'USGS PAGER':>14}{'razón':>10}")
for b in (6, 7, 8):
    n, u = int(df[f"pob_pager{b}"].sum()), acum[b]
    print(f"  MMI {b}+{'':<7}{n:>14,}{u:>14,}{n / u:>9.2f}x")
print("\n  Nuestro reparto es por área municipal; el del USGS usa grilla Landscan.")
print("  Coincidir en orden de magnitud es la validación que buscamos, no la igualdad.")

print("\n" + "=" * 78)
print("ALCANCE GEOGRÁFICO")
print("=" * 78)
for umbral, etiqueta in [(6, "daño posible"), (7, "daño probable"), (7.5, "daño severo")]:
    n = int((df["mmi_max"] >= umbral).sum())
    print(f"  municipios con MMI máxima ≥ {umbral:<4} ({etiqueta:14s}): {n:>4}")
print(f"  municipios dentro de la huella del ShakeMap:      {len(df):>4}")
print("  UNGRD reporta afectación en 403 municipios de 14 departamentos.")

print("\n" + "=" * 78)
print("TOP 25 POR ÍNDICE DE TAMIZAJE")
print("=" * 78)
cols_out = [
    "rank",
    "municipio",
    "departamento",
    "mmi_max",
    "mmi_media",
    "vs30_medio",
    "pob_total",
    "def_cualitativo",
]
t = df.head(25)[cols_out].copy()
t["pob_total"] = t["pob_total"].map(lambda v: f"{v:,.0f}" if pd.notna(v) else "?")
t["def_cualitativo"] = t["def_cualitativo"].map(lambda v: f"{v:.1f}%" if pd.notna(v) else "?")
print(t.to_string(index=False))
