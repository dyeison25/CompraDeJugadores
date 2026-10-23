from functools import wraps

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for

from domain.servicio.errores import ErrorDominio
from .imagenes import descartar_foto_nueva, guardar_foto

web = Blueprint("web", __name__)


def servicio(nombre):
    return current_app.extensions[nombre]


def requiere_rol(rol):
    def decorador(funcion):
        @wraps(funcion)
        def protegida(*args, **kwargs):
            if not g.usuario:
                flash("Inicia sesión para continuar.", "info")
                return redirect(url_for("web.login"))
            if g.usuario.rol != rol:
                abort(403)
            return funcion(*args, **kwargs)
        return protegida
    return decorador


def entero_formulario(clave):
    try:
        return int(request.form.get(clave, ""))
    except (ValueError, TypeError):
        raise ErrorDominio("El formulario no es válido. Recarga la página.")


@web.get("/")
def mercado():
    datos = servicio("catalogo").explorar(
        request.args.get("q", ""), request.args.get("posicion", ""),
        request.args.get("equipo", ""), request.args.get("orden", ""),
    )
    return render_template("mercado.html", **datos)


@web.route("/login", methods=["GET", "POST"])
def login():
    if g.usuario:
        return redirect(url_for("web.admin" if g.usuario.es_admin else "web.mercado"))
    if request.method == "POST":
        try:
            usuario = servicio("auth").iniciar_sesion(request.form.get("email", ""), request.form.get("password", ""))
            session.clear()
            session["usuario_id"] = usuario.id
            session.permanent = True
            flash(f"¡Bienvenido, {usuario.nombre}!", "success")
            return redirect(url_for("web.admin" if usuario.es_admin else "web.mercado"))
        except ErrorDominio as error:
            flash(str(error), "error")
    return render_template("auth.html", registro=False, datos=request.form)


@web.route("/register", methods=["GET", "POST"])
def register():
    if g.usuario:
        return redirect(url_for("web.mercado"))
    if request.method == "POST":
        try:
            if request.form.get("password") != request.form.get("confirmar"):
                raise ErrorDominio("Las contraseñas no coinciden.")
            usuario = servicio("auth").registrar(
                request.form.get("nombre", ""), request.form.get("email", ""), request.form.get("password", "")
            )
            session.clear()
            session["usuario_id"] = usuario.id
            session.permanent = True
            flash("Tu cuenta está lista. Es hora de construir tu equipo.", "success")
            return redirect(url_for("web.mercado"))
        except ErrorDominio as error:
            flash(str(error), "error")
    return render_template("auth.html", registro=True, datos=request.form)


@web.post("/logout")
def logout():
    session.clear()
    flash("Cerraste sesión correctamente.", "info")
    return redirect(url_for("web.mercado"))


@web.get("/jugadores/<int:jugador_id>")
def detalle(jugador_id):
    return render_template("detalle.html", jugador=servicio("jugadores").obtener(jugador_id))


@web.route("/jugadores/<int:jugador_id>/comprar", methods=["GET", "POST"])
@requiere_rol("usuario")
def comprar(jugador_id):
    jugador = servicio("jugadores").obtener(jugador_id)
    if request.method == "POST":
        try:
            servicio("compras").comprar(g.usuario.id, jugador_id, entero_formulario("version"))
            flash(f"¡Fichaje completado! {jugador.nombre} ya forma parte de tu equipo.", "success")
            return redirect(url_for("web.mis_fichajes"))
        except ErrorDominio as error:
            flash(str(error), "error")
            return redirect(url_for("web.detalle", jugador_id=jugador_id))
    if jugador.estado != "disponible":
        flash("Este jugador ya fue fichado.", "info")
        return redirect(url_for("web.detalle", jugador_id=jugador_id))
    return render_template("comprar.html", jugador=jugador)


@web.get("/mis-fichajes")
@requiere_rol("usuario")
def mis_fichajes():
    return render_template("mis_fichajes.html", **servicio("estadisticas").resumen_usuario(g.usuario.id))


@web.get("/admin")
@requiere_rol("admin")
def admin():
    jugadores = servicio("jugadores").listar(busqueda=request.args.get("q", ""), incluir_vendidos=True, orden="recientes")
    return render_template("admin.html", jugadores=jugadores,
                           **servicio("estadisticas").resumen_admin(g.usuario.id))


@web.route("/admin/jugadores/nuevo", methods=["GET", "POST"])
@requiere_rol("admin")
def nuevo_jugador():
    return formulario_jugador()


@web.route("/admin/jugadores/<int:jugador_id>/editar", methods=["GET", "POST"])
@requiere_rol("admin")
def editar_jugador(jugador_id):
    jugador = servicio("jugadores").obtener(jugador_id)
    if jugador.estado != "disponible":
        flash("Los jugadores vendidos se conservan como parte del historial.", "info")
        return redirect(url_for("web.admin"))
    return formulario_jugador(jugador)


def formulario_jugador(jugador=None):
    datos = request.form if request.method == "POST" else (
        dict(nombre=jugador.nombre, equipo=jugador.equipo, nacionalidad=jugador.nacionalidad,
             edad=jugador.edad, dorsal=jugador.dorsal, posicion=jugador.posicion,
             precio=str(jugador.precio), descripcion=jugador.descripcion, destacado="1" if jugador.destacado else "",
             foto_url=jugador.foto if jugador.foto.startswith("https://") else "", version=jugador.version)
        if jugador else {}
    )
    if request.method == "POST":
        foto_nueva = None
        try:
            foto_nueva = guardar_foto(request.files.get("foto"))
            foto = foto_nueva or request.form.get("foto_url", "").strip() or (jugador.foto if jugador else "")
            if jugador:
                servicio("jugadores").editar(g.usuario.id, jugador.id, datos, foto, entero_formulario("version"))
            else:
                servicio("jugadores").agregar(g.usuario.id, datos, foto)
            flash("Jugador actualizado." if jugador else "Jugador agregado al mercado.", "success")
            return redirect(url_for("web.admin"))
        except ErrorDominio as error:
            descartar_foto_nueva(foto_nueva)
            flash(str(error), "error")
    return render_template("jugador_form.html", jugador=jugador, datos=datos)


@web.route("/admin/jugadores/<int:jugador_id>/eliminar", methods=["GET", "POST"])
@requiere_rol("admin")
def eliminar_jugador(jugador_id):
    jugador = servicio("jugadores").obtener(jugador_id)
    if request.method == "POST":
        try:
            servicio("jugadores").eliminar(g.usuario.id, jugador_id, entero_formulario("version"))
            flash(f"Se eliminó a {jugador.nombre} del mercado.", "success")
        except ErrorDominio as error:
            flash(str(error), "error")
        return redirect(url_for("web.admin"))
    return render_template("eliminar.html", jugador=jugador)


@web.get("/diagramas")
def diagramas():
    return render_template("diagramas.html")
