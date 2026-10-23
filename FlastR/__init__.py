import os
import secrets
from datetime import timedelta
from pathlib import Path

import click
from flask import Flask, abort, g, render_template, request, session, send_from_directory

from domain.entidades.jugador import POSICIONES
from infraestructura.persistencia import crear_persistencia
from infraestructura.seguridad import ClavesWerkzeug
from .configuracion import configurar, RAIZ
from domain.servicio.autenticacion_servicio import AutenticacionServicio
from domain.servicio.jugador_servicio import JugadorServicio
from domain.servicio.compra_servicio import CompraServicio
from domain.servicio.catalogo_servicio import CatalogoServicio
from domain.servicio.estadistica_servicio import EstadisticaServicio
from domain.servicio.errores import AccesoDenegado, ErrorDominio, NoEncontrado


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=str(Path(app.instance_path) / "fichaje.sqlite"),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        SEED_DEMO=True,
        UPLOAD_FOLDER=str(Path(app.static_folder) / "uploads"),
    )
    configurar(app, test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if not app.config.get("SECRET_KEY"):
        secret_file = Path(app.instance_path) / ".secret_key"
        secret_env = os.environ.get("SECRET_KEY")
        if not secret_env:
            try:
                with secret_file.open("x", encoding="utf-8") as stream:
                    stream.write(secrets.token_hex(32))
            except FileExistsError:
                pass
        app.config["SECRET_KEY"] = secret_env or secret_file.read_text(encoding="utf-8").strip()
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    persistencia = crear_persistencia(app.config, RAIZ)
    auth = AutenticacionServicio(persistencia.usuarios, ClavesWerkzeug())
    app.extensions["persistencia"] = persistencia
    app.extensions["auth"] = auth
    app.extensions["jugadores"] = JugadorServicio(persistencia.jugadores, auth)
    app.extensions["compras"] = CompraServicio(persistencia.compras, auth)
    app.extensions["catalogo"] = CatalogoServicio(app.extensions["jugadores"])
    app.extensions["estadisticas"] = EstadisticaServicio(persistencia.jugadores, persistencia.compras, auth)

    def csrf_token():
        if "_csrf" not in session:
            session["_csrf"] = secrets.token_urlsafe(32)
        return session["_csrf"]

    @app.before_request
    def cargar_usuario_y_proteger_formularios():
        if request.endpoint == "salud":
            return None
        g.usuario = auth.obtener(session.get("usuario_id")) if session.get("usuario_id") else None
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            recibido = request.form.get("_csrf", "")
            esperado = session.get("_csrf", "")
            if not esperado or not secrets.compare_digest(recibido, esperado):
                abort(400, description="El formulario caducó. Recarga la página e inténtalo de nuevo.")

    @app.get("/healthz")
    def salud():
        # Comprueba el proceso web sin despertar Neon en cada sondeo.
        return {"status": "ok"}

    @app.get("/static/uploads/<filename>")
    def foto_subida(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.context_processor
    def contexto():
        return dict(usuario=g.get("usuario"), csrf_token=csrf_token, posiciones=POSICIONES)

    @app.template_filter("euros")
    def euros(centimos):
        valor = f"{int(centimos) / 100:,.2f}"
        return "€ " + valor.replace(",", "_").replace(".", ",").replace("_", ".")

    @app.template_filter("millones")
    def millones(centimos):
        cantidad = int(centimos) / 100
        if cantidad >= 1_000_000:
            return "€ " + f"{cantidad / 1_000_000:,.1f}".rstrip("0").rstrip(".").replace(".", ",") + " M"
        return euros(centimos)

    @app.after_request
    def cabeceras(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' https: data: blob:; "
            "style-src 'self'; script-src 'self'; font-src 'self'; "
            "form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'"
        )
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
        return response

    from .rutas import web
    app.register_blueprint(web)

    @app.errorhandler(AccesoDenegado)
    def sin_permiso(error):
        return render_template("error.html", codigo=403, mensaje=str(error)), 403

    @app.errorhandler(NoEncontrado)
    def inexistente(error):
        return render_template("error.html", codigo=404, mensaje=str(error)), 404

    for codigo in (400, 403, 404, 405, 413, 500):
        app.register_error_handler(codigo, pagina_error)

    @app.cli.command("crear-admin")
    @click.option("--nombre", prompt="Nombre", default="Administrador")
    @click.option("--email", prompt="Correo del administrador")
    @click.password_option(confirmation_prompt=True)
    def crear_admin(nombre, email, password):
        """Crea un administrador desde la terminal, nunca desde el registro público."""
        try:
            auth.crear_admin(nombre, email, password)
        except ErrorDominio as error:
            raise click.ClickException(str(error)) from error
        click.echo("Administrador creado correctamente.")

    @app.cli.command("crear-demo")
    def crear_demo():
        """Crea cuentas locales con claves aleatorias, sin modificar las existentes."""
        for nombre, email, rol in (
            ("Admin Fichaje", "admin@fichaje.local", "admin"),
            ("Alex Morgan", "usuario@fichaje.local", "usuario"),
        ):
            existente = auth.buscar_por_email(email)
            if existente:
                click.echo(f"La cuenta {email} ya existe; no se modificó.")
                continue
            clave = secrets.token_urlsafe(24)
            if rol == "admin":
                auth.crear_admin(nombre, email, clave)
            else:
                auth.registrar(nombre, email, clave)
            click.echo(f"Cuenta de demostración creada: {email} / {clave}")

    from .comandos_neon import registrar_comandos_neon
    registrar_comandos_neon(app)

    from sqlalchemy.exc import SQLAlchemyError

    @app.errorhandler(SQLAlchemyError)
    def persistencia_no_disponible(error):
        app.logger.error("No se pudo acceder a la persistencia: %s", type(error).__name__)
        return render_template("error.html", codigo=503,
                               mensaje="No pudimos conectar con la base de datos. Inténtalo nuevamente."), 503

    return app


def pagina_error(error):
    mensajes = {
        400: getattr(error, "description", "No pudimos validar el formulario."),
        403: "Esta sección requiere una cuenta con los permisos adecuados.",
        404: "Esta página está fuera de juego.",
        405: "Esta acción no está disponible desde ese enlace.",
        413: "La imagen es demasiado grande. El tamaño máximo es de 5 MB.",
        500: "No pudimos completar la jugada. Inténtalo de nuevo.",
    }
    codigo = getattr(error, "code", 500)
    return render_template("error.html", codigo=codigo, mensaje=mensajes.get(codigo, mensajes[500])), codigo
