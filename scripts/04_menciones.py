"""Cuenta menciones de cada municipio en el corpus de prensa, con desambiguación.

Contar nombres de municipios en texto libre es una trampa. Los tres modos de
fallar que encontramos en la primera versión, y cómo se corrigen aquí:

  1. SUBCADENA. "Palmar" (Santander) aparecía 82 veces porque se colaba dentro
     de "San José del Palmar" (Chocó, el epicentro). La frontera de palabra no
     lo evita. Solución: recorrer los nombres de más largo a más corto y
     ENMASCARAR cada coincidencia antes de buscar los nombres más cortos.

  2. PALABRA CORRIENTE. "Socorro" (Santander) aparecía 64 veces por "organismos
     de socorro". "Colombia" (Huila) 1.892 veces por el nombre del país.
     Solución: lista de nombres riesgosos que exigen el departamento cerca.

  3. HOMÓNIMO. "Candelaria" es del Valle y del Atlántico; "Risaralda" es
     municipio de Caldas y departamento. Solución: exigir el departamento cerca.

Los municipios cuyo nombre exige desambiguación se reportan aparte: su conteo
es menos confiable en ambos sentidos, así que no entran en el titular.
"""

import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "proc"
VENTANA = 150

# Nombres de municipio que también son palabra corriente en una nota de prensa
# sobre un desastre, o nombre de país/departamento/accidente geográfico.
RIESGOSAS = {
    "colombia", "socorro", "rivera", "palmar", "risaralda", "quindio", "cauca",
    "narino", "choco", "caldas", "tolima", "huila", "antioquia", "santander",
    "la union", "la victoria", "la paz", "la merced", "la playa", "la cruz",
    "el carmen", "el rosario", "el penol", "la esperanza", "el dorado",
    "puerto rico", "san jose", "santa rosa", "el aguila", "la sierra",
    "el retiro", "la plata", "el tambo", "la primavera", "san juan",
    "el banco", "la gloria", "la pena", "el charco", "la salina", "el paso",
    "el castillo", "la macarena", "san rafael", "santa barbara", "la cumbre",
    "buenos aires", "la calera", "el molino", "la mesa", "el copey", "la uvita",
    "san pedro", "san luis", "san carlos", "san antonio", "san francisco",
    "santa ana", "santa maria", "el porvenir", "la florida", "el rosal",
    "la esmeralda", "el guamo", "la union panamericana", "villa rica",
    "el aguacate", "guatape", "la ceja", "el peon", "san isidro",
}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()


import sys

CORPUS = PROC / (sys.argv[1] if len(sys.argv) > 1 else "corpus_limpio.json")
SALIDA_CSV = len(sys.argv) <= 1  # solo el corpus limpio actualiza el CSV oficial

print(f"cargando {CORPUS.name} ...")
notas = json.loads(CORPUS.read_text(encoding="utf-8"))
df = pd.read_csv(PROC / "municipios_sismo.csv", dtype={"divipola": str})
textos = [norm(n["texto"]) for n in notas]
print(f"  {len(notas)} notas, {len(df)} municipios")

# Un municipio cubierto SOLO por su prensa local no está "sin informar": está
# ausente del relato nacional, que es una afirmación distinta y más precisa.
REGIONALES = {"La Patria (Manizales)", "El País (Cali)", "Chocó7dias", "El Diario (Pereira)"}
es_regional = [n["medio"] in REGIONALES for n in notas]
print(f"  notas regionales: {sum(es_regional)} | nacionales: {len(notas) - sum(es_regional)}")

df["nombre_norm"] = df["municipio"].map(norm)
df["depto_norm"] = df["departamento"].map(norm)

conteo_nombres = df["nombre_norm"].value_counts()
deptos = set(df["depto_norm"].unique())


def clasificar(r):
    n = r["nombre_norm"]
    if len(n) < 5:
        return "corto"
    if n in RIESGOSAS or n in deptos:
        return "palabra_riesgosa"
    if conteo_nombres.get(n, 0) > 1:
        return "nombre_repetido"
    return "unico"


df["ambiguedad"] = df.apply(clasificar, axis=1)
df["requiere_contexto"] = df["ambiguedad"] != "unico"
print("\nclasificación de nombres:")
for k, v in df["ambiguedad"].value_counts().items():
    print(f"  {k:20s} {v:>4}")

# ------------------------------------------------------------------ conteo
# Orden de más largo a más corto: al enmascarar lo ya encontrado, "San José del
# Palmar" se consume antes de que "Palmar" pueda buscar, y deja de haber
# coincidencias espurias por subcadena.
print("\ncontando (nombres largos primero, enmascarando lo ya emparejado) ...")
orden = df.assign(_l=df["nombre_norm"].str.len()).sort_values("_l", ascending=False).index

menciones = {i: 0 for i in df.index}
en_notas = {i: 0 for i in df.index}
men_nac = {i: 0 for i in df.index}
men_reg = {i: 0 for i in df.index}
ejemplos = {i: [] for i in df.index}

trabajo = list(textos)
for i in orden:
    r = df.loc[i]
    nombre, depto, req = r["nombre_norm"], r["depto_norm"], r["requiere_contexto"]
    pat = re.compile(rf"\b{re.escape(nombre)}\b")
    tot, nn = 0, 0
    for k, t in enumerate(trabajo):
        hits, nuevo, ini_prev = 0, [], 0
        for m in pat.finditer(t):
            if req:
                lo = max(0, m.start() - VENTANA)
                if depto not in t[lo : m.end() + VENTANA]:
                    continue
            hits += 1
            if len(ejemplos[i]) < 2:
                lo = max(0, m.start() - 70)
                ejemplos[i].append(t[lo : m.end() + 70])
            nuevo.append(t[ini_prev : m.start()])
            nuevo.append("\x00" * (m.end() - m.start()))  # enmascara
            ini_prev = m.end()
        if hits:
            nuevo.append(t[ini_prev:])
            trabajo[k] = "".join(nuevo)
            tot += hits
            nn += 1
            if es_regional[k]:
                men_reg[i] += hits
            else:
                men_nac[i] += hits
    menciones[i], en_notas[i] = tot, nn

df["menciones"] = df.index.map(menciones)
df["notas_que_lo_nombran"] = df.index.map(en_notas)
df["menciones_nacional"] = df.index.map(men_nac)
df["menciones_regional"] = df.index.map(men_reg)
if SALIDA_CSV:
    df.to_csv(PROC / "municipios_sismo.csv", index=False)
    print(f"  actualizado: {PROC / 'municipios_sismo.csv'}")
df[["divipola", "municipio", "departamento", "menciones", "ambiguedad"]].to_csv(
    PROC / f"menciones_{CORPUS.stem}.csv", index=False
)

# --------------------------------------------------- verificación a ojo
print("\n" + "=" * 88)
print("VERIFICACIÓN — contexto real de los 12 más mencionados")
print("=" * 88)
for _, r in df.nlargest(12, "menciones").iterrows():
    print(f"\n  {r['municipio']} ({r['departamento']})  {r['menciones']} menciones  [{r['ambiguedad']}]")
    for e in ejemplos[r.name][:1]:
        print(f"      …{e}…")

# ------------------------------------------------------------- hallazgos
sac = df[df["mmi_max"] >= 6]
seguro = sac[~sac["requiere_contexto"]]  # solo nombres inequívocos
sin = seguro[seguro["menciones"] == 0]

print("\n" + "=" * 88)
print(f"COBERTURA vs SACUDIDA — {len(sac)} municipios con MMI máxima ≥ 6")
print("=" * 88)
print(f"  de nombre inequívoco:          {len(seguro)}")
print(f"  de esos, nunca nombrados:      {len(sin)}  ({len(sin) / len(seguro) * 100:.0f}%)")
print(f"  población que vive en ellos:   {sin['pob_total'].sum():,.0f}")
amb = sac[sac["requiere_contexto"]]
print(f"  aparte, {len(amb)} de nombre ambiguo quedan para revisión manual")

print("\n" + "=" * 88)
print("DOS NIVELES DE AUSENCIA")
print("=" * 88)
solo_reg = seguro[(seguro["menciones_nacional"] == 0) & (seguro["menciones_regional"] > 0)]
nada = seguro[seguro["menciones"] == 0]
print(f"  cubiertos solo por prensa regional: {len(solo_reg):>4}   ({solo_reg['pob_total'].sum():>10,.0f} hab)")
print(f"  sin cobertura en ningún medio:      {len(nada):>4}   ({nada['pob_total'].sum():>10,.0f} hab)")
if len(solo_reg):
    print("\n  ejemplos de cobertura solo regional:")
    for _, r in solo_reg.nlargest(6, "indice").iterrows():
        print(
            f"    {r['municipio']:22s} {r['departamento']:18s} MMI {r['mmi_max']:.1f}  "
            f"regional {int(r['menciones_regional']):>3}  nacional 0"
        )

print("\n" + "=" * 88)
print("LOS INVISIBLES — sacudida fuerte, nombre inequívoco, cero menciones en TODO el corpus")
print("=" * 88)
cols = ["municipio", "departamento", "mmi_max", "vs30_medio", "pob_total", "def_cualitativo"]
t = sin.sort_values("indice", ascending=False).head(25)[cols].copy()
t["pob_total"] = t["pob_total"].map(lambda v: f"{v:,.0f}")
t["def_cualitativo"] = t["def_cualitativo"].map(lambda v: f"{v:.0f}%")
t["vs30_medio"] = t["vs30_medio"].map(lambda v: f"{v:.0f}")
print(t.to_string(index=False))

tot = df["menciones"].sum()
t10 = df.nlargest(10, "menciones")["menciones"].sum()
print(f"\n  10 municipios concentran {t10 / tot * 100:.0f}% de las menciones ({t10:,} de {tot:,})")
