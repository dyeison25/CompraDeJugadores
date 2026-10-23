import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from FlastR import create_app


@pytest.fixture
def app(tmp_path, request):
    config = {
        "TESTING": True,
        "SECRET_KEY": "test-secret-is-not-a-production-secret",
        "DATABASE": str(tmp_path / "test.sqlite"),
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    }
    if request.config.getoption("--orm-sqlite"):
        config.update(DATABASE_BACKEND="postgresql", DATABASE_URL="sqlite:///" + (tmp_path / "orm.sqlite").as_posix(),
                      SEED_DEMO=True)
    app = create_app(config)
    auth = app.extensions["auth"]
    app.config["ADMIN_ID"] = auth.crear_admin("Admin Test", "admin@test.local", "AdminTest123!").id
    app.config["USER_ID"] = auth.registrar("Usuario Test", "user@test.local", "UsuarioTest123!").id
    yield app
    if app.config["DATABASE_BACKEND"] == "postgresql":
        app.extensions["persistencia"].conexion.cerrar()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def login(client):
    def autenticar(rol="usuario"):
        client.get("/login")
        with client.session_transaction() as sesion:
            token = sesion["_csrf"]
        correo, clave = ("admin@test.local", "AdminTest123!") if rol == "admin" else ("user@test.local", "UsuarioTest123!")
        return client.post("/login", data={"_csrf": token, "email": correo, "password": clave}, follow_redirects=True)
    return autenticar


def token(client):
    client.get("/login", follow_redirects=True)
    with client.session_transaction() as sesion:
        return sesion["_csrf"]


def pytest_addoption(parser):
    parser.addoption("--orm-sqlite", action="store_true", default=False)
