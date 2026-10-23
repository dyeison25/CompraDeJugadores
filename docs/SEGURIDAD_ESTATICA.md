# Analisis estatico de SQL y credenciales

## Checkers y reglas

| Archivo | Responsabilidad |
| --- | --- |
| `scripts/analizar_capas.py` | Reglas de imports en `infraccion`, excepciones exactas en `EXCEPCIONES` y deteccion de ciclos |
| `scripts/analizar_seguridad.py` | Ejecuta Bandit, detect-secrets y comprueba nombres de archivos sensibles en el indice Git |
| `seguridad/excepciones_secretos.json` | Datos ficticios revisados, identificados por archivo, tipo y huella; cada excepcion tiene un motivo |
| `scripts/analizar_proyecto.py` | Ejecuta ambos analizadores y devuelve un codigo de fallo si alguno falla |
| `.github/workflows/arquitectura.yml` | Instala analizadores, prueba los checkers y ejecuta los controles en GitHub Actions |

Bandit aplica **B608** a todo el Python inventariado para detectar construccion dinamica de SQL. Aplica **B105, B106 y B107** al Python fuera de `tests/` para detectar posibles contrasenas literales. Los comentarios `nosec` no desactivan estas reglas. Las pruebas tambien pasan por detect-secrets.

detect-secrets revisa texto UTF-8, incluyendo codigo, pruebas, documentacion y configuracion. Un detector complementario busca credenciales en URL con caracteres especiales. Se usa `--no-verify`: no se prueban claves contra servicios externos. La salida muestra ubicacion y regla, nunca el valor encontrado. Las huellas identifican excepciones; no son un mecanismo para almacenar contrasenas.

## Ejecutar

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-analysis.txt
.\.venv\Scripts\python.exe scripts/analizar_proyecto.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_analizador_*.py' -v
```

El analizador de seguridad devuelve 0 si no hay hallazgos pendientes, 1 ante hallazgos y 2 si no pudo completar la revision. No inicia Flask ni conecta con Neon. El workflow se activara cuando estos archivos se publiquen en GitHub; no configura proteccion de ramas.

## Cambios realizados

- Las consultas SQLite de insercion, listado y actualizacion ahora usan sentencias completas fijas y parametros. Antes habia composicion de identificadores internos: el hallazgo estatico no demostraba una inyeccion explotable, pues los valores ya estaban parametrizados.
- `crear-demo` genera una clave aleatoria distinta por cuenta nueva y la muestra una vez. No modifica cuentas existentes ni rota contrasenas anteriores.
- La verificacion visual genera su clave de sesion en cada ejecucion.
- Las excepciones revisadas corresponden a fixtures de pruebas, una URL ilustrativa de la documentacion y las propias huellas. No se excluyen globalmente las pruebas ni se aceptan automaticamente nuevos hallazgos.

## Alcance y limites

Verificacion local del 23 de octubre de 2026: 36 modulos y 109 imports, sin infracciones ni ciclos; 91 archivos de texto (52 Python), sin hallazgos Bandit ni secretos pendientes y sin archivos sensibles versionados. Se revisaron 16 detecciones de datos ficticios y huellas. Pasaron las 18 pruebas de los checkers y las 81 pruebas funcionales y de analisis con cada adaptador: SQLite directo y ORM sobre SQLite temporal. Estos conteos describen esta revision; vuelve a ejecutar los comandos tras cambiar codigo.

Se omiten entornos virtuales, dependencias, binarios, enlaces simbolicos, `.git`, `.env` privados, `secrets/` e `instance/` y caches. `.env.example`, cuando existe, se analiza. El indice Git se revisa por separado para detectar archivos sensibles versionados aunque su contenido quede excluido. No se inspecciona el historial de commits ni el contenido desplegado en Render.

Son detectores de patrones, no una prueba de ausencia de vulnerabilidades: pueden producir falsos positivos y omitir SQL indirecto o secretos con formatos desconocidos. Las pruebas de regresion verifican entradas con comillas, conservacion de datos y cuentas demo en bases temporales; las pruebas ORM usan SQLite y no certifican el comportamiento especifico de PostgreSQL. No se modificaron datos de Neon.

Los informes JSON opcionales contienen huellas. Guardalos fuera del arbol analizado para que no se detecten sus propios metadatos en la siguiente ejecucion. Revisa cada hallazgo antes de anadir una excepcion; una credencial real requiere retirarla del codigo y rotarla, no exceptuarla.
