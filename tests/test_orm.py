from dataclasses import replace

import pytest
from sqlalchemy import inspect

from FlastR import create_app
from domain.entidades import Compra
from domain.servicio.datos_demo import jugadores_demo
from domain.servicio.errores import ErrorDominio
from infraestructura.orm.conexion import BaseORM, normalizar_url
from infraestructura.orm.mappers import JugadorMapperORM
from infraestructura.orm.repositorios import JugadorRepositorioORM, CompraRepositorioORM


def test_url_neon_preserva_parametros_y_no_admite_ssl_desactivado():
    url = normalizar_url("postgresql://persona:clave@ejemplo.neon.tech/base?sslmode=require&channel_binding=require")
    assert url.drivername == "postgresql+psycopg"
    assert url.query["channel_binding"] == "require"
    assert url.query["sslmode"] == "require"
    with pytest.raises(RuntimeError, match="SSL"):
        normalizar_url("postgresql://persona:clave@ejemplo.neon.tech/base?sslmode=disable")


def test_pruebas_orm_no_admiten_proyecto_real():
    with pytest.raises(RuntimeError, match="temporal"):
        BaseORM("postgresql://persona:clave@ejemplo.neon.tech/base", testing=True)


def test_configuracion_da_prioridad_neon_y_aisla_pruebas(monkeypatch, tmp_path):
    from flask import Flask
    from FlastR.configuracion import configurar
    monkeypatch.setenv("DATABASE_URL", "postgresql://persona:clave@ejemplo.neon.tech/base")
    monkeypatch.delenv("DATABASE_BACKEND", raising=False)
    # Override explicito evita depender del backend que el usuario tenga en .env.
    config = Flask("test-config")
    configurar(config, {"DATABASE_BACKEND": "postgresql"})
    assert config.config["DATABASE_BACKEND"] == "postgresql"
    app = create_app({"TESTING": True, "SECRET_KEY": "test", "DATABASE": str(tmp_path / "aislada.sqlite"),
                      "UPLOAD_FOLDER": str(tmp_path / "uploads"), "SEED_DEMO": False})
    assert app.config["DATABASE_BACKEND"] == "sqlite"


def test_mapper_orm_conserva_precio_grande_y_campos():
    jugador = replace(jugadores_demo()[0], id=42, precio_centimos=100000000000)
    assert JugadorMapperORM.a_entidad(JugadorMapperORM.a_modelo(jugador)) == jugador


def test_fallo_compra_revierte_estado_y_no_crea_historial(tmp_path):
    db = BaseORM("sqlite:///" + (tmp_path / "fallo.sqlite").as_posix(), testing=True)
    try:
        db.inicializar()
        jugadores, compras = JugadorRepositorioORM(db), CompraRepositorioORM(db)
        jugador = jugadores.agregar(jugadores_demo()[0])
        def preparar(j):
            return Compra(0, 999, j.id, j.precio_centimos, "2026-10-16T00:00:00Z", j.nombre, j.equipo, j.foto)
        with pytest.raises(ErrorDominio):
            compras.registrar_atomica(jugador.id, preparar)
        assert jugadores.obtener(jugador.id).estado == "disponible"
        assert jugadores.obtener(jugador.id).version == 1
        assert compras.resumen() == {"total": 0, "volumen": 0}
    finally:
        db.cerrar()


def test_inicializar_es_idempotente_y_no_modifica_registros(tmp_path):
    db = BaseORM("sqlite:///" + (tmp_path / "esquema.sqlite").as_posix(), testing=True)
    try:
        assert inspect(db.engine).get_table_names() == []
        db.inicializar()
        repositorio = JugadorRepositorioORM(db)
        jugador = repositorio.agregar(jugadores_demo()[0])
        db.inicializar()
        assert repositorio.listar() == [jugador]
        assert set(inspect(db.engine).get_table_names()) == {"usuarios", "jugadores", "compras"}
    finally:
        db.cerrar()
