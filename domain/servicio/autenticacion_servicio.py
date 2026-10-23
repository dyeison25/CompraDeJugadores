import re
from domain.entidades import Usuario
from domain.repositorios import UsuarioRepositorio, GestorClaves
from .errores import AccesoDenegado, ErrorDominio


class AutenticacionServicio:
    def __init__(self, usuarios: UsuarioRepositorio, claves: GestorClaves):
        self.usuarios = usuarios
        self.claves = claves
        self._hash_ficticio = claves.generar("credencial-inexistente")

    def obtener(self, usuario_id):
        return self.usuarios.obtener(usuario_id)

    def buscar_por_email(self, email):
        return self.usuarios.por_email(email.strip().lower())

    def registrar(self, nombre, email, password):
        return self._crear(nombre, email, password, "usuario")

    def crear_admin(self, nombre, email, password):
        return self._crear(nombre, email, password, "admin")

    def _crear(self, nombre, email, password, rol):
        nombre, email = nombre.strip(), email.strip().lower()
        if not 2 <= len(nombre) <= 80:
            raise ErrorDominio("El nombre debe tener entre 2 y 80 caracteres.")
        if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise ErrorDominio("Escribe un correo electrónico válido.")
        if not 8 <= len(password) <= 128:
            raise ErrorDominio("La contraseña debe tener entre 8 y 128 caracteres.")
        usuario = Usuario(0, nombre, email, self.claves.generar(password), rol)
        return self.usuarios.agregar(usuario)

    def iniciar_sesion(self, email, password):
        usuario = self.buscar_por_email(email)
        validada = self.claves.verificar(usuario.password_hash if usuario else self._hash_ficticio, password[:129])
        if not usuario or not validada:
            raise ErrorDominio("El correo o la contraseña no son correctos.")
        return usuario

    def exigir_rol(self, usuario_id, rol):
        usuario = self.obtener(usuario_id)
        if not usuario or usuario.rol != rol:
            raise AccesoDenegado("Tu cuenta no tiene permiso para realizar esta acción.")
        return usuario
