"""Serie temporal de las cifras oficiales, curada y con fuente por dato.

Por qué curada y no extraída con regex: se intentó primero automático sobre el
corpus y no sirve. Un patrón no distingue "273 muertos en Colombia" de "14
muertos en Chocó", ni la fecha del hecho de cualquier fecha citada en la nota.
Producía series con muertos bajando de 281 a 14 y cortes en junio y diciembre.
Publicar eso sería peor que no publicar nada.

Cada fila de abajo es un corte oficial que se pudo verificar contra una nota
fechada y atribuida. La extracción automática se conserva como AUDITORÍA: si
encuentra en el corpus una cifra que contradice la tabla, lo avisa.

El hallazgo: entre el 12 y el 13 de agosto los desaparecidos suben de 287 a 496
y vuelven a bajar a 377, y los heridos bajan de 3.755 a 3.494. Un conteo que
oscila no se está corrigiendo con información nueva: refleja que no hay un
registro único. Es exactamente lo que denunció la Defensoría del Pueblo.
"""

import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "proc"

# fecha, hora_corte, muertos, heridos, desaparecidos, familias, personas, fuente, url
SERIE = [
    ("2026-08-10", "noche", 132, 570, None, None, None, "Infobae",
     "https://www.infobae.com/colombia/2026/08/11/mas-de-130-muertos-570-heridos-viviendas-y-vias-danadas-y-aeropuertos-cerrados-las-dramaticas-cifras-que-deja-hasta-ahora-el-terremoto-en-colombia/"),
    ("2026-08-11", "—", 188, 1677, None, None, None, "Infobae",
     "https://www.infobae.com/colombia/2026/08/11/sube-a-188-la-cifra-de-muertos-y-1677-heridos-en-quibdo-pereira-manizales-cali-armenia-y-popayan-por-el-terremoto-de-magnitud-74/"),
    ("2026-08-12", "07:30", 239, 3755, 287, None, None, "UNGRD vía El Colombiano",
     "https://www.elcolombiano.com/colombia/muertos-terremoto-en-colombia-heridos-replicas-choco-hoy-GC39809690"),
    ("2026-08-12", "tarde", 265, 3494, 496, None, 53816, "UNGRD vía El Colombiano",
     "https://www.elcolombiano.com/colombia/cifra-muertos-heridos-desaparecidos-por-terremoto-colombia-MK39884181"),
    ("2026-08-13", "mañana", 273, 3824, 377, 40753, 97515, "UNGRD vía El Tiempo",
     "https://www.eltiempo.com/amp/vida/ungrd-entrega-nuevo-balance-del-terremoto-en-colombia-40-753-familias-afectadas-y-273-muertos-3578185"),
    ("2026-08-13", "17:00", 281, 3971, 379, 44936, 102105, "UNGRD / Fiscalía vía El Tiempo",
     "https://www.eltiempo.com/colombia/otras-ciudades/balance-oficial-de-la-ungrd-tras-terremoto-de-magnitud-7-4-en-colombia-273-fallecidos-3-824-heridos-y-377-desaparecidos-3578196"),
]

COLS = ["fecha", "corte", "muertos", "heridos", "desaparecidos", "familias", "personas",
        "fuente", "url"]
df = pd.DataFrame(SERIE, columns=COLS)
df.to_csv(PROC / "serie_oficial.csv", index=False)

# Daños materiales, corte del 13 de agosto (UNGRD)
DANOS = {
    "viviendas_destruidas": 12584,
    "viviendas_averiadas": 74873,
    "edificaciones_colapsadas": 172,
    "centros_educativos_afectados": 2198,
    "centros_salud_afectados": 216,
    "municipios_afectados": 403,
    "departamentos_afectados": 14,
}
(PROC / "danos_oficiales.json").write_text(json.dumps(DANOS, indent=1), encoding="utf-8")

print("=" * 92)
print("SERIE OFICIAL (curada, cada dato con fuente)")
print("=" * 92)
print(df[COLS[:7]].to_string(index=False, na_rep="—"))

print("\n" + "=" * 92)
print("VARIACIÓN ENTRE CORTES CONSECUTIVOS")
print("=" * 92)
print(f"  {'corte':<22}{'muertos':>10}{'heridos':>10}{'desaparec.':>12}")
prev = None
for _, r in df.iterrows():
    if prev is not None:
        d = []
        for c in ["muertos", "heridos", "desaparecidos"]:
            if pd.notna(r[c]) and pd.notna(prev[c]):
                v = int(r[c] - prev[c])
                d.append(f"{v:+,}")
            else:
                d.append("—")
        print(f"  {r['fecha']} {r['corte']:<10}{d[0]:>10}{d[1]:>10}{d[2]:>12}")
    prev = r

print("\n  Los heridos BAJAN 261 entre la mañana y la tarde del 12 de agosto.")
print("  Los desaparecidos SUBEN 209 y luego BAJAN 119 en menos de 24 horas.")
print("  Un conteo que oscila en ambos sentidos no se está corrigiendo con")
print("  información nueva: indica que no hay un registro único consolidado.")

print("\n" + "=" * 92)
print("CONTRASTE CON EL MODELO PAGER DEL USGS")
print("=" * 92)
ultimo = int(df["muertos"].iloc[-1])
desap = int(df["desaparecidos"].iloc[-1])
print(f"  último conteo oficial:        {ultimo:>6,} muertos + {desap:,} desaparecidos")
print(f"  PAGER, mediana empírica:      {961:>6,} muertos")
print(f"  razón modelo / conteo:        {961 / ultimo:>6.1f}x")
print("\n  PAGER es un modelo calibrado con sismos históricos, no un conteo, y su")
print("  intervalo es ancho. La brecha NO prueba subregistro. Lo que sí muestra")
print("  es que el orden de magnitud esperado por el modelo está muy por encima")
print("  del conteo, y que la incertidumbre solo se cierra con el censo que la")
print("  Defensoría del Pueblo denunció que no existe.")

# --------------------------------------------------------------- auditoría
print("\n" + "=" * 92)
print("AUDITORÍA — cifras del corpus que superan la tabla curada")
print("=" * 92)


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


notas = json.loads((PROC / "corpus_prensa.json").read_text(encoding="utf-8"))
tope = {"muertos": int(df["muertos"].max()), "heridos": int(df["heridos"].max()),
        "desaparecidos": int(df["desaparecidos"].max())}
PATS = {
    "muertos": r"([\d][\d.,]*)\s+(?:personas\s+)?(?:muertos|fallecidos|victimas mortales)",
    "heridos": r"([\d][\d.,]*)\s+(?:personas\s+)?heridos",
    "desaparecidos": r"([\d][\d.,]*)\s+(?:personas\s+)?desaparecidos",
}
alertas = 0
for cat, pat in PATS.items():
    vistos = set()
    for n in notas:
        for m in re.finditer(pat, norm(n["texto"])):
            v = m.group(1).replace(".", "").replace(",", "")
            if not v.isdigit():
                continue
            v = int(v)
            if v > tope[cat] and v < 100_000 and v not in vistos:
                vistos.add(v)
                print(f"  {cat}: {v:,} > {tope[cat]:,} curado   [{n['medio']}]")
                alertas += 1
if not alertas:
    print("  ninguna cifra del corpus supera la tabla curada.")

print(f"\nescrito: {PROC / 'serie_oficial.csv'}  y  {PROC / 'danos_oficiales.json'}")
