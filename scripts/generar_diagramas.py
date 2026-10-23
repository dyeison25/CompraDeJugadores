"""Genera diagramas UML como SVG, sin herramientas externas."""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESTINO = ROOT / "FlastR" / "static" / "diagramas"
INK, GREEN, LINE = "#213b2d", "#173e2d", "#719365"


class SVG:
    def __init__(self, ancho, alto, titulo, descripcion):
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}" role="img" aria-labelledby="title desc">',
                      f'<title id="title">{escape(titulo)}</title><desc id="desc">{escape(descripcion)}</desc>',
                      '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M1 1 9 5 1 9" fill="none" stroke="#719365" stroke-width="1.4"/></marker></defs>',
                      f'<rect width="{ancho}" height="{alto}" fill="#f7f9f3"/>']
        self.text(40, 42, titulo, size=25, weight=700)
        self.text(40, 69, descripcion, size=13, fill="#708069")

    def text(self, x, y, contenido, size=14, fill=INK, weight=400, anchor="start", mono=False):
        family = "Consolas, monospace" if mono else "Segoe UI, Arial, sans-serif"
        self.parts.append(f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(contenido)}</text>')

    def rect(self, x, y, w, h, fill="#fff", stroke=LINE, radius=9):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>')

    def path(self, d, dashed=False, arrow=False):
        extra = (' stroke-dasharray="6 5"' if dashed else '') + (' marker-end="url(#arrow)"' if arrow else '')
        self.parts.append(f'<path d="{d}" fill="none" stroke="{LINE}" stroke-width="1.5"{extra}/>')

    def clase(self, x, y, w, nombre, etiqueta, atributos, metodos):
        altura = 76 + 21 * len(atributos) + (20 + 22 * len(metodos) if metodos else 10)
        self.rect(x, y, w, altura)
        self.rect(x, y, w, 62, fill=GREEN, stroke=GREEN)
        self.text(x+w/2, y+21, etiqueta, size=10, fill="#c7d6a9", anchor="middle")
        self.text(x+w/2, y+44, nombre, size=17, fill="#fff", weight=700, anchor="middle")
        baseline = y + 87
        for atributo in atributos:
            self.text(x+16, baseline, atributo, size=12, mono=True)
            baseline += 21
        if metodos:
            self.path(f"M{x} {baseline-6}H{x+w}")
            baseline += 16
            for metodo in metodos:
                self.text(x+16, baseline, metodo, size=12, mono=True)
                baseline += 22
        return altura

    def actor(self, x, y, nombre):
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="15" fill="#eaf0dc" stroke="{GREEN}" stroke-width="2"/>')
        self.path(f"M{x} {y+15}v42m-27-26h54m-27 26-24 32m24-32 24 32")
        self.text(x, y+116, nombre, size=16, weight=700, anchor="middle")

    def caso(self, x, y, w, lineas, fill="#fff"):
        self.parts.append(f'<ellipse cx="{x}" cy="{y}" rx="{w/2}" ry="33" fill="{fill}" stroke="{LINE}" stroke-width="1.4"/>')
        if isinstance(lineas, str):
            lineas = [lineas]
        for indice, linea in enumerate(lineas):
            self.text(x, y+5 + (indice-(len(lineas)-1)/2)*18, linea, size=13, anchor="middle")

    def guardar(self, nombre):
        DESTINO.mkdir(parents=True, exist_ok=True)
        (DESTINO / nombre).write_text("\n".join(self.parts + ["</svg>"]), encoding="utf-8")


def clases():
    d = SVG(1510, 1400, "FICHAJE / DIAGRAMA DE CLASES",
            "Arquitectura: FlastR → domain.servicio → domain.entidades y BaseDatos. Firmas resumidas.")
    d.rect(22, 798, 1165, 515, fill="#eff3e7", stroke="#d1debf")
    d.text(44, 824, "domain.entidades", size=13, fill="#6b8754", weight=700)
    d.clase(480, 102, 540, "FlastR · aplicación web", "«capa de presentación»", [],
            ["+ create_app(config): Flask", "+ rutas, sesiones, formularios y plantillas", "+ requiere_rol(rol), guardar_foto(archivo)"])
    for x in (215, 605, 995):
        d.path(f"M750 264V294H{x}V341", dashed=True, arrow=True)
    d.text(40, 322, "domain.servicio", size=13, fill="#6b8754", weight=700)
    auth_height = d.clase(45, 345, 340, "AutenticacionServicio", "«servicio»", ["+ db: BaseDatos"],
                         ["+ obtener(id): Usuario", "+ registrar(...): Usuario", "+ crear_admin(...): Usuario", "+ iniciar_sesion(...): Usuario", "+ exigir_rol(id, rol): Usuario"])
    jugador_height = d.clase(435, 345, 340, "JugadorServicio", "«servicio»", ["+ db: BaseDatos", "+ auth: AutenticacionServicio"],
                            ["+ listar(filtros): list[Jugador]", "+ obtener(id): Jugador", "+ equipos(): list[str]", "+ validar(datos, foto): dict",
                             "+ agregar(...): Jugador", "+ editar(..., version): Jugador", "+ eliminar(..., version)"])
    compra_height = d.clase(825, 345, 340, "CompraServicio", "«servicio»", ["+ db: BaseDatos", "+ auth: AutenticacionServicio"],
                           ["+ comprar(..., version): int", "+ historial(id): list[Compra]", "+ resumen(admin_id): dict"])
    d.clase(1210, 490, 265, "BaseDatos", "«persistencia SQLite»", ["+ ruta: str"],
            ["+ conectar()", "+ inicializar()"])
    for x, h in ((215, auth_height), (605, jugador_height), (995, compra_height)):
        d.path(f"M{x} {345+h}V742H1342V{490+161}", dashed=True, arrow=True)
    d.text(1225, 732, "conexión / transacción", size=11, fill="#6b8754")
    d.rect(1210, 827, 265, 207, fill="#eaf1db", stroke="#d1debf")
    d.text(1228, 853, "REGLAS DEL MODELO", size=12, weight=700)
    for i, linea in enumerate(["• Usuario.rol: admin | usuario", "• El registro crea usuarios.", "• Precio entero en céntimos.", "• Una venta por jugador.", "• Compra atómica y simulada.", "• Se conserva la ficha vendida.", "• La versión evita datos obsoletos."]):
        d.text(1228, 883+i*20, linea, size=11)
    d.clase(45, 850, 340, "Usuario", "«entidad / dataclass»",
            ["+ id: int", "+ nombre: str", "+ email: str", "+ password_hash: str", "+ rol: str"], ["+ es_admin: bool {propiedad}"])
    d.clase(435, 850, 340, "Jugador", "«entidad / dataclass»",
            ["+ id: int", "+ nombre: str", "+ equipo: str", "+ nacionalidad: str", "+ edad: int", "+ posicion: str",
             "+ precio_centimos: int", "+ foto: str", "+ dorsal: int", "+ descripcion: str", "+ estado: str",
             "+ destacado: int", "+ version: int"], ["+ precio: Decimal {propiedad}"])
    d.clase(825, 850, 340, "Compra", "«entidad / dataclass»",
            ["+ id: int", "+ usuario_id: int", "+ jugador_id: int", "+ precio_centimos: int",
             "+ fecha: str", "+ jugador_nombre: str", "+ equipo: str", "+ foto: str"], [])
    for x in (215, 605, 995):
        d.path(f"M{x} 750V844", dashed=True, arrow=True)
    d.path("M385 981H410V1290H1197V970H1165")
    d.text(391, 971, "1", size=13, weight=700)
    d.text(1168, 960, "0..*", size=13, weight=700)
    d.text(775, 1281, "realiza", size=13, fill="#527347")
    d.path("M775 1072H825")
    d.text(782, 1061, "1", size=12, weight=700)
    d.text(798, 1061, "0..1", size=12, weight=700)
    d.text(805, 1090, "venta", size=10, fill="#527347", anchor="middle")
    d.text(44, 1350, "Línea continua: asociación y multiplicidad. Flecha discontinua: dependencia o uso.", size=13, fill="#6c7c61")
    d.text(44, 1376, "Los servicios de jugadores y compras también usan AutenticacionServicio para comprobar permisos; relación completa en docs/clases.puml.", size=12, fill="#6c7c61")
    d.guardar("clases.svg")


def casos():
    d = SVG(1390, 1410, "FICHAJE / DIAGRAMA DE CASOS DE USO",
            "Tres actores. Un mercado. Compras simuladas y administración según el rol.")
    d.rect(215, 104, 1140, 1230, fill="#fff", stroke="#c0d0b1")
    d.text(239, 134, "SISTEMA FICHAJE", size=14, weight=700)
    d.rect(250, 156, 1068, 423, fill="#f6f8f0", stroke="#e2e9d7")
    d.text(275, 183, "MERCADO Y ACCESO", size=11, fill="#6a8554", weight=700)
    d.rect(250, 617, 1068, 223, fill="#f0f5e5", stroke="#e2e9d7")
    d.text(275, 645, "ÁREA DE USUARIO", size=11, fill="#6a8554", weight=700)
    d.rect(250, 882, 1068, 410, fill="#f6f8f0", stroke="#e2e9d7")
    d.text(275, 910, "ÁREA DE ADMINISTRACIÓN", size=11, fill="#6a8554", weight=700)
    d.actor(92, 267, "Visitante")
    d.actor(92, 690, "Usuario")
    d.actor(92, 1090, "Administrador")
    # Cada asociación termina en el borde izquierdo de un caso de uso.
    # No se dibujan enlaces entre casos que no estén relacionados.
    for origen, destinos in [
        (308, [227, 303, 379, 455]),
        (731, [227, 303, 455, 531, 690, 775]),
        (1131, [227, 303, 455, 531, 978, 1058, 1138, 1218]),
    ]:
        for destino in destinos:
            d.path(f"M119 {origen}L350 {destino}")
    for y, nombre in [
        (227, "Explorar y filtrar mercado"), (303, "Consultar ficha de jugador"),
        (379, "Registrarse"), (455, "Iniciar sesión"), (531, "Cerrar sesión"),
    ]:
        d.caso(550, y, 400, nombre)
    d.text(857, 278, "ACCESO PÚBLICO", size=12, weight=700, fill="#607b49")
    d.text(857, 305, "Todos pueden explorar y consultar fichas.", size=12, fill="#6b7f5b")
    d.text(857, 332, "El visitante puede crear una cuenta.", size=12, fill="#6b7f5b")
    d.text(857, 450, "SESIONES", size=12, weight=700, fill="#607b49")
    d.text(857, 477, "Usuario y administrador acceden con", size=12, fill="#6b7f5b")
    d.text(857, 498, "correo y contraseña. El rol determina", size=12, fill="#6b7f5b")
    d.text(857, 519, "qué acciones pueden realizar.", size=12, fill="#6b7f5b")
    d.caso(550, 690, 400, ["Comprar jugador", "(confirmación simulada)"], fill="#e7f1d0")
    d.caso(1090, 690, 355, ["Validar disponibilidad", "y versión del precio"])
    d.path("M750 690H907", dashed=True, arrow=True)
    d.text(795, 676, "«include»", size=12, fill="#62834b")
    d.caso(550, 775, 400, "Consultar mis fichajes")
    d.text(913, 784, "Precondición: sesión de usuario.", size=12, fill="#678050")
    for y, nombre in [
        (978, "Consultar panel de administración"), (1058, "Agregar jugador"),
        (1138, "Editar jugador disponible"), (1218, "Eliminar jugador disponible"),
    ]:
        d.caso(550, y, 400, nombre)
    d.caso(1090, 1098, 355, "Validar ficha y foto")
    d.path("M750 1058H827V1088H907", dashed=True, arrow=True)
    d.path("M750 1138H827V1108H907", dashed=True, arrow=True)
    d.text(827, 1050, "«include»", size=12, fill="#62834b")
    d.text(827, 1158, "«include»", size=12, fill="#62834b")
    d.text(888, 964, "Precondición: sesión de administrador.", size=12, fill="#678050")
    d.text(888, 990, "Las publicaciones vendidas se conservan", size=12, fill="#678050")
    d.text(888, 1011, "para mantener el historial de compras.", size=12, fill="#678050")
    d.text(242, 1317, "Las compras guardan el historial y retiran la publicación. No existe cobro real ni actor de pagos.", size=12, fill="#6c7c61")
    d.text(40, 1374, "«include»: comportamiento obligatorio dentro del caso de uso. Tener el rol y la sesión adecuados es una precondición.", size=12, fill="#6c7c61")
    d.guardar("casos-de-uso.svg")


if __name__ == "__main__":
    clases()
    casos()
    print("Diagramas SVG generados en " + str(DESTINO))
