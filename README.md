# ARCHIVUM

Gestor privado de biblioteca cinematográfica para Windows. Versión inicial 0.1.0.

## Estado de esta entrega

Incluye la base de la Fase 1:

- Aplicación de escritorio PySide6 con navegación funcional.
- Configuración persistente y ubicación de datos configurable.
- Base SQLite inicial, creada automáticamente.
- Esquema relacional para películas, archivos, fuentes, identificadores,
  personas, créditos, géneros, artwork, colecciones y operaciones.
- Panel de inicio con estadísticas reales de la base de datos.
- Pantalla de configuración para cambiar la carpeta de datos.
- Pruebas iniciales del esquema y del repositorio.

Todavía no incluye el escáner de discos, integración TMDB, descarga de imágenes,
renombrado ni modificación de archivos multimedia. Esos módulos pertenecen a
las siguientes fases.

## Requisitos

- Windows 10/11 de 64 bits.
- Python 3.12 o superior.
- Conexión a Internet solo para instalar dependencias en esta fase.

## Ejecutar desde el código fuente

En PowerShell, dentro de la carpeta del proyecto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
archivum
```

También se puede ejecutar con:

```powershell
python -m archivum.main
```

## Ubicación de los datos

Por defecto, ARCHIVUM utiliza:

`%LOCALAPPDATA%\ARCHIVUM\`

La ubicación se puede cambiar desde **Configuración → Almacenamiento**.
El cambio crea o utiliza la estructura de datos en la nueva ubicación y actualiza
la configuración. No mueve automáticamente una biblioteca preexistente ni borra
la carpeta anterior.

Estructura creada:

```text
ARCHIVUM_DATA/
├── database/archivum.db
├── artwork/
│   ├── posters/
│   ├── backdrops/
│   ├── logos/
│   └── banners/
├── cache/
├── backups/
├── exports/
└── logs/
```

El archivo `settings.json` de la aplicación se conserva en el directorio de
configuración del usuario, separado de los datos de la biblioteca.

## Base de datos

SQLite con claves foráneas y modo WAL. El archivo de base de datos permanece
en el equipo local. No se debe colocar una base SQLite en una carpeta de red
compartida para acceso simultáneo desde varios equipos.

## Desarrollo

```powershell
pytest
```

## Seguridad

La Fase 1 no realiza operaciones sobre los archivos de películas. No escanea,
mueve, renombra ni elimina contenido multimedia.
