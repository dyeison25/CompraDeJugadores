from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import sys
import unittest

from scripts.analizar_seguridad import bandit, clasificar_secretos, inventario, secretos


class AnalizadorSeguridadTests(unittest.TestCase):
    def archivo(self, raiz, nombre, texto):
        ruta = raiz / nombre
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(texto, encoding="utf-8")

    def test_sql_interpolado_detectado_y_parametrizado_permitido(self):
        with TemporaryDirectory() as carpeta:
            raiz = Path(carpeta)
            variantes = [
                'db.execute(f"SELECT * FROM usuarios WHERE email = {entrada}")',
                'db.execute("SELECT * FROM usuarios WHERE email = " + entrada)',
                'db.execute("SELECT * FROM usuarios WHERE email = %s" % entrada)',
                'db.execute("SELECT * FROM usuarios WHERE email = {}".format(entrada))',
                'sql = f"SELECT * FROM usuarios WHERE email = {entrada}"\ndb.execute(sql)',
            ]
            for i, codigo in enumerate(variantes):
                self.archivo(raiz, f"malo{i}.py", codigo)
            self.archivo(raiz, "bien.py", 'db.execute("SELECT * FROM usuarios WHERE email = ?", (entrada,))')
            resultado = bandit(raiz, inventario(raiz))
            self.assertEqual({e["archivo"] for e in resultado if e["regla"] == "B608"},
                             {f"malo{i}.py" for i in range(len(variantes))})

    def test_clave_literal_detectada_sin_publicar_el_valor(self):
        with TemporaryDirectory() as carpeta:
            raiz = Path(carpeta)
            valor = "clave" + "-ficticia-exclusiva-del-checker-12345"
            self.archivo(raiz, "app.py", "SECRET_KEY = " + repr(valor))
            hallazgos = bandit(raiz, inventario(raiz))
            detectados = secretos(raiz, inventario(raiz))
            self.assertTrue(any(e["regla"] == "B105" for e in hallazgos))
            self.assertTrue(detectados)
            self.assertNotIn(valor, json.dumps(hallazgos + detectados))

    def test_credenciales_en_documentacion_y_configuracion(self):
        with TemporaryDirectory() as carpeta:
            raiz = Path(carpeta)
            valor = "prueba" + "CredencialUnica987!"
            self.archivo(raiz, "config.yaml", 'password: "' + valor + '"')
            self.archivo(raiz, "README.md", 'postgresql://usuario:' + valor + '@ejemplo.local/base')
            resultados = secretos(raiz, inventario(raiz))
            self.assertEqual({r["archivo"] for r in resultados}, {"config.yaml", "README.md"})

    def test_excepcion_no_oculta_otro_valor_o_archivo(self):
        registro = {"archivo": "tests/caso.py", "tipo": "Secret Keyword", "huella": "a" * 40, "linea": 1}
        excepcion = {**registro, "motivo": "Dato sintetico de pruebas"}
        otros = [{**registro, "archivo": "app.py"}, {**registro, "huella": "b" * 40}]
        pendientes, revisados = clasificar_secretos([registro, *otros], [excepcion])
        self.assertEqual(len(revisados), 1)
        self.assertEqual(pendientes, otros)

    def test_inventario_no_lee_env_ni_credenciales_locales(self):
        with TemporaryDirectory() as carpeta:
            raiz = Path(carpeta)
            for nombre in (".env", ".env.production", "secrets/cuenta.json", "instance/datos.txt",
                           ".venv/lib/modulo.py", ".git/config", "app.py", ".env.example"):
                self.archivo(raiz, nombre, "dato")
            self.assertEqual(inventario(raiz), [".env.example", "app.py"])

    def test_cli_falla_con_hallazgo_y_no_filtra_secreto(self):
        with TemporaryDirectory() as carpeta:
            raiz = Path(carpeta)
            valor = "dato" + "-falso-para-comprobar-salida-redactada"
            self.archivo(raiz, "app.py", "SECRET_KEY = " + repr(valor))
            script = Path(__file__).resolve().parents[1] / "scripts/analizar_seguridad.py"
            resultado = subprocess.run([sys.executable, str(script), "--raiz", str(raiz)],
                                       capture_output=True, text=True)
            self.assertEqual(resultado.returncode, 1)
            self.assertNotIn(valor, resultado.stdout + resultado.stderr)


if __name__ == "__main__":
    unittest.main()
