/* =============================================================================
   Sistema de Gestión para Carpintería
   11 - Migración: luces laterales por módulo (requerimientos v3.1)
   -----------------------------------------------------------------------------
   Cada módulo guarda la luz izquierda y derecha de sus puertas y frentes.
   Por defecto 0,3 cm; del lado en que se une a otro módulo se usa 0,15 para
   que entre los dos frentes queden 0,3 y no 0,6.
   Los módulos ya cargados quedan con 0,3 de cada lado (como se calculaban).

   Ejecutar en SSMS como administrador (Windows Authentication). Re-ejecutable.
   ============================================================================= */

USE Carpinteria;
GO

IF COL_LENGTH('dbo.Modulo', 'luz_izquierda_mod') IS NULL
    ALTER TABLE dbo.Modulo ADD luz_izquierda_mod DECIMAL(5,2) NOT NULL
        CONSTRAINT DF_Modulo_luz_izquierda DEFAULT (0.3);
GO
IF COL_LENGTH('dbo.Modulo', 'luz_derecha_mod') IS NULL
    ALTER TABLE dbo.Modulo ADD luz_derecha_mod DECIMAL(5,2) NOT NULL
        CONSTRAINT DF_Modulo_luz_derecha DEFAULT (0.3);
GO
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Modulo_luz_costados')
    ALTER TABLE dbo.Modulo ADD CONSTRAINT CK_Modulo_luz_costados
        CHECK (luz_izquierda_mod >= 0 AND luz_derecha_mod >= 0);
GO

-- Verificación: deben aparecer las dos columnas
SELECT name FROM sys.columns
WHERE object_id = OBJECT_ID('dbo.Modulo') AND name IN ('luz_izquierda_mod', 'luz_derecha_mod');
GO
