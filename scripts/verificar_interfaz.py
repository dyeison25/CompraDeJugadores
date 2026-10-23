"""Prueba real en Edge con una base aislada; guarda capturas para revisar el diseño."""
import json
import logging
import secrets
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from FlastR import create_app
from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

logging.getLogger("werkzeug").setLevel(logging.ERROR)
CAPTURAS = ROOT / "docs" / "capturas"


def ejecutar():
    CAPTURAS.mkdir(parents=True, exist_ok=True)
    instance = (ROOT / "instance").resolve()
    instance.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="fichaje-ui-", dir=instance) as temporal:
        carpeta = Path(temporal).resolve()
        assert carpeta.is_relative_to(instance)
        app = create_app({
            "TESTING": True, "SECRET_KEY": secrets.token_hex(32),
            "DATABASE": str(carpeta / "ui.sqlite"),
            "UPLOAD_FOLDER": str(carpeta / "uploads"),
        })
        app.extensions["auth"].crear_admin("Admin Prueba", "admin@ui.local", "AdminUI123!")
        servidor = make_server("127.0.0.1", 0, app, threaded=True)
        hilo = Thread(target=servidor.serve_forever, daemon=True)
        hilo.start()
        base = f"http://127.0.0.1:{servidor.server_port}"
        errores = []
        fallos_red = []
        try:
            with sync_playwright() as p:
                navegador = p.chromium.launch(channel="msedge", headless=True)
                contexto = navegador.new_context(viewport={"width": 1440, "height": 1080}, device_scale_factor=1)
                pagina = contexto.new_page()
                pagina.on("pageerror", lambda error: errores.append(str(error)))
                pagina.on("response", lambda response: fallos_red.append(f"{response.status} {response.url}") if response.status >= 400 else None)
                pagina.goto(base, wait_until="networkidle")
                pagina.evaluate("document.fonts.ready")
                expect(pagina.locator(".player-card")).to_have_count(8)
                assert pagina.locator("img").evaluate_all("(imgs) => imgs.every(i => i.complete && i.naturalWidth > 0)")
                assert pagina.locator("img[data-failed]").count() == 0
                pagina.screenshot(path=str(CAPTURAS / "mercado-escritorio.png"), full_page=True)
                pagina.locator('select[name="posicion"]').select_option("Portero")
                pagina.get_by_role("button", name="Filtrar", exact=True).click()
                expect(pagina.locator(".player-card")).to_have_count(1)
                expect(pagina.locator(".player-card h3")).to_have_text("Alisson Becker")
                pagina.goto(base + "/register")
                pagina.locator('[name="nombre"]').fill("Camila Ruiz")
                pagina.locator('[name="email"]').fill("camila@ui.local")
                pagina.locator('[name="password"]').fill("CamilaUI123!")
                pagina.locator('[name="confirmar"]').fill("CamilaUI123!")
                pagina.get_by_role("button", name="Crear mi cuenta").click()
                expect(pagina.locator(".account-name")).to_contain_text("Camila")
                pagina.goto(base + "/jugadores/1")
                pagina.get_by_role("link", name="Comprar jugador").click()
                expect(pagina.get_by_role("heading", name="Hazlo oficial.")).to_be_visible()
                pagina.screenshot(path=str(CAPTURAS / "confirmar-compra.png"), full_page=True)
                pagina.get_by_role("button", name="Confirmar compra simulada").click()
                expect(pagina.locator(".purchase-card")).to_have_count(1)
                expect(pagina.locator(".purchase-card h2")).to_have_text("Kylian Mbappé")
                pagina.screenshot(path=str(CAPTURAS / "mis-fichajes.png"), full_page=True)
                pagina.get_by_role("button", name="Cerrar sesión", exact=True).click()
                pagina.goto(base + "/login")
                pagina.screenshot(path=str(CAPTURAS / "login.png"), full_page=True)
                pagina.locator('[name="email"]').fill("admin@ui.local")
                pagina.locator('[name="password"]').fill("AdminUI123!")
                pagina.get_by_role("button", name="Iniciar sesión", exact=True).click()
                expect(pagina.get_by_role("heading", name="Panel de administración.")).to_be_visible()
                pagina.screenshot(path=str(CAPTURAS / "administracion.png"), full_page=True)
                pagina.get_by_role("link", name="Agregar jugador").click()
                for campo, valor in {
                    "nombre": "Estrella de Prueba", "equipo": "Club UI", "nacionalidad": "Colombia",
                    "edad": "24", "dorsal": "7", "precio": "1234567.89", "descripcion": "Jugador para comprobar el formulario."
                }.items():
                    pagina.locator(f'[name="{campo}"]').fill(valor)
                pagina.locator('[name="posicion"]').select_option("Delantero")
                pagina.locator('[name="foto"]').set_input_files(str(ROOT / "FlastR/static/img/jugadores/mbappe.png"))
                pagina.screenshot(path=str(CAPTURAS / "agregar-jugador.png"), full_page=True)
                pagina.get_by_role("button", name="Publicar jugador").click()
                expect(pagina.get_by_text("Jugador agregado al mercado.", exact=True)).to_be_visible()
                pagina.get_by_role("link", name="Editar Estrella de Prueba", exact=True).click()
                pagina.locator('[name="precio"]').fill("2000000")
                pagina.get_by_role("button", name="Guardar cambios").click()
                expect(pagina.get_by_text("Jugador actualizado.", exact=True)).to_be_visible()
                pagina.get_by_role("link", name="Eliminar Estrella de Prueba", exact=True).click()
                pagina.get_by_role("button", name="Eliminar jugador", exact=True).click()
                expect(pagina.get_by_text("Se eliminó a Estrella de Prueba del mercado.", exact=True)).to_be_visible()
                pagina.get_by_role("button", name="Cerrar sesión", exact=True).click()
                for ancho in (390, 320):
                    pagina.set_viewport_size({"width": ancho, "height": 844})
                    pagina.goto(base, wait_until="networkidle")
                    assert pagina.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Desbordamiento en {ancho}px"
                    assert pagina.locator(".hero h1").evaluate("(el) => el.scrollWidth <= el.clientWidth"), "Titulo recortado"
                    boton = pagina.locator(".hero-copy .button").bounding_box()
                    retrato = pagina.locator(".hero-portrait").bounding_box()
                    assert boton["y"] + boton["height"] <= retrato["y"], "La foto se superpone al boton"
                    if ancho == 390:
                        pagina.screenshot(path=str(CAPTURAS / "mercado-movil.png"), full_page=True)
                    pagina.goto(base + "/login", wait_until="networkidle")
                    assert pagina.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    if ancho == 390:
                        pagina.screenshot(path=str(CAPTURAS / "login-movil.png"), full_page=True)
                pagina.set_viewport_size({"width": 1440, "height": 1080})
                pagina.goto(base + "/diagramas", wait_until="networkidle")
                assert pagina.locator(".diagram-section img").evaluate_all("(imgs) => imgs.every(i => i.complete && i.naturalWidth > 0)")
                pagina.screenshot(path=str(CAPTURAS / "diagramas.png"), full_page=True)
                navegador.close()
            assert not errores, errores
            assert not fallos_red, fallos_red
            print(json.dumps({
                "resultado": "correcto", "flujos": ["catalogo", "filtros", "registro", "compra", "historial", "login",
                "admin agregar", "admin editar", "admin eliminar", "logout", "movil 390 y 320", "diagramas"],
                "errores_javascript": errores, "errores_http": fallos_red, "capturas": str(CAPTURAS)
            }, ensure_ascii=False, indent=2))
        finally:
            servidor.shutdown()
            hilo.join(timeout=5)


if __name__ == "__main__":
    ejecutar()
