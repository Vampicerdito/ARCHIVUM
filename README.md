# ARCHIVUM

Gestor privado de biblioteca cinematográfica para Windows. Versión de desarrollo 0.3.0.

## Estado de esta entrega

Incluye la fundación (Fase 1), el inventario y la incorporación manual (Fase 2), y la identificación TMDB inicial (Fase 3):

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
- Pruebas de base de datos, escaneo, incorporación manual e integración TMDB.

Incluye búsqueda e identificación revisada mediante TMDB, importación de metadatos y
caché local de carteles y fondos. El análisis de subtítulos y la organización automática
de archivos multimedia quedan pendientes.

## Requisitos

- Windows 10/11 de 64 bits.
- Python 3.12 o superior.
- Conexión a Internet para instalar dependencias y consultar TMDB/descargar artwork.

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

## Identificación con TMDB

ARCHIVUM permite buscar películas en TMDB y presentar candidatos antes de
vincularlos a una ficha local. La importación solo se realiza después de una
confirmación explícita.

1. Crea una cuenta en https://www.themoviedb.org/.
2. En la configuración de tu cuenta, solicita acceso API y copia el API Read Access Token.
3. En ARCHIVUM, abre **Configuración**, pega el token y pulsa **Guardar token**.
4. Pulsa **Probar conexión** para validar la autenticación.
5. En **Biblioteca**, selecciona una ficha local, busca el título y el año en TMDB.
6. Selecciona el candidato correcto y confirma la identificación.

El token se guarda mediante el almacén de credenciales del sistema operativo
(`keyring`); no se escribe en la base de datos ni en `settings.json`. No publiques
el token ni lo incluyas en capturas, logs o commits.

Al confirmar una coincidencia se importan título localizado y original, fecha,
año, sinopsis, duración, idioma, países, puntuación TMDB, géneros, identificadores
TMDB/IMDb y créditos de dirección y reparto. Los carteles y fondos se descargan
a `artwork/` cuando están disponibles; sus referencias remotas se conservan.

La biblioteca ya catalogada sigue siendo consultable sin conexión. Las búsquedas
y las descargas de metadatos o imágenes necesitan Internet. La identificación no
mueve, renombra ni modifica los archivos multimedia originales.

TMDB exige atribución en la aplicación. ARCHIVUM incluye el aviso:
> This product uses the TMDB API but is not endorsed or certified by TMDB.

Antes de distribuir una compilación pública debe incorporarse también uno de los
logotipos oficiales aprobados de TMDB en la sección de créditos.

## Desarrollo

```powershell
pytest
```

## Seguridad

El escáner solo lee e inventaría archivos. No mueve, renombra ni elimina contenido multimedia.
