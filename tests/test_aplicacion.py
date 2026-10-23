import io
from concurrent.futures import ThreadPoolExecutor

import pytest
from PIL import Image

from FlastR import create_app
from domain.servicio.errores import AccesoDenegado, ErrorDominio, NoEncontrado
from conftest import token


def ficha(**cambios):
    datos = dict(nombre="Jugador de Prueba", equipo="Club Prueba", nacionalidad="Colombia",
                 edad="25", dorsal="10", posicion="Delantero", precio="1250000.50",
                 descripcion="Talento de prueba", destacado="1")
    datos.update(cambios)
    return datos


def test_catalogo_fotos_detalle_y_diagramas(client):
    for ruta in ("/", "/login", "/register", "/jugadores/1", "/diagramas"):
        respuesta = client.get(ruta)
        assert respuesta.status_code == 200
        assert b"Fichaje" in respuesta.data or b"fichaje" in respuesta.data
    assert b"mbappe.png" in client.get("/").data


def test_registro_normaliza_email_impide_elegir_admin_y_cifra_password(app, client):
    respuesta = client.post("/register", data={
        "_csrf": token(client), "nombre": "Nueva Persona", "email": "NUEVA@TEST.LOCAL",
        "password": "Segura123!", "confirmar": "Segura123!", "rol": "admin"
    }, follow_redirects=True)
    assert respuesta.status_code == 200
    with client.session_transaction() as sesion:
        usuario = app.extensions["auth"].obtener(sesion["usuario_id"])
    assert usuario.email == "nueva@test.local"
    assert usuario.rol == "usuario"
    assert usuario.password_hash != "Segura123!"
    assert usuario.password_hash.startswith("scrypt:")


def test_registro_duplicado_con_mayusculas(app):
    with pytest.raises(ErrorDominio, match="Ya existe"):
        app.extensions["auth"].registrar("Duplicado", "USER@test.local", "Clave123!")


def test_registro_password_y_confirmacion(client):
    respuesta = client.post("/register", data={
        "_csrf": token(client), "nombre": "Nuevo", "email": "otro@test.local",
        "password": "Clave123!", "confirmar": "Otra123!"
    })
    assert "no coinciden" in respuesta.get_data(as_text=True)


@pytest.mark.parametrize("ruta", ["/logout", "/register", "/login", "/jugadores/1/comprar", "/admin/jugadores/1/eliminar"])
def test_csrf_obligatorio_en_mutaciones(client, ruta):
    assert client.post(ruta, data={}).status_code == 400


def test_login_fallido_no_crea_sesion(client):
    respuesta = client.post("/login", data={
        "_csrf": token(client), "email": "admin@test.local", "password": "incorrecta"
    })
    assert "no son correctos" in respuesta.get_data(as_text=True)
    with client.session_transaction() as sesion:
        assert "usuario_id" not in sesion


def test_login_rota_csrf_y_logout_limpia_sesion(client, login):
    anterior = token(client)
    login()
    assert token(client) != anterior
    assert client.post("/logout", data={"_csrf": token(client)}).status_code == 302
    with client.session_transaction() as sesion:
        assert "usuario_id" not in sesion


def test_visitante_y_usuario_no_pueden_administrar(client, login):
    assert client.get("/admin").status_code == 302
    login()
    for ruta in ("/admin", "/admin/jugadores/nuevo", "/admin/jugadores/1/editar", "/admin/jugadores/1/eliminar"):
        assert client.get(ruta).status_code == 403
        if ruta != "/admin":
            assert client.post(ruta, data={"_csrf": token(client)}).status_code == 403


def test_servicios_verifican_permisos(app):
    servicio = app.extensions["jugadores"]
    with pytest.raises(AccesoDenegado):
        servicio.agregar(app.config["USER_ID"], ficha(), "https://example.com/foto.png")
    with pytest.raises(AccesoDenegado):
        app.extensions["compras"].comprar(app.config["ADMIN_ID"], 1, 1)


def test_admin_agrega_edita_elimina(app, client, login):
    assert login("admin").status_code == 200
    datos = {**ficha(), "_csrf": token(client), "foto_url": "https://example.com/foto.png"}
    respuesta = client.post("/admin/jugadores/nuevo", data=datos, follow_redirects=True)
    assert "Jugador agregado" in respuesta.get_data(as_text=True)
    jugador = app.extensions["jugadores"].listar(orden="recientes")[0]
    assert jugador.precio_centimos == 125000050
    respuesta = client.post(f"/admin/jugadores/{jugador.id}/editar", data={
        **datos, "_csrf": token(client), "nombre": "Nombre Actualizado", "precio": "999.99", "version": jugador.version
    }, follow_redirects=True)
    actualizado = app.extensions["jugadores"].obtener(jugador.id)
    assert actualizado.nombre == "Nombre Actualizado"
    assert actualizado.precio_centimos == 99999
    assert client.get(f"/admin/jugadores/{jugador.id}/eliminar").status_code == 200
    client.post(f"/admin/jugadores/{jugador.id}/eliminar", data={
        "_csrf": token(client), "version": actualizado.version
    })
    with pytest.raises(NoEncontrado):
        app.extensions["jugadores"].obtener(jugador.id)


@pytest.mark.parametrize("cambio", [
    {"precio": "-1"}, {"precio": "NaN"}, {"precio": "Infinity"}, {"precio": "1.001"},
    {"precio": "1000000001"}, {"edad": "15"}, {"posicion": "Inventada"}, {"dorsal": "0"}
])
def test_valida_datos_jugador(app, cambio):
    with pytest.raises(ErrorDominio):
        app.extensions["jugadores"].agregar(app.config["ADMIN_ID"], ficha(**cambio), "https://example.com/foto.png")


@pytest.mark.parametrize("url", ["javascript:alert(1)", "http://example.com/a.png", "/static/../secret", "https://"])
def test_rechaza_fotos_con_url_insegura(app, url):
    with pytest.raises(ErrorDominio):
        app.extensions["jugadores"].agregar(app.config["ADMIN_ID"], ficha(), url)


@pytest.mark.parametrize("modo", ["RGB", "RGBA", "P"])
def test_foto_subida_valida_y_archivo_falso(app, client, login, modo):
    login("admin")
    foto = io.BytesIO()
    imagen = Image.new(modo, (100, 100))
    if modo == "P":
        imagen.info["transparency"] = bytes([0, 255])
    imagen.save(foto, format="PNG")
    foto.seek(0)
    respuesta = client.post("/admin/jugadores/nuevo", data={
        **ficha(), "_csrf": token(client), "foto": (foto, "../../foto.png")
    }, content_type="multipart/form-data", follow_redirects=True)
    assert "Jugador agregado" in respuesta.get_data(as_text=True)
    jugador = app.extensions["jugadores"].listar(orden="recientes")[0]
    assert jugador.foto.startswith("/static/uploads/")
    assert jugador.foto.endswith(".webp")
    respuesta_foto = client.get(jugador.foto)
    assert respuesta_foto.status_code == 200
    if modo in ("RGBA", "P"):
        with Image.open(io.BytesIO(respuesta_foto.data)) as guardada:
            assert "A" in guardada.getbands()
    from pathlib import Path
    assert (Path(app.config["UPLOAD_FOLDER"]) / jugador.foto.rsplit("/", 1)[-1]).is_file()
    respuesta = client.post("/admin/jugadores/nuevo", data={
        **ficha(), "_csrf": token(client), "foto": (io.BytesIO(b"<script>alert(1)</script>"), "falsa.png")
    }, content_type="multipart/form-data")
    assert "no es una imagen" in respuesta.get_data(as_text=True)


def test_limite_de_carga(client, login):
    login("admin")
    assert client.post("/admin/jugadores/nuevo", data={
        "_csrf": token(client), "foto": (io.BytesIO(b"x" * (5 * 1024 * 1024)), "grande.png")
    }, content_type="multipart/form-data").status_code == 413


def test_compra_precio_servidor_historial_y_no_reventa(app, client, login):
    login()
    assert client.get("/jugadores/1/comprar").status_code == 200
    compra = client.post("/jugadores/1/comprar", data={
        "_csrf": token(client), "version": "1", "precio_centimos": "1", "usuario_id": "999"
    }, follow_redirects=True)
    assert "Fichaje completado" in compra.get_data(as_text=True)
    servicio = app.extensions["compras"]
    historial = servicio.historial(app.config["USER_ID"])
    assert len(historial) == 1
    assert historial[0].precio_centimos == 18000000000
    assert app.extensions["jugadores"].obtener(1).estado == "vendido"
    assert not any(j.id == 1 for j in app.extensions["jugadores"].listar())
    with pytest.raises(ErrorDominio, match="ya fichó"):
        servicio.comprar(app.config["USER_ID"], 1, 1)
    assert len(servicio.historial(app.config["USER_ID"])) == 1


def test_usuario_solo_ve_sus_compras(app, client, login):
    otro = app.extensions["auth"].registrar("Otro Usuario", "otro@test.local", "Otro123!")
    app.extensions["compras"].comprar(otro.id, 1, 1)
    login()
    assert "Kylian Mbappé" not in client.get("/mis-fichajes?usuario_id=" + str(otro.id)).get_data(as_text=True)
    assert not app.extensions["compras"].historial(app.config["USER_ID"])


def test_cambio_precio_impide_confirmacion_antigua_y_edicion_obsoleta(app):
    jugadores = app.extensions["jugadores"]
    original = jugadores.obtener(1)
    jugadores.editar(app.config["ADMIN_ID"], 1, ficha(precio="3333333"), original.foto, original.version)
    with pytest.raises(ErrorDominio, match="cambiaron"):
        app.extensions["compras"].comprar(app.config["USER_ID"], 1, original.version)
    with pytest.raises(ErrorDominio, match="cambió"):
        jugadores.editar(app.config["ADMIN_ID"], 1, ficha(), original.foto, original.version)
    assert app.extensions["jugadores"].obtener(1).estado == "disponible"


def test_vendido_no_se_edita_ni_se_elimina(app):
    app.extensions["compras"].comprar(app.config["USER_ID"], 1, 1)
    jugador = app.extensions["jugadores"].obtener(1)
    with pytest.raises(ErrorDominio):
        app.extensions["jugadores"].editar(app.config["ADMIN_ID"], 1, ficha(), jugador.foto, jugador.version)
    with pytest.raises(ErrorDominio):
        app.extensions["jugadores"].eliminar(app.config["ADMIN_ID"], 1, jugador.version)


def test_dos_compras_simultaneas_solo_una_tiene_exito(app):
    otro = app.extensions["auth"].registrar("Segundo Usuario", "segundo@test.local", "Segundo123!")
    servicio = app.extensions["compras"]
    def comprar(usuario_id):
        try:
            servicio.comprar(usuario_id, 1, 1)
            return True
        except ErrorDominio:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(comprar, [app.config["USER_ID"], otro.id]))
    assert sorted(resultados) == [False, True]
    assert servicio.resumen(app.config["ADMIN_ID"])["total"] == 1


def test_filtros_orden_y_sql_parametrizado(app, client):
    assert all(j.posicion == "Portero" for j in app.extensions["jugadores"].listar(posicion="Portero"))
    jugadores = app.extensions["jugadores"].listar(orden="precio_asc")
    assert [j.precio_centimos for j in jugadores] == sorted(j.precio_centimos for j in jugadores)
    assert not app.extensions["jugadores"].listar(busqueda="' OR 1=1 --")
    assert client.get("/?q=Messi&orden=precio_asc").status_code == 200


def test_persistencia_y_no_reponer_catalogo_vacio(app):
    jugadores = app.extensions["jugadores"]
    for jugador in jugadores.listar():
        jugadores.eliminar(app.config["ADMIN_ID"], jugador.id, jugador.version)
    nueva = create_app({
        "TESTING": True, "SECRET_KEY": "test", "DATABASE": app.config["DATABASE"],
        "UPLOAD_FOLDER": app.config["UPLOAD_FOLDER"],
        "DATABASE_BACKEND": app.config["DATABASE_BACKEND"],
        "DATABASE_URL": app.config.get("DATABASE_URL"),
        "SEED_DEMO": True,
    })
    assert nueva.extensions["jugadores"].listar() == []
    assert nueva.extensions["auth"].obtener(app.config["USER_ID"]) is not None


def test_errores_y_cabeceras(client):
    assert client.get("/ruta-que-no-existe").status_code == 404
    assert client.get("/jugadores/99999").status_code == 404
    assert client.get("/logout").status_code == 405
    respuesta = client.get("/")
    assert respuesta.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in respuesta.headers["Content-Security-Policy"]
