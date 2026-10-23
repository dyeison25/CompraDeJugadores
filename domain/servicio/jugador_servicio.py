from dataclasses import replace
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from domain.entidades import Jugador
from domain.entidades.jugador import POSICIONES
from domain.repositorios import JugadorRepositorio
from .errores import ErrorDominio, NoEncontrado


class JugadorServicio:
    def __init__(self, jugadores: JugadorRepositorio, autenticacion):
        self.jugadores = jugadores
        self.auth = autenticacion

    def listar(self, busqueda="", posicion="", equipo="", orden="destacados", incluir_vendidos=False):
        jugadores = self.jugadores.listar(incluir_vendidos)
        if busqueda:
            texto = busqueda[:100].casefold()
            jugadores = [j for j in jugadores if any(texto in valor.casefold()
                        for valor in (j.nombre, j.equipo, j.nacionalidad))]
        if posicion in POSICIONES:
            jugadores = [j for j in jugadores if j.posicion == posicion]
        if equipo:
            jugadores = [j for j in jugadores if j.equipo == equipo]
        claves = {
            "destacados": lambda j: (-j.destacado, j.id),
            "precio_asc": lambda j: (j.precio_centimos, j.id),
            "precio_desc": lambda j: (-j.precio_centimos, j.id),
            "nombre": lambda j: (j.nombre.casefold(), j.id),
            "recientes": lambda j: -j.id,
        }
        return sorted(jugadores, key=claves.get(orden, claves["destacados"]))

    def obtener(self, jugador_id):
        jugador = self.jugadores.obtener(jugador_id)
        if jugador is None:
            raise NoEncontrado("No encontramos este jugador.")
        return jugador

    def equipos(self):
        return sorted({j.equipo for j in self.jugadores.listar()})

    def validar(self, datos, foto):
        valores = {}
        for campo, limite in (("nombre", 80), ("equipo", 80), ("nacionalidad", 50)):
            valor = str(datos.get(campo, "")).strip()
            if not 2 <= len(valor) <= limite:
                raise ErrorDominio(f"El campo {campo} debe tener entre 2 y {limite} caracteres.")
            valores[campo] = valor
        try:
            edad = int(datos.get("edad", ""))
            dorsal = int(datos.get("dorsal", ""))
            precio = Decimal(str(datos.get("precio", "")).strip())
            if not precio.is_finite() or not Decimal("0.01") <= precio <= Decimal("1000000000"):
                raise ValueError
            if precio.as_tuple().exponent < -2:
                raise ValueError
        except (ValueError, TypeError, InvalidOperation):
            raise ErrorDominio("Revisa la edad, el dorsal y el precio (máximo dos decimales).")
        if not 16 <= edad <= 55 or not 1 <= dorsal <= 99:
            raise ErrorDominio("La edad debe estar entre 16 y 55, y el dorsal entre 1 y 99.")
        posicion = datos.get("posicion", "")
        if posicion not in POSICIONES:
            raise ErrorDominio("Selecciona una posición válida.")
        descripcion = str(datos.get("descripcion", "")).strip()
        if len(descripcion) > 1500:
            raise ErrorDominio("La descripción no puede superar los 1500 caracteres.")
        if not foto or len(foto) > 1000:
            raise ErrorDominio("Agrega una foto del jugador.")
        if foto.startswith("/static/"):
            if ".." in foto or "\\" in foto or "?" in foto or "#" in foto:
                raise ErrorDominio("La ruta de la imagen no es válida.")
        else:
            try:
                url = urlsplit(foto)
                valida = url.scheme == "https" and bool(url.hostname) and not url.username and not url.password
            except ValueError:
                valida = False
            if not valida:
                raise ErrorDominio("La URL de la foto debe comenzar por https://.")
        valores.update(
            edad=edad, dorsal=dorsal, posicion=posicion, precio_centimos=int(precio * 100),
            foto=foto, descripcion=descripcion, destacado=int(datos.get("destacado") in ("1", "on", True)),
        )
        return valores

    def agregar(self, admin_id, datos, foto):
        self.auth.exigir_rol(admin_id, "admin")
        jugador = Jugador(id=0, estado="disponible", version=1, **self.validar(datos, foto))
        return self.jugadores.agregar(jugador)

    def editar(self, admin_id, jugador_id, datos, foto, version):
        self.auth.exigir_rol(admin_id, "admin")
        valores = self.validar(datos, foto)
        actual = self.obtener(jugador_id)
        if actual.estado != "disponible" or actual.version != version:
            raise ErrorDominio("El jugador cambió o ya fue vendido. Recarga la página antes de editar.")
        return self.jugadores.actualizar(replace(actual, **valores), version)

    def eliminar(self, admin_id, jugador_id, version):
        self.auth.exigir_rol(admin_id, "admin")
        self.jugadores.eliminar(jugador_id, version)
