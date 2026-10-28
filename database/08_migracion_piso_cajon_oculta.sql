/* =============================================================================
   Sistema de Gestión para Carpintería
   08 - Migración: piso del cajón con guía lateral oculta (requerimientos v2.9)
   -----------------------------------------------------------------------------
   El piso del cajón con guía oculta mide (ancho interior - 7,5) x (largo de la
   guía - 0,9), no - 1. Corrige la regla en todas las guías ocultas, incluidas
   las que se crearon desde el sistema basadas en otra.

   Ejecutar en SSMS como administrador (Windows Authentication). Re-ejecutable.
   ============================================================================= */

USE Carpinteria;
GO

UPDATE pg
SET descuento_largo_pgu = 0.9
FROM dbo.Pieza_Guia pg
JOIN dbo.Tipo_Pieza tp ON tp.id_tipo_pieza = pg.id_tipo_pieza
WHERE tp.nombre_tpi = N'Piso de cajón'
  AND pg.descuento_ancho_pgu = 7.5      -- regla de las guías ocultas (la telescópica usa 2,7)
  AND pg.descuento_largo_pgu = 1.0;
GO

-- Verificación: el piso de cada guía oculta debe mostrar 0,9 (y la telescópica, 0)
SELECT g.nombre_tgu, pg.descuento_ancho_pgu, pg.descuento_largo_pgu
FROM dbo.Pieza_Guia pg
JOIN dbo.Tipo_Guia g   ON g.id_tipo_guia = pg.id_tipo_guia
JOIN dbo.Tipo_Pieza tp ON tp.id_tipo_pieza = pg.id_tipo_pieza
WHERE tp.nombre_tpi = N'Piso de cajón'
ORDER BY g.nombre_tgu;
GO
