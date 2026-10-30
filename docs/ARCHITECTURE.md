# Arquitectura ARCHIVUM 0.1

## Límites de esta fase

La Fase 1 entrega el esqueleto ejecutable, configuración persistente, SQLite y UI.
Los servicios de escaneo, proveedores de metadatos y operaciones sobre archivos
se incorporarán en fases posteriores.

## Decisiones

- Aplicación de escritorio PySide6.
- SQLite local, con WAL y claves foráneas activadas.
- SQLAlchemy 2 para el mapeo de entidades.
- Configuración de usuario separada de los datos de biblioteca.
- Datos en una carpeta seleccionable desde la interfaz.
- No se modifican archivos multimedia en la Fase 1.

## Migraciones

`Base.metadata.create_all()` crea las tablas iniciales. Antes de distribuir
versiones con cambios de esquema se incorporará Alembic y una política formal
de migraciones respaldadas.
