# El sismo que no se contó

Análisis de datos del terremoto de magnitud 7,4 con epicentro en San José del Palmar
(Chocó, Colombia), el 10 de agosto de 2026.

La pregunta de partida fue qué no se ha informado. La respuesta que sostienen los
datos: **208 municipios recibieron sacudida de nivel de daño (MMI ≥ VI) y en ellos
viven 11,1 millones de personas, pero diez municipios concentran el 57% de las
menciones** en el corpus de prensa analizado.

## Hallazgos

1. **El suelo pesa más que la distancia.** El epicentro estuvo en el Chocó y la ciudad
   más golpeada fue Pereira, a más de 100 km. Hay un cinturón de suelo blando en el
   norte del Cauca y el valle del río Cauca (Villa Rica 225 m/s, Puerto Tejada 226,
   Candelaria 232) que recibió sacudida de daño lejos del epicentro. La probabilidad
   de licuefacción, de un modelo independiente, lo confirma.

2. **El corredor fluvial del Chocó acumula todo a la vez.** Los municipios ribereños
   del Atrato, el San Juan y el Baudó suman sacudida fuerte, la mayor superficie con
   licuefacción probable del país y un parque de vivienda que el censo clasifica casi
   entero en déficit (Medio Baudó 99,6%, Bojayá 97,7%).

3. **El conteo oficial no converge, oscila.** Entre el 12 y el 13 de agosto los
   desaparecidos suben de 287 a 496 y bajan a 377; los heridos bajan de 3.755 a 3.494.
   Un conteo que se mueve en ambos sentidos no se corrige con información nueva:
   refleja que no hay registro único, que es lo que denunció la Defensoría del Pueblo.

## Reproducir

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/01_shakemap_a_raster.py    # ShakeMap -> GeoTIFF
.venv/bin/python scripts/02_cruce_municipal.py      # sacudida x población x vivienda
.venv/bin/python scripts/03_corpus_prensa.py        # corpus de prensa
.venv/bin/python scripts/03b_limpiar_corpus.py      # quita plantilla de los portales
.venv/bin/python scripts/04_menciones.py            # menciones por municipio
.venv/bin/python scripts/05_suelo_fallido.py        # deslizamientos y licuefacción
.venv/bin/python scripts/06_serie_cifras.py         # serie oficial curada
.venv/bin/python scripts/07_export_web.py           # payload del mapa
cd web && npm install && npm run dev
```

Los datos crudos (~230 MB) no están versionados; los scripts los descargan.

## Fuentes

| Qué | Fuente |
|---|---|
| Intensidad, PGA, Vs30 | USGS ShakeMap v6, evento `us6000tjl2` |
| Deslizamientos | Nowicki Jessee y otros (2018), USGS ground-failure |
| Licuefacción | Zhu y otros (2017), USGS ground-failure |
| Geometría municipal | DANE, Marco Geoestadístico Nacional 2023 |
| Población | DANE, proyecciones municipales 2018–2042 (corte 2026) |
| Vulnerabilidad de vivienda | DANE, déficit habitacional CNPV 2018 |
| Cifras oficiales | UNGRD, vía prensa fechada y atribuida |

## Límites que conviene tener presentes

- **El índice de exposición es de tamizaje, no un modelo de pérdidas.** Combina
  sacudida, población y vulnerabilidad para priorizar dónde mirar. Su validación es
  que ubica a Pereira primero sin usar ningún dato de víctimas.
- **La población se reparte de forma uniforme por área municipal.** Subestima la
  concentración urbana. Por eso las cifras de exposición quedan por debajo de las del
  USGS (0,8x en MMI VI+, 0,4x en MMI VIII+), que usa grilla de población.
- **El conteo de prensa demuestra presencia, no ausencia.** El corpus son 199 notas de
  11 medios. Que un municipio no aparezca significa que está fuera de ese relato, no
  que ningún medio lo haya cubierto: se verificó que varios sin menciones sí tenían
  cobertura regional. La afirmación es sobre concentración, no sobre silencio.
- **La serie oficial está curada a mano.** La extracción automática confundía totales
  nacionales con conteos departamentales y fechaba mal; cada punto de la tabla tiene
  medio y URL.

## Licencia

Datos de fuentes públicas (USGS, DANE, UNGRD). Análisis y visualización de
[Daniel Otero](https://danielotero.dev).
