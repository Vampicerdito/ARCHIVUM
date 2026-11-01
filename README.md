# ARCHIVUM

Gestor privado de biblioteca cinematográfica para Windows. Versión de desarrollo 0.2.0.

## Estado de esta entrega

Incluye la base de la Fase 1 y el primer módulo funcional de la Fase 2:

- Aplicación de escritorio PySide6 con navegación funcional.
- Configuración persistente y ubicación de datos configurable.
- Base SQLite inicial, creada automáticamente.
- Esquema relacional para películas, archivos, fuentes, identificadores,
  personas, créditos, géneros, artwork, colecciones y operaciones.
- Panel de inicio con estadísticas reales de la base de datos.
- Pantalla de configuración para cambiar la carpeta de datos.
- Explorador de ubicaciones con registro de carpetas y unidades.
- Escaneo recursivo de archivos de vídeo en segundo plano.
- Inventario persistente e idempotente de rutas, tamaños y fechas de modificación.
- Extracción técnica opcional mediante FFprobe, si está instalado y disponible en PATH.
- Detección de archivos nuevos, modificados, no localizados y candidatos a duplicados.
- Pruebas iniciales de escaneo, repetición y desconexión de unidades.

Todavía no incluye identificación TMDB, descarga de carteles, análisis de subtítulos,
renombrado ni modificación de archivos multimedia.

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

## Explorador e inventario

1. Abre **Explorador**.
2. Pulsa **Añadir carpeta** y selecciona una carpeta raíz o una unidad montada.
3. Selecciona la ubicación registrada y pulsa **Escanear ubicación seleccionada**.
4. Consulta el resumen del escaneo y sus advertencias.

Extensiones de vídeo detectadas: MKV, MP4, AVI, MOV, M4V, MPG, MPEG, TS, M2TS,
WMV, WEBM, OGV y VOB.

FFprobe es opcional. Si está instalado y accesible desde PATH, ARCHIVUM registra
contenedor, códecs, resolución, frecuencia de fotogramas, bitrate y duración.
Sin FFprobe, el inventario básico de archivos sigue funcionando.

La huella rápida usa tamaño y bloques inicial/final para agrupar posibles
duplicados; no es una verificación criptográfica completa del contenido. Las
coincidencias deben revisarse antes de tomar decisiones.

Los archivos no localizados se marcan como `missing`, pero no se borran de la
base de datos. Si una unidad completa no está disponible, su fuente se marca
como `offline` y no se modifica la disponibilidad de sus archivos. Si el
recorrido de carpetas fue parcial por errores de acceso, ARCHIVUM evita marcar
en masa archivos como desaparecidos.

## Incorporar archivos a la biblioteca

Después de escanear una ubicación:

1. Abre **Biblioteca**.
2. En **Archivos inventariados sin ficha**, selecciona uno o varios archivos.
3. Pulsa **Crear película con archivos seleccionados**.
4. Introduce el título y, si se conoce, el año de estreno.
5. ARCHIVUM crea una ficha y asocia los archivos seleccionados sin moverlos ni renombrarlos.

Un archivo solo puede pertenecer a una película. La aplicación rechaza asignaciones
duplicadas y registra la operación en el historial. Esta incorporación es manual:
la identificación automática mediante TMDB y la revisión de candidatos se
incorporarán en el siguiente bloque.

## Desarrollo

```powershell
pytest
```

## Seguridad

El escáner solo lee e inventaría archivos. No mueve, renombra ni elimina contenido multimedia.
