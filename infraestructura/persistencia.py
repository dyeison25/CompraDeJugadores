from dataclasses import dataclass

from domain.repositorios import UsuarioRepositorio, JugadorRepositorio, CompraRepositorio
from domain.servicio.datos_demo import jugadores_demo


@dataclass
class Persistencia:
    usuarios: UsuarioRepositorio
    jugadores: JugadorRepositorio
    compras: CompraRepositorio
    conexion: object


def crear_persistencia(config, raiz):
    backend = config["DATABASE_BACKEND"]
    if backend == "postgresql":
        from infraestructura.orm.conexion import BaseORM
        from infraestructura.orm.repositorios import UsuarioRepositorioORM, JugadorRepositorioORM, CompraRepositorioORM
        db = BaseORM(config.get("DATABASE_URL"), testing=config.get("TESTING", False))
        usuarios, jugadores, compras = UsuarioRepositorioORM(db), JugadorRepositorioORM(db), CompraRepositorioORM(db)
        if config.get("TESTING"):
            from sqlalchemy import inspect
            nueva = not inspect(db.engine).has_table("jugadores")
            db.inicializar()
            if config["SEED_DEMO"] and nueva:
                for jugador in jugadores_demo():
                    jugadores.agregar(jugador)
        elif config["SEED_DEMO"]:
            raise RuntimeError("No se permite sembrar jugadores automaticamente en Neon.")
        return Persistencia(usuarios, jugadores, compras, db)
    if backend == "sqlite":
        from infraestructura.sqlite.base_datos import BaseDatos
        from infraestructura.sqlite.repositorios import (
            UsuarioRepositorioSQLite, JugadorRepositorioSQLite, CompraRepositorioSQLite, cargar_demo_sqlite
        )
        db = BaseDatos(config["DATABASE"])
        db.inicializar()
        if config["SEED_DEMO"]:
            cargar_demo_sqlite(db, jugadores_demo())
        return Persistencia(UsuarioRepositorioSQLite(db), JugadorRepositorioSQLite(db), CompraRepositorioSQLite(db), db)
    raise RuntimeError("DATABASE_BACKEND debe ser sqlite o postgresql.")
