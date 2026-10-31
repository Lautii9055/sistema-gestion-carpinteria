/* =============================================================================
   Sistema de Gestión para Carpintería
   16 - Migración: cajoneras con piso y 2 fajas arriba (requerimientos v3.9, RN-04)
   -----------------------------------------------------------------------------
   Dos tipos de armado nuevos, además de las cajoneras de 4 fajas:
   - Cajonera con piso y fajas de luz: piso entero; laterales sobre el piso
     (alto - 1,8) y 2 fajas arriba (adelante y atrás) entre ellos.
   - Cajonera con piso y laterales de luz: piso entero y 2 fajas enteras arriba;
     laterales entre ellos (alto - 3,6).

   Ejecutar en SSMS como administrador (Windows Authentication). Re-ejecutable.
   ============================================================================= */

USE Carpinteria;
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Tipo_Armado WHERE nombre_tar = N'Cajonera con piso y fajas de luz')
    INSERT INTO dbo.Tipo_Armado (nombre_tar, es_cajonera_tar, descripcion_tar)
    VALUES (N'Cajonera con piso y fajas de luz', 1, N'Piso entero; laterales sobre el piso y 2 fajas arriba entre ellos');
GO
IF NOT EXISTS (SELECT 1 FROM dbo.Tipo_Armado WHERE nombre_tar = N'Cajonera con piso y laterales de luz')
    INSERT INTO dbo.Tipo_Armado (nombre_tar, es_cajonera_tar, descripcion_tar)
    VALUES (N'Cajonera con piso y laterales de luz', 1, N'Piso entero y 2 fajas enteras arriba; laterales entre ellos');
GO

-- Si ya se había corrido la primera versión de este script, corrige las descripciones.
UPDATE dbo.Tipo_Armado SET descripcion_tar = N'Piso entero; laterales sobre el piso y 2 fajas arriba entre ellos'
WHERE nombre_tar = N'Cajonera con piso y fajas de luz';
UPDATE dbo.Tipo_Armado SET descripcion_tar = N'Piso entero y 2 fajas enteras arriba; laterales entre ellos'
WHERE nombre_tar = N'Cajonera con piso y laterales de luz';
GO

-- Verificación: deben aparecer los 5 tipos de armado
SELECT nombre_tar, es_cajonera_tar FROM dbo.Tipo_Armado ORDER BY id_tipo_armado;
GO
