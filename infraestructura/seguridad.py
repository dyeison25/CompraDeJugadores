from werkzeug.security import check_password_hash, generate_password_hash


class ClavesWerkzeug:
    def generar(self, password):
        return generate_password_hash(password)

    def verificar(self, password_hash, password):
        return check_password_hash(password_hash, password)
