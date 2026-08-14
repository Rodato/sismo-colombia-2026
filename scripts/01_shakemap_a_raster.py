"""Convierte el grid.xml del ShakeMap del USGS en un GeoTIFF multibanda.

El grid.xml trae 685x683 celdas (~1 km) con 10 campos por celda. Nos quedamos
con los cuatro que importan para el análisis:

  MMI   intensidad de Mercalli — lo que la gente sintió y lo que rompe casas
  PGA   aceleración pico (%g)
  PGV   velocidad pico (cm/s)
  SVEL  Vs30, velocidad de onda de corte del suelo (m/s) — suelo blando = amplificación

El orden del grid es row-major desde la esquina noroeste (lat_max, lon_min),
que es la orientación estándar de un ráster, así que el reshape es directo.
"""

import io
import re
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "proc"
PROC.mkdir(parents=True, exist_ok=True)

BANDAS = ["MMI", "PGA", "PGV", "SVEL"]

print("leyendo grid.xml ...")
texto = (RAW / "shakemap_grid.xml").read_text(encoding="utf-8")

# --- metadatos del grid -------------------------------------------------
spec = re.search(r"<grid_specification([^/]*)/>", texto).group(1)
attrs = dict(re.findall(r'(\w+)="([^"]+)"', spec))
lon_min, lon_max = float(attrs["lon_min"]), float(attrs["lon_max"])
lat_min, lat_max = float(attrs["lat_min"]), float(attrs["lat_max"])
nlon, nlat = int(attrs["nlon"]), int(attrs["nlat"])

# orden real de los campos según los <grid_field>
campos = [m[1] for m in re.findall(r'<grid_field index="(\d+)" name="(\w+)"', texto)]
print(f"  grid {nlon}x{nlat}  lon[{lon_min}, {lon_max}]  lat[{lat_min}, {lat_max}]")
print(f"  campos: {campos}")

# --- datos --------------------------------------------------------------
i0 = texto.index("<grid_data>") + len("<grid_data>")
i1 = texto.index("</grid_data>")
print("parseando celdas ...")
datos = np.loadtxt(io.StringIO(texto[i0:i1]), dtype=np.float32)
del texto

esperado = nlon * nlat
if datos.shape[0] != esperado:
    raise SystemExit(f"ABORTA: {datos.shape[0]} celdas, esperaba {esperado}")
print(f"  {datos.shape[0]:,} celdas x {datos.shape[1]} campos")

# verifica la orientación asumida antes de confiar en el reshape
if not (
    np.isclose(datos[0, 0], lon_min, atol=1e-3) and np.isclose(datos[0, 1], lat_max, atol=1e-3)
):
    raise SystemExit(
        f"ABORTA: la primera celda es ({datos[0, 0]}, {datos[0, 1]}), "
        f"esperaba la esquina NO ({lon_min}, {lat_max}). El orden del grid no es el asumido."
    )

dx = (lon_max - lon_min) / (nlon - 1)
dy = (lat_max - lat_min) / (nlat - 1)
transform = from_origin(lon_min - dx / 2, lat_max + dy / 2, dx, dy)

perfil = dict(
    driver="GTiff",
    height=nlat,
    width=nlon,
    count=len(BANDAS),
    dtype="float32",
    crs="EPSG:4326",
    transform=transform,
    compress="deflate",
    nodata=np.nan,
)

salida = PROC / "shakemap.tif"
with rasterio.open(salida, "w", **perfil) as dst:
    for i, nombre in enumerate(BANDAS, start=1):
        arr = datos[:, campos.index(nombre)].reshape(nlat, nlon)
        dst.write(arr, i)
        dst.set_band_description(i, nombre)
        print(f"  banda {i} {nombre:5s} min={arr.min():8.2f}  max={arr.max():8.2f}")

print(f"\nescrito: {salida}  ({salida.stat().st_size / 1e6:.1f} MB)")

# --- chequeo de sanidad contra las cifras publicadas por el USGS --------
mmi = datos[:, campos.index("MMI")]
print("\nreparto de celdas por intensidad MMI:")
for lo in range(3, 10):
    n = int(((mmi >= lo) & (mmi < lo + 1)).sum())
    if n:
        print(f"  MMI {lo}–{lo + 1}: {n:>7,} celdas  ({n / len(mmi) * 100:5.1f}%)")
print(f"  MMI máxima en el grid: {mmi.max():.2f}")
