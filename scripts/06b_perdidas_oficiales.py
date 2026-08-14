"""Pérdidas reportadas por municipio y por departamento, curadas a mano.

POR QUÉ ESTE SCRIPT NO PUEDE LLENAR LOS 682 MUNICIPIOS
------------------------------------------------------
No es una limitación del método: el dato no existe en público.

La UNGRD SÍ tuvo un tablero con cifras de fallecidos, heridos, desaparecidos,
viviendas destruidas y daños de infraestructura DESAGREGADAS POR MUNICIPIO Y
DEPARTAMENTO. Lo deshabilitó 42 minutos después de que el periodista Ronny
Suárez Celemín hiciera pública su existencia (Infobae, 14 ago 2026). El
Sindicato Colombiano de Periodistas lo denunció citando la Ley 1712 de 2014 y
el propio índice de información clasificada de la UNGRD, que lista esa
información como pública.

Se buscó la vía de datos abiertos. Los datasets de emergencias de la UNGRD en
datos.gov.co (wwkg-r6te, 4fd8-ptcr, 4t8v-ywmw, rgre-6ak4) tienen exactamente el
esquema que haría falta —municipio, fallecidos, heridos, familias, viviendas—
pero el más reciente termina en 2024. Para 2026 no hay nada. Verificado por API
el 14 de agosto de 2026: wwkg-r6te devuelve 25.857 filas entre 2019-01-01 y
2022-12-31.

Queda entonces lo que la prensa publicó, en dos niveles muy desiguales:

  · 5 municipios  con cifra propia — todos capitales, vía Asocapitales
  · 16 departamentos con cifra propia — vía UNGRD
  · 677 municipios sin ningún dato

Los 5 municipios son capitales por una razón estructural, no por azar:
Asocapitales es la Asociación Colombiana de Ciudades Capitales. Por diseño no
puede contar un municipio que no sea capital. Dosquebradas —#5 de 682 en
nuestro índice de exposición, 246.388 habitantes, MMI 7,9, pegado a Pereira—
es invisible para la única fuente municipal que existe.

CADA DATO LLEVA SU CORTE
------------------------
Mezclar cortes es el error que ya se pagó en 06_serie_cifras.py. Acá cada fila
es un corte con hora, fuente y URL. Las cifras de Asocapitales del 11 de agosto
NO se combinan con las del 13: se guardan como serie.

Eso deja a la vista una contradicción que vale por sí sola: el 11 de agosto
Cali reporta 95 muertos (Asocapitales, 16:00) mientras el Valle del Cauca
entero reporta 70 (UNGRD, mañana). La ciudad supera a su propio departamento.
Son fuentes y horas distintas, así que no es un error de nadie — es la prueba
de que no hay un registro único, que es justo lo que denunció la Defensoría.
"""

import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "proc"

BLU = "https://www.bluradio.com/nacion/aumenta-a-273-el-numero-de-muertos-por-el-terremoto-en-colombia-so35"
INFOBAE_22 = "https://www.infobae.com/colombia/2026/08/13/mas-de-900-psicologos-se-movilizan-para-brindar-atencion-gratuita-a-victimas-del-fuerte-terremoto/"
CARACOL = "https://www.noticiascaracol.com/colombia/en-vivo-colombia-hoy-tras-terremoto-de-magnitud-7-4-continuan-las-lab"
VALORA = "https://www.valoraanalitik.com/terremoto-en-colombia-balance-de-departamentos-y-ciudades-mas-afectadas/"
CENSURA = "https://www.infobae.com/colombia/2026/08/14/sindicato-colombiano-de-periodistas-se-despacho-contra-de-la-espriella-por-restriccion-a-informacion-del-terremoto-primer-acto-de-censura/"

# municipio, departamento, fecha, corte, muertos, heridos, desaparecidos,
# viv_colapsadas, viv_averiadas, fuente, url
MUNICIPAL = [
    ("CALI", "VALLE DEL CAUCA", "2026-08-11", "16:00", 95, 997, 180, 56, 93,
     "Asocapitales vía Noticias Caracol", CARACOL),
    ("PEREIRA", "RISARALDA", "2026-08-11", "16:00", 79, 278, 37, 92, 26,
     "Asocapitales vía Noticias Caracol", CARACOL),
    ("QUIBDÓ", "CHOCÓ", "2026-08-11", "16:00", 9, 116, 5, 23, 862,
     "Asocapitales vía Noticias Caracol", CARACOL),
    ("MANIZALES", "CALDAS", "2026-08-11", "16:00", 5, 112, None, 23, None,
     "Asocapitales vía Noticias Caracol", CARACOL),
    ("ARMENIA", "QUINDIO", "2026-08-11", "16:00", 0, 174, None, 69, None,
     "Asocapitales vía Valora Analitik", VALORA),

    # Consolidado No. 22, corte 13 ago 10:00. Es el más completo que se publicó.
    ("CALI", "VALLE DEL CAUCA", "2026-08-13", "10:00", 96, None, None, None, None,
     "Asocapitales No. 22 vía Blu Radio", BLU),
    # OJO: Blu Radio atribuye los 260 desaparecidos a Pereira, pero otra nota del
    # mismo día dice "260 desaparecidas en Pereira y Dosquebradas". El dato es
    # ambiguo entre dos municipios; se deja en Pereira porque así lo publica la
    # fuente citada, y se marca la ambigüedad en la salida.
    ("PEREIRA", "RISARALDA", "2026-08-13", "10:00", 93, 259, 260, None, None,
     "Asocapitales No. 22 vía Blu Radio", BLU),
    ("QUIBDÓ", "CHOCÓ", "2026-08-13", "10:00", 9, 119, None, 100, 2125,
     "Asocapitales No. 22 vía Blu Radio", BLU),
    ("MANIZALES", "CALDAS", "2026-08-13", "10:00", 6, 182, None, 1449, None,
     "Asocapitales No. 22 vía Blu Radio", BLU),
    ("ARMENIA", "QUINDIO", "2026-08-13", "10:00", 0, 174, None, None, 54,
     "Asocapitales No. 22 vía Blu Radio", BLU),
]

# departamento, muertos, heridos, desaparecidos, viv_averiadas, viv_destruidas,
# edif_colapsadas   —  UNGRD, corte 11 ago mañana, vía Valora Analitik
DEPARTAMENTAL = [
    ("RISARALDA", 90, 224, 14, 40, 0, 0),
    ("VALLE DEL CAUCA", 70, 1648, 171, 1073, 256, 44),
    ("CHOCÓ", 14, 131, 10, 1832, 715, None),
    ("CALDAS", 6, 274, None, 1959, 156, 4),
    ("QUINDIO", 0, 306, None, 2144, 3, 0),
    ("ANTIOQUIA", 1, None, None, 857, None, None),
    ("TOLIMA", None, None, None, 234, 6, None),
    ("CUNDINAMARCA", None, None, None, 89, None, None),
    ("HUILA", None, None, None, 52, None, None),
    ("SUCRE", None, None, None, 56, None, None),
    ("CAUCA", None, None, None, 5, None, None),
    ("NORTE DE SANTANDER", None, None, None, 5, None, None),
    ("BOLIVAR", None, None, None, 1, None, None),
]

CORTE_PRINCIPAL = "2026-08-13"


def norm(s):
    """Sin tildes y en mayúsculas: el CSV trae QUINDIO sin tilde y CHOCÓ con."""
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).upper().strip()


mun = pd.DataFrame(MUNICIPAL, columns=[
    "municipio", "departamento", "fecha", "corte", "muertos", "heridos",
    "desaparecidos", "viv_colapsadas", "viv_averiadas", "fuente", "url"])
dep = pd.DataFrame(DEPARTAMENTAL, columns=[
    "departamento", "muertos", "heridos", "desaparecidos", "viv_averiadas",
    "viv_destruidas", "edif_colapsadas"])
dep["fecha"], dep["corte"] = "2026-08-11", "mañana"
dep["fuente"], dep["url"] = "UNGRD vía Valora Analitik", VALORA

mun.to_csv(PROC / "perdidas_municipales.csv", index=False)
dep.to_csv(PROC / "perdidas_departamentales.csv", index=False)

# ------------------------------------------------------- pegar al CSV maestro
tab = pd.read_csv(PROC / "municipios_sismo.csv", dtype={"divipola": str})
tab["_m"] = tab["municipio"].map(norm)
tab["_d"] = tab["departamento"].map(norm)

ultimo = mun[mun["fecha"] == CORTE_PRINCIPAL].copy()
ultimo["_m"] = ultimo["municipio"].map(norm)
ultimo["_d"] = ultimo["departamento"].map(norm)

# Match por municipio Y departamento. Sin el departamento, ARMENIA del Quindío
# (307.103 hab, capital) se confunde con ARMENIA de Antioquia (5.292 hab), que
# es justo la clase de homónimo que ya rompió el conteo de menciones en 04.
for c in ["muertos", "heridos", "desaparecidos", "viv_colapsadas", "viv_averiadas"]:
    tab[f"{c}_rep"] = tab.set_index(["_m", "_d"]).index.map(
        ultimo.set_index(["_m", "_d"])[c]) if c in ultimo else None

tab["fuente_perdidas"] = tab.set_index(["_m", "_d"]).index.map(
    ultimo.set_index(["_m", "_d"])["fuente"])

deps_con_dato = {norm(d[0]) for d in DEPARTAMENTAL}

# 2 = tiene cifra propia | 1 = solo el agregado de su departamento | 0 = nada
tab["cobertura_dato"] = 0
tab.loc[tab["_d"].isin(deps_con_dato), "cobertura_dato"] = 1
tab.loc[tab["muertos_rep"].notna(), "cobertura_dato"] = 2

tab["muertos_100k"] = (tab["muertos_rep"] / tab["pob_total"] * 1e5).round(1)

tab = tab.drop(columns=["_m", "_d"])
tab.to_csv(PROC / "municipios_sismo.csv", index=False)

# ------------------------------------------------------------------ auditoría
n = len(tab)
c2 = int((tab["cobertura_dato"] == 2).sum())
c1 = int((tab["cobertura_dato"] == 1).sum())
c0 = int((tab["cobertura_dato"] == 0).sum())

print("=" * 92)
print("COBERTURA DEL DATO DE PÉRDIDAS")
print("=" * 92)
print(f"  cifra propia del municipio      {c2:>5} de {n}  ({100*c2/n:>5.1f}%)")
print(f"  solo el agregado departamental  {c1:>5} de {n}  ({100*c1/n:>5.1f}%)")
print(f"  sin ningún dato                 {c0:>5} de {n}  ({100*c0/n:>5.1f}%)")

if c2 != len(ultimo):
    print(f"\n  ¡ALERTA! {len(ultimo)} municipios curados pero {c2} emparejados.")
    print("  Revisar nombres/departamentos contra el CSV maestro.")

print("\n" + "=" * 92)
print(f"MORTALIDAD REPORTADA, NORMALIZADA POR POBLACIÓN (corte {CORTE_PRINCIPAL})")
print("=" * 92)
con = tab[tab["cobertura_dato"] == 2].sort_values("muertos_100k", ascending=False)
print(f"  {'municipio':<12}{'población':>12}{'muertos':>9}{'por 100k':>10}"
      f"{'MMI máx':>9}{'rank índ.':>11}")
for _, r in con.iterrows():
    print(f"  {r['municipio']:<12}{r['pob_total']:>12,.0f}{r['muertos_rep']:>9.0f}"
          f"{r['muertos_100k']:>10.1f}{r['mmi_max']:>9.1f}{int(r['rank']):>11}")

tot = float(con["muertos_rep"].sum())
print(f"\n  suma de los {c2}: {tot:,.0f} muertos de 281 nacionales ({100*tot/281:.0f}%)")
print(f"  sin atribución municipal: {281-tot:,.0f} muertos repartidos entre 398 municipios")

print("\n" + "=" * 92)
print("LA CIUDAD QUE SUPERA A SU DEPARTAMENTO")
print("=" * 92)
d11 = mun[mun["fecha"] == "2026-08-11"].set_index("municipio")
# Normalizar el índice también, no solo la búsqueda: CHOCÓ != CHOCO.
dd = dep.set_index(dep["departamento"].map(norm))
for ciudad, depto in [("CALI", "VALLE DEL CAUCA"), ("PEREIRA", "RISARALDA"),
                      ("QUIBDÓ", "CHOCÓ")]:
    mc, md = d11.loc[ciudad, "muertos"], dd.loc[norm(depto), "muertos"]
    flag = "  <-- IMPOSIBLE si fuera el mismo registro" if mc > md else ""
    print(f"  {ciudad:<10} {mc:>4.0f} muertos   vs   {depto:<17} {md:>4.0f}{flag}")
print("\n  Mismo día (11 ago). Asocapitales corta a las 16:00 y la UNGRD por la")
print("  mañana, así que la diferencia de hora explica el número — pero también")
print("  demuestra que las dos cifras no salen del mismo registro.")

print("\n" + "=" * 92)
print("EL PUNTO CIEGO ESTRUCTURAL")
print("=" * 92)
ds = tab[tab["municipio"].map(norm) == "DOSQUEBRADAS"].iloc[0]
print(f"  Dosquebradas: rank {int(ds['rank'])} de {n} en el índice de exposición,")
print(f"  {ds['pob_total']:,.0f} habitantes, MMI {ds['mmi_max']:.1f}, cobertura_dato = {int(ds['cobertura_dato'])}.")
print("  No es capital, así que Asocapitales no lo cuenta. Aparece en la prensa")
print("  solo como apéndice: \"260 desaparecidas en Pereira y Dosquebradas\".")
print("\n  Los 5 municipios con cifra propia son los 5 que Asocapitales declaró en")
print("  alerta roja. Nuestro top-5 del índice es Pereira, Cali, Manizales,")
print("  Armenia y Dosquebradas: coincide en 4 de 5 sin usar ningún dato de")
print("  víctimas. El quinto que ellos listan, Quibdó, es nuestro #9.")

print(f"\nescrito: {PROC / 'perdidas_municipales.csv'} ({len(mun)} filas)")
print(f"escrito: {PROC / 'perdidas_departamentales.csv'} ({len(dep)} filas)")
print(f"actualizado: {PROC / 'municipios_sismo.csv'} (+8 columnas)")
print(f"\nsobre el tablero deshabilitado: {CENSURA}")
