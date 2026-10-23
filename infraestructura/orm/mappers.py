from infraestructura.mappers import UsuarioMapper, JugadorMapper, CompraMapper
from .modelos import UsuarioModelo, JugadorModelo, CompraModelo


class MapperORM:
    """Reutiliza las conversiones del proyecto sin introducir ORM en las entidades."""
    modelo = None
    mapper = None

    @classmethod
    def a_entidad(cls, modelo):
        if modelo is None:
            return None
        return cls.mapper.desde_datos({c.name: getattr(modelo, c.name) for c in modelo.__table__.columns})

    @classmethod
    def a_modelo(cls, entidad):
        datos = cls.mapper.a_datos(entidad)
        if datos["id"] == 0:
            datos.pop("id")
        return cls.modelo(**datos)


class UsuarioMapperORM(MapperORM):
    modelo, mapper = UsuarioModelo, UsuarioMapper


class JugadorMapperORM(MapperORM):
    modelo, mapper = JugadorModelo, JugadorMapper


class CompraMapperORM(MapperORM):
    modelo, mapper = CompraModelo, CompraMapper
