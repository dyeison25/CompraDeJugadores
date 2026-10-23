# Analisis estatico del aislamiento de capas

## Ejecutar

```powershell
.\.venv\Scripts\python.exe scripts/analizar_capas.py
.\.venv\Scripts\python.exe scripts/analizar_capas.py --json docs/analisis_capas.json
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_analizador_capas.py -v
```

El analizador utiliza el AST de Python, no ejecuta los modulos del proyecto, no necesita dependencias externas y no lee `.env` ni conecta con Neon. Puedes ejecutarlo con Python 3.12 sin crear Flask. Devuelve codigo **0** si cumple las reglas y **1** si encuentra infracciones, ciclos o imports que requieren revision.

## Reglas verificadas

| Origen | Dependencias permitidas / restricciones |
| --- | --- |
| Entidades | Otras entidades y biblioteca estandar; sin contratos ni servicios |
| Contratos de repositorio | Entidades, otros contratos y biblioteca estandar; sin servicios |
| Servicios | Dominio y biblioteca estandar; sin Flask, ORM, controladores SQL ni infraestructura |
| Infraestructura | Dominio e infraestructura; sin Flask ni capa web; sin servicios de negocio concretos |
| Adaptadores ORM y SQLite | No pueden importarse entre si |
| Capa web | Dominio y componentes web; sin persistencia directa salvo excepciones delimitadas |
| Todas las capas | Sin ciclos entre modulos; imports dinamicos reconocidos y comodines requieren revision |

Se inspeccionan imports absolutos y relativos, incluidos los que aparecen dentro de funciones o bloques `TYPE_CHECKING`. El informe identifica archivo, linea, regla y dependencia que falla. Las excepciones se declaran en `EXCEPCIONES` y requieren un origen y destino exactos.

## Excepciones y acoplamientos existentes

- `FlastR/__init__.py` actua como raiz de composicion: importa la fabrica de persistencia y el adaptador de claves para inyectarlos en los servicios. Tambien importa `sqlalchemy.exc` para convertir errores tecnicos a una respuesta HTTP 503.
- `FlastR/comandos_neon.py` es un adaptador de operaciones de base de datos. Importa modelos ORM y SQLAlchemy para preparar tablas y verificar la conexion. Las rutas HTTP normales no tienen esta excepcion.
- `infraestructura/persistencia.py` utiliza `domain.servicio.datos_demo` para sembrar datos de pruebas/locales.
- Los repositorios utilizan las excepciones de dominio alojadas en `domain.servicio.errores`; se permite ese modulo especifico, no los servicios completos.

Estas dependencias significan que la capa web completa no es independiente de infraestructura: la composicion y los comandos administrativos conocen los adaptadores. El nucleo del dominio si mantiene la direccion de dependencias hacia dentro. Si se exigiera aislamiento estricto de todo `FlastR`, habria que extraer la composicion y los comandos operativos a otro paquete.

## Resultado inicial

36 archivos Python analizados, 109 importaciones, **0 infracciones de las reglas definidas** y **0 ciclos detectados**. El detalle reproducible esta en `docs/analisis_capas.json`. Los conteos cambian al evolucionar el codigo: ejecuta de nuevo el comando para obtener el estado actual.

El flujo `.github/workflows/arquitectura.yml` ejecuta la comprobacion junto con los controles de SQL y credenciales en pushes y pull requests cuando se publique en GitHub. Instala `requirements-analysis.txt`; no necesita credenciales, una base de datos ni instalar las dependencias web. Un fallo marca el job como fallido; exigirlo para fusionar ramas requiere configurar proteccion de ramas en GitHub. Consulta `docs/SEGURIDAD_ESTATICA.md` para las reglas adicionales.

## Alcance y limites

Es una comprobacion de **dependencias expresadas mediante imports**, no una prueba completa de independencia en tiempo de ejecucion. No analiza acceso a objetos mediante `app.extensions`, invocaciones SQL indirectas, plantillas, inyeccion por configuracion, reflexion arbitraria, `eval`/`exec`, ni los imports internos de dependencias externas. El grafo se construye con modulos explicitamente resueltos; no simula todos los efectos de inicializacion o reexportacion de paquetes.

Las llamadas reconocidas a `__import__` e `importlib.import_module` (incluidos aliases directos) se reportan para revision, pero la metaprogramacion puede ocultar otras formas de carga. La prueba complementa las pruebas funcionales y la revision del codigo. Pylint puede revisar otros aspectos de calidad, pero su puntuacion por si sola no demuestra el aislamiento de capas.
