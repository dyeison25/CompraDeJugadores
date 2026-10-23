# Fichaje · Mercado de jugadores de fútbol

Aplicación web en español con Flask, PostgreSQL en Neon y SQLAlchemy como ORM. Incluye fotos, catálogo con filtros, registro, inicio de sesión, roles, administración de jugadores y compras simuladas. Conserva un adaptador alternativo de SQLite.

La configuración y arquitectura actuales están en [Neon y SQLAlchemy](docs/NEON.md). Cambiar de base no traslada registros automáticamente.

## Desplegar en Render

Consulta [la guia de Render](docs/RENDER.md). El repositorio incluye `render.yaml` para el plan gratuito, usando Neon y fotos por URL HTTPS.

## Iniciar en Windows / PowerShell

Desde la carpeta del proyecto:

```powershell
.\.venv\Scripts\python.exe app.py
```

Abre **http://127.0.0.1:5000**.

Si copias el proyecto a otro equipo, prepara primero el entorno:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app app inicializar-neon
.\.venv\Scripts\python.exe scripts\descargar_recursos.py
.\.venv\Scripts\python.exe scripts\generar_diagramas.py
.\.venv\Scripts\python.exe -m flask --app app crear-demo
.\.venv\Scripts\python.exe app.py
```

Las fotos y fuentes ya descargadas se sirven localmente. Si las copias junto con el proyecto, no necesitas volver a descargarlas.

## Cuentas de demostración

El comando `crear-demo` crea estas cuentas, sin sobrescribir ninguna existente:

| Rol | Correo | Contraseña |
| --- | --- | --- |
| Administrador | admin@fichaje.local | Admin123! |
| Usuario | usuario@fichaje.local | Usuario123! |

Son credenciales conocidas para la demostración local. La aplicación **no crea cuentas automáticamente** al iniciarse. Para crear un administrador propio:

```powershell
.\.venv\Scripts\python.exe -m flask --app app crear-admin
```

El comando solicita nombre, correo y contraseña. El registro de la página siempre crea cuentas de usuario.

## Arquitectura solicitada

Se conserva el nombre **FlastR** indicado en el enunciado. El framework utilizado es **Flask**.

```text
Tendencias De Software/
├── app.py                         # Punto de entrada
├── FlastR/                        # Capa web Flask
│   ├── __init__.py                # create_app, configuración, sesión, CSRF y CLI
│   ├── rutas.py                   # Rutas públicas, usuario y administrador
│   ├── imagenes.py                # Validación y almacenamiento de fotos
│   ├── templates/                 # Vistas Jinja
│   └── static/
│       ├── css/                   # Diseño adaptable
│       ├── js/                    # Interacciones y vista previa de fotos
│       ├── img/jugadores/         # Fotografías locales
│       ├── fonts/                 # Tipografías y licencias
│       ├── uploads/               # Fotos cargadas por el administrador
│       └── diagramas/             # Diagramas SVG
├── domain/
│   ├── entidades/
│   │   ├── usuario.py
│   │   ├── jugador.py
│   │   └── compra.py
│   └── servicio/
│       ├── autenticacion_servicio.py
│       ├── jugador_servicio.py
│       ├── compra_servicio.py
│       ├── datos_demo.py
│       └── errores.py
├── infraestructura/               # Repositorios, mappers y conexiones
│   ├── orm/                       # SQLAlchemy: modelos, sesiones, mappers y repositorios
│   ├── sqlite/                    # Adaptador SQLite original
│   └── mappers/                   # Conversión compartida de entidades
├── docs/                          # Explicación y fuentes PlantUML
├── scripts/                       # Descargas, diagramas y verificación visual
├── tests/                         # Pruebas de reglas y flujos HTTP
├── instance/                      # SQLite y clave de sesión; no versionar
├── requirements.txt
└── requirements-dev.txt
```

Flujo de una petición: **navegador → FlastR/rutas.py → servicios → contratos de repositorios → adaptador ORM y mappers → PostgreSQL**. La respuesta vuelve a las plantillas Jinja.

`domain` no importa Flask ni SQLAlchemy. Las entidades son dataclasses y los servicios contienen las reglas de negocio. Los contratos están en `domain/repositorios`; SQLAlchemy y sus modelos pertenecen a infraestructura.

## Funciones

La aplicación tiene cinco servicios de negocio en `domain/servicio`:

| Servicio | Responsabilidad |
| --- | --- |
| `AutenticacionServicio` | Cuentas, credenciales y roles |
| `JugadorServicio` | Validación y administración de jugadores |
| `CompraServicio` | Registro de compras e historial |
| `CatalogoServicio` | Búsquedas, filtros y datos públicos del mercado |
| `EstadisticaServicio` | Métricas del administrador y resumen personal de compras |

`CatalogoServicio.explorar()` prepara el catálogo y sus indicadores. `EstadisticaServicio.resumen_admin()` calcula disponibilidad, valor del mercado y ventas; `resumen_usuario()` calcula el gasto y devuelve únicamente las compras del usuario indicado, después de comprobar su rol. Las rutas toman ese identificador de la sesión autenticada. Los nuevos servicios se inyectan desde la fábrica Flask, sin depender del ORM ni modificar el esquema de Neon.

- Catálogo con fotografía, equipo, nacionalidad, posición, edad y precio.
- Búsqueda por jugador, equipo o país; filtros de posición y club; orden por precio, nombre, novedades y destacados.
- Detalle de cada jugador y confirmación de compra.
- Registro, inicio y cierre de sesión; contraseñas almacenadas con hash scrypt.
- Administrador: agregar, editar y eliminar jugadores; subir foto JPG/PNG/WebP o utilizar una URL HTTPS; consultar métricas.
- Usuario: comprar jugadores disponibles y consultar su propio historial.
- Una compra retira al jugador del catálogo. El servidor toma el precio de la base y comprueba la versión mostrada.
- Transacción PostgreSQL con bloqueo del jugador y restricción única de compra para evitar ventas duplicadas.
- CSRF en formularios de escritura, permisos tanto en rutas como en servicios, SQL parametrizado, imágenes recodificadas, límite de 5 MB y límite de 16 megapíxeles.
- Los jugadores vendidos no se editan ni eliminan, para conservar el historial.
- Neon no recibe jugadores de ejemplo automáticamente. La semilla del adaptador SQLite se aplica una sola vez.

Los valores, edades, equipos y disponibilidad de la semilla son **datos ilustrativos**. No son una oferta ni una fuente de datos deportivos en tiempo real. Todas las compras son simuladas, sin pasarela de pagos.

## Diagramas

El [diagrama de persistencia actual con ORM](docs/NEON.md#arquitectura) muestra repositorios, mappers y modelos. Los SVG y PlantUML siguientes corresponden a la versión inicial con SQLite.

- [Explicación y casos de uso paso a paso](docs/DIAGRAMAS.md)
- [Diagrama de clases SVG](FlastR/static/diagramas/clases.svg)
- [Diagrama de casos de uso SVG](FlastR/static/diagramas/casos-de-uso.svg)
- [Clases: fuente PlantUML](docs/clases.puml)
- [Casos de uso: fuente PlantUML](docs/casos-de-uso.puml)

También se pueden consultar en **http://127.0.0.1:5000/diagramas**.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest -q --orm-sqlite
.\.venv\Scripts\python.exe scripts\verificar_interfaz.py
```

Las pruebas de dominio y HTTP usan bases de datos temporales. La verificación visual también utiliza una base aislada y ejecuta Edge sin abrir ventanas; requiere Microsoft Edge instalado. Genera capturas en `docs/capturas/`.

## Configuración y datos

Copia `.env.example` como `.env` y completa tu conexión local. Git excluye `.env`, credenciales, bases locales, respaldos, archivos subidos y el entorno virtual. El repositorio incluye únicamente la plantilla de configuración sin secretos.

- Base activa: `DATABASE_URL` en `.env` para Neon y `DATABASE_BACKEND=postgresql`. Sin backend explícito se prioriza Neon, luego SQLite.
- SQLite alternativo: `instance/fichaje.sqlite`.
- Clave de sesión: variable de entorno `SECRET_KEY`; si falta, se genera una clave aleatoria persistente en `instance/.secret_key`.
- `COOKIE_SECURE=1` activa cookies exclusivas para HTTPS.
- Sesiones de hasta ocho horas; modo depuración desactivado.
- `SEED_DEMO=False` puede pasarse a `create_app` para iniciar una nueva base sin jugadores de ejemplo.
- Para un servidor WSGI local: `.\.venv\Scripts\waitress-serve.exe --host=127.0.0.1 --port=5000 app:app`.

La base SQLite, la clave de sesión y las imágenes subidas deben conservarse para mantener los datos. Las cuentas demo son exclusivamente para uso local; una publicación real debe usar una base nueva, administradores propios, HTTPS y controles de despliegue adecuados.

## Recursos y referencias

Las fotos de ejemplo proceden de FUTBIN (retratos de EA FC 25) y ESPN (Messi) y se incluyen para la demostración académica. Los derechos de las imágenes pertenecen a sus titulares; para distribuir un producto, sustitúyelas por fotos con autorización o licencia adecuada. El administrador permite usar imágenes propias.

Fuentes de las fotos: [Mbappé](https://cdn.futbin.com/content/fifa25/img/players/231747.png), [Haaland](https://cdn.futbin.com/content/fifa25/img/players/239085.png), [Bellingham](https://cdn.futbin.com/content/fifa25/img/players/252371.png), [Díaz](https://cdn.futbin.com/content/fifa25/img/players/241084.png), [Messi](https://a.espncdn.com/i/headshots/soccer/players/full/45843.png), [Van Dijk](https://cdn.futbin.com/content/fifa25/img/players/203376.png), [Alisson](https://cdn.futbin.com/content/fifa25/img/players/212831.png), [Pedri](https://cdn.futbin.com/content/fifa25/img/players/251854.png). Las fotos ilustran al jugador y pueden mostrar una camiseta de otra temporada.

Tipografías Manrope y Barlow Condensed, distribuidas bajo SIL Open Font License; los textos de licencia están en `FlastR/static/fonts/`. Iconos y diagramas son SVG locales.

Referencia técnica: [fábricas de aplicaciones de Flask](https://flask.palletsprojects.com/en/stable/patterns/appfactories/) y [guía oficial de Flask](https://flask.palletsprojects.com/en/stable/quickstart/).
