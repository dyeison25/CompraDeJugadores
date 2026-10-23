from dataclasses import replace

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError

from domain.servicio.errores import ErrorDominio, NoEncontrado
from infraestructura.mappers import JugadorMapper
from .mappers import UsuarioMapperORM, JugadorMapperORM, CompraMapperORM
from .modelos import UsuarioModelo, JugadorModelo, CompraModelo


class UsuarioRepositorioORM:
    def __init__(self, db):
        self.db = db

    def obtener(self, usuario_id):
        if usuario_id is None:
            return None
        with self.db.sesiones() as sesion:
            return UsuarioMapperORM.a_entidad(sesion.get(UsuarioModelo, usuario_id))

    def por_email(self, email):
        with self.db.sesiones() as sesion:
            modelo = sesion.scalar(select(UsuarioModelo).where(func.lower(UsuarioModelo.email) == email.strip().lower()))
            return UsuarioMapperORM.a_entidad(modelo)

    def agregar(self, usuario):
        modelo = UsuarioMapperORM.a_modelo(usuario)
        try:
            with self.db.sesiones.begin() as sesion:
                sesion.add(modelo)
                sesion.flush()
                entidad = UsuarioMapperORM.a_entidad(modelo)
            return entidad
        except IntegrityError:
            raise ErrorDominio("Ya existe una cuenta con este correo.") from None


class JugadorRepositorioORM:
    def __init__(self, db):
        self.db = db

    def listar(self, incluir_vendidos=False):
        consulta = select(JugadorModelo)
        if not incluir_vendidos:
            consulta = consulta.where(JugadorModelo.estado == "disponible")
        with self.db.sesiones() as sesion:
            return [JugadorMapperORM.a_entidad(m) for m in sesion.scalars(consulta)]

    def obtener(self, jugador_id):
        with self.db.sesiones() as sesion:
            return JugadorMapperORM.a_entidad(sesion.get(JugadorModelo, jugador_id))

    def agregar(self, jugador):
        with self.db.sesiones.begin() as sesion:
            modelo = JugadorMapperORM.a_modelo(jugador)
            sesion.add(modelo)
            sesion.flush()
            return JugadorMapperORM.a_entidad(modelo)

    def actualizar(self, jugador, version_esperada):
        actualizado = replace(jugador, version=version_esperada + 1)
        datos = JugadorMapper.a_datos(actualizado)
        datos.pop("id")
        with self.db.sesiones.begin() as sesion:
            resultado = sesion.execute(update(JugadorModelo).where(
                JugadorModelo.id == jugador.id, JugadorModelo.estado == "disponible",
                JugadorModelo.version == version_esperada).values(**datos))
            if resultado.rowcount != 1:
                raise ErrorDominio("El jugador cambió o ya fue vendido. Recarga la página antes de editar.")
        return actualizado

    def eliminar(self, jugador_id, version_esperada):
        try:
            with self.db.sesiones.begin() as sesion:
                resultado = sesion.execute(delete(JugadorModelo).where(
                    JugadorModelo.id == jugador_id, JugadorModelo.estado == "disponible",
                    JugadorModelo.version == version_esperada))
                if resultado.rowcount != 1:
                    raise ErrorDominio("El jugador cambio o ya fue vendido. No se pudo eliminar.")
        except IntegrityError:
            raise ErrorDominio("El jugador tiene una compra asociada. No se pudo eliminar.") from None


class CompraRepositorioORM:
    def __init__(self, db):
        self.db = db

    def registrar_atomica(self, jugador_id, preparar):
        try:
            with self.db.sesiones.begin() as sesion:
                modelo = sesion.scalar(select(JugadorModelo).where(
                    JugadorModelo.id == jugador_id).with_for_update())
                if modelo is None:
                    raise NoEncontrado("Este jugador ya no esta en el mercado.")
                jugador = JugadorMapperORM.a_entidad(modelo)
                compra = preparar(jugador)
                cambio = sesion.execute(update(JugadorModelo).where(
                    JugadorModelo.id == jugador_id, JugadorModelo.estado == "disponible",
                    JugadorModelo.version == jugador.version
                ).values(estado="vendido", version=jugador.version + 1))
                if cambio.rowcount != 1:
                    raise ErrorDominio("Otro usuario ya ficho a este jugador o su ficha cambio.")
                registro = CompraMapperORM.a_modelo(compra)
                sesion.add(registro)
                sesion.flush()
                return registro.id
        except IntegrityError:
            # El rollback tambien revierte el estado del jugador.
            raise ErrorDominio("No se pudo registrar la compra. Revisa la cuenta y disponibilidad del jugador.") from None

    def historial(self, usuario_id):
        with self.db.sesiones() as sesion:
            consulta = select(CompraModelo).where(CompraModelo.usuario_id == usuario_id).order_by(CompraModelo.id.desc())
            return [CompraMapperORM.a_entidad(m) for m in sesion.scalars(consulta)]

    def resumen(self):
        with self.db.sesiones() as sesion:
            total, volumen = sesion.execute(select(func.count(CompraModelo.id),
                func.coalesce(func.sum(CompraModelo.precio_centimos), 0))).one()
            return {"total": total, "volumen": int(volumen)}
