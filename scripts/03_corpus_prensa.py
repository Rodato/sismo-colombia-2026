"""Construye un corpus de notas de prensa sobre el sismo y guarda su texto.

Parte de páginas de sección/etiqueta de medios colombianos, saca los enlaces a
notas del sismo, y baja el texto de cada una.

Incluye medios REGIONALES a propósito. Si solo midiéramos cobertura nacional,
un municipio podría parecer "invisible" cuando en realidad su prensa local sí
lo cubrió — y eso sería un hallazgo falso.
"""

import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "proc"
PROC.mkdir(parents=True, exist_ok=True)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HDRS = {"User-Agent": UA, "Accept-Language": "es-CO,es;q=0.9"}

SEMILLAS = [
    # nacionales
    ("El Tiempo", "https://www.eltiempo.com/noticias/terremoto"),
    ("El Tiempo", "https://www.eltiempo.com/noticias/sismo"),
    ("Semana", "https://www.semana.com/noticias/terremoto/"),
    ("Blu Radio", "https://www.bluradio.com/noticias/terremoto"),
    ("La FM", "https://www.lafm.com.co/tags/terremoto"),
    ("La FM", "https://www.lafm.com.co/tags/sismo"),
    ("Infobae", "https://www.infobae.com/colombia/"),
    ("El Universal", "https://www.eluniversal.com.co/tags/terremoto/"),
    ("El Espectador", "https://www.elespectador.com/tag/terremoto/"),
    ("El Colombiano", "https://www.elcolombiano.com/tags/terremoto"),
    ("Caracol Radio", "https://caracol.com.co/tema/terremoto/"),
    ("W Radio", "https://www.wradio.com.co/tema/terremoto/"),
    ("RCN Radio", "https://www.rcnradio.com/tag/terremoto"),
    ("Noticias Caracol", "https://www.noticiascaracol.com/tags/terremoto"),
    ("Pulzo", "https://www.pulzo.com/tags/terremoto"),
    ("Infobae", "https://www.infobae.com/tag/terremoto-en-colombia/"),
    # regionales — clave para no inventar "invisibilidad"
    ("El País (Cali)", "https://www.elpais.com.co/tags/terremoto"),
    ("La Patria (Manizales)", "https://www.lapatria.com/tags/terremoto"),
    ("El Diario (Pereira)", "https://www.eldiario.com.co/tag/terremoto/"),
    ("La Cronica (Quindio)", "https://www.cronicadelquindio.com/tag/terremoto"),
    ("Chocó7dias", "https://choco7dias.com/"),
    ("Las2orillas", "https://www.las2orillas.co/?s=terremoto"),
    ("El Nuevo Dia (Tolima)", "https://www.elnuevodia.com.co/nuevodia/buscar?searchword=terremoto"),
    ("Q'hubo Pereira", "https://qhuboperiodico.com/?s=terremoto"),
]

PAT_NOTA = re.compile(r"(terremoto|sismo|temblor|replica|réplica|damnificad)", re.I)
# Descarta enlaces que no son notas: secciones, tags, autores, media.
PAT_NO = re.compile(
    r"(/tags?/|/tema/|/temas/|/autor|/author|/buscar|\?s=|/video/?$|\.(jpg|png|gif|mp4|pdf)$)", re.I
)


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def limpiar_html(html):
    html = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<!--.*?-->", " ", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;?", " ", html)
    html = re.sub(r"&[a-z]+;", " ", html)
    return re.sub(r"\s+", " ", html).strip()


def get(url, timeout=25):
    try:
        r = requests.get(url, headers=HDRS, timeout=timeout)
        if r.status_code == 200 and len(r.content) > 500:
            return r.text
    except Exception:
        pass
    return None


# La cobertura regional es la que decide si un municipio está de verdad sin
# contar o solo ausente del relato nacional. Paginamos las secciones que lo
# permiten para no subrepresentarla.
PAGINAS = 6


def expandir(seed):
    yield seed
    unión = "&" if "?" in seed else "?"
    for n in range(1, PAGINAS):
        yield f"{seed}{unión}page={n}"
        yield f"{seed.rstrip('/')}/page/{n}"


SEMILLAS = [(m, u) for m, s in SEMILLAS for u in expandir(s)]

# ------------------------------------------------------- 1. descubrir URLs
print(f"descubriendo notas desde {len(SEMILLAS)} páginas de sección ...")
urls = {}
vistos_medio = {}
for medio, seed in SEMILLAS:
    html = get(seed)
    if not html:
        continue
    base = f"{urlparse(seed).scheme}://{urlparse(seed).netloc}"
    hall = 0
    for m in re.finditer(r'href="([^"]+)"', html):
        href = m.group(1)
        if not PAT_NOTA.search(href) or PAT_NO.search(href):
            continue
        full = urljoin(base, href.split("#")[0])
        if urlparse(full).netloc != urlparse(seed).netloc:
            continue
        if len(urlparse(full).path) < 25:  # rutas muy cortas no son notas
            continue
        if full not in urls:
            urls[full] = medio
            hall += 1
    if hall:
        vistos_medio[medio] = vistos_medio.get(medio, 0) + hall

for medio, c in sorted(vistos_medio.items(), key=lambda x: -x[1]):
    print(f"  {medio:26s} {c:>4} notas")
print(f"\ntotal notas únicas descubiertas: {len(urls)}")

# ------------------------------------------------------- 2. bajar el texto
print("bajando texto de cada nota ...")


def bajar(item):
    url, medio = item
    html = get(url)
    if not html:
        return None
    texto = limpiar_html(html)
    if len(texto) < 400:
        return None
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    return dict(
        url=url,
        medio=medio,
        titulo=limpiar_html(m.group(1)) if m else "",
        texto=texto,
        n_chars=len(texto),
    )


with ThreadPoolExecutor(max_workers=8) as ex:
    notas = [n for n in ex.map(bajar, urls.items()) if n]

# Filtra a las que realmente hablan del sismo (no cualquier nota del portal).
notas = [n for n in notas if len(PAT_NOTA.findall(norm(n["texto"][:6000]))) >= 2]

print(f"  notas con texto útil: {len(notas)}")
por_medio = {}
for n in notas:
    por_medio[n["medio"]] = por_medio.get(n["medio"], 0) + 1
for medio, c in sorted(por_medio.items(), key=lambda x: -x[1]):
    print(f"    {medio:26s} {c:>3}")

salida = PROC / "corpus_prensa.json"
salida.write_text(json.dumps(notas, ensure_ascii=False), encoding="utf-8")
print(f"\nescrito: {salida}  ({salida.stat().st_size / 1e6:.1f} MB)")
print(f"caracteres totales de corpus: {sum(n['n_chars'] for n in notas):,}")
