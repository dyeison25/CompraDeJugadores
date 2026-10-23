class ErrorDominio(ValueError):
    """Regla de negocio incumplida; su mensaje puede mostrarse al usuario."""


class AccesoDenegado(ErrorDominio):
    pass


class NoEncontrado(ErrorDominio):
    pass
