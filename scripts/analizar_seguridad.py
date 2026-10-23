"""Bandit y detect-secrets: analisis local, sin red y con salida redactada."""
import argparse
import json
from hashlib import sha1
import os
import re
from pathlib import Path
import subprocess
import sys

OMITIR = {".git", ".venv", "venv", "instance", "secrets", "__pycache__", ".pytest_cache",
          ".agents", ".codex", ".aws", "node_modules", ".mypy_cache", ".ruff_cache", "htmlcov"}


def inventario(raiz):
    archivos = []
    for carpeta, directorios, nombres in os.walk(raiz):
        directorios[:] = sorted(d for d in directorios if d not in OMITIR and not (Path(carpeta) / d).is_symlink())
        for nombre in sorted(nombres):
            ruta = Path(carpeta) / nombre
            if ruta.is_symlink() or (nombre.startswith(".env") and nombre != ".env.example"):
                continue
            try:
                contenido = ruta.read_bytes()
                if b"\x00" in contenido:
                    continue
                contenido.decode("utf-8-sig")
            except UnicodeError:
                continue
            archivos.append(ruta.relative_to(raiz).as_posix())
    return sorted(archivos)


def ejecutar_json(comando, raiz, permitidos=(0,)):
    resultado = subprocess.run(comando, cwd=raiz, capture_output=True, encoding="utf-8", errors="replace",
                               timeout=180, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if resultado.returncode not in permitidos:
        # Nunca imprimir stderr/stdout crudos: podrian incluir una linea con secretos.
        raise RuntimeError("No se pudo ejecutar el analizador. Instala requirements-analysis.txt.")
    try:
        return json.loads(resultado.stdout)
    except ValueError:
        raise RuntimeError("El analizador no devolvio un informe JSON valido.") from None


def ruta_relativa(nombre):
    return nombre.replace("\\", "/").removeprefix("./")


def bandit(raiz, archivos):
    python = [f for f in archivos if f.endswith(".py")]
    if not python:
        raise RuntimeError("No hay archivos Python que analizar.")
    base = [sys.executable, "-m", "bandit", "-q", "--ignore-nosec", "-f", "json", "-t"]
    hallazgos = []
    grupos = [("B608", python), ("B105,B106,B107", [f for f in python if not f.startswith("tests/")])]
    for reglas, rutas in grupos:
        if not rutas:
            continue
        informe = ejecutar_json([*base, reglas, *rutas], raiz, (0, 1))
        if informe.get("errors"):
            raise RuntimeError("Bandit no pudo analizar todos los archivos Python.")
        for item in informe["results"]:
            hallazgos.append({"archivo": ruta_relativa(item["filename"]), "linea": item["line_number"],
                              "regla": item["test_id"], "severidad": item["issue_severity"],
                              "confianza": item["issue_confidence"]})
    return hallazgos


def secretos(raiz, archivos):
    if not archivos:
        raise RuntimeError("No hay archivos que analizar.")
    informe = ejecutar_json([sys.executable, "-m", "detect_secrets", "scan", "--no-verify", "--all-files",
                              *archivos], raiz)
    encontrados = []
    for archivo, items in informe["results"].items():
        for item in items:
            encontrados.append({"archivo": ruta_relativa(archivo), "linea": item["line_number"],
                                "tipo": item["type"], "huella": item["hashed_secret"]})
    # Complementa el detector de Basic Auth para contrasenas con !, $, etc.
    # No conecta a las URL ni muestra usuario, host o contrasena.
    patron = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://[^\s:/@\"'{}]+:([^\s@\"'{}]+)@")
    for archivo in archivos:
        for numero, linea in enumerate((raiz / archivo).read_text(encoding="utf-8-sig").splitlines(), 1):
            for coincidencia in patron.finditer(linea):
                encontrados.append({"archivo": archivo, "linea": numero, "tipo": "Basic Auth Credentials",
                                    "huella": sha1(coincidencia.group(1).encode(), usedforsecurity=False).hexdigest()})
    encontrados = list({(e["archivo"], e["linea"], e["tipo"], e["huella"]): e for e in encontrados}.values())
    return encontrados


def clasificar_secretos(encontrados, excepciones):
    permitidos = {(e["archivo"], e["tipo"], e["huella"]): e["motivo"] for e in excepciones if e.get("motivo")}
    # Las huellas SHA-1 del archivo de excepciones son identificadores publicos,
    # no claves. Se exceptuan solo sus valores exactos, no el archivo completo.
    for entrada in excepciones:
        huella = entrada["huella"]
        if len(huella) == 40 and all(c in "0123456789abcdef" for c in huella):
            permitidos[("seguridad/excepciones_secretos.json", "Hex High Entropy String",
                        sha1(huella.encode(), usedforsecurity=False).hexdigest())] = "Huella de un dato ficticio revisado, no una credencial."
    pendientes, revisados = [], []
    for item in encontrados:
        clave = (item["archivo"], item["tipo"], item["huella"])
        if clave in permitidos:
            revisados.append({**item, "motivo": permitidos[clave]})
        else:
            pendientes.append(item)
    return pendientes, revisados


def archivos_sensibles_versionados(raiz):
    if not (raiz / ".git").exists():
        return [], False
    resultado = subprocess.run(["git", "-c", "safe.directory=" + raiz.as_posix(), "ls-files", "-z"],
                               cwd=raiz, capture_output=True, timeout=30)
    if resultado.returncode:
        raise RuntimeError("No se pudo revisar el indice de Git.")
    prohibidos = []
    for nombre in resultado.stdout.decode("utf-8").split("\0"):
        if not nombre:
            continue
        ruta = Path(nombre)
        if (ruta.parts[0] in {"instance", "secrets", ".venv", ".aws"}
                or (ruta.name.startswith(".env") and ruta.name != ".env.example")
                or ruta.suffix in {".pem", ".key", ".sqlite", ".db"}):
            prohibidos.append(nombre)
    return prohibidos, True


def analizar(raiz):
    raiz = Path(raiz).resolve()
    archivos = inventario(raiz)
    fichero = raiz / "seguridad/excepciones_secretos.json"
    excepciones = json.loads(fichero.read_text(encoding="utf-8"))["excepciones"] if fichero.exists() else []
    hallazgos = bandit(raiz, archivos)
    pendientes, revisados = clasificar_secretos(secretos(raiz, archivos), excepciones)
    versionados, git_revisado = archivos_sensibles_versionados(raiz)
    return {"archivos_texto": len(archivos), "python": sum(f.endswith(".py") for f in archivos),
            "bandit": hallazgos, "secretos_pendientes": pendientes, "hallazgos_revisados": revisados,
            "archivos_sensibles_versionados": versionados, "indice_git_revisado": git_revisado,
            "correcto": not (hallazgos or pendientes or versionados)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    try:
        informe = analizar(args.raiz)
    except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError, KeyError):
        print("No se completo la revision. Comprueba las dependencias y la configuracion de los analizadores.")
        return 2
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Archivos de texto: {informe['archivos_texto']} | Python: {informe['python']}")
    print(f"Bandit: {len(informe['bandit'])} | Secretos pendientes: {len(informe['secretos_pendientes'])} | "
          f"Hallazgos revisados (datos ficticios y huellas): {len(informe['hallazgos_revisados'])} | "
          f"Archivos sensibles versionados: {len(informe['archivos_sensibles_versionados'])}")
    for item in informe["bandit"]:
        print(f"{item['archivo']}:{item['linea']} [{item['regla']}]")
    for item in informe["secretos_pendientes"]:
        print(f"{item['archivo']}:{item['linea']} [CREDENCIAL: {item['tipo']}] valor oculto")
    for archivo in informe["archivos_sensibles_versionados"]:
        print(f"{archivo} [ARCHIVO_SENSIBLE_VERSIONADO]")
    return 0 if informe["correcto"] else 1


if __name__ == "__main__":
    sys.exit(main())
