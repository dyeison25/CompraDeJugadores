from domain.entidades import Jugador
from .base import Mapper


class JugadorMapper(Mapper):
    entidad = Jugador
    enteros = ("id", "edad", "precio_centimos", "dorsal", "destacado", "version")

    @classmethod
    def desde_datos(cls, datos, documento_id=None):
        jugador = super().desde_datos(datos, documento_id)
        if jugador.estado not in ("disponible", "vendido") or jugador.precio_centimos <= 0 or jugador.version < 1:
            raise ValueError("Estado, precio o versión del jugador inválidos.")
        return jugador
