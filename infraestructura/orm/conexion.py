from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import sessionmaker

from .modelos import Base


def normalizar_url(valor, testing=False):
    if not valor:
        raise RuntimeError("Configura DATABASE_URL en .env con la conexion PostgreSQL de Neon.")
    try:
        url = make_url(valor)
    except (ArgumentError, ValueError):
        raise RuntimeError("DATABASE_URL no tiene un formato valido.") from None
    if testing:
        if url.get_backend_name() != "sqlite":
            raise RuntimeError("Las pruebas ORM ordinarias requieren una base SQLite temporal.")
        return url
    if url.drivername not in ("postgres", "postgresql", "postgresql+psycopg"):
        raise RuntimeError("DATABASE_URL debe utilizar PostgreSQL.")
    if not url.host or not url.database:
        raise RuntimeError("DATABASE_URL debe indicar servidor y base de datos.")
    url = url.set(drivername="postgresql+psycopg")
    if url.host.endswith(".neon.tech"):
        if url.query.get("sslmode", "require") not in ("require", "verify-ca", "verify-full"):
            raise RuntimeError("La conexion a Neon requiere SSL.")
        url = url.update_query_dict({"sslmode": url.query.get("sslmode", "require")})
    return url


class BaseORM:
    def __init__(self, url, testing=False):
        url = normalizar_url(url, testing)
        opciones = {"pool_pre_ping": True, "hide_parameters": True, "echo": False}
        if url.get_backend_name() == "postgresql":
            opciones.update(pool_size=3, max_overflow=2, pool_recycle=300,
                            connect_args={"connect_timeout": 15, "prepare_threshold": None})
        self.engine = create_engine(url, **opciones)
        if url.get_backend_name() == "sqlite":
            @event.listens_for(self.engine, "connect")
            def activar_integridad(conexion, _):
                conexion.execute("PRAGMA foreign_keys=ON")
                conexion.execute("PRAGMA busy_timeout=15000")
        self.sesiones = sessionmaker(bind=self.engine, expire_on_commit=False)

    def inicializar(self):
        # Solo crea tablas ausentes; nunca DROP, TRUNCATE, ni reemplaza registros.
        with self.engine.begin() as conexion:
            Base.metadata.create_all(conexion)

    def cerrar(self):
        self.engine.dispose()
