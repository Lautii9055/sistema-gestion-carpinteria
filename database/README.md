# Base de datos — Sistema de Gestión para Carpintería

Motor: **SQL Server 2025 Express** · Herramienta: **SSMS 22** · Modelo de datos v1.8 (3FN, 30 tablas)

## 1. Instalación del entorno (Windows)

### SQL Server 2025 Express
1. Descargar el instalador desde la página oficial de descargas de SQL Server: https://www.microsoft.com/es-es/sql-server/sql-server-downloads → **Express** → *Descargar ahora* (`SQL2025-SSEI-Expr.exe`).
2. Ejecutarlo y elegir **Básica**.
3. Al terminar, anotar el **nombre de la instancia** que muestra el resumen (habitualmente `SQLEXPRESS`). El servidor queda como `localhost\SQLEXPRESS`.

### SSMS 22 (SQL Server Management Studio)
1. Descargar `vs_SSMS.exe` desde https://aka.ms/ssms/22/release/vs_SSMS.exe.
2. Ejecutarlo como administrador. Instala el *Visual Studio Installer* y desde ahí SSMS (opciones por defecto).

### Primera conexión
En SSMS → **Connect**:
- **Server name:** `localhost\SQLEXPRESS`
- **Authentication:** Windows Authentication
- **Trust server certificate:** marcado (la instancia local usa un certificado autofirmado)

## 2. Creación de la base

Abrir cada script en SSMS (**File → Open → File…**) y ejecutarlo con **F5**, en este orden:

| Orden | Script | Qué hace |
|-------|--------|----------|
| 1 | `00_crear_base_de_datos.sql` | Crea la base `Carpinteria` con collation `Modern_Spanish_CI_AI` |
| 2 | `01_tablas.sql` | Crea las 30 tablas con PK, FK, CHECK, UNIQUE y DEFAULT |
| 3 | `02_indices.sql` | Índices de FK, de búsqueda y únicos filtrados |
| 4 | `03_datos_iniciales.sql` | Estados, tipos, filos, guías, estilos, parámetros, tipos de evento y usuario inicial |
| 5 | `04_procedimientos.sql` | `sp_alta_placa`, `sp_alta_liston`, `sp_eliminar_trabajo`, `sp_registrar_evento` |
| 6 | `05_seguridad.sql` | Login `app_carpinteria` con mínimo privilegio, rol `rol_app`, deshabilita `sa` (ver sección 4) |

### Migraciones (bases ya creadas)
Si la base ya estaba creada, ejecutar además, en orden, las migraciones que falten (son re-ejecutables y no borran datos):

| Script | Qué hace |
|--------|----------|
| `06_migracion_fecha_presupuesto.sql` | Agrega la fecha de presupuesto del trabajo (editable), un CHECK para que ninguna fecha sea anterior a ella, su índice y el evento de auditoría `CAMBIO_FECHA_PRESUPUESTO` |
| `07_migracion_entrega_pactada.sql` | Agrega `entrega_aproximada_tra`: permite pactar la entrega por semana |
| `08_migracion_piso_cajon_oculta.sql` | Corrige el piso del cajón con guía oculta: largo de la guía − 0,9 (antes − 1) |
| `09_migracion_descuento_fondo.sql` | Agrega el parámetro `descuento_fondo` (0,3 cm): el fondo mide (ancho − 0,3) × (alto − 0,3) |
| `10_migracion_veta_rotada.sql` | Tabla `Modulo_Veta_Rotada`: tipos de pieza con la veta rotada en cada módulo (se respeta al recalcular) |

`01_tablas.sql` es re-ejecutable: borra las tablas y las vuelve a crear (se pierden los datos). Después hay que volver a correr 02, 03, 04 y 05.

## 3. Verificación

```sql
USE Carpinteria;

-- Debe devolver 30
SELECT COUNT(*) AS tablas FROM sys.tables;

-- Catálogos cargados
SELECT nombre_etr FROM dbo.Estado_Trabajo ORDER BY orden_etr;
SELECT nombre_efr, luz_superior_efr, luz_inferior_efr, luz_entre_frentes_efr FROM dbo.Estilo_Frente;

-- Piezas que genera cada guía
SELECT g.nombre_tgu, p.nombre_tpi, pg.cantidad_pgu,
       pg.descuento_ancho_pgu, pg.descuento_largo_pgu, pg.descuento_alto_pgu
FROM dbo.Pieza_Guia pg
JOIN dbo.Tipo_Guia  g ON g.id_tipo_guia  = pg.id_tipo_guia
JOIN dbo.Tipo_Pieza p ON p.id_tipo_pieza = pg.id_tipo_pieza
ORDER BY g.nombre_tgu, p.nombre_tpi;
```

## 4. Seguridad: usuario de la aplicación (`05_seguridad.sql`)
La aplicación no usa la cuenta de administrador: se conecta con `app_carpinteria`, que solo puede trabajar con los datos y hacer copias de seguridad (no puede borrar tablas ni modificar la auditoría).

1. **Habilitar el modo mixto:** en SSMS, clic derecho en el servidor → *Properties* → *Security* → **SQL Server and Windows Authentication mode** → OK. Después clic derecho en el servidor → **Restart**.
2. Abrir `05_seguridad.sql` y reemplazar `REEMPLAZAR_ANTES_DE_EJECUTAR` por una contraseña larga y aleatoria (16 caracteres o más). Anotarla en un lugar seguro: la aplicación la va a pedir una vez para guardarla en el Administrador de credenciales de Windows.
3. Ejecutar con **F5** y **cerrar el archivo sin guardar**. La contraseña nunca debe quedar en un archivo ni subirse a GitHub.
4. Opcional: probar el mínimo privilegio conectándose con *SQL Server Authentication* como `app_carpinteria` (instrucciones al final del script).

## 5. Datos pendientes de carga
- Alto del contrafrente de cada marca de guía oculta (`Pieza_Guia`).
- Largos disponibles de cada guía (`Largo_Guia`).

Hay ejemplos comentados al final de `03_datos_iniciales.sql`.

## 6. Usuario inicial
- Usuario: `admin`
- Contraseña provisoria: `Cambiar.123` (se guarda como hash bcrypt; el sistema pide cambiarla en el primer ingreso).
