"""Datos ilustrativos: no son cotizaciones ni disponibilidad reales."""
JUGADORES_DEMO = [
    ("Kylian Mbappé", "Real Madrid", "Francia", 27, "Delantero", 18000000000, "mbappe.png", 10, "Velocidad que cambia partidos. Un delantero explosivo, con desmarque y definición de élite.", 1),
    ("Erling Haaland", "Manchester City", "Noruega", 26, "Delantero", 17500000000, "haaland.png", 9, "Potencia, intuición y gol. La referencia ofensiva para llevar a tu equipo al siguiente nivel.", 1),
    ("Jude Bellingham", "Real Madrid", "Inglaterra", 23, "Centrocampista", 15000000000, "bellingham.png", 5, "Talento en cada zona del campo. Un centrocampista con llegada, visión y personalidad.", 1),
    ("Luis Díaz", "Bayern Múnich", "Colombia", 29, "Delantero", 7000000000, "diaz.png", 14, "El desequilibrio tiene acento colombiano. Regate, intensidad y creatividad por la banda.", 1),
    ("Lionel Messi", "Inter Miami", "Argentina", 39, "Delantero", 2500000000, "messi.png", 10, "Una zurda para imaginar lo imposible. Visión de juego, precisión y magia entre líneas.", 0),
    ("Virgil van Dijk", "Liverpool", "Países Bajos", 35, "Defensa", 3000000000, "vandijk.png", 4, "Liderazgo desde la defensa. Seguridad en el juego aéreo y criterio en la salida de balón.", 0),
    ("Alisson Becker", "Liverpool", "Brasil", 33, "Portero", 3500000000, "alisson.png", 1, "Confianza bajo los tres palos. Reflejos, colocación y una salida de balón que inicia el ataque.", 0),
    ("Pedri", "FC Barcelona", "España", 23, "Centrocampista", 13000000000, "pedri.png", 8, "El ritmo del partido en sus botas. Control, pase y una lectura privilegiada de los espacios.", 0),
]


def jugadores_demo():
    from domain.entidades import Jugador

    return [Jugador(
        id=0, nombre=fila[0], equipo=fila[1], nacionalidad=fila[2], edad=fila[3],
        posicion=fila[4], precio_centimos=fila[5], foto="/static/img/jugadores/" + fila[6],
        dorsal=fila[7], descripcion=fila[8], destacado=fila[9], estado="disponible", version=1,
    ) for fila in JUGADORES_DEMO]
