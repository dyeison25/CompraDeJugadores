from dataclasses import asdict, fields
from datetime import datetime, timezone


class Mapper:
    entidad = None
    enteros = ()

    @classmethod
    def desde_datos(cls, datos, documento_id=None):
        valores = dict(datos)
        if documento_id is not None:
            try:
                identificador = int(documento_id)
            except (ValueError, TypeError):
                raise ValueError("El documento no utiliza un identificador numérico de Fichaje.") from None
            if "id" in valores and valores["id"] != identificador:
                raise ValueError("El ID del documento no coincide con el de la entidad.")
            valores["id"] = identificador
        for campo in cls.enteros:
            if not isinstance(valores.get(campo), int) or isinstance(valores.get(campo), bool):
                raise ValueError(f"El campo {campo} debe ser un entero.")
        if valores.get("id", 0) < 0:
            raise ValueError("El identificador no puede ser negativo.")
        fecha = valores.get("fecha")
        if isinstance(fecha, datetime):
            if fecha.tzinfo is None:
                raise ValueError("La fecha debe incluir zona horaria.")
            valores["fecha"] = fecha.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        nombres = {campo.name for campo in fields(cls.entidad)}
        return cls.entidad(**{clave: valores[clave] for clave in nombres})

    @classmethod
    def a_datos(cls, entidad):
        # Solo se serializan campos declarados; nunca objetos del SDK ni conexiones.
        return asdict(entidad)

