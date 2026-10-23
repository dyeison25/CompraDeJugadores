"""Descarga fotos y fuentes para que la interfaz funcione sin CDN en tiempo de ejecución."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "FlastR" / "static"
RECURSOS = {
    **{f"img/jugadores/{nombre}.png": ("https://a.espncdn.com/i/headshots/soccer/players/full/45843.png" if nombre == "messi" else f"https://cdn.futbin.com/content/fifa25/img/players/{identificador}.png")
       for nombre, identificador in [
           ("mbappe", 231747), ("haaland", 239085), ("bellingham", 252371), ("diaz", 241084),
           ("messi", 158023), ("vandijk", 203376), ("alisson", 212831), ("pedri", 251854)
       ]},
    "fonts/Manrope.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/Manrope%5Bwght%5D.ttf",
    "fonts/BarlowCondensed-ExtraBold.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/barlowcondensed/BarlowCondensed-ExtraBold.ttf",
    "fonts/Manrope-OFL.txt": "https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/OFL.txt",
    "fonts/BarlowCondensed-OFL.txt": "https://raw.githubusercontent.com/google/fonts/main/ofl/barlowcondensed/OFL.txt",
}


def descargar(item):
    relative, url = item
    destino = (STATIC / relative).resolve()
    if not destino.is_relative_to(STATIC.resolve()):
        raise ValueError("Ruta inválida")
    if destino.exists() and destino.stat().st_size > 100:
        return relative + ": ya existe"
    with urlopen(Request(url, headers={"User-Agent": "Fichaje-Academic-Demo/1.0"}), timeout=45) as respuesta:
        contenido = respuesta.read(5 * 1024 * 1024)
    if relative.endswith(".png") and not contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("El servidor no devolvió una imagen PNG: " + relative)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    return f"{relative}: {len(contenido)} bytes"


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=4) as pool:
        for resultado in pool.map(descargar, RECURSOS.items()):
            print(resultado)
