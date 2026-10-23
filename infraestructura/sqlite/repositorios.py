import sqlite3
from dataclasses import replace
from domain.servicio.errores import ErrorDominio, NoEncontrado
from infraestructura.mappers import UsuarioMapper, JugadorMapper, CompraMapper


INSERTS = {
    "usuarios": "INSERT INTO usuarios (id,nombre,email,password_hash,rol) VALUES (:id,:nombre,:email,:password_hash,:rol)",
    "jugadores": """INSERT INTO jugadores
        (id,nombre,equipo,nacionalidad,edad,posicion,precio_centimos,foto,dorsal,descripcion,destacado,estado,version)
        VALUES (:id,:nombre,:equipo,:nacionalidad,:edad,:posicion,:precio_centimos,:foto,:dorsal,:descripcion,:destacado,:estado,:version)""",
    "compras": """INSERT INTO compras
        (id,usuario_id,jugador_id,precio_centimos,fecha,jugador_nombre,equipo,foto)
        VALUES (:id,:usuario_id,:jugador_id,:precio_centimos,:fecha,:jugador_nombre,:equipo,:foto)""",
}


def insertar(db, tabla, datos):
    # Lista cerrada de sentencias. Ningun nombre o valor se interpola en el SQL.
    if tabla not in INSERTS:
        raise ValueError("Tabla no permitida.")
    valores = dict(datos)
    valores["id"] = valores.get("id") or None
    cursor = db.execute(INSERTS[tabla], valores)
    return cursor.lastrowid


class UsuarioRepositorioSQLite:
    def __init__(self, db):
        self.db = db

    def obtener(self, usuario_id):
        with self.db.conectar() as db:
            fila = db.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        return UsuarioMapper.desde_datos(fila) if fila else None

    def por_email(self, email):
        with self.db.conectar() as db:
            fila = db.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
        return UsuarioMapper.desde_datos(fila) if fila else None

    def agregar(self, usuario):
        try:
            with self.db.conectar() as db:
                identificador = insertar(db, "usuarios", UsuarioMapper.a_datos(usuario))
        except sqlite3.IntegrityError as error:
            raise ErrorDominio("Ya existe una cuenta con este correo.") from error
        return replace(usuario, id=identificador)


class JugadorRepositorioSQLite:
    def __init__(self, db):
        self.db = db

    def listar(self, incluir_vendidos=False):
        sql = "SELECT * FROM jugadores" if incluir_vendidos else "SELECT * FROM jugadores WHERE estado = 'disponible'"
        with self.db.conectar() as db:
            filas = db.execute(sql).fetchall()
        return [JugadorMapper.desde_datos(fila) for fila in filas]

    def obtener(self, jugador_id):
        with self.db.conectar() as db:
            fila = db.execute("SELECT * FROM jugadores WHERE id = ?", (jugador_id,)).fetchone()
        return JugadorMapper.desde_datos(fila) if fila else None

    def agregar(self, jugador):
        with self.db.conectar() as db:
            identificador = insertar(db, "jugadores", JugadorMapper.a_datos(jugador))
        return replace(jugador, id=identificador)

    def actualizar(self, jugador, version_esperada):
        actualizado = replace(jugador, version=version_esperada + 1)
        valores = JugadorMapper.a_datos(actualizado)
        valores["version_esperada"] = version_esperada
        with self.db.conectar() as db:
            cursor = db.execute(
                """UPDATE jugadores SET nombre=:nombre, equipo=:equipo, nacionalidad=:nacionalidad,
                edad=:edad, posicion=:posicion, precio_centimos=:precio_centimos, foto=:foto,
                dorsal=:dorsal, descripcion=:descripcion, destacado=:destacado, estado=:estado, version=:version
                WHERE id=:id AND estado='disponible' AND version=:version_esperada""",
                valores,
            )
            if cursor.rowcount != 1:
                raise ErrorDominio("El jugador cambió o ya fue vendido. Recarga la página antes de editar.")
        return actualizado

    def eliminar(self, jugador_id, version_esperada):
        with self.db.conectar() as db:
            cursor = db.execute(
                "DELETE FROM jugadores WHERE id = ? AND estado = 'disponible' AND version = ?",
                (jugador_id, version_esperada),
            )
            if cursor.rowcount != 1:
                raise ErrorDominio("El jugador cambió o ya fue vendido. No se pudo eliminar.")


class CompraRepositorioSQLite:
    def __init__(self, db):
        self.db = db

    def registrar_atomica(self, jugador_id, preparar):
        with self.db.conectar() as db:
            db.execute("BEGIN IMMEDIATE")
            fila = db.execute("SELECT * FROM jugadores WHERE id = ?", (jugador_id,)).fetchone()
            if not fila:
                raise NoEncontrado("Este jugador ya no está en el mercado.")
            jugador = JugadorMapper.desde_datos(fila)
            compra = preparar(jugador)
            identificador = insertar(db, "compras", CompraMapper.a_datos(compra))
            db.execute("UPDATE jugadores SET estado = 'vendido',version = version + 1 WHERE id = ?", (jugador_id,))
            return identificador

    def historial(self, usuario_id):
        with self.db.conectar() as db:
            filas = db.execute("SELECT * FROM compras WHERE usuario_id = ? ORDER BY id DESC", (usuario_id,)).fetchall()
        return [CompraMapper.desde_datos(fila) for fila in filas]

    def resumen(self):
        with self.db.conectar() as db:
            return dict(db.execute(
                "SELECT COUNT(*) AS total, COALESCE(SUM(precio_centimos),0) AS volumen FROM compras"
            ).fetchone())


def cargar_demo_sqlite(db, jugadores):
    with db.conectar() as conexion:
        conexion.execute("BEGIN IMMEDIATE")
        if conexion.execute("SELECT 1 FROM metadatos WHERE clave = 'catalogo_demo'").fetchone():
            return
        # Una base ya usada tampoco recibe jugadores de ejemplo adicionales.
        if not conexion.execute("SELECT 1 FROM jugadores LIMIT 1").fetchone():
            for jugador in jugadores:
                insertar(conexion, "jugadores", JugadorMapper.a_datos(jugador))
        conexion.execute("INSERT INTO metadatos VALUES('catalogo_demo','1')")
