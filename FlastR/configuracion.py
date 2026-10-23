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
        ALLOW_UPLOADS=valor("ALLOW_UPLOADS", "1") == "1",
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
    if os.environ.get("RENDER") == "true" and not app.config.get("TESTING"):
        if app.config["DATABASE_BACKEND"] != "postgresql" or not app.config.get("DATABASE_URL"):
            raise RuntimeError("Configura DATABASE_BACKEND=postgresql y DATABASE_URL en Render.")
        if not app.config.get("SECRET_KEY"):
            raise RuntimeError("Configura una SECRET_KEY persistente en Render.")
