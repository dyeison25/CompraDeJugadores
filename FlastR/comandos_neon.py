import json

import click
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError

from infraestructura.orm.modelos import Base


def registrar_comandos_neon(app):
    def base():
        if app.config["DATABASE_BACKEND"] != "postgresql":
            raise click.ClickException("Selecciona DATABASE_BACKEND=postgresql para utilizar Neon.")
        return app.extensions["persistencia"].conexion

    @app.cli.command("inicializar-neon")
    def inicializar():
        """Crea las tablas ausentes; no altera tablas existentes ni inserta datos."""
        try:
            base().inicializar()
        except SQLAlchemyError:
            raise click.ClickException("No se pudo crear el esquema. Revisa conexion y permisos en Neon.") from None
        click.echo("Tablas preparadas. No se borraron ni sobrescribieron registros.")

    @app.cli.command("verificar-neon")
    def verificar():
        """Comprueba la conexion y cuenta registros, sin escribir datos."""
        try:
            db = base()
            with db.engine.connect() as conexion:
                conexion.execute(text("SELECT 1"))
                inspector = inspect(conexion)
                cantidades = {}
                for tabla in Base.metadata.sorted_tables:
                    cantidades[tabla.name] = (conexion.scalar(select(func.count()).select_from(tabla))
                                             if inspector.has_table(tabla.name) else None)
            click.echo(json.dumps({"backend": "postgresql", "orm": "SQLAlchemy", "conexion": "correcta",
                                   "registros": cantidades, "operacion": "solo lectura"}, indent=2))
            if any(c is None for c in cantidades.values()):
                click.echo("Faltan tablas. Ejecuta inicializar-neon para crearlas.")
        except SQLAlchemyError:
            raise click.ClickException("No se pudo consultar Neon. Revisa DATABASE_URL, permisos y conectividad.") from None
