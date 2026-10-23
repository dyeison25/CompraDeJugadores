# Neon con PostgreSQL y SQLAlchemy

La aplicacion dispone de un adaptador PostgreSQL implementado con **SQLAlchemy 2.0 (ORM)** y **psycopg 3**. Neon aloja PostgreSQL. Los cinco servicios de negocio son autenticacion, jugadores, compras, catalogo y estadisticas. Catalogo prepara las consultas publicas y estadisticas calcula los resumenes autorizados; ninguno depende de Flask ni SQLAlchemy.

## Configuracion

En `.env`, guarda la cadena que entrega Neon, sin el comando `psql` que a veces aparece alrededor:

```dotenv
DATABASE_BACKEND=postgresql
DATABASE_URL=postgresql://USUARIO:CONTRASENA@HOST.neon.tech/BASE?sslmode=require&channel_binding=require
```

Este ejemplo contiene marcadores: usa tu URL real solo en `.env`, que no debe versionarse. Los caracteres especiales de usuario/contrasena deben venir codificados en la URL. La aplicacion convierte internamente el protocolo a `postgresql+psycopg` y conserva los parametros de SSL. No imprimas ni compartas la conexion.

Sin `DATABASE_BACKEND` explicito, se selecciona PostgreSQL si existe `DATABASE_URL`; en su ausencia, SQLite. Las variables del proceso tienen prioridad sobre `.env`. Reinicia Flask despues de cambiar la configuracion.

## Preparar y ejecutar

Desde la raiz del proyecto:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app app verificar-neon
.\.venv\Scripts\python.exe -m flask --app app inicializar-neon
.\.venv\Scripts\python.exe -m flask --app app verificar-neon
.\.venv\Scripts\python.exe -m flask --app app crear-admin
.\.venv\Scripts\python.exe app.py
```

`verificar-neon` solo consulta la conexion y los conteos. Un valor `null` significa que falta esa tabla. `inicializar-neon` crea tablas e indices ausentes y no inserta, elimina ni sobrescribe filas. No se ejecuta automaticamente al arrancar Flask. Tampoco modifica columnas de tablas existentes: futuros cambios de esquema requieren una migracion especifica, por ejemplo con Alembic, que todavia no esta configurado.

`crear-admin` solicita nombre, correo y contrasena y crea una cuenta nueva. Luego abre http://127.0.0.1:5000/login, inicia sesion y agrega jugadores desde http://127.0.0.1:5000/admin.

## Datos existentes

**La conexion no traslada registros de otras bases de datos.** Sus usuarios, jugadores y compras permanecen en sus bases de origen. Neon empieza sin registros: las cuentas anteriores no funcionan alli hasta crear una cuenta o realizar una migracion planificada. Esta integracion no ejecuta migraciones de datos.

Si necesitas trasladar datos a Neon, hay que revisar conflictos, preservar relaciones y hashes de contrasena y ajustar las secuencias de IDs antes de habilitar escrituras. No copies documentos manualmente a las tablas omitiendo estas verificaciones.

Las fotos siguen almacenadas localmente o mediante URL HTTPS; PostgreSQL guarda la ruta/URL. Conserva `FlastR/static/uploads/`.

## Arquitectura

```text
FlastR/                           Rutas, sesiones, roles y comandos
domain/entidades/                 Usuario, Jugador, Compra: dataclasses
domain/servicio/                  Reglas de autenticacion, jugadores y compras
domain/repositorios/contratos.py  Contratos independientes de la base
infraestructura/persistencia.py  Seleccion e inyeccion del adaptador
infraestructura/orm/
    conexion.py                  Engine, sesiones y creacion explicita de tablas
    modelos.py                   Modelos declarativos de SQLAlchemy
    mappers.py                   Entidad <-> modelo ORM; reutiliza mappers existentes
    repositorios.py              Consultas y transacciones ORM
```

El dominio no importa SQLAlchemy, psycopg ni Flask. Los modelos ORM pertenecen a infraestructura; las entidades no se convierten en modelos de base de datos.

```mermaid
classDiagram
    class AutenticacionServicio
    class JugadorServicio
    class CompraServicio
    class UsuarioRepositorio {
      <<interface>>
    }
    class JugadorRepositorio {
      <<interface>>
    }
    class CompraRepositorio {
      <<interface>>
    }
    AutenticacionServicio --> UsuarioRepositorio
    JugadorServicio --> JugadorRepositorio
    CompraServicio --> CompraRepositorio
    UsuarioRepositorioORM ..|> UsuarioRepositorio
    JugadorRepositorioORM ..|> JugadorRepositorio
    CompraRepositorioORM ..|> CompraRepositorio
    UsuarioRepositorioORM --> UsuarioMapperORM
    JugadorRepositorioORM --> JugadorMapperORM
    CompraRepositorioORM --> CompraMapperORM
    UsuarioMapperORM --> UsuarioModelo
    JugadorMapperORM --> JugadorModelo
    CompraMapperORM --> CompraModelo
    UsuarioModelo "1" --> "0..*" CompraModelo : usuario_id
    JugadorModelo "1" --> "0..1" CompraModelo : jugador_id
```

La compra bloquea la fila del jugador con `SELECT FOR UPDATE`, vuelve a validar estado/version/precio y guarda compra y estado vendido en una transaccion. Una restriccion unica en `compras.jugador_id` impide duplicados. Los errores revierten toda la transaccion. Las ediciones y eliminaciones comprueban version y disponibilidad.

Los precios son `BIGINT` en centimos para mantener exactitud y admitir los importes del catalogo. La fecha conserva el formato UTC de las entidades. Hay claves foraneas que protegen el historial y un indice unico de correo normalizado. Cada operacion utiliza una sesion que se cierra al terminar. La conexion usa un pool pequeno, comprueba conexiones reutilizadas y admite SSL de Neon.

## Pruebas

```powershell
# Adaptador SQLite anterior y verificaciones especificas del ORM
.\.venv\Scripts\python.exe -m pytest -q
# Mismos flujos de la aplicacion con repositorios SQLAlchemy
.\.venv\Scripts\python.exe -m pytest -q --orm-sqlite
```

Ambos comandos usan archivos temporales y no conectan a Neon. Incluyen registro, roles, CRUD, compras simultaneas, precios/versiones, mappers, restricciones y rollback. Las pruebas ORM locales emplean SQLite: no sustituyen pruebas de concurrencia sobre PostgreSQL.

Para usar temporalmente SQLite, selecciona `DATABASE_BACKEND=sqlite` y reinicia Flask. No hay sincronizacion automatica entre las bases.

Referencias: [sesiones SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/session_basics.html), [controlador PostgreSQL](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg), [conexion a Neon](https://neon.com/docs/connect/connect-from-any-app).
