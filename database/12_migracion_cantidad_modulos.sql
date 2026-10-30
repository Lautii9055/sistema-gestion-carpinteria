/* =============================================================================
   Sistema de Gestión para Carpintería
   12 - Migración: cantidad de módulos iguales (requerimientos v3.2, RF-14.2)
   -----------------------------------------------------------------------------
   Un módulo se carga una sola vez con la cantidad de módulos iguales; sus
   piezas se guardan para un módulo y el listado las multiplica.
   Los módulos ya cargados quedan con cantidad 1.

   Ejecutar en SSMS como administrador (Windows Authentication). Re-ejecutable.
   ============================================================================= */

USE Carpinteria;
GO

IF COL_LENGTH('dbo.Modulo', 'cantidad_mod') IS NULL
    ALTER TABLE dbo.Modulo ADD cantidad_mod INT NOT NULL
        CONSTRAINT DF_Modulo_cantidad DEFAULT (1);
GO
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Modulo_cantidad')
    ALTER TABLE dbo.Modulo ADD CONSTRAINT CK_Modulo_cantidad CHECK (cantidad_mod BETWEEN 1 AND 50);
GO

-- Verificación: debe devolver una fila con cantidad_mod
SELECT name FROM sys.columns WHERE object_id = OBJECT_ID('dbo.Modulo') AND name = 'cantidad_mod';
GO
