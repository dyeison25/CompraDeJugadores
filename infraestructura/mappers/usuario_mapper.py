from domain.entidades import Usuario
from .base import Mapper


class UsuarioMapper(Mapper):
    entidad = Usuario
    enteros = ("id",)

    @classmethod
    def desde_datos(cls, datos, documento_id=None):
        usuario = super().desde_datos(datos, documento_id)
        if usuario.rol not in ("admin", "usuario"):
            raise ValueError("Rol de usuario no reconocido.")
        if usuario.email != usuario.email.strip().lower():
            raise ValueError("El correo almacenado debe estar normalizado.")
        return usuario
