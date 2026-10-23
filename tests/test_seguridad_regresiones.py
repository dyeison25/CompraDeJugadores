from dataclasses import replace
from unittest.mock import Mock

import pytest

from infraestructura.sqlite.repositorios import insertar


def test_demo_claves_aleatorias_y_cuentas_existentes(app):
    runner = app.test_cli_runner()
    resultado = runner.invoke(args=["crear-demo"])
    assert resultado.exit_code == 0
    cuentas = []
    for linea in resultado.output.splitlines():
        if " / " in linea:
            correo, clave = linea.split(": ", 1)[1].split(" / ")
            usuario = app.extensions["auth"].iniciar_sesion(correo, clave)
            cuentas.append((usuario, clave))
    assert len(cuentas) == 2
    assert cuentas[0][1] != cuentas[1][1]
    assert all(len(clave) >= 24 for _, clave in cuentas)
    assert {usuario.rol for usuario, _ in cuentas} == {"admin", "usuario"}
    repetido = runner.invoke(args=["crear-demo"])
    assert repetido.exit_code == 0
    assert " / " not in repetido.output
    for usuario, clave in cuentas:
        actual = app.extensions["auth"].iniciar_sesion(usuario.email, clave)
        assert actual == usuario


def test_sql_con_comillas_se_conserva_como_dato(app):
    servicio = app.extensions["jugadores"]
    repositorio = servicio.jugadores
    original = repositorio.listar()[0]
    nombre = "O'Brien'); DROP TABLE jugadores; --"
    nuevo = repositorio.agregar(replace(original, id=0, nombre=nombre))
    assert repositorio.obtener(nuevo.id).nombre == nombre
    actualizado = repositorio.actualizar(replace(nuevo, equipo=nombre), nuevo.version)
    assert repositorio.obtener(nuevo.id).equipo == nombre
    assert actualizado.version == nuevo.version + 1
    assert repositorio.obtener(original.id) == original
    assert app.extensions["auth"].buscar_por_email("' OR 1=1 --") is None


def test_insertar_rechaza_identificadores_fuera_de_lista():
    conexion = Mock()
    with pytest.raises(ValueError, match="Tabla no permitida"):
        insertar(conexion, "usuarios; DROP TABLE jugadores", {})
    conexion.execute.assert_not_called()
