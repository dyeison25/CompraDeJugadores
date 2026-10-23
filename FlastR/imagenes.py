import warnings
from pathlib import Path
from uuid import uuid4

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

from domain.servicio.errores import ErrorDominio


def guardar_foto(archivo):
    """Decodifica y recodifica la imagen; no confía en su extensión ni en su MIME."""
    if not archivo or not archivo.filename:
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(archivo.stream) as original:
                if original.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ErrorDominio("Sube una foto JPG, PNG o WebP.")
                if original.width * original.height > 16_000_000:
                    raise ErrorDominio("La imagen no puede superar los 16 megapíxeles.")
                foto = ImageOps.exif_transpose(original)
                foto.thumbnail((1200, 1200))
                foto = foto.convert("RGBA" if "A" in foto.getbands() or "transparency" in foto.info else "RGB")
                nombre = uuid4().hex + ".webp"
                foto.save(Path(current_app.config["UPLOAD_FOLDER"]) / nombre, "WEBP", quality=88)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ErrorDominio("El archivo no es una imagen válida. Usa JPG, PNG o WebP.") from exc
    return "/static/uploads/" + nombre


def descartar_foto_nueva(ruta):
    if ruta and ruta.startswith("/static/uploads/"):
        nombre = ruta.rsplit("/", 1)[-1]
        carpeta = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
        archivo = (carpeta / nombre).resolve()
        if archivo.parent == carpeta:
            archivo.unlink(missing_ok=True)
