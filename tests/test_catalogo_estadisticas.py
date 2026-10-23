import pytest

from domain.servicio.errores import AccesoDenegado


def test_catalogo_filtra_sin_cambiar_totales_del_mercado(app):
    servicio = app.extensions["catalogo"]
    completo = servicio.explorar()
    primero = completo["jugadores"][0]
    filtrado = servicio.explorar(busqueda="  " + primero.nombre + "  ", equipo=primero.equipo)
    assert [jugador.id for jugador in filtrado["jugadores"]] == [primero.id]
    assert filtrado["filtros"]["q"] == primero.nombre
    assert filtrado["total"] == completo["total"]
    assert filtrado["equipos"] == completo["equipos"]
    assert filtrado["total_equipos"] == len(completo["equipos"])


def test_compra_actualiza_catalogo_y_estadisticas_sin_exponer_otro_historial(app):
    auth = app.extensions["auth"]
    otro = auth.registrar("Otra persona", "otro@pruebas.local", "Segura123!")
    jugadores = app.extensions["jugadores"]
    estadisticas = app.extensions["estadisticas"]
    jugador = jugadores.listar()[0]
    antes = estadisticas.resumen_admin(app.config["ADMIN_ID"])
    app.extensions["compras"].comprar(app.config["USER_ID"], jugador.id, jugador.version)
    despues = estadisticas.resumen_admin(app.config["ADMIN_ID"])
    assert despues["disponibles"] == antes["disponibles"] - 1
    assert despues["valor"] == antes["valor"] - jugador.precio_centimos
    assert despues["resumen"] == {"total": 1, "volumen": jugador.precio_centimos}
    personal = estadisticas.resumen_usuario(app.config["USER_ID"])
    assert personal["volumen"] == jugador.precio_centimos
    assert len(personal["compras"]) == 1
    assert estadisticas.resumen_usuario(otro.id) == {"compras": [], "volumen": 0}
    assert jugador.id not in [j.id for j in app.extensions["catalogo"].explorar()["jugadores"]]


def test_estadisticas_verifican_roles(app):
    servicio = app.extensions["estadisticas"]
    with pytest.raises(AccesoDenegado):
        servicio.resumen_admin(app.config["USER_ID"])
    with pytest.raises(AccesoDenegado):
        servicio.resumen_usuario(app.config["ADMIN_ID"])
    with pytest.raises(AccesoDenegado):
        servicio.resumen_admin(999999)


def test_catalogo_y_estadisticas_sin_jugadores(app):
    jugadores = app.extensions["jugadores"]
    for jugador in jugadores.listar():
        jugadores.eliminar(app.config["ADMIN_ID"], jugador.id, jugador.version)
    catalogo = app.extensions["catalogo"].explorar()
    assert catalogo["jugadores"] == []
    assert catalogo["destacado"] is None
    assert catalogo["total"] == catalogo["total_equipos"] == catalogo["total_paises"] == 0
    assert app.extensions["estadisticas"].resumen_admin(app.config["ADMIN_ID"]) == {
        "disponibles": 0, "valor": 0, "resumen": {"total": 0, "volumen": 0}}
