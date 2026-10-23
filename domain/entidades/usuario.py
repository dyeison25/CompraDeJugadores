from dataclasses import dataclass


@dataclass(frozen=True)
class Usuario:
    id: int
    nombre: str
    email: str
    password_hash: str
    rol: str

    @property
    def es_admin(self) -> bool:
        return self.rol == "admin"
