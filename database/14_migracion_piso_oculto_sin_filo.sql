/* =============================================================================
   Sistema de Gestión para Carpintería
   14 - Migración: con guía de lateral oculto, el piso del cajón no lleva filo
        (requerimientos v3.7, RN-08.4)
   -----------------------------------------------------------------------------
   Con cualquier guía de lateral oculto (la que no lleva laterales de cajón), el
   piso del cajón es como un fondo: nunca lleva filo. Deja los ya cargados con
   «Sin filo», sin cantos y sin color de filo. Desde esta versión el sistema los
   crea así y no deja ponerles filo.

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
JOIN   dbo.Cajon c       ON c.id_cajon = p.id_cajon
WHERE  tp.nombre_tpi = N'Piso de cajón'
  AND  NOT EXISTS (SELECT 1
                   FROM   dbo.Pieza_Guia pg
                   JOIN   dbo.Tipo_Pieza t2 ON t2.id_tipo_pieza = pg.id_tipo_pieza
                   WHERE  pg.id_tipo_guia = c.id_tipo_guia AND t2.nombre_tpi = N'Lateral de cajón');
GO

-- Verificación: debe devolver 0
SELECT COUNT(*) AS pisos_ocultos_con_filo
FROM   dbo.Pieza p
JOIN   dbo.Tipo_Pieza tp ON tp.id_tipo_pieza = p.id_tipo_pieza
JOIN   dbo.Cajon c       ON c.id_cajon = p.id_cajon
JOIN   dbo.Tipo_Filo tf  ON tf.id_tipo_filo = p.id_tipo_filo
WHERE  tp.nombre_tpi = N'Piso de cajón' AND tf.nombre_tfi <> N'Sin filo'
  AND  NOT EXISTS (SELECT 1
                   FROM   dbo.Pieza_Guia pg
                   JOIN   dbo.Tipo_Pieza t2 ON t2.id_tipo_pieza = pg.id_tipo_pieza
                   WHERE  pg.id_tipo_guia = c.id_tipo_guia AND t2.nombre_tpi = N'Lateral de cajón');
GO
