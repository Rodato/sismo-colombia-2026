# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Pieza de periodismo de datos sobre el terremoto de magnitud 7,4 del 10 de agosto de 2026
(epicentro: San José del Palmar, Chocó). Cruza el ShakeMap del USGS con población y
vulnerabilidad de vivienda del DANE, y lo publica como mapa interactivo.

- Producción: https://sismo-colombia-2026.vercel.app (scope Vercel `rodatos-projects`)
- Repo público: `github.com/Rodato/sismo-colombia-2026`

## Comandos

```bash
# Python: venv con 3.14 (NO usar el 3.9 del sistema)
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# El pipeline COMPLETO, en este orden (ver "Dependencias entre scripts")
.venv/bin/python scripts/01_shakemap_a_raster.py
.venv/bin/python scripts/02_cruce_municipal.py
.venv/bin/python scripts/03_corpus_prensa.py       # red, lento (~200 notas)
.venv/bin/python scripts/03b_limpiar_corpus.py
.venv/bin/python scripts/04_menciones.py
.venv/bin/python scripts/05_suelo_fallido.py
.venv/bin/python scripts/06_serie_cifras.py
.venv/bin/python scripts/06b_perdidas_oficiales.py
.venv/bin/python scripts/07_export_web.py

# Web
cd web && npm install
npm run dev            # http://localhost:3000
npm run build          # prerender estático; falla si resumen.json tiene NaN
npx tsc --noEmit
npm run lint
```

No hay tests. La verificación de este repo es distinta y está descrita abajo en
"Cómo se valida aquí".

### Capturas de pantalla

La extensión Claude-in-Chrome **no está conectada** en esta máquina; las herramientas
`mcp__claude-in-chrome__*` fallan. Usar Chrome headless:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
  --hide-scrollbars --virtual-time-budget=15000 --window-size=1200,4600 \
  --screenshot=/tmp/full.png "http://localhost:3000"
```

`--force-dark-mode` NO sirve para probar el modo oscuro: aplica el oscurecido automático
de Chrome, no la `prefers-color-scheme` del CSS. Para el modo oscuro, auditar que cada
token esté definido en los tres ámbitos de `globals.css` (`:root`, la media query y
`:root[data-theme="dark"]`).

## Arquitectura

### La columna vertebral es un CSV que los scripts van mutando

`data/proc/municipios_sismo.csv` tiene una fila por municipio dentro de la huella del
ShakeMap (682) y **cada script le agrega columnas**. Esto no se ve leyendo un script solo:

| Script | Lee | Escribe |
|---|---|---|
| `01` | `data/raw/shakemap_grid.xml` | `data/proc/shakemap.tif` (MMI, PGA, PGV, SVEL) |
| `02` | shakemap.tif + MGN + xlsx DANE | **crea** `municipios_sismo.csv` + `.gpkg` |
| `03` | web (medios) | `corpus_prensa.json` |
| `03b` | corpus_prensa.json | `corpus_limpio.json` |
| `04` | corpus_limpio.json + csv | **añade** `menciones*` al csv |
| `05` | csv + gpkg + tif de ground-failure | `suelo_fallido.csv`, reescribe el `.gpkg` |
| `06` | (tabla curada en el código) | `serie_oficial.csv`, `danos_oficiales.json` |
| `06b` | (tabla curada en el código) + csv | `perdidas_{municipales,departamentales}.csv`, **añade** 8 columnas al csv |
| `07` | csv + suelo_fallido + serie + pérdidas | `web/public/data/*` |

**Dependencias entre scripts.** `02` recrea el CSV desde cero, así que **borra las columnas
que agregan `04` y `06b`**. Si tocás `02`, hay que re-correr `04 → 05 → 06b → 07`. `03` solo
hace falta si querés refrescar el corpus de prensa; `03b` y `04` trabajan sobre el JSON ya
guardado. `06b` va después de `06` y **antes de `07`**: muta el CSV igual que `04`, y `07`
espera encontrar ahí `cobertura_dato`, `muertos_rep` y `muertos_100k`.

`data/raw/` (~230 MB) no está versionado. Los scripts lo descargan, pero **verificar el
tamaño de `shakemap_grid.xml` contra los 28.513.196 bytes esperados**: ya llegó truncado una
vez y el parser aborta sin `</grid_data>`.

### El web app solo consume `web/public/data/`

`web/src/app/page.tsx` es un Server Component que lee `resumen.json` del filesystem **en
build time**; el mapa (`components/Mapa.tsx`, cliente) hace `fetch` del GeoJSON. No hay API
routes ni base de datos: cambiar datos = re-correr `07` + `npm run build`.

`web/src/lib/capas.ts` define las 6 capas del mapa (campo, cortes, formato, si es invertida).
Agregar una capa es agregar una entrada ahí; no hay que tocar el componente.

El mapa es **SVG con d3-geo, sin basemap ni tiles**: los polígonos municipales son el mapa.
Eso evita API keys de terceros. No introducir MapLibre/Leaflet sin una razón fuerte.

Hay un `web/CLAUDE.md` que importa `web/AGENTS.md`; los genera `next dev` y advierten que
**Next.js 16 tiene breaking changes** (docs en `web/node_modules/next/dist/docs/`). No
borrarlos: `next dev` los vuelve a crear.

## Trampas que ya se pagaron

No revertir ninguna de estas sin entender por qué está así.

**d3-geo quiere el anillo exterior en sentido HORARIO**, al contrario de RFC 7946. Con el
sentido equivocado interpreta cada polígono como su complemento (el planeta menos el
municipio), `geoBounds` devuelve `[[-180,-90],[180,90]]` y `fitSize` colapsa el país a media
docena de píxeles — se ve como un rectángulo azul sólido. Lo arregla
`orient(g, sign=-1.0)` en `07_export_web.py`. Verificar empíricamente con `geoBounds`, no
razonando desde la especificación.

**`cortes` debe tener exactamente `RAMPA.length - 1` entradas** (6 para 7 pasos). N cortes
producen N+1 cubetas; con un corte de más, el índice se sale de la rampa, el `fill` queda
`undefined` y el SVG pinta el municipio **de negro** — justo los de intensidad más alta.
`paso()` tiene un clamp de seguridad, pero eso enmascara el bug en vez de arreglarlo.

**Vulnerabilidad = déficit habitacional TOTAL, nunca solo el cualitativo.** En el Chocó la
vivienda es tan precaria que el DANE la clasifica como déficit *cuantitativo* (reemplazo) y
no cualitativo (mejora): Alto Baudó aparecía con 3,0% cuando su déficit real es 99,6%. Usar
el cualitativo invisibiliza justo a los más precarios e invierte la conclusión (Chocó 90,1%
vs Caldas 46,2%, no la paridad que sugiere el cualitativo).

**Comparar exposición contra el USGS exige la convención de PAGER**, que redondea al entero:
la banda VIII cubre 7,5–8,5, no 8,0+. Sin eso el contraste no es válido. Nuestro reparto de
población es **uniforme por área municipal**, así que queda sistemáticamente por debajo del
USGS (0,8x en MMI VI+, 0,4x en VIII+), que usa grilla Landscan. Coincidir en orden de
magnitud es la validación, no la igualdad.

**Contar nombres de municipios en texto libre falla de cuatro maneras**, todas resueltas en
`04_menciones.py`: subcadena ("Palmar" dentro de "San José del Palmar" → 82 falsos), palabra
corriente ("Socorro" por "organismos de socorro", "Colombia" por el país), homónimos
(Candelaria en Valle y Atlántico), y apellidos (Beltrán, Alvarado). Se corrige recorriendo
los nombres de más largo a más corto y **enmascarando** lo ya emparejado, más lista de
nombres riesgosos que exigen el departamento cerca.

**El "chrome" de los portales contamina los conteos.** Los widgets de "otras noticias" viven
en mitad del HTML, así que recortar prefijo/sufijo no basta: Infobae nombraba Rioblanco 2
veces en sus 36 notas. `03b` elimina los bloques de 12 palabras presentes en ≥60% de las
notas de un mismo dominio. Al cambiar ese umbral, verificar qué municipios pasan de >0 a 0
menciones y revisarlos a mano — la limpieza puede crear invisibles falsos.

## Cómo se valida aquí

No hay suite de tests; la corrección se sostiene con tres cosas:

1. **Contraste contra cifras publicadas.** `02` imprime nuestra exposición junto a la de
   PAGER; `06` audita el corpus contra la tabla curada y avisa de cifras que la superan
   (las de 5.000/10.000/20.000 muertos son comparaciones históricas: Armero, Armenia 1999).
2. **Verificación a ojo del contexto.** `04` imprime fragmentos reales de los 12 municipios
   más mencionados. Ahí se cazaron todos los falsos positivos. Mirarlos siempre.
3. **Validación de la coherencia interna.** El índice de exposición ubica a **Pereira #1 sin
   usar ningún dato de víctimas**. Si un cambio rompe eso, sospechar del cambio.

Al tocar gráficas o color, cargar la skill `dataviz` primero. La paleta es la de referencia
validada (rampa secuencial azul para magnitud; slots categóricos 1–3 para series). **No usar
la escala arcoíris del ShakeMap del USGS**: no es segura para daltonismo. El validador está
en la skill: `node scripts/validate_palette.js "<hex,…>" --mode light --pairs all`.

## Límites editoriales de la pieza

Son restricciones de qué se puede afirmar, no preferencias de estilo. Cruzarlas hace la
pieza desmentible.

- **El corpus de prensa demuestra presencia, no ausencia.** Son 199 notas de 11 medios. Se
  verificó que municipios con cero menciones (Chinchiná, Candelaria) **sí** tenían cobertura
  regional. La afirmación publicable es *concentración del relato* (10 municipios = 57% de
  las menciones), nunca "nadie los cubrió". La ficha del mapa y la sección "Cómo se hizo"
  dicen esto explícitamente.
- **El índice es de tamizaje, no un modelo de pérdidas** ni una estimación de víctimas.
- **PAGER (mediana 961 muertos) es un modelo, no un conteo.** La brecha contra los 281
  oficiales no prueba subregistro; acota incertidumbre.
- **La serie de cifras oficiales se cura a mano, con medio y URL por dato.** La extracción
  por regex confundía totales nacionales con departamentales ("14 muertos" era Chocó) y
  fechaba mal (cortes en junio y diciembre). El regex quedó solo como auditoría en `06`.
- **La capa de pérdidas muestra dónde se PUEDE saber, no dónde hubo pérdidas.** Solo 5 de
  682 municipios tienen cifra propia, y los 5 son capitales porque la única fuente municipal
  es Asocapitales, la asociación de ciudades capitales. Que un municipio salga claro en esa
  capa no dice nada sobre su daño: dice que nadie publicó el dato. Dosquebradas —#5 del
  índice, 246.388 habitantes, MMI 7,9— es el caso que lo prueba. **No rellenar los 677
  restantes con un modelo de fragilidad**: la pieza declara explícito que el índice no es un
  modelo de pérdidas, y cruzarlo la hace desmentible.
- **Los `*_rep` en null no son cero.** Armenia reportó cero muertos; los otros 677 municipios
  no reportaron nada. `07` los deja en `null` a propósito y la ficha del mapa solo muestra
  las filas de pérdidas cuando `cobertura_dato == 2`. Rellenar con `0` borra el hallazgo.

## Convenciones del repo

- Código y comentarios en español; los comentarios explican **por qué**, sobre todo en las
  trampas de arriba.
- Atribución: **Daniel Otero / danielotero.dev** (proyecto personal, no Estudio Plural).
- Los commits deben ir firmados con `otero.r.daniel@gmail.com` o Vercel rechaza el
  git-deploy. Ya está configurado en el repo (`git config user.email`).
- Deploy: `cd web && vercel deploy --prod --yes` (scope `rodatos-projects`).

## Dónde NO buscar el dato municipal de pérdidas

Ya se recorrieron estas rutas y están cerradas. No repetirlas sin una razón nueva.

- **El tablero de la UNGRD existió** con fallecidos, heridos, desaparecidos y viviendas
  desagregados por municipio. Lo restringieron 42 minutos después de que el periodista Ronny
  Suárez Celemín lo hiciera público; el Sindicato Colombiano de Periodistas lo denunció
  citando la Ley 1712 de 2014.
- **datos.gov.co no sirve para 2026.** Los datasets de emergencias de la UNGRD
  (`wwkg-r6te`, `4fd8-ptcr`, `4t8v-ywmw`, `rgre-6ak4`) tienen el esquema exacto que haría
  falta, pero el más reciente termina en 2024. Verificado por API el 14 ago 2026:
  `wwkg-r6te` devuelve 25.857 filas entre 2019-01-01 y 2022-12-31.
- **Wayback Machine** está bloqueado desde este entorno (`curl` sale por timeout y WebFetch
  rechaza `web.archive.org`). Si se reintenta, hacerlo desde una máquina con red abierta.

Lo que sí quedó: 5 municipios vía Asocapitales (Consolidado No. 22) y 13 departamentos vía
UNGRD. Están en `data/proc/perdidas_*.csv`, cada fila con fuente, URL y corte.

## Pendiente conocido

Las **réplicas** no están en la pieza. El USGS solo cataloga 4 eventos de la secuencia
(M 7.4 y réplicas M 4.2–5.0) porque no indexa sismos pequeños fuera de EE.UU.; el SGC
reportó 96. Haría falta el catálogo del Servicio Geológico Colombiano
(`sismo.sgc.gov.co`), que responde pero cuyo endpoint de descarga no se exploró.
