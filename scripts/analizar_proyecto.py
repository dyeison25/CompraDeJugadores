"""Punto de entrada conjunto para arquitectura, SQL y credenciales."""
from pathlib import Path
import subprocess
import sys


def main():
    raiz = Path(__file__).resolve().parents[1]
    resultados = [subprocess.run([sys.executable, str(raiz / "scripts" / script)], cwd=raiz).returncode
                  for script in ("analizar_capas.py", "analizar_seguridad.py")]
    return max(resultados)


if __name__ == "__main__":
    sys.exit(main())
