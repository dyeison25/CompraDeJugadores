from io import BytesIO
from pathlib import Path

import pytest
from flask import Flask
from werkzeug.datastructures import FileStorage

from FlastR.configuracion import configurar
from FlastR.imagenes import guardar_foto
from domain.servicio.errores import ErrorDominio


def test_salud_no_consulta_base_ni_expone_configuracion(app, monkeypatch):
    def prohibido(*args, **kwargs):
        raise AssertionError("El health check no debe consultar cuentas")
    monkeypatch.setattr(app.extensions["auth"], "obtener", prohibido)
    cliente = app.test_client()
    with cliente.session_transaction() as sesion:
        sesion["usuario_id"] = app.config["USER_ID"]
    respuesta = cliente.get("/healthz")
    assert respuesta.status_code == 200
    assert respuesta.json == {"status": "ok"}


def test_render_exige_conexion_y_clave_persistente(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    for opciones, mensaje in (
        ({"DATABASE_BACKEND": "sqlite", "DATABASE_URL": ""}, "DATABASE_BACKEND"),
        ({"DATABASE_BACKEND": "postgresql", "DATABASE_URL": "postgresql://ejemplo/base",
          "SECRET_KEY": ""}, "SECRET_KEY"),
    ):
        with pytest.raises(RuntimeError, match=mensaje):
            configurar(Flask("prueba-config"), opciones)


def test_modo_url_rechaza_archivos_sin_guardarlos(app):
    app.config["ALLOW_UPLOADS"] = False
    carpeta = Path(app.config["UPLOAD_FOLDER"])
    antes = list(carpeta.iterdir())
    with app.app_context():
        with pytest.raises(ErrorDominio, match="URL HTTPS"):
            guardar_foto(FileStorage(stream=BytesIO(b"imagen"), filename="foto.png"))
        assert guardar_foto(None) is None
    assert list(carpeta.iterdir()) == antes


def test_formulario_render_solo_ofrece_url(app, client, login):
    app.config["ALLOW_UPLOADS"] = False
    login("admin")
    respuesta = client.get("/admin/jugadores/nuevo")
    assert respuesta.status_code == 200
    assert b'name="foto_url"' in respuesta.data
    assert b'type="file"' not in respuesta.data
    assert b'Debes subir una foto' not in respuesta.data
