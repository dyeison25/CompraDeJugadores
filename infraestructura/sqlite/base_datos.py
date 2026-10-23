import sqlite3
from contextlib import contextmanager
from pathlib import Path


class BaseDatos:
    def __init__(self, ruta):
        self.ruta = str(ruta)

    @contextmanager
    def conectar(self):
        conexion = sqlite3.connect(self.ruta, timeout=15)
        conexion.row_factory = sqlite3.Row
        conexion.execute("PRAGMA foreign_keys = ON")
        try:
            yield conexion
            conexion.commit()
        except Exception:
            conexion.rollback()
            raise
        finally:
            conexion.close()

    def inicializar(self):
        Path(self.ruta).parent.mkdir(parents=True, exist_ok=True)
        with self.conectar() as db:
            db.executescript("""
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    rol TEXT NOT NULL CHECK(rol IN ('admin', 'usuario'))
                );
                CREATE TABLE IF NOT EXISTS jugadores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    equipo TEXT NOT NULL,
                    nacionalidad TEXT NOT NULL,
                    edad INTEGER NOT NULL CHECK(edad BETWEEN 16 AND 55),
                    posicion TEXT NOT NULL,
                    precio_centimos INTEGER NOT NULL CHECK(precio_centimos > 0),
                    foto TEXT NOT NULL,
                    dorsal INTEGER NOT NULL CHECK(dorsal BETWEEN 1 AND 99),
                    descripcion TEXT NOT NULL DEFAULT '',
                    estado TEXT NOT NULL DEFAULT 'disponible'
                        CHECK(estado IN ('disponible', 'vendido')),
                    destacado INTEGER NOT NULL DEFAULT 0,
                    version INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS compras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
                    jugador_id INTEGER NOT NULL UNIQUE REFERENCES jugadores(id),
                    precio_centimos INTEGER NOT NULL CHECK(precio_centimos > 0),
                    fecha TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                    jugador_nombre TEXT NOT NULL,
                    equipo TEXT NOT NULL,
                    foto TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS metadatos (
                    clave TEXT PRIMARY KEY,
                    valor TEXT NOT NULL
                );
            """)
