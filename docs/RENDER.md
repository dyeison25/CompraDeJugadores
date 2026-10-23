# Despliegue en Render con Neon

El archivo `render.yaml` define un Web Service de Python en el plan **Free**, con Waitress (servidor WSGI), puerto `$PORT`, HTTPS mediante Render y comprobacion de proceso `/healthz`. No crea otra base de datos ni ejecuta migraciones o cuentas de ejemplo. Reutiliza las tablas y registros de Neon.

## Crear el servicio

1. Entra a https://dashboard.render.com/ y conecta GitHub.
2. Selecciona **New > Blueprint** y el repositorio `dyeison25/CompraDeJugadores`, rama `main`.
3. Render detectara `render.yaml`. Confirma que el plan sea **Free**.
4. Completa `DATABASE_URL` con la cadena de Neon que tienes en `.env`. No la pegues en el chat ni la subas a GitHub.
5. Crea el servicio. El Blueprint genera `SECRET_KEY` y configura las demas variables.
6. Cuando termine, abre la URL HTTPS que Render muestra para el servicio.

No subas `.env`. `SECRET_KEY` debe mantenerse entre despliegues para conservar las sesiones. `COOKIE_SECURE=1` hace que las cookies viajen por HTTPS. Si Render no tiene clave o conexion PostgreSQL, la aplicacion detiene el arranque con un mensaje de configuracion.

Si creas un Web Service manualmente en vez de un Blueprint, utiliza:

| Campo | Valor |
| --- | --- |
| Runtime | Python 3 |
| Branch | main |
| Build command | `pip install -r requirements.txt` |
| Start command | `waitress-serve --host=0.0.0.0 --port=$PORT app:app` |
| Health check | `/healthz` |
| Plan | Free |

Configura `DATABASE_BACKEND=postgresql`, `DATABASE_URL`, una `SECRET_KEY` aleatoria persistente, `COOKIE_SECURE=1` y `ALLOW_UPLOADS=0`. `.python-version` selecciona Python 3.12. Para generar una clave en tu terminal: `python -c "import secrets; print(secrets.token_hex(32))"`; guarda el resultado solo en Render.

## Fotografias

En el despliegue gratuito se utiliza **URL HTTPS**, porque Render no conserva archivos subidos despues de un reinicio. `ALLOW_UPLOADS=0` oculta el control de archivos y rechaza su envio en el servidor. En el equipo local las subidas siguen habilitadas por defecto.

Las imagenes de ejemplo en `FlastR/static/img/jugadores/` si forman parte del repositorio. Las fotos que subiste a `FlastR/static/uploads/` solo existen en tu equipo y **no se publican**. Si un jugador apunta a una de esas fotos, entra como administrador, edita su ficha y proporciona una URL HTTPS publica de imagen. No se modifican sus registros automaticamente. Las compras anteriores conservan su propia copia de la ruta de foto.

## Verificar

- Abre `/healthz`: debe responder `{"status":"ok"}`. Este endpoint comprueba el proceso, no la conexion con Neon.
- Abre `/`: debe mostrar el catalogo de Neon; esto si comprueba consultas a la base.
- Inicia sesion con una cuenta existente y revisa el panel correspondiente.
- Agrega o edita jugadores con imagenes HTTPS desde el panel de administrador.

Las cuentas existentes permanecen en Neon; no ejecutes `crear-demo` para desplegar. Los commits nuevos en la rama vinculada pueden activar despliegues automaticos. El plan gratuito puede suspender el proceso por inactividad y tardar al reactivarse.

Referencias: [Render Free](https://render.com/docs/free), [Blueprints](https://render.com/docs/blueprint-spec), [version de Python](https://render.com/docs/python-version).
