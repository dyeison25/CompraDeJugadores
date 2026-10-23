from datetime import datetime, timezone
from domain.entidades import Compra
from domain.repositorios import CompraRepositorio
from .errores import ErrorDominio


class CompraServicio:
    def __init__(self, compras: CompraRepositorio, autenticacion):
        self.compras = compras
        self.auth = autenticacion

    def comprar(self, usuario_id, jugador_id, version_esperada):
        self.auth.exigir_rol(usuario_id, "usuario")

        def preparar(jugador):
            # El repositorio invoca estas reglas con la lectura protegida por la transacción.
            if jugador.estado != "disponible":
                raise ErrorDominio("Otro usuario ya fichó a este jugador.")
            if jugador.version != version_esperada:
                raise ErrorDominio("La ficha o el precio cambiaron. Revisa los datos y confirma de nuevo.")
            return Compra(
                id=0, usuario_id=usuario_id, jugador_id=jugador.id,
                precio_centimos=jugador.precio_centimos,
                fecha=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                jugador_nombre=jugador.nombre, equipo=jugador.equipo, foto=jugador.foto,
            )

        return self.compras.registrar_atomica(jugador_id, preparar)

    def historial(self, usuario_id):
        self.auth.exigir_rol(usuario_id, "usuario")
        return self.compras.historial(usuario_id)

    def resumen(self, admin_id):
        self.auth.exigir_rol(admin_id, "admin")
        return self.compras.resumen()
