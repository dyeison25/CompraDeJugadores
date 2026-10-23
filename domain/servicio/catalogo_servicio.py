from .jugador_servicio import JugadorServicio


class CatalogoServicio:
    """Prepara las consultas y los indicadores publicos del mercado."""

    def __init__(self, jugadores: JugadorServicio):
        self.jugadores = jugadores

    def explorar(self, busqueda="", posicion="", equipo="", orden="") -> dict:
        filtros = {clave: valor.strip()[:100] for clave, valor in (
            ("q", busqueda), ("posicion", posicion), ("equipo", equipo), ("orden", orden)
        )}
        encontrados = self.jugadores.listar(
            filtros["q"], filtros["posicion"], filtros["equipo"], filtros["orden"]
        )
        disponibles = self.jugadores.listar()
        equipos = sorted({jugador.equipo for jugador in disponibles})
        return {
            "jugadores": encontrados,
            "filtros": filtros,
            "equipos": equipos,
            "total": len(disponibles),
            "destacado": disponibles[0] if disponibles else None,
            "total_equipos": len(equipos),
            "total_paises": len({jugador.nacionalidad for jugador in disponibles}),
        }
