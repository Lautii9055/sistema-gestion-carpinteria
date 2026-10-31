/* =============================================================================
   Sistema de Gestión para Carpintería
   15 - Migración: piso (fondo) del cajón con guía telescópica
        (requerimientos v3.8, 4.4 a y RN-08.4)
   -----------------------------------------------------------------------------
   1) Con guía telescópica (las que llevan laterales de cajón, de cualquier
      marca), el fondo del cajón es de 5,5 mm y mide 0,3 cm menos que la caja:
      (ancho interior - 3,0) x (largo de la guía - 0,3). Antes: - 2,7 x largo.
   2) El piso del cajón nunca lleva filo, con ninguna guía.

   Las piezas ya guardadas conservan sus medidas y su placa hasta que se abre el
   módulo y se guarda de nuevo (ahí se recalculan con la regla nueva y el
   sistema pide la placa de 5,5 mm).

   Ejecutar en SSMS como administrador (Windows Authentication). Re-ejecutable.
   ============================================================================= */

USE Carpinteria;
GO

-- 1) Regla del piso en las guías telescópicas
UPDATE pg
SET    pg.descuento_ancho_pgu = 3.0,
       pg.descuento_largo_pgu = 0.3
FROM   dbo.Pieza_Guia pg
JOIN   dbo.Tipo_Pieza tp ON tp.id_tipo_pieza = pg.id_tipo_pieza
WHERE  tp.nombre_tpi = N'Piso de cajón'
  AND  EXISTS (SELECT 1
               FROM   dbo.Pieza_Guia l
               JOIN   dbo.Tipo_Pieza tl ON tl.id_tipo_pieza = l.id_tipo_pieza
               WHERE  l.id_tipo_guia = pg.id_tipo_guia AND tl.nombre_tpi = N'Lateral de cajón');
GO

-- 2) Ningún piso de cajón con filo
UPDATE p
SET    p.id_tipo_filo = (SELECT id_tipo_filo FROM dbo.Tipo_Filo WHERE nombre_tfi = N'Sin filo'),
       p.lleva_filo_superior_pie = 0, p.lleva_filo_inferior_pie = 0,
       p.lleva_filo_izquierdo_pie = 0, p.lleva_filo_derecho_pie = 0,
       p.id_color_placa_filo = NULL
FROM   dbo.Pieza p
JOIN   dbo.Tipo_Pieza tp ON tp.id_tipo_pieza = p.id_tipo_pieza
WHERE  tp.nombre_tpi = N'Piso de cajón';
GO

-- Verificación: la regla de cada telescópica (3.0 / 0.3) y 0 pisos con filo
SELECT g.nombre_tgu, pg.descuento_ancho_pgu, pg.descuento_largo_pgu
FROM   dbo.Pieza_Guia pg
JOIN   dbo.Tipo_Guia g   ON g.id_tipo_guia = pg.id_tipo_guia
JOIN   dbo.Tipo_Pieza tp ON tp.id_tipo_pieza = pg.id_tipo_pieza
WHERE  tp.nombre_tpi = N'Piso de cajón';

SELECT COUNT(*) AS pisos_con_filo
FROM   dbo.Pieza p
JOIN   dbo.Tipo_Pieza tp ON tp.id_tipo_pieza = p.id_tipo_pieza
JOIN   dbo.Tipo_Filo tf  ON tf.id_tipo_filo = p.id_tipo_filo
WHERE  tp.nombre_tpi = N'Piso de cajón' AND tf.nombre_tfi <> N'Sin filo';
GO
