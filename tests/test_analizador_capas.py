from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.analizar_capas import analizar


class AnalizadorCapasTests(unittest.TestCase):
    def revisar(self, archivos):
        with TemporaryDirectory() as carpeta:
            raiz = Path(carpeta)
            for capa in ("domain", "infraestructura", "FlastR"):
                (raiz / capa).mkdir()
            for nombre, texto in archivos.items():
                archivo = raiz / nombre
                archivo.parent.mkdir(parents=True, exist_ok=True)
                archivo.write_text(texto, encoding="utf-8")
            return analizar(raiz)

    def reglas(self, archivos):
        return {e["regla"] for e in self.revisar(archivos)["errores"]}

    def test_dependencias_permitidas(self):
        self.assertFalse(self.revisar({
            "domain/entidades/jugador.py": "from dataclasses import dataclass",
            "domain/repositorios/contratos.py": "from domain.entidades.jugador import Jugador",
            "domain/servicio/jugadores.py": "from domain.repositorios.contratos import Repositorio",
            "infraestructura/orm/repo.py": "from sqlalchemy import select\nfrom domain.repositorios import Repositorio",
            "FlastR/rutas.py": "from domain.servicio.jugadores import Servicio",
        })["errores"])

    def test_import_en_funcion_y_type_checking(self):
        reglas = self.reglas({"domain/servicio/malo.py":
            "def ejecutar():\n    import sqlalchemy\nif TYPE_CHECKING:\n    import flask"})
        self.assertIn("DOMINIO_EXTERNO", reglas)

    def test_relativa_entidad_no_depende_servicio(self):
        self.assertIn("ENTIDAD_DEPENDE_CAPA_SUPERIOR", self.reglas({
            "domain/entidades/jugador.py": "from ..servicio.compra import comprar"}))

    def test_from_paquete_import_modulo(self):
        self.assertIn("DOMINIO_EXTERNO", self.reglas({
            "domain/servicio/malo.py": "from infraestructura import seguridad",
            "infraestructura/seguridad.py": ""}))

    def test_contratos_no_dependen_servicios(self):
        self.assertIn("CONTRATO_DEPENDE_SERVICIO", self.reglas({
            "domain/repositorios/contratos.py": "from ..servicio import comprar"}))

    def test_infraestructura_no_depende_web_ni_servicios(self):
        reglas = self.reglas({"infraestructura/repo.py":
            "import FlastR\nfrom domain.servicio.compra_servicio import CompraServicio"})
        self.assertTrue({"INFRAESTRUCTURA_DEPENDE_WEB", "ADAPTADOR_DEPENDE_SERVICIO"} <= reglas)

    def test_adaptadores_independientes(self):
        self.assertIn("ADAPTADORES_ACOPLADOS", self.reglas({
            "infraestructura/orm/repo.py": "from ..sqlite import repositorios"}))

    def test_excepcion_limitada_a_modulo_y_destino(self):
        informe = self.revisar({
            "FlastR/__init__.py": "from infraestructura.persistencia import crear_persistencia",
            "FlastR/rutas.py": "from infraestructura.persistencia import crear_persistencia",
            "FlastR/comandos_neon.py": "from infraestructura.orm.repositorios import CompraRepositorioORM",
        })
        self.assertEqual(len(informe["errores"]), 2)
        self.assertTrue(all(e["regla"] == "WEB_DEPENDE_PERSISTENCIA" for e in informe["errores"]))

    def test_imports_dinamicos_y_comodines(self):
        reglas = self.reglas({"domain/servicio/malo.py":
            "import importlib as il\nfrom importlib import import_module as cargar\n"
            "il.import_module('flask')\ncargar('sqlalchemy')\n__import__('sqlite3')\nfrom typing import *"})
        self.assertTrue({"IMPORT_DINAMICO", "IMPORT_COMODIN"} <= reglas)

    def test_ciclo_relativo(self):
        informe = self.revisar({
            "domain/servicio/a.py": "from .b import B",
            "domain/servicio/b.py": "from .a import A",
        })
        self.assertEqual(informe["ciclos"], [["domain.servicio.a", "domain.servicio.b"]])

    def test_sintaxis_y_relativa_invalida(self):
        self.assertIn("SINTAXIS", self.reglas({"domain/malo.py": "def :"}))
        self.assertIn("IMPORT_RELATIVO", self.reglas({"domain/malo.py": "from ...afuera import x"}))

    def test_raiz_incorrecta_no_aprueba_silenciosamente(self):
        with TemporaryDirectory() as carpeta:
            self.assertIn("CAPA_AUSENTE", {e["regla"] for e in analizar(carpeta)["errores"]})


if __name__ == "__main__":
    unittest.main()
