from dataclasses import dataclass
from decimal import Decimal


POSICIONES = ("Delantero", "Centrocampista", "Defensa", "Portero")


@dataclass(frozen=True)
class Jugador:
    id: int
    nombre: str
    equipo: str
    nacionalidad: str
    edad: int
    posicion: str
    precio_centimos: int
    foto: str
    dorsal: int
    descripcion: str
    estado: str
    destacado: int
    version: int

    @property
    def precio(self) -> Decimal:
        return Decimal(self.precio_centimos) / 100
