/* =============================================================================
   Sistema de Gestión para Carpintería
   06 - Migración: fecha de presupuesto del trabajo (requerimientos v2.4)
   -----------------------------------------------------------------------------
   Para una base YA CREADA con los scripts 00 a 05: agrega la columna sin perder
   datos. Una base nueva no lo necesita (ya está en 01, 02 y 03).

   - fecha_alta_tra sigue siendo cuándo se cargó el trabajo en el sistema y no
     se edita (sirve de registro).
   - fecha_presupuesto_tra es cuándo se presupuestó de verdad: se puede cargar
     con una fecha pasada si el trabajo se anotó tarde. Las demás fechas no
     pueden ser anteriores a ella (lo controla la aplicación y, además, un CHECK).
   - Nuevo tipo de evento de auditoría CAMBIO_FECHA_PRESUPUESTO.

   Ejecutar en SSMS con la cuenta de administrador (Windows Authentication),
   no con app_carpinteria: la aplicación no tiene permisos para cambiar la
   estructura. Es re-ejecutable: lo que ya existe no se vuelve a crear.
   ============================================================================= */

USE Carpinteria;
GO

/* ---------- 1. Columna (los trabajos existentes toman su fecha de alta) ---------- */
IF COL_LENGTH(N'dbo.Trabajo', N'fecha_presupuesto_tra') IS NULL
BEGIN
    ALTER TABLE dbo.Trabajo ADD fecha_presupuesto_tra DATE NULL;
END
GO

UPDATE dbo.Trabajo
SET fecha_presupuesto_tra = CAST(fecha_alta_tra AS DATE)
WHERE fecha_presupuesto_tra IS NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.default_constraints WHERE name = N'DF_Trabajo_fecha_presupuesto')
BEGIN
    ALTER TABLE dbo.Trabajo ALTER COLUMN fecha_presupuesto_tra DATE NOT NULL;
    ALTER TABLE dbo.Trabajo ADD CONSTRAINT DF_Trabajo_fecha_presupuesto
        DEFAULT (CAST(SYSDATETIME() AS DATE)) FOR fecha_presupuesto_tra;
END
GO

/* ---------- 2. Ninguna fecha anterior al presupuesto ----------
   Si algún trabajo cargado durante las pruebas no cumple la regla, el CHECK no
   se puede crear y el script lo informa: corregí esas fechas desde el sistema
   (o borrá el trabajo de prueba) y volvé a ejecutarlo. */
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_Trabajo_fechas_desde_presupuesto')
BEGIN
    IF EXISTS (SELECT 1 FROM dbo.Trabajo
               WHERE fecha_cobro_sena_tra   < fecha_presupuesto_tra OR fecha_comienzo_tra < fecha_presupuesto_tra
                  OR fecha_finalizacion_tra < fecha_presupuesto_tra OR fecha_entrega_tra  < fecha_presupuesto_tra
                  OR fecha_cobro_saldo_tra  < fecha_presupuesto_tra)
    BEGIN
        SELECT id_trabajo, descripcion_tra, fecha_presupuesto_tra, fecha_cobro_sena_tra, fecha_comienzo_tra,
               fecha_finalizacion_tra, fecha_entrega_tra, fecha_cobro_saldo_tra
        FROM dbo.Trabajo
        WHERE fecha_cobro_sena_tra   < fecha_presupuesto_tra OR fecha_comienzo_tra < fecha_presupuesto_tra
           OR fecha_finalizacion_tra < fecha_presupuesto_tra OR fecha_entrega_tra  < fecha_presupuesto_tra
           OR fecha_cobro_saldo_tra  < fecha_presupuesto_tra;
        RAISERROR (N'Hay trabajos con fechas anteriores al presupuesto (ver la lista). Corregilos y volvé a ejecutar.', 16, 1);
    END
    ELSE
        ALTER TABLE dbo.Trabajo ADD CONSTRAINT CK_Trabajo_fechas_desde_presupuesto CHECK (
            fecha_cobro_sena_tra   >= fecha_presupuesto_tra AND fecha_comienzo_tra    >= fecha_presupuesto_tra AND
            fecha_finalizacion_tra >= fecha_presupuesto_tra AND fecha_entrega_tra     >= fecha_presupuesto_tra AND
            fecha_cobro_saldo_tra  >= fecha_presupuesto_tra);
END
GO

/* ---------- 3. Índice para filtrar y ordenar por fecha de presupuesto ---------- */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_Trabajo_fecha_presupuesto')
    CREATE INDEX IX_Trabajo_fecha_presupuesto ON dbo.Trabajo (fecha_presupuesto_tra);
GO

/* ---------- 4. Tipo de evento de auditoría ---------- */
IF NOT EXISTS (SELECT 1 FROM dbo.Tipo_Evento WHERE codigo_tev = 'CAMBIO_FECHA_PRESUPUESTO')
    INSERT INTO dbo.Tipo_Evento (codigo_tev, descripcion_tev, es_critico_tev)
    VALUES ('CAMBIO_FECHA_PRESUPUESTO', N'Fecha de presupuesto cargada o cambiada a mano', 0);
GO

/* ---------- 5. Verificación ---------- */
SELECT COL_LENGTH(N'dbo.Trabajo', N'fecha_presupuesto_tra') AS columna_ok,   -- 3
       (SELECT COUNT(*) FROM sys.check_constraints
        WHERE name = N'CK_Trabajo_fechas_desde_presupuesto') AS check_ok,       -- 1
       (SELECT COUNT(*) FROM dbo.Tipo_Evento
        WHERE codigo_tev = 'CAMBIO_FECHA_PRESUPUESTO') AS evento_ok;            -- 1
GO
