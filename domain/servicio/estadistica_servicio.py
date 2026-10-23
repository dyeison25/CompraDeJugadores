from domain.repositorios import JugadorRepositorio, CompraRepositorio
from .autenticacion_servicio import AutenticacionServicio


class EstadisticaServicio:
    """Calcula indicadores respetando los permisos y la privacidad del historial."""

    def __init__(self, jugadores: JugadorRepositorio, compras: CompraRepositorio,
                 autenticacion: AutenticacionServicio):
        self.jugadores = jugadores
        self.compras = compras
        self.auth = autenticacion

    def resumen_admin(self, admin_id: int) -> dict:
        self.auth.exigir_rol(admin_id, "admin")
        disponibles = self.jugadores.listar()
        return {
            "disponibles": len(disponibles),
            "valor": sum(jugador.precio_centimos for jugador in disponibles),
            "resumen": self.compras.resumen(),
        }

    def resumen_usuario(self, usuario_id: int) -> dict:
        self.auth.exigir_rol(usuario_id, "usuario")
        compras = self.compras.historial(usuario_id)
        return {"compras": compras, "volumen": sum(compra.precio_centimos for compra in compras)}
