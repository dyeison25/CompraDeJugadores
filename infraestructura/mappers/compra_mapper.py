from domain.entidades import Compra
from .base import Mapper


class CompraMapper(Mapper):
    entidad = Compra
    enteros = ("id", "usuario_id", "jugador_id", "precio_centimos")

    @classmethod
    def desde_datos(cls, datos, documento_id=None):
        compra = super().desde_datos(datos, documento_id)
        if compra.precio_centimos <= 0:
            raise ValueError("El precio de la compra debe ser positivo.")
        return compra
