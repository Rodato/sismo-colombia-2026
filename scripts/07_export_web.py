"""Exporta el payload que consume el mapa web: geometría simplificada + atributos.

La geometría del MGN viene a resolución catastral (90 MB). Para el navegador hay
que simplificarla, pero sin abrir huecos entre municipios vecinos: si se
simplifica cada polígono por separado, las fronteras compartidas dejan de
coincidir y aparecen ranuras blancas. Por eso se simplifica con topología
preservada, disolviendo y reconstruyendo desde los bordes comunes.
"""

import json
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "proc"
WEB = ROOT / "web" / "public" / "data"
WEB.mkdir(parents=True, exist_ok=True)

TOLERANCIA = 0.004  # grados (~400 m): suficiente a escala nacional

print("cargando ...")
geo = gpd.read_file(PROC / "municipios_sismo.gpkg")
tab = pd.read_csv(PROC / "municipios_sismo.csv", dtype={"divipola": str})
sf = pd.read_csv(PROC / "suelo_fallido.csv", dtype={"divipola": str})

cols_tab = [
    "divipola", "municipio", "departamento", "mmi_max", "mmi_media", "vs30_medio",
    "pob_total", "pob_cabecera", "pob_rural", "def_cualitativo", "def_habitacional",
    "menciones", "menciones_nacional", "menciones_regional", "indice", "rank",
    "cobertura_dato", "muertos_rep", "heridos_rep", "desaparecidos_rep", "muertos_100k",
]
d = tab[cols_tab].merge(
    sf[["divipola", "desliz_max", "desliz_km2", "licuef_max", "licuef_km2", "licuef_frac"]],
    on="divipola",
    how="left",
)

geo = geo[["divipola", "geometry"]].merge(d, on="divipola")
print(f"  {len(geo)} municipios")

print(f"simplificando (tolerancia {TOLERANCIA}°, topología preservada) ...")
antes = geo.geometry.apply(lambda g: len(g.wkt))
try:
    import topojson as tp

    geo["geometry"] = tp.Topology(geo, prequantize=False).toposimplify(TOLERANCIA).to_gdf().geometry
    metodo = "topojson (fronteras compartidas intactas)"
except ImportError:
    geo["geometry"] = geo.geometry.simplify(TOLERANCIA, preserve_topology=True)
    metodo = "shapely preserve_topology (puede dejar ranuras finas entre vecinos)"
despues = geo.geometry.apply(lambda g: len(g.wkt))
print(f"  método: {metodo}")
print(f"  wkt: {antes.sum() / 1e6:.1f} MB -> {despues.sum() / 1e6:.1f} MB")

geo = geo[~geo.geometry.is_empty & geo.geometry.notna()]

# Sentido de giro para d3-geo: anillo exterior HORARIO.
#
# Cuidado, esto contradice RFC 7946, que pide el exterior antihorario. d3-geo
# usa geometría esférica y toma el interior del polígono como el lado
# izquierdo del recorrido; con el sentido equivocado interpreta cada municipio
# como su COMPLEMENTO, o sea el planeta entero menos ese municipio. Entonces
# geoBounds devuelve [[-180,-90],[180,90]] para cada feature, fitSize calcula
# una escala para el globo y el país se colapsa a media docena de píxeles.
#
# Verificado a mano, no deducido de la especificación: con el anillo tal como
# venía, geoBounds daba el globo; invirtiéndolo, daba los límites correctos
# del municipio.
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.polygon import orient


def horario(g):
    """sign=-1.0 deja el anillo exterior en sentido horario."""
    if isinstance(g, Polygon):
        return orient(g, sign=-1.0)
    if isinstance(g, MultiPolygon):
        return MultiPolygon([orient(p, sign=-1.0) for p in g.geoms])
    return g


geo["geometry"] = geo.geometry.map(horario)
print("  anillos orientados en sentido horario (lo que espera d3-geo)")

# Redondea para que el JSON no cargue decimales sin significado.
for c in ["mmi_max", "mmi_media", "desliz_max", "licuef_max"]:
    geo[c] = geo[c].astype(float).round(2)
for c in ["vs30_medio", "def_cualitativo", "def_habitacional", "licuef_km2", "desliz_km2"]:
    geo[c] = geo[c].astype(float).round(1)
geo["indice"] = geo["indice"].astype(float).round(0)
geo["licuef_frac"] = geo["licuef_frac"].astype(float).round(3)
for c in ["pob_total", "pob_cabecera", "pob_rural"]:
    geo[c] = geo[c].fillna(0).astype(int)
geo["cobertura_dato"] = geo["cobertura_dato"].fillna(0).astype(int)
# Los *_rep quedan en null donde no hay dato, a propósito: 0 significaría "cero
# muertos reportados" (que es el caso real de Armenia) y null significa "nadie
# publicó una cifra". Confundirlos borraría justo el hallazgo de esta capa.
for c in ["muertos_rep", "heridos_rep", "desaparecidos_rep", "muertos_100k"]:
    geo[c] = geo[c].astype(float).round(1)

salida = WEB / "municipios.geojson"
geo.to_file(salida, driver="GeoJSON", coordinate_precision=4)
print(f"escrito: {salida}  ({salida.stat().st_size / 1e6:.2f} MB)")

# ------------------------------------------------------------------ resumen
serie = pd.read_csv(PROC / "serie_oficial.csv")
danos = json.loads((PROC / "danos_oficiales.json").read_text())
pmun = pd.read_csv(PROC / "perdidas_municipales.csv")
pdep = pd.read_csv(PROC / "perdidas_departamentales.csv")
sac = d[d["mmi_max"] >= 6]

con_cifra = d[d["cobertura_dato"] == 2].sort_values("muertos_100k", ascending=False)

resumen = {
    "evento": {
        "magnitud": 7.4,
        "profundidad_km": 110.3,
        "fecha_utc": "2026-08-10T12:34:28Z",
        "hora_local": "07:34",
        "epicentro": "San José del Palmar, Chocó",
        "lat": 4.8436,
        "lon": -76.2422,
        "mecanismo": "falla de rumbo, sismo intraplaca profundo",
    },
    "alcance": {
        "municipios_mmi6": int((d["mmi_max"] >= 6).sum()),
        "municipios_mmi7": int((d["mmi_max"] >= 7).sum()),
        "municipios_mmi75": int((d["mmi_max"] >= 7.5).sum()),
        "poblacion_mmi6": int(sac["pob_total"].sum()),
        "municipios_ungrd": danos["municipios_afectados"],
        "departamentos_ungrd": danos["departamentos_afectados"],
    },
    "cobertura": {
        "notas_corpus": 199,
        "medios": 11,
        "municipios_con_mencion": int((sac["menciones"] > 0).sum()),
        "municipios_sacudidos": int(len(sac)),
        "concentracion_top10_pct": round(
            float(d.nlargest(10, "menciones")["menciones"].sum() / d["menciones"].sum() * 100), 1
        ),
    },
    "danos": danos,
    "serie": serie.to_dict(orient="records"),
    "pager": {
        "mediana_muertos": 961,
        "poblacion_mmi6": 5507652,
        "poblacion_mmi7": 5163899,
        "poblacion_mmi8": 1218340,
        "alerta": "roja",
        "alerta_deslizamientos": "naranja",
        "deslizamiento_km2": 37,
        "deslizamiento_personas": 4400,
    },
    "perdidas": {
        # Cuántos municipios tienen realmente un dato de pérdidas, que es el
        # hallazgo de esta sección: 5 de 682.
        "con_cifra_propia": int((d["cobertura_dato"] == 2).sum()),
        "solo_departamental": int((d["cobertura_dato"] == 1).sum()),
        "sin_dato": int((d["cobertura_dato"] == 0).sum()),
        "total_municipios": int(len(d)),
        "muertos_atribuidos": int(con_cifra["muertos_rep"].sum()),
        "muertos_nacionales": int(serie["muertos"].iloc[-1]),
        "muertos_sin_atribuir": int(serie["muertos"].iloc[-1] - con_cifra["muertos_rep"].sum()),
        "corte": "2026-08-13",
        "tablero_ungrd": {
            "existio": True,
            "desagregacion": "municipio y departamento",
            "campos": "fallecidos, heridos, desaparecidos, viviendas destruidas, infraestructura",
            "minutos_hasta_restriccion": 42,
            "quien_lo_reveló": "Ronny Suárez Celemín",
            "denuncia": "Sindicato Colombiano de Periodistas, Ley 1712 de 2014",
            "url": "https://www.infobae.com/colombia/2026/08/14/sindicato-colombiano-de-periodistas-se-despacho-contra-de-la-espriella-por-restriccion-a-informacion-del-terremoto-primer-acto-de-censura/",
        },
        "municipios": [
            {"municipio": r["municipio"], "departamento": r["departamento"],
             "pob": int(r["pob_total"]), "muertos": int(r["muertos_rep"]),
             "por_100k": round(float(r["muertos_100k"]), 1),
             "mmi": round(float(r["mmi_max"]), 1), "rank": int(r["rank"])}
            for _, r in con_cifra.iterrows()
        ],
        "departamentos": [
            {k: (None if pd.isna(v) else (v if isinstance(v, str) else int(v)))
             for k, v in r.items() if k not in ("fuente", "url")}
            for _, r in pdep.iterrows()
        ],
        "serie_municipal": [
            {k: (None if pd.isna(v) else (v if isinstance(v, str) else int(v)))
             for k, v in r.items()}
            for _, r in pmun.iterrows()
        ],
    },
    "cinturon_suelo_blando": [
        {
            "municipio": r["municipio"], "departamento": r["departamento"],
            "vs30": round(float(r["vs30_medio"])), "mmi": round(float(r["mmi_max"]), 1),
            "pob": int(r["pob_total"]), "licuef": round(float(r["licuef_max"]), 2),
            "menciones": int(r["menciones"]),
        }
        for _, r in sac.nsmallest(8, "vs30_medio").iterrows()
    ],
    "corredor_choco": [
        {
            "municipio": r["municipio"], "mmi": round(float(r["mmi_max"]), 1),
            "licuef_km2": round(float(r["licuef_km2"])), "pob": int(r["pob_total"]),
            "deficit": round(float(r["def_habitacional"]), 1), "menciones": int(r["menciones"]),
        }
        for _, r in sac[sac["departamento"] == "CHOCÓ"].nlargest(10, "licuef_km2").iterrows()
    ],
    "mas_mencionados": [
        {"municipio": r["municipio"], "departamento": r["departamento"],
         "menciones": int(r["menciones"]), "mmi": round(float(r["mmi_max"]), 1)}
        for _, r in d.nlargest(10, "menciones").iterrows()
    ],
    "fuentes": {
        "sacudida": "USGS ShakeMap v6, evento us6000tjl2",
        "suelo": "Vs30 del propio ShakeMap",
        "deslizamientos": "Nowicki Jessee y otros (2018), USGS ground-failure",
        "licuefaccion": "Zhu y otros (2017), USGS ground-failure",
        "poblacion": "DANE, proyecciones municipales 2018-2042 (corte 2026)",
        "vulnerabilidad": "DANE, déficit habitacional CNPV 2018",
        "geometria": "DANE, Marco Geoestadístico Nacional 2023",
        "cifras_oficiales": "UNGRD, vía prensa fechada y atribuida",
        "perdidas_municipales": "Asocapitales, Informe Consolidado No. 22 (5 capitales)",
        "perdidas_departamentales": "UNGRD, corte 11 ago, vía prensa",
    },
}
def sanear(o):
    """NaN/NaT no existen en JSON: JSON.parse los rechaza. Se convierten a null."""
    if isinstance(o, dict):
        return {k: sanear(v) for k, v in o.items()}
    if isinstance(o, list):
        return [sanear(v) for v in o]
    if isinstance(o, float) and (np.isnan(o) or np.isinf(o)):
        return None
    if o is pd.NaT or (o is not None and o is pd.NA):
        return None
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    return o


(WEB / "resumen.json").write_text(
    json.dumps(sanear(resumen), ensure_ascii=False, indent=1, allow_nan=False), encoding="utf-8"
)
print(f"escrito: {WEB / 'resumen.json'}")

# tabla plana para la vista de lista y descarga
tabla = d.sort_values("indice", ascending=False)
tabla.to_csv(WEB / "municipios.csv", index=False)
print(f"escrito: {WEB / 'municipios.csv'}  ({len(tabla)} filas)")

print("\nresumen del payload:")
print(f"  municipios con MMI>=6: {resumen['alcance']['municipios_mmi6']}")
print(f"  población expuesta:    {resumen['alcance']['poblacion_mmi6']:,}")
print(f"  con mención en prensa: {resumen['cobertura']['municipios_con_mencion']}")
print(f"  concentración top-10:  {resumen['cobertura']['concentracion_top10_pct']}%")
p = resumen["perdidas"]
print(f"  con cifra de pérdidas: {p['con_cifra_propia']} de {p['total_municipios']}"
      f"  ({100 * p['con_cifra_propia'] / p['total_municipios']:.1f}%)")
print(f"  muertos sin atribuir:  {p['muertos_sin_atribuir']} de {p['muertos_nacionales']}")
