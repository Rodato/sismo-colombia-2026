"""Limpia el corpus: quita el 'chrome' del sitio y descarta notas que no son del sismo.

Dos contaminaciones detectadas al verificar los conteos a mano:

  1. MENÚS DE NAVEGACIÓN. Al aplanar el HTML, la barra de secciones de cada
     portal ("...cali santander boyaca llano mas ciudades bogota opinion...")
     queda dentro del texto y se cuenta como si el artículo nombrara esas
     ciudades. Se elimina buscando el prefijo y el sufijo comunes a todos los
     artículos de un mismo dominio: la plantilla es idéntica, el artículo no.

  2. NOTAS QUE NO SON DEL SISMO. Se colaron notas de conflicto armado
     ("ataque armado en Rioblanco, Tolima") que inflaban municipios sin
     relación con el terremoto. Se exige que la nota hable del sismo de forma
     sostenida, no que lo mencione de paso.
"""

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "proc"

MIN_HITS = 6  # menciones al sismo para considerar que la nota trata del sismo
PAT_SISMO = re.compile(r"(terremoto|sismo|temblor|replica|magnitud 7|7 4|damnificad|epicentro)")
PAT_TITULO = re.compile(r"(terremoto|sismo|temblor|replica|réplica|damnificad|epicentro)", re.I)


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()


K = 12  # palabras por shingle
UMBRAL_DOC = 0.6  # presente en >=60% de las notas del dominio => es plantilla


def quitar_plantilla(grupo):
    """Elimina los bloques de texto que se repiten en casi todas las notas del dominio.

    El recorte de prefijo/sufijo no basta: los portales insertan módulos de
    'otras noticias' EN MITAD de la página. En Infobae ese widget nombraba
    Rioblanco 2 veces y El Tambo 1 vez en las 36 notas, y esos municipios
    aparecían como cubiertos sin que ninguna nota hablara de ellos.

    Se marca como plantilla toda secuencia de K palabras presente en al menos
    el 60% de las notas del dominio, y se borra de cada nota.
    """
    if len(grupo) < 4:
        return 0
    palabras = [n["texto"].split() for n in grupo]
    doc_freq = defaultdict(int)
    for w in palabras:
        for sh in {tuple(w[i : i + K]) for i in range(max(0, len(w) - K + 1))}:
            doc_freq[sh] += 1

    minimo = max(3, int(len(grupo) * UMBRAL_DOC))
    quitadas = 0
    for n, w in zip(grupo, palabras):
        tapar = [False] * len(w)
        for i in range(max(0, len(w) - K + 1)):
            if doc_freq[tuple(w[i : i + K])] >= minimo:
                for j in range(i, min(i + K, len(w))):
                    tapar[j] = True
        nuevo = [x for x, t in zip(w, tapar) if not t]
        quitadas += len(w) - len(nuevo)
        n["texto"] = " ".join(nuevo)
    return quitadas


notas = json.loads((PROC / "corpus_prensa.json").read_text(encoding="utf-8"))
print(f"corpus crudo: {len(notas)} notas")

por_dom = defaultdict(list)
for n in notas:
    por_dom[urlparse(n["url"]).netloc].append(n)

print("\nquitando plantilla por dominio (bloques repetidos) ...")
for dom, grupo in por_dom.items():
    antes = sum(len(n["texto"].split()) for n in grupo)
    q = quitar_plantilla(grupo)
    if q:
        print(f"  {dom:34s} -{q:>6} palabras de {antes:>6}  ({len(grupo)} notas)")
    else:
        print(f"  {dom:34s} {'(pocas notas para detectar plantilla)':>40}  ({len(grupo)} notas)")

print("\nfiltrando notas que no tratan del sismo ...")
limpio, fuera = [], []
for n in notas:
    t = norm(n["texto"])
    hits = len(PAT_SISMO.findall(t))
    tiene_titulo = bool(PAT_TITULO.search(n.get("titulo", "")))
    if len(t) < 400:
        fuera.append((n, "texto corto tras limpiar"))
    elif tiene_titulo or hits >= MIN_HITS:
        n["texto"] = n["texto"]
        n["hits_sismo"] = hits
        limpio.append(n)
    else:
        fuera.append((n, f"solo {hits} menciones al sismo"))

print(f"  conservadas: {len(limpio)}")
print(f"  descartadas: {len(fuera)}")
for n, motivo in fuera[:12]:
    print(f"    [{motivo:28s}] {n['titulo'][:64]}")

por_medio = defaultdict(int)
for n in limpio:
    por_medio[n["medio"]] += 1
print("\nnotas por medio:")
for m, c in sorted(por_medio.items(), key=lambda x: -x[1]):
    print(f"  {m:26s} {c:>3}")

salida = PROC / "corpus_limpio.json"
salida.write_text(json.dumps(limpio, ensure_ascii=False), encoding="utf-8")
print(f"\nescrito: {salida}")
print(f"caracteres: {sum(len(n['texto']) for n in limpio):,}")
