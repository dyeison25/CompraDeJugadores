from dataclasses import dataclass


@dataclass(frozen=True)
class Compra:
    id: int
    usuario_id: int
    jugador_id: int
    precio_centimos: int
    fecha: str
    jugador_nombre: str
    equipo: str
    foto: str
