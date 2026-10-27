"""Nombres de los estados del trabajo, tal como están cargados en la base
(03_datos_iniciales.sql). Están aparte para que clientes y trabajos los usen
sin depender uno del otro."""
PRESUPUESTADO = "Presupuestado"
CONFIRMADO = "Confirmado"
EN_PRODUCCION = "En producción"
TERMINADO = "Terminado"
INSTALADO = "Instalado"
COBRADO = "Cobrado"
CANCELADO = "Cancelado"
ESTADOS_FINALES = (COBRADO, CANCELADO)   # el trabajo terminó su ciclo
