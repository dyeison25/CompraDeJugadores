"""Analisis AST de dependencias, sin importar la aplicacion ni leer .env."""
import argparse
import ast
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys

CAPAS = ("domain", "infraestructura", "FlastR")
PERSISTENCIA = {"sqlite3", "sqlalchemy", "psycopg", "psycopg2"}
# Puntos de composicion/operacion: excepciones exactas, no carpetas completas.
EXCEPCIONES = {
    "FlastR": {"infraestructura.persistencia", "infraestructura.seguridad", "sqlalchemy.exc"},
    "FlastR.comandos_neon": {"infraestructura.orm.modelos", "sqlalchemy", "sqlalchemy.exc"},
    "infraestructura.persistencia": {"domain.servicio.datos_demo"},
}


@dataclass(frozen=True)
class Dependencia:
    origen: str
    destino: str
    archivo: str
    linea: int


def pertenece(modulo, paquete):
    return modulo == paquete or modulo.startswith(paquete + ".")


def infraccion(origen, destino):
    if destino in EXCEPCIONES.get(origen, set()):
        return None
    raiz = destino.split(".")[0]
    if pertenece(origen, "domain"):
        if raiz != "domain" and (raiz not in sys.stdlib_module_names or raiz in PERSISTENCIA):
            return "DOMINIO_EXTERNO"
        if pertenece(origen, "domain.entidades") and raiz == "domain" and not pertenece(destino, "domain.entidades"):
            return "ENTIDAD_DEPENDE_CAPA_SUPERIOR"
        if pertenece(origen, "domain.repositorios") and raiz == "domain" and not any(
                pertenece(destino, p) for p in ("domain.entidades", "domain.repositorios")):
            return "CONTRATO_DEPENDE_SERVICIO"
    if pertenece(origen, "infraestructura"):
        if raiz in {"FlastR", "flask", "app"}:
            return "INFRAESTRUCTURA_DEPENDE_WEB"
        if pertenece(destino, "domain.servicio") and destino != "domain.servicio.errores":
            return "ADAPTADOR_DEPENDE_SERVICIO"
        for actual, otro in (("orm", "sqlite"), ("sqlite", "orm")):
            if pertenece(origen, "infraestructura." + actual) and pertenece(destino, "infraestructura." + otro):
                return "ADAPTADORES_ACOPLADOS"
    if pertenece(origen, "FlastR"):
        if raiz == "infraestructura" or raiz in PERSISTENCIA:
            return "WEB_DEPENDE_PERSISTENCIA"
    return None


def resolver_from(nodo, modulo, es_paquete):
    if not nodo.level:
        return nodo.module or ""
    partes = modulo.split(".") if es_paquete else modulo.split(".")[:-1]
    if nodo.level > len(partes):
        raise ValueError("Importacion relativa fuera del paquete")
    base = partes[:len(partes) - nodo.level + 1]
    if nodo.module:
        base.extend(nodo.module.split("."))
    return ".".join(base)


def ciclos(grafo):
    # Tarjan: reporta componentes fuertemente conexas, sin repetir cada camino.
    indices, bajos, pila, activos, resultado = {}, {}, [], set(), []
    def visitar(nodo):
        indices[nodo] = bajos[nodo] = len(indices)
        pila.append(nodo)
        activos.add(nodo)
        for vecino in sorted(grafo[nodo]):
            if vecino not in indices:
                visitar(vecino)
                bajos[nodo] = min(bajos[nodo], bajos[vecino])
            elif vecino in activos:
                bajos[nodo] = min(bajos[nodo], indices[vecino])
        if bajos[nodo] == indices[nodo]:
            componente = []
            while True:
                vecino = pila.pop()
                activos.remove(vecino)
                componente.append(vecino)
                if vecino == nodo:
                    break
            if len(componente) > 1:
                resultado.append(sorted(componente))
    for nodo in sorted(grafo):
        if nodo not in indices:
            visitar(nodo)
    return sorted(resultado)


def analizar(raiz):
    raiz = Path(raiz).resolve()
    archivos = {}
    for capa in CAPAS:
        for archivo in sorted((raiz / capa).rglob("*.py")):
            if "__pycache__" in archivo.parts:
                continue
            partes = list(archivo.relative_to(raiz).with_suffix("").parts)
            if partes[-1] == "__init__":
                partes.pop()
            archivos[".".join(partes)] = archivo
    dependencias, errores = [], []
    def error(archivo, linea, regla, detalle):
        errores.append({"archivo": archivo, "linea": linea, "regla": regla, "detalle": detalle})
    for capa in CAPAS:
        if not (raiz / capa).is_dir():
            error(capa, 0, "CAPA_AUSENTE", "No se encontro la carpeta de la capa")
    for modulo, archivo in archivos.items():
        relativo = archivo.relative_to(raiz).as_posix()
        try:
            arbol = ast.parse(archivo.read_text(encoding="utf-8-sig"), filename=relativo)
        except (SyntaxError, UnicodeError) as exc:
            error(relativo, getattr(exc, "lineno", 0), "SINTAXIS", str(exc))
            continue
        alias_dinamicos = {"__import__"}
        alias_importlib = {"importlib"}
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                for alias in nodo.names:
                    if alias.name == "importlib":
                        alias_importlib.add(alias.asname or alias.name)
            if isinstance(nodo, ast.ImportFrom) and nodo.module in {"importlib", "builtins"}:
                for alias in nodo.names:
                    if alias.name in {"import_module", "__import__"}:
                        alias_dinamicos.add(alias.asname or alias.name)
        for nodo in ast.walk(arbol):
            destinos = []
            if isinstance(nodo, ast.Import):
                destinos = [alias.name for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom):
                try:
                    base = resolver_from(nodo, modulo, archivo.name == "__init__.py")
                except ValueError as exc:
                    error(relativo, nodo.lineno, "IMPORT_RELATIVO", str(exc))
                    continue
                destinos = [base + "." + alias.name if base + "." + alias.name in archivos else base
                            for alias in nodo.names]
                if any(alias.name == "*" for alias in nodo.names):
                    error(relativo, nodo.lineno, "IMPORT_COMODIN", "Declara los nombres importados explicitamente")
            elif isinstance(nodo, ast.Call):
                funcion = nodo.func
                dinamico = (isinstance(funcion, ast.Name) and funcion.id in alias_dinamicos) or (
                    isinstance(funcion, ast.Attribute) and isinstance(funcion.value, ast.Name)
                    and funcion.value.id in alias_importlib and funcion.attr == "import_module")
                if dinamico:
                    error(relativo, nodo.lineno, "IMPORT_DINAMICO", "Requiere revision; no puede certificar aislamiento")
            for destino in sorted(set(destinos)):
                dep = Dependencia(modulo, destino, relativo, nodo.lineno)
                dependencias.append(dep)
                regla = infraccion(modulo, destino)
                if regla:
                    error(relativo, nodo.lineno, regla, modulo + " -> " + destino)
    grafo = {modulo: set() for modulo in archivos}
    for dep in dependencias:
        if dep.destino in archivos and dep.origen != dep.destino:
            grafo[dep.origen].add(dep.destino)
    encontrados = ciclos(grafo)
    for ciclo in encontrados:
        error(archivos[ciclo[0]].relative_to(raiz).as_posix(), 0, "CICLO", ", ".join(ciclo))
    return {"archivos": len(archivos), "importaciones": len(dependencias), "errores": errores,
            "ciclos": encontrados, "excepciones": {k: sorted(v) for k, v in EXCEPCIONES.items()},
            "dependencias": [asdict(d) for d in dependencias]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", type=Path, help="Guardar informe JSON en la ruta indicada")
    args = parser.parse_args()
    informe = analizar(args.raiz)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Archivos: {informe['archivos']} | Importaciones: {informe['importaciones']} | "
          f"Infracciones: {len(informe['errores'])} | Ciclos: {len(informe['ciclos'])}")
    for error in informe["errores"]:
        print(f"{error['archivo']}:{error['linea']} [{error['regla']}] {error['detalle']}")
    return 1 if informe["errores"] else 0


if __name__ == "__main__":
    sys.exit(main())
