from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from FlastR import create_app
from domain.entidades import Usuario, Compra
from domain.servicio.datos_demo import jugadores_demo
from domain.servicio.errores import ErrorDominio
from infraestructura.mappers import UsuarioMapper, JugadorMapper, CompraMapper


def test_aislamiento_de_capas():
    from scripts.analizar_capas import analizar
    informe = analizar(Path(__file__).resolve().parents[1])
    assert not informe["errores"], informe["errores"]


@pytest.mark.parametrize("mapper,entidad", [
    (UsuarioMapper, Usuario(7, "Persona", "persona@test.local", "hash", "usuario")),
    (JugadorMapper, replace(jugadores_demo()[0], id=8)),
    (CompraMapper, Compra(9, 7, 8, 18000000001, "2026-10-15T12:00:00Z", "Jugador", "Equipo", "/static/img/foto.png")),
])
def test_mapper_roundtrip_sin_perder_ids_ni_precision(mapper, entidad):
    datos = mapper.a_datos(entidad)
    datos["campo_externo"] = "conservar fuera de la entidad"
    assert mapper.desde_datos(datos, str(entidad.id)) == entidad
    with pytest.raises(ValueError, match="no coincide"):
        mapper.desde_datos(datos, str(entidad.id + 1))


def test_mapper_compra_convierte_timestamp_a_utc():
    datos = CompraMapper.a_datos(Compra(1, 2, 3, 125050, "", "Jugador", "Club", "foto"))
    datos["fecha"] = datetime(2026, 10, 15, 12, 30, tzinfo=timezone.utc)
    assert CompraMapper.desde_datos(datos).fecha == "2026-10-15T12:30:00Z"


def test_mapper_rechaza_precio_flotante_y_rol_desconocido():
    jugador = JugadorMapper.a_datos(jugadores_demo()[0])
    jugador["precio_centimos"] = 1.5
    with pytest.raises(ValueError):
        JugadorMapper.desde_datos(jugador)
    with pytest.raises(ValueError):
        UsuarioMapper.desde_datos(dict(id=1, nombre="Admin", email="x@test.local", password_hash="hash", rol="superadmin"))


def test_testing_no_utiliza_neon_real(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_BACKEND", "postgresql")
    monkeypatch.setenv("DATABASE_URL", "postgresql://usuario:clave@ejemplo.neon.tech/base")
    app = create_app({"TESTING": True, "SECRET_KEY": "test", "DATABASE": str(tmp_path / "aislada.sqlite"),
                      "UPLOAD_FOLDER": str(tmp_path / "uploads"), "SEED_DEMO": False})
    assert app.config["DATABASE_BACKEND"] == "sqlite"



def test_registro_simultaneo_no_duplica_email(app):
    def registrar(_):
        try:
            app.extensions["auth"].registrar("Persona concurrente", "UNICO@test.local", "Segura123!")
            return True
        except ErrorDominio:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(registrar, range(2))) == [False, True]
