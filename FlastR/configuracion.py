import os
from pathlib import Path
from dotenv import dotenv_values

RAIZ = Path(__file__).resolve().parents[1]


def configurar(app, ajustes=None):
    ajustes = ajustes or {}
    locales = dotenv_values(RAIZ / ".env", encoding="utf-8-sig")
    def valor(nombre, predeterminado=""):
        return os.environ.get(nombre, locales.get(nombre) or predeterminado)

    app.config.update(
        DATABASE_URL=valor("DATABASE_URL"),
        SESSION_COOKIE_SECURE=valor("COOKIE_SECURE") == "1",
    )
    clave = valor("SECRET_KEY")
    if clave:
        app.config["SECRET_KEY"] = clave
    # Las pruebas ordinarias nunca heredan el proyecto real configurado en .env.
    backend_default = "sqlite" if ajustes.get("TESTING") else (
        "postgresql" if app.config["DATABASE_URL"] else "sqlite"
    )
    backend = "sqlite" if ajustes.get("TESTING") else valor("DATABASE_BACKEND", backend_default)
    backend = ajustes.get("DATABASE_BACKEND", backend).strip().lower()
    app.config["DATABASE_BACKEND"] = backend
    app.config["SEED_DEMO"] = backend == "sqlite"
    app.config.update(ajustes)
