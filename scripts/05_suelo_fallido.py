"""Cruza los modelos de falla del terreno del USGS con municipios y población.

Dos fenómenos distintos, dos poblaciones distintas:

  DESLIZAMIENTOS (Nowicki Jessee 2018) — laderas empinadas del área epicentral.
  Golpea zona rural dispersa, sin vías ni conectividad. Es donde tiene sentido
  buscar a los desaparecidos que no aparecen en ningún censo urbano.

  LICUEFACCIÓN (Zhu 2017) — suelos saturados y planos. Golpea el valle aluvial
  del río Cauca. Es el mismo terreno blando que amplificó la sacudida, así que
  sirve de verificación cruzada del cinturón de suelo blando del norte del Cauca.

El USGS marcó alerta NARANJA de deslizamientos: 37 km² de área agregada y unas
4.400 personas expuestas. Aquí repartimos eso por municipio.
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

UMBRAL_DESLIZ = 0.10  # probabilidad a partir de la cual contamos área afectable
UMBRAL_LICUEF = 0.20


def zonal(ruta, municipios, umbral, prefijo):
    with rasterio.open(ruta) as src:
        arr = src.read(1)
        transform, shape = src.transform, src.shape
    arr = np.where(np.isfinite(arr), arr, 0.0)

    idx = rasterize(
        ((g, i + 1) for i, g in enumerate(municipios.geometry)),
        out_shape=shape,
        transform=transform,
        fill=0,
        dtype="int32",
    )
    # área real de una celda (varía con la latitud; basta la aproximación local)
    lat_media = municipios.geometry.union_all().centroid.y
    km2_celda = (
        abs(transform.a) * 111.32 * np.cos(np.radians(lat_media)) * abs(transform.e) * 110.57
    )

    filas = []
    for i in range(len(municipios)):
        m = idx == (i + 1)
        if not m.any():
            filas.append({f"{prefijo}_max": 0.0, f"{prefijo}_media": 0.0, f"{prefijo}_km2": 0.0,
                          f"{prefijo}_frac": 0.0})
            continue
        v = arr[m]
        sobre = v > umbral
        filas.append(
            {
                f"{prefijo}_max": float(v.max()),
                f"{prefijo}_media": float(v.mean()),
                f"{prefijo}_km2": float(sobre.sum() * km2_celda),
                f"{prefijo}_frac": float(sobre.mean()),
            }
        )
    return pd.DataFrame(filas, index=municipios.index)


print("cargando municipios y tabla base ...")
geo = gpd.read_file(PROC / "municipios_sismo.gpkg")
tab = pd.read_csv(PROC / "municipios_sismo.csv", dtype={"divipola": str})
geo = geo[["divipola", "geometry"]].merge(
    tab[["divipola", "municipio", "departamento", "mmi_max", "vs30_medio", "pob_total",
         "pob_cabecera", "pob_rural", "def_cualitativo"]],
    on="divipola",
).reset_index(drop=True)
print(f"  {len(geo)} municipios")

print("deslizamientos (Jessee 2018) ...")
d = zonal(RAW / "gf_landslide_jessee2018.tif", geo, UMBRAL_DESLIZ, "desliz")
print("licuefacción (Zhu 2017) ...")
lq = zonal(RAW / "gf_liquefaction_zhu2017.tif", geo, UMBRAL_LICUEF, "licuef")

geo = pd.concat([geo, d, lq], axis=1)

# Población rural expuesta a deslizamiento: la fracción del municipio sobre
# umbral, aplicada a la población rural dispersa (la que vive en las laderas).
geo["pob_rural_desliz"] = (geo["pob_rural"].fillna(0) * geo["desliz_frac"]).round()
geo["pob_licuef"] = (geo["pob_total"].fillna(0) * geo["licuef_frac"]).round()

salida = PROC / "suelo_fallido.csv"
geo.drop(columns="geometry").to_csv(salida, index=False)
geo.to_file(PROC / "municipios_sismo.gpkg", driver="GPKG")
print(f"escrito: {salida}")

print("\n" + "=" * 92)
print(f"DESLIZAMIENTOS — municipios con más área sobre probabilidad {UMBRAL_DESLIZ}")
print("=" * 92)
top = geo[geo["desliz_km2"] > 0].nlargest(15, "desliz_km2")
t = top[["municipio", "departamento", "desliz_max", "desliz_km2", "pob_rural",
         "pob_rural_desliz", "mmi_max"]].copy()
t["desliz_max"] = t["desliz_max"].map("{:.3f}".format)
t["desliz_km2"] = t["desliz_km2"].map("{:.1f}".format)
for c in ["pob_rural", "pob_rural_desliz"]:
    t[c] = t[c].map(lambda v: f"{v:,.0f}")
print(t.to_string(index=False))
print(f"\n  área total sobre umbral: {geo['desliz_km2'].sum():.0f} km²")
print(f"  (USGS reporta 37 km² de 'área agregada de amenaza', con umbral propio)")
print(f"  población rural en esa área: {geo['pob_rural_desliz'].sum():,.0f}")

print("\n" + "=" * 92)
print(f"LICUEFACCIÓN — municipios con más área sobre probabilidad {UMBRAL_LICUEF}")
print("=" * 92)
top = geo.nlargest(15, "licuef_km2")
t = top[["municipio", "departamento", "licuef_max", "licuef_km2", "vs30_medio",
         "pob_total", "mmi_max"]].copy()
t["licuef_max"] = t["licuef_max"].map("{:.3f}".format)
t["licuef_km2"] = t["licuef_km2"].map("{:.0f}".format)
t["vs30_medio"] = t["vs30_medio"].map("{:.0f}".format)
t["pob_total"] = t["pob_total"].map(lambda v: f"{v:,.0f}")
print(t.to_string(index=False))

print("\n" + "=" * 92)
print("VERIFICACIÓN CRUZADA — ¿la licuefacción confirma el cinturón de suelo blando?")
print("=" * 92)
blandos = geo[geo["mmi_max"] >= 6].nsmallest(8, "vs30_medio")
t = blandos[["municipio", "departamento", "vs30_medio", "licuef_max", "licuef_frac", "pob_total"]].copy()
t["vs30_medio"] = t["vs30_medio"].map("{:.0f}".format)
t["licuef_max"] = t["licuef_max"].map("{:.3f}".format)
t["licuef_frac"] = t["licuef_frac"].map("{:.0%}".format)
t["pob_total"] = t["pob_total"].map(lambda v: f"{v:,.0f}")
print(t.to_string(index=False))
