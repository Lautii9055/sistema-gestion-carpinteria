/* =============================================================================
   Sistema de Gestión para Carpintería
   13 - Migración: los fondos nunca llevan filo (requerimientos v3.6, RN-08.3)
   -----------------------------------------------------------------------------
   Deja todos los fondos ya cargados con «Sin filo», sin cantos marcados y sin
   color de filo. Desde esta versión el sistema los crea así y no deja ponerles
   filo.

   Ejecutar en SSMS como administrador (Windows Authentication). Re-ejecutable.
   ============================================================================= */

USE Carpinteria;
GO

UPDATE p
SET    p.id_tipo_filo = (SELECT id_tipo_filo FROM dbo.Tipo_Filo WHERE nombre_tfi = N'Sin filo'),
       p.lleva_filo_superior_pie = 0, p.lleva_filo_inferior_pie = 0,
       p.lleva_filo_izquierdo_pie = 0, p.lleva_filo_derecho_pie = 0,
       p.id_color_placa_filo = NULL
FROM   dbo.Pieza p
JOIN   dbo.Tipo_Pieza tp ON tp.id_tipo_pieza = p.id_tipo_pieza
WHERE  tp.nombre_tpi = N'Fondo';
GO

-- Verificación: debe devolver 0
SELECT COUNT(*) AS fondos_con_filo
FROM   dbo.Pieza p
JOIN   dbo.Tipo_Pieza tp ON tp.id_tipo_pieza = p.id_tipo_pieza
JOIN   dbo.Tipo_Filo tf  ON tf.id_tipo_filo = p.id_tipo_filo
WHERE  tp.nombre_tpi = N'Fondo' AND tf.nombre_tfi <> N'Sin filo';
GO
