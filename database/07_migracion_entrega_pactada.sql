/* =============================================================================
   Sistema de Gestión para Carpintería
   07 - Migración: entrega pactada por semana (requerimientos v2.5)
   -----------------------------------------------------------------------------
   Para una base YA CREADA: agrega entrega_aproximada_tra. Mientras el trabajo
   no está instalado, fecha_entrega_tra es la entrega pactada; si este campo
   vale 1, lo pactado es la SEMANA de esa fecha (ej.: "la semana del 2/11").
   Al instalar, la fecha pasa a ser la real y el campo vuelve a 0.

   Ejecutar en SSMS como administrador (Windows Authentication). Re-ejecutable.
   ============================================================================= */

USE Carpinteria;
GO

IF COL_LENGTH(N'dbo.Trabajo', N'entrega_aproximada_tra') IS NULL
    ALTER TABLE dbo.Trabajo ADD entrega_aproximada_tra BIT NOT NULL
        CONSTRAINT DF_Trabajo_entrega_aproximada DEFAULT (0);
GO

-- Verificación: debe devolver 1
SELECT COUNT(*) AS columna_ok FROM sys.columns
WHERE object_id = OBJECT_ID(N'dbo.Trabajo') AND name = N'entrega_aproximada_tra';
GO
