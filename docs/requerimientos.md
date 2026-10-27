# Sistema de Gestión para Carpintería — Documento de Requerimientos

**Versión del documento:** 2.7 (catálogo: RF-11.1 precisado; baja de clientes con trabajos: RF-04.1; flujo de estados y cobros: RF-25.1, RF-25.2; fecha de presupuesto editable: RF-26.1, RF-26.2; entrega pactada: RF-26.4)
**Autor:** Lautaro Zanino
**Estado:** Aprobado para diseño

---

## 1. Introducción

### 1.1 Propósito
Este documento define el alcance, los requerimientos funcionales y no funcionales y las reglas de negocio de un sistema de escritorio para una carpintería que fabrica muebles a medida en melamina y MDF.

### 1.2 Problema que resuelve
Hoy todo el proceso es manual:

- Las medidas finales de cada pieza se calculan con papel y calculadora a partir de las medidas exteriores de cada módulo, descontando espesores, luces y filos. Es la tarea más repetitiva y la más propensa a errores.
- El listado de piezas para la maderera se escribe a mano, indicando con marcador los cantos que llevan filo.
- No hay registro de clientes ni de trabajos anteriores, aunque los clientes vuelven con frecuencia.
- No hay seguimiento formal del estado de los trabajos ni de los pagos (seña y saldo).
- Los retazos que quedan en el taller no están registrados: encontrar uno implica revisar placa por placa.

### 1.3 Usuarios
Dos usuarios (el dueño de la carpintería y su hijo), que usan el sistema desde una PC. No se requieren roles diferenciados.

La PC donde se va a instalar todavía no está definida. Los requerimientos no dependen de un equipo en particular; cuando se elija, se le aplica la lista de verificación de la sección 6.1.4.

### 1.4 Contexto del negocio
- Se fabrican exclusivamente muebles a medida: cocinas, vestidores, placares, vanitorys, escritorios, bibliotecas, vajilleros, revestimientos de pared, vitrinas, muebles de recepción, etc.
- Material: melamina MDF (blanco, color, laqueado o enchapado). El 95% de las placas son de 18 mm. Fondos de 5,5 mm.
- Filos de 2 mm y de 0,45 mm.
- La maderera corta las placas (optimizando el desperdicio con su propio sistema) y aplica los filos.
- Flujo de un trabajo: contacto del cliente → medición → diseño → presupuesto → confirmación con seña del 60% → compra de materiales y fabricación → instalación → cobro del saldo.

---

## 2. Alcance y versiones

### Versión 1 (alcance actual)
| ID | Módulo |
|----|--------|
| M1 | Autenticación, seguridad y auditoría |
| M2 | Clientes e historial de trabajos |
| M3 | Catálogo de materiales |
| M4 | Trabajos, muebles y módulos |
| M5 | Despiece automático |
| M6 | Listado de corte para la maderera (PDF) |
| M7 | Estados y pagos de trabajos |
| M8 | Inventario de retazos |

### Versión 2
- Cálculo de presupuesto (a partir de m² de placa y metros lineales de filo).
- Reportes y dashboard en Power BI.

### Futuro
- Optimizador de corte de placas, incluyendo la comparación de desperdicio según el sentido de la veta de las piezas (para consultarle al cliente con datos concretos).

### Fuera de alcance
- Diseño o visualización 3D.
- Integración con WhatsApp (se gestiona desde la web de la carpintería).
- Stock de placas enteras (se compran por trabajo).

> El modelo de datos de la versión 1 debe contemplar la versión 2, para que su incorporación no requiera reestructurar lo existente.

---

## 3. Requerimientos funcionales

### M1 — Autenticación, seguridad y auditoría
- **RF-01** El sistema requiere usuario y contraseña para ingresar.
- **RF-02** Un usuario puede dar de alta a otro usuario y cambiar su propia contraseña.
- **RF-03** Las contraseñas se almacenan con hash, nunca en texto plano.
- **RF-03.1 Bloqueo por intentos fallidos:** tras 5 contraseñas incorrectas seguidas, el usuario queda bloqueado 15 minutos (ambos valores son parámetros). Ante cualquier error de ingreso el mensaje es siempre "Usuario o contraseña incorrectos", sin indicar cuál de los dos falló ni si el usuario existe.
- **RF-03.2 Política de contraseñas:** al menos 10 caracteres (parámetro), distinta del nombre de usuario y distinta de la contraseña actual.
- **RF-03.3 Cierre por inactividad:** la sesión se cierra tras 15 minutos sin uso (parámetro) y hay que volver a ingresar. Los datos que se estaban cargando y no se guardaron se descartan, con aviso previo.
- **RF-03.4 Gestión de usuarios:** un usuario puede blanquear la contraseña de otro (le asigna una provisoria y lo obliga a cambiarla al ingresar), dar de baja a otro usuario y reactivarlo. No puede darse de baja a sí mismo y siempre tiene que quedar al menos un usuario activo.
- **RF-03.5 Auditoría:** el sistema registra quién hizo qué y cuándo en los eventos relevantes: ingresos correctos y fallidos, bloqueos, cierres de sesión, cambios y blanqueos de contraseña, altas, bajas y reactivaciones de usuarios, eliminación de trabajos, cambios del monto total o de la seña, cambios de estado de un trabajo, cambios de parámetros y resultado de las copias de seguridad. Cada registro guarda fecha y hora, usuario, evento, el dato afectado, el detalle del cambio (valor anterior → nuevo) y el nombre de la PC.
- **RF-03.6 Consulta de auditoría:** pantalla con filtros por fecha, usuario y tipo de evento, con los eventos críticos resaltados (bloqueos, blanqueos, altas y bajas de usuarios, eliminación de trabajos, cambios de montos y parámetros, copias fallidas). Los registros no se pueden modificar ni borrar desde el sistema.
- **RF-03.7 Aviso de último ingreso:** al ingresar, el sistema muestra la fecha y hora del último ingreso del usuario y, si los hubo, los intentos fallidos desde entonces. Así el propio usuario detecta si alguien intentó entrar con su cuenta.

### M2 — Clientes
- **RF-04** Alta, modificación, baja lógica y consulta de clientes (nombre, teléfono, email opcional, observaciones).
- **RF-04.1** Baja de un cliente: no se permite si tiene trabajos en curso (no cobrados ni cancelados); el sistema los lista para terminarlos o cancelarlos primero. Un cliente dado de baja no admite obras ni trabajos nuevos, ni cambios en sus obras. Sus trabajos terminados quedan como historial: no aparecen en el listado general de trabajos (sí al buscarlos, ej.: por el nombre del cliente), se ven en su ficha y no se pueden modificar hasta reactivarlo.
- **RF-05** Un cliente puede tener una o más obras (casas o inmuebles), cada una con su dirección, localidad y un alias opcional.
- **RF-05.1** Historial por obra: se pueden consultar todos los trabajos realizados en una misma obra y crear trabajos nuevos en ella, aunque hayan pasado años.
- **RF-06** Búsquedas flexibles en todo el sistema:
  - Por texto parcial (palabras o fragmentos, ej.: "lib" encuentra "Av. Libertador"), sin distinguir mayúsculas ni tildes.
  - Por número (ID de trabajo, cliente u obra; teléfono).
  - Clientes: por nombre, apellido, teléfono, email o dirección de cualquiera de sus obras.
  - Obras: por dirección, localidad o alias.
  - Trabajos: por ID, descripción, cliente, obra, estado y rango de fechas.
  - Materiales y colores: por nombre o código.
  - Retazos: por material, color y medidas mínimas (RF-30).
- **RF-07** Historial de trabajos del cliente, agrupado por obra: trabajos realizados, muebles, materiales y colores usados.

### M3 — Catálogo de materiales
- **RF-08** ABM de placas: marca, color, espesor (18 mm, 15 mm, 9 mm, 5,5 mm u otros), medidas de la placa entera y si tiene veta. Los fondos son placas de 5,5 mm.
- **RF-08.1** Cada color se identifica por nombre y/o código del fabricante (al menos uno de los dos es obligatorio). Como un mismo color puede tener códigos distintos según la marca, el código se registra por marca. Se puede buscar un color por cualquiera de los dos.
- **RF-09** ABM de tipos de filo (sin filo, 0,45 mm, 2 mm) con su descuento por canto. El color del filo es, por defecto, el de la pieza; si es otro, se elige entre los colores de placa.
- **RF-10** ABM de listones (pino), con su sección (ej. 2×1").
- **RF-11** Las medidas de la placa entera dependen de la marca y se registran por material. Un mismo color y espesor puede venir en más de un tamaño de placa.
- **RF-11.0** ABM de estilos de frente: nombre, luces superior, inferior y entre frentes, y descripción (ej.: indicaciones de fabricación).
- **RF-11.1** Los elementos del catálogo (marcas, colores, placas, listones, lacas, terminaciones, guías, estilos de frente) no se borran si están en uso: se dan de baja lógica. Un elemento dado de baja no se ofrece para cargas nuevas, pero los trabajos anteriores lo siguen mostrando. Lo que nunca se usó (ej.: cargado por error) se puede eliminar. Una placa o un listón en uso no cambia su color, espesor, medidas ni sección (se da de baja y se carga el nuevo), y un color en uso no cambia si tiene veta.

### M4 — Trabajos, muebles y módulos
- **RF-12** Un trabajo pertenece a una obra (y, a través de ella, a un cliente) y contiene uno o más muebles. En una obra se puede registrar todo en un solo trabajo o en varios trabajos por etapas, cada uno con su propio estado, montos y fechas.
- **RF-13** Un mueble contiene uno o más módulos y puede tener piezas sueltas cargadas manualmente (ajustes, revestimientos u otras piezas que no surgen de un módulo).
- **RF-13.1** Un mueble puede tener uno o más zócalos (opcional). Cada zócalo es una estructura de melamina que puede abarcar un módulo, varios o el mueble entero, de alto variable (5, 8, 10 cm, etc.), con refuerzos según su largo. Las partes que no se ven (algún lateral, los refuerzos) pueden ir de otro color.
- **RF-14** Un módulo se define por sus medidas exteriores (ancho × alto sin zócalo × profundidad), sus materiales, su tipo de armado y sus componentes:
  - Materiales: placa de la estructura; placa de los frentes (puertas y frentes de cajón), que puede ser de otro color, enchapada o cruda para laquear; placa de la caja de los cajones (puede ser blanca aunque el mueble sea de color); color de laca de los frentes (opcional). Si no se indican, frentes y cajones usan la placa de la estructura.
  - Tipo de armado: módulo (piso y techo enteros) o cajonera (laterales enteros con fajas).
  - Estructura: con techo o sin techo (bajo mesada).
  - Cantidad de estantes.
  - Fondo: sí / no.
  - Puertas: cantidad.
  - Cajones: cantidad, tipo de guía, alto estimado de la caja y, opcionalmente, alto del frente.
  - Estilo de frente y luces: se elige un estilo (con tirador, alacena que sobresale abajo, bajo mesada con gola, etc.) que completa las luces superior, inferior y entre frentes; luego se pueden ajustar (ej.: abajo a filo de la cajonera = 0). Una luz negativa indica que el frente sobresale.
  - Un mismo módulo puede combinar cajones y puertas (ej.: cajón arriba y puertas abajo).
  - Pinos de apoyo de mesada (bajo mesada).
- **RF-14.1** Asistente de carga de módulos: la carga se hace paso a paso y cada respuesta define las preguntas siguientes. El primer paso es el tipo de armado:
  - **Módulo:** se continúa con medidas, materiales, techo, estantes, fondo, pinos, puertas y cajones.
  - **Cajonera:** se pregunta si las fajas van de luz o si los laterales van de luz, y el ancho de las fajas (10 o 12 cm habitualmente); luego medidas, materiales y cajones. Una cajonera no lleva techo, estantes, puertas ni pinos.
  - En ambos casos, el asistente pregunta el estilo de frente, completa las luces y permite modificarlas.
- **RF-15** Cada pieza tiene asignado un tipo de filo (sin filo, 0,45 mm o 2 mm) e indica cuáles de sus 4 cantos lo llevan. El sistema **no carga filos por defecto** (un filo de más es un costo): el usuario define el filo de cada pieza según los cantos que queden a la vista (ver RN-08).
- **RF-15.1** El filo es, por defecto, del mismo color que la pieza. Opcionalmente se puede indicar otro color.
- **RF-15.2** Una pieza puede laquearse, indicando el color de laca (código de marcas como Alba o Sherwin Williams) y la terminación (mate, semimate, brillante), que es obligatoria. Habitualmente se laquean solo los frentes, mientras la estructura queda en el color de la placa. Las piezas a laquear pueden cortarse de placa cruda o de color. Las piezas laqueadas no llevan filo: al marcar una pieza como laqueada, el sistema le asigna "sin filo" automáticamente.
- **RF-15.3** Ayudas para definir los filos rápido:
  - **Una sola vez por fila:** las piezas iguales se generan en una fila con su cantidad (ej.: "Lateral ×2"), y el filo se define una vez para toda la fila.
  - **Aplicar a varias piezas:** se seleccionan varias filas (ej.: todos los estantes) y se les asigna el mismo filo de una sola vez.
  - **Dividir una fila:** si una o más piezas de una fila llevan un filo distinto (ej.: de dos laterales, uno es visto), se separan en una fila nueva con su propia cantidad y su propio filo. La fila original reduce su cantidad.
- **RF-16** Se puede duplicar un módulo, un mueble o un trabajo anterior como base para uno nuevo.

### M5 — Despiece automático
- **RF-17** A partir de los datos del módulo, el sistema calcula todas sus piezas: nombre, cantidad, medidas finales, material, color y sentido de la veta. Los filos quedan sin definir para que el usuario los elija (RN-08).
- **RF-18** El cálculo aplica las reglas de la sección 4 y los parámetros configurables de la sección 5.
- **RF-19** El usuario puede editar manualmente cualquier pieza calculada, incluido rotar el sentido de la veta (las piezas editadas quedan marcadas). Al rotar, se intercambian las medidas y también los cantos con filo.
- **RF-20** Se puede recalcular el despiece de un módulo o de un cajón si cambian sus medidas (ej.: el alto de un solo cajón). Se regeneran solo las piezas no editadas; las editadas a mano se conservan y el sistema avisa para revisarlas.

### M6 — Listado de corte
- **RF-21** Genera un PDF imprimible con todas las piezas de un trabajo. Requiere que todas las piezas tengan el filo definido (RN-08.1).
- **RF-22** Agrupa las piezas por material: una sección por cada combinación de marca, color y espesor de placa (18 mm, fondos de 5,5 mm, otros espesores), y una sección aparte para el pino.
- **RF-23** Por cada pieza: cantidad, medida de corte 1 (sentido de la veta), medida de corte 2, tipo de filo, color del filo cuando es distinto al de la pieza, y un dibujo de los cantos con filo (cuadrado, U, L o línea), siguiendo la notación usada hoy con la maderera. Las medidas de corte ya tienen descontado el filo (RN-03.1).
- **RF-24** Las piezas exactamente iguales (mismo material, medidas, sentido de la veta, tipo de filo, cantos con filo, color de filo, laca y terminación) se consolidan en una sola fila con su cantidad.
- **RF-24.1** Genera un PDF aparte para el laqueador con las piezas a laquear de un trabajo, agrupadas por color de laca (marca y código) y terminación (mate, semimate, brillante), con cantidad y medidas finales.

### M7 — Estados y pagos
- **RF-25** Estados de un trabajo: Presupuestado → Confirmado → En producción → Terminado → Instalado → Cobrado. También Cancelado.
- **RF-25.1** Los estados avanzan de a uno y en orden. Para corregir un paso marcado por error se vuelve un solo paso atrás, y se borra la fecha de fabricación de ese paso (comienzo, finalización o entrega). No se puede volver a Presupuestado con la seña cobrada. Se puede cancelar en cualquier estado salvo Cobrado; al retomar un trabajo cancelado, vuelve al último estado que indican sus fechas.
- **RF-25.2** Cobrar no es un paso de la fabricación: la seña y el saldo se registran cuando ocurren. Registrar el cobro de la seña de un trabajo presupuestado lo confirma. El saldo se puede cobrar por adelantado desde Confirmado (ej.: el cliente paga el total al confirmar); el trabajo sigue su curso y, al pasar a Cobrado, conserva esa fecha. Para pasar a Cobrado, la seña y el saldo tienen que estar cobrados.
- **RF-26** Cada trabajo registra su monto total (cargado manualmente en la V1) y el monto de la seña. El saldo no se almacena: se calcula como total − seña.
- **RF-26.1** Cada trabajo registra su fecha de presupuesto (por defecto, el día en que se carga; se puede indicar una fecha pasada si el trabajo se anotó tarde, nunca futura, y su cambio queda en la auditoría) y, además, cinco fechas como atributos independientes:
  - Fecha de cobro de la seña
  - Fecha de comienzo
  - Fecha de finalización (fin de fabricación)
  - Fecha de entrega (instalación)
  - Fecha de cobro del saldo
- **RF-26.2** El sistema valida que las fechas sean coherentes: ninguna es anterior a la fecha de presupuesto; cobro de la seña ≤ comienzo ≤ finalización ≤ entrega; cobro de la seña ≤ cobro del saldo; los cobros no pueden ser futuros, y tampoco la fecha de un estado ya alcanzado. Las fechas de estados todavía no alcanzados (ej.: entrega pactada) pueden ser futuras y se muestran como previstas; el orden entre fechas se exige entre fechas reales (o entre previstas), no entre una real y una prevista que quedó atrás.
- **RF-26.3** Al cambiar el estado del trabajo, el sistema sugiere completar la fecha correspondiente: Confirmado → cobro de la seña; En producción → comienzo; Terminado → finalización; Instalado → entrega; Cobrado → cobro del saldo.
- **RF-26.4** Entrega pactada: mientras el trabajo no está instalado, la fecha de entrega es la pactada con el cliente, que puede ser un día ("tiene que estar instalado el jueves 5") o solo una semana ("la semana del 2/11"). Se carga al crear el trabajo o después, y al pasar a Instalado se reemplaza por la fecha real. Si pasa el día (o termina la semana) sin instalar, el inicio la marca como entrega atrasada. Una entrega pactada que quedó atrás no impide registrar los pasos de fabricación de un trabajo demorado.
- **RF-27** El sistema sugiere la seña como un porcentaje del total (por defecto 60%) y calcula el saldo como total − seña.
- **RF-28** Listado de trabajos filtrable por estado y vista de trabajos con saldo pendiente.

### M8 — Inventario de retazos
El inventario es de uso interno del taller: registra los sobrantes que llegan de la maderera para saber qué hay disponible. No interviene en los pedidos a la maderera.

- **RF-29** Alta de retazos: medidas, material, color y ubicación opcional en el taller.
- **RF-30** Búsqueda por material/color y medidas mínimas requeridas.
- **RF-31** En materiales sin veta, la búsqueda considera la pieza rotada. En materiales con veta, respeta el sentido.
- **RF-32** Al usar un retazo se da de baja y, opcionalmente, se registra el sobrante resultante.

---

## 4. Reglas de negocio (despiece)

### 4.1 Convenciones
- **RN-01** Todas las medidas se expresan en centímetros con un decimal.
- **RN-02** La primera medida de una pieza es siempre el sentido de la veta. En colores lisos el orden es indistinto.
- **RN-02.1** El sentido de la veta no es fijo: cada tipo de pieza propone uno por defecto, pero el usuario puede rotarlo pieza por pieza según el gusto del cliente o para reducir desperdicio. Rotar intercambia el orden de las medidas.
  - **Vertical (en el alto):** puertas y laterales.
  - **Horizontal (en el largo):** estantes, pisos, techos, fajas y frentes de cajón.
- **RN-03** Los resultados se redondean hacia abajo al milímetro (ej.: 44,55 → 44,5).
- **RN-03.1** Las piezas se guardan con su **medida final** (terminada, con el filo incluido). La **medida de corte** que se envía a la maderera se calcula al generar el listado, restando el filo de cada canto que lo lleve (ver 4.5). Así, la maderera corta exactamente a la medida recibida.
- **RN-04** Construcción según el tipo de armado:
  - **Módulo:** el piso y el techo van enteros (ancho exterior) y los laterales van entre ellos. Se agujerean pisos y techos.
  - **Cajonera:** lleva 4 fajas (2 arriba y 2 abajo, adelante y atrás) de ancho variable (habitualmente 10 o 12 cm). Puede armarse de dos formas:
    - **Fajas de luz:** los laterales van enteros (alto exterior) y las fajas entre ellos. Se agujerean los laterales. Ej.: cajonera de 34 de alto → espacio interior de 30,4.
    - **Laterales de luz:** las fajas van enteras (ancho exterior) y los laterales entre ellas.

| Pieza (cajonera) | Cant. | Fajas de luz | Laterales de luz |
|------------------|-------|--------------|------------------|
| Laterales | 2 | H × P | (H − 2e) × P |
| Fajas | 4 | (A − 2e) × ancho faja | A × ancho faja |

### 4.2 Estructura
Siendo `A` ancho, `H` alto, `P` profundidad y `e` el espesor de placa (1,8 cm):

| Pieza | Cant. | Medidas |
|-------|-------|---------|
| Piso | 1 | A × P |
| Techo (si lleva) | 1 | A × P |
| Laterales con techo | 2 | (H − 2e) × P |
| Laterales sin techo | 2 | (H − e) × P |
| Estantes | n | (A − 2e) × P |
| Fondo (opcional, 5,5 mm) | 1 | A × H |
| Pinos (bajo mesada, 2×1") | 2 | largo = A − 2e (uno adelante y uno atrás, arriba) |

### 4.3 Puertas
Siendo `n` la cantidad de puertas, `lext` la luz exterior (0,3 cm), `lint` la luz entre puertas (0,3 cm) y `lsup` / `linf` las luces superior e inferior del módulo (según el estilo de frente; una luz negativa indica que la puerta sobresale):

- Ancho = (A − 2 × lext − (n − 1) × lint) / n
- Alto = H − lsup − linf
- Esa es la medida final; la de corte descuenta el filo (ver 4.5).

### 4.3 bis Estilos de frente
Las luces de los frentes dependen del diseño. Para no cargarlas a mano, se elige un estilo que las completa; después se pueden ajustar en cada módulo. Signo: positiva = el frente queda adentro del borde; 0 = a filo; negativa = sobresale.

| Estilo | Luz arriba | Luz abajo | Entre frentes | Notas |
|--------|------------|-----------|---------------|-------|
| Con tirador | 0,4 | 0,4 | 0,3 | |
| Cajonera con tirador | 0,6 | 0,6 | 0,3 | |
| Alacena (sobresale abajo) | 0 | −1,3 | 0,3 | Puertas parejas arriba; sobresalen 1,3 cm abajo para abrirlas |
| Bajo mesada con gola | 3 | 0 | 3 | Frentes hasta abajo de todo |

**Bajo mesada con gola:** los laterales llevan rebajes de 3,6 cm de profundidad que funcionan como agarradera: uno de 5 cm de alto arriba (el frente lo tapa 2 cm y quedan 3 cm de luz) y, entre frentes de cajón, uno de 7 cm (cada frente tapa 2 cm y quedan 3 cm). Los rebajes se hacen en el taller, por lo que no modifican el listado de corte: los laterales se cortan rectos.

Los estilos se cargan como datos: se pueden agregar nuevos sin modificar el código.

### 4.4 Cajones
El tipo de guía define qué piezas lleva el cajón. Cada pieza se calcula como una medida de referencia (ancho interior del módulo, largo de la guía o alto del cajón) menos una constante propia de la guía. Las constantes se cargan como datos por tipo de guía, de modo que incorporar una guía nueva no requiere cambiar el código.

- El largo del cajón es igual al largo de la guía, que se elige según la profundidad del módulo (ver d).
- El frente visible es siempre una pieza aparte y puede laquearse.

**a) Guía telescópica de cierre suave**

Siendo `g` el descuento de la guía por lado (1,35 cm), `ec` el espesor de los laterales del cajón (1,8 cm) y `d` la diferencia de altura del frente interno (3 cm, modificable en los datos de la guía o pieza por pieza):

| Pieza | Cant. | Medidas |
|-------|-------|---------|
| Laterales (18 mm) | 2 | largo guía × alto cajón |
| Contrafrente (atrás, 18 mm) | 1 | (A − 2e − 2g − 2ec) × alto cajón |
| Frente interno (adelante, 18 mm) | 1 | (A − 2e − 2g − 2ec) × (alto cajón − d) |
| Fondo (placa de 5,5 mm) | 1 | (A − 2e − 2g) × largo guía |
| Frente visible | 1 | ver más abajo |

Al frente interno se atornilla el frente visible. El fondo se calcula sin rebaje (clavado por debajo de la caja); cuando las piezas llevan rebaje (en las 4 piezas, o en laterales y contrafrente), la medida se ajusta manualmente.

**b) Corredera de lateral oculto**

Los laterales son parte del herraje, por lo que no se cortan.

| Pieza | Cant. | Medidas |
|-------|-------|---------|
| Contrafrente (18 mm) | 1 | (A − 2e − 8,7) × alto fijo según la marca |
| Piso (18 o 15 mm) | 1 | (A − 2e − 7,5) × (largo guía − 1) |
| Frente visible | 1 | ver más abajo |

El frente visible se fija directamente a las guías (no hay frente interno). Las constantes (8,7, 7,5 y 1) son las mismas para Rincón del Herraje, Eurohard y Häfele. Solo el alto del contrafrente varía por marca. Cada marca se carga como un tipo de guía distinto.

Ejemplo: módulo de 60 de ancho (interior 56,4) con guía de 45 → piso de 48,9 × 44; contrafrente de 47,7 × alto según la marca.

**c) Frente visible**
Los frentes cubren el alto exterior del módulo. Siendo `n` la cantidad de frentes, `lext` la luz lateral, `lsup` / `linf` las luces superior e inferior y `lf` la luz entre frentes:

- Ancho = A − 2 × lext
- Alto (reparto en partes iguales) = (H − lsup − linf − (n − 1) × lf) / n
- Esa es la medida final; la de corte descuenta el filo (ver 4.5).
- `lext` = 0,3 cm (igual que las puertas).
- `lsup`, `linf` y `lf` se definen por módulo, a partir del estilo de frente (ver 4.3 bis), y se pueden ajustar según el diseño (ej.: abajo a filo de la cajonera = 0).

Ejemplo (cajonera de 34 de alto, 2 cajones con tirador, filo de 2 mm): (34 − 0,6 − 0,6 − 0,3) / 2 = 16,25 → 16,2 (redondeo hacia abajo) → se corta a 15,8 de alto (103,2 × 16,2 final → 102,8 × 15,8 de corte).

**Módulos con cajones y puertas:** cada cajón tiene su alto de frente (obligatorio); las puertas ocupan el alto restante:
Alto puertas = H − lsup − linf − Σ altos de frentes de cajón − (cantidad de cajones) × lf.

**Cajones con distinto alto de frente:** si solo algunos cajones tienen alto de frente definido, los demás se reparten en partes iguales el alto que queda libre.

**Material de cada pieza:** el piso del cajón usa la placa elegida para el piso; laterales, contrafrente y frente interno, la placa de cajones del módulo; el frente visible, la placa de frentes.

**d) Largo de la guía**
Se propone la guía más larga disponible que entre en el módulo: el mayor largo comercial tal que largo + espacio adicional de la guía ≤ profundidad del módulo + tolerancia (0,5 cm: se acepta que la guía sobresalga hasta 5 mm). Los largos disponibles se cargan por tipo de guía (no siempre van de 5 en 5). El usuario puede cambiar la guía propuesta.

| Profundidad | Telescópica (0,2) | Oculta Häfele / Eurohard (0,8) | Oculta Rincón del Herraje (1,1) |
|-------------|-------------------|--------------------------------|---------------------------------|
| 50 | 50 | 45 | 45 |
| 48 | 45 | 45 | 45 |
| 40,5 | 40 | 40 | 35 |
| 40 | 40 | 35 | 35 |
| 37 | 35 | 35 | 35 |

**e) Alto del cajón**
Todo se pide en un solo pedido. Los frentes se calculan exactos; el alto de la caja se carga estimado al diseñar (ej.: 12 cm) y las piezas de la caja (laterales, frente interno y contrafrente) se calculan con ese valor. Se puede corregir y recalcular.

### 4.4 bis Zócalo
Es un marco de melamina (habitualmente 18 mm) sobre el que apoyan los módulos. Puede cubrir un módulo, varios o el mueble entero.

- **Opcional:** un mueble no lleva zócalo salvo que se agregue (los bajo mesadas habitualmente no llevan).
- **Medidas:** en la práctica se retira 1,5 cm del frente del mueble y 1,5 cm de cada costado libre (el mueble "vuela" 1,5 cm); entre paredes, va de pared a pared.
- **Propuesta del sistema:** retira 1,5 cm solo del frente. A los costados propone el largo completo del tramo, para que ante un error la pieza sobre (se corta) y no falte (desperdicio). Si un costado queda libre, el usuario descuenta el retiro.
- Siendo `L` el largo del zócalo, `Pz` su profundidad, `Hz` su alto y `e` el espesor (1,8 cm):

| Pieza | Cant. | Medidas |
|-------|-------|---------|
| Frente | 1 | L × Hz |
| Trasera | 1 | L × Hz |
| Laterales | 2 | (Pz − 2e) × Hz |
| Refuerzos | según el largo | (Pz − 2e) × Hz, repartidos |

- El frente y la trasera van siempre enteros; los laterales y refuerzos, entre ellos.
- La cantidad de refuerzos se define en la fabricación: se carga a mano (puede ser 0) y se puede agregar después, recalculando el zócalo.
- Las partes que no se ven (trasera, refuerzos y, a veces, algún lateral) pueden ir de otro color.

Ejemplo: tramo de 180 × 55 → el sistema propone un zócalo de 180 × 53,5. Si los dos costados quedan libres, el usuario lo ajusta a 177 × 53,5.

### 4.5 Filos
- **RN-05** Filo de 2 mm: en la medida de corte se descuenta 0,2 cm por cada canto con filo, en cualquier pieza (frentes, laterales vistos, vestidores, etc.). Ej.: lateral visto final 73,2 × 55 con 2 mm en un canto corto → corte 73,0 × 55.
- **RN-06** Filo de 0,45 mm: no se descuenta nada (casi no suma espesor). El valor queda configurable en el tipo de filo.
- **RN-07** Una pieza lleva un solo tipo de filo.
- **RN-08** Sin filos por defecto: toda pieza nace con el filo **sin definir** (distinto de "sin filo"). La única excepción son las piezas laqueadas, que nacen sin filo.
- **RN-08.1** No se puede generar el listado para la maderera mientras alguna pieza del trabajo tenga el filo sin definir; el sistema indica cuáles faltan. Así no se agregan filos de más ni se olvida ninguno.
- **RN-08.2** Usos habituales, como referencia (no se cargan solos): puertas con 2 mm alrededor; laterales vistos con 2 mm en un canto largo y uno corto; estructura, estantes, pisos y techos con 0,45 mm (estantes: solo el canto largo de adelante); vestidores mayormente todo en 2 mm.

### 4.6 Ejemplos de validación
**Bajo mesada 90 × 75 × 55, sin techo, 1 estante, 2 pinos:**
piso 90 × 55 · laterales 73,2 × 55 (×2) · estante 86,4 × 55 · pinos 86,4 (×2).

**Módulo con techo 90 × 60 × 40, 1 estante, fondo, 2 puertas con filo de 2 mm:**
piso y techo 90 × 40 (×2) · laterales 56,4 × 40 (×2) · estante 86,4 × 40 · fondo 90 × 60 · puertas: final 59,2 × 44,5 → corte 58,8 × 44,1 con filo de 2 mm en los 4 cantos (×2), con veta vertical por defecto.

**Cajonera 60 × 34 × 50, fajas de luz de 10 cm, 2 cajones telescópicos con tirador, frentes con filo de 2 mm, caja estimada de 12:**
laterales 34 × 50 (×2) · fajas 56,4 × 10 (×4) · frentes final 59,4 × 16,2 → corte 59,0 × 15,8 (×2) · por cajón (guía de 50): laterales 50 × 12 (×2), contrafrente 50,1 × 12, frente interno 50,1 × 9, fondo de 5,5 mm 53,7 × 50.

**Cajonera de 80 de alto con 3 cajones (luces 0,6 / 0,6, entre frentes 0,3; espacio para frentes 78,2):**
sin altos definidos → 26,0 cada frente · con el primero en 15 → 15, 31,6 y 31,6.

**Módulo mixto 90 × 75, 1 cajón arriba (frente de 15) y 2 puertas abajo, luz superior 0,4 e inferior 0:**
frente del cajón 89,4 × 15 · puertas 59,3 × 44,5 (×2).

**Bajo mesada con gola de 90 × 75, 2 puertas:** puertas 72 × 44,5 (75 − 3 − 0) (×2).

**Alacena de 90 × 60, 2 puertas, estilo alacena:** puertas 61,3 × 44,5 (60 − 0 + 1,3) (×2).

> Estos ejemplos se convierten en casos de prueba automatizados del motor de despiece.

---

## 5. Parámetros configurables
Los valores de cálculo se guardan en la base de datos y se pueden modificar sin cambiar el código. Las luces de los frentes provienen de los estilos de frente: se copian a cada módulo al crearlo y ahí se ajustan según el diseño.

| Parámetro | Valor por defecto |
|-----------|-------------------|
| Luz lateral de puertas y frentes de cajón (por lado) | 0,3 cm |
| Luz entre puertas | 0,3 cm |
| Tolerancia para que la guía sobresalga | 0,5 cm |
| Retiro del zócalo (frente; a los costados lo aplica el usuario) | 1,5 cm |
| Porcentaje de seña | 60% |

Otros valores de cálculo viven en la entidad a la que pertenecen, no como parámetros generales:

| Valor | Dónde se guarda | Valor habitual |
|-------|-----------------|----------------|
| Luces superior, inferior y entre frentes | Estilos de frente (copiadas a cada módulo) | Ver 4.3 bis |
| Espesor de placa | Cada placa | 1,8 cm (también 1,5, 0,9, 0,55) |
| Descuento por canto, filo 2 mm | Tipo de filo | 0,2 cm |
| Descuento por canto, filo 0,45 mm | Tipo de filo | 0 cm |
| Largos disponibles y espacio adicional de cada guía | Tipo de guía y sus largos | Telescópica: 0,2 cm; lateral oculto Rincón del Herraje: 1,1 cm; Eurohard y Häfele: 0,8 cm |
| Diferencia de altura del frente interno del cajón | Piezas por tipo de guía | 3 cm (telescópica) |
| Descuentos de las piezas del cajón | Piezas por tipo de guía | Telescópica: 6,3 cm a lo ancho para contrafrente y frente interno (2 × 1,35 guía + 2 × 1,8 laterales); 2,7 cm para el fondo (2 × 1,35 guía) |

---

## 6. Requerimientos no funcionales
- **RNF-01 Arquitectura en 3 capas:** presentación (interfaz), lógica de negocio (servicios y motor de despiece) y acceso a datos (repositorios). Cada capa solo se comunica con la inmediata inferior.
- **RNF-02 Diseño:** principios SOLID y patrones GRASP. El motor de despiece se basa en componentes con su propia regla de cálculo, de modo que agregar un componente nuevo no requiere modificar los existentes (principio abierto/cerrado).
- **RNF-03 Base de datos relacional normalizada hasta 3FN**, con claves foráneas, restricciones e índices.
- **RNF-04 Tecnologías:** Python, interfaz gráfica con Flet, SQL Server Express (conexión con pyodbc), desarrollo en VS Code, control de versiones con Git/GitHub.
- **RNF-05 Seguridad:** ver la sección 6.1.
- **RNF-06 Calidad:** pruebas unitarias del motor de despiece con los ejemplos de la sección 4.6.
- **RNF-07 Usabilidad:** interfaz gráfica moderna; cargar un módulo y obtener su despiece debe llevar menos de un minuto.
- **RNF-08 Respaldo:** copia de seguridad automática de la base de datos (al menos diaria), guardada fuera de la PC (ej.: carpeta sincronizada en la nube). Evita perder clientes y trabajos si falla, se roba o se formatea la PC, o si un ransomware cifra el disco.
  - **Cifrada:** antes de salir de la PC, la copia se cifra con AES (cifrado simétrico); la clave se guarda en el Administrador de credenciales de Windows y una copia impresa en un lugar seguro fuera del taller. Sin esa clave las copias no se pueden restaurar.
  - **Verificable:** junto a cada copia se guarda su hash SHA-256; antes de restaurar se comprueba que coincida (integridad).
  - **Retención:** se conservan las últimas 30 copias diarias, así se puede volver a un día anterior a un problema.
  - **Prueba de restauración:** una vez por mes se restaura la última copia en una base de prueba, para confirmar que sirve. Una copia que nunca se probó no es una copia confiable.
  - **Restauración:** se hace siguiendo el plan de respuesta a incidentes (RNF-05.8) con la cuenta de administrador, no desde la aplicación, porque reemplaza la base completa.
- **RNF-09 Integridad:** borrado en cascada solo de lo que depende de un trabajo (muebles, módulos, cajones, piezas); clientes, obras y catálogo no se borran si están en uso (se dan de baja lógica).
- **RNF-10 Primer uso:** el sistema se instala con un usuario inicial y contraseña provisoria, que debe cambiarse en el primer ingreso.

### 6.1 Seguridad

#### 6.1.1 Criterio
La seguridad es proporcional al riesgo real: dos usuarios en una PC del taller. Los riesgos principales no son ataques sofisticados, sino perder los datos, el error humano y el uso de la PC por personas no autorizadas. Los clientes son datos personales (nombre, teléfono, dirección), protegidos por la Ley 25.326 de Protección de Datos Personales.

#### 6.1.2 Evaluación de riesgos
| Activo | Amenaza | Impacto | Controles |
|--------|---------|---------|-----------|
| Base de datos completa | Falla del disco, robo de la PC, ransomware | Alto: se pierden clientes, trabajos y montos | Copia diaria cifrada fuera de la PC con prueba mensual (RNF-08); cifrado del disco (6.1.4) |
| Datos de clientes | Acceso de alguien que usa la PC | Medio: exposición de datos personales | Ingreso con contraseña, bloqueo, cierre por inactividad (RF-01 a RF-03.3); bloqueo de pantalla de Windows |
| Trabajos y montos | Error humano o cambio indebido | Medio: montos o trabajos perdidos o alterados | Auditoría (RF-03.5); bajas lógicas y confirmaciones (RNF-09) |
| Contraseñas de usuarios | Robo de la base | Medio | Hash bcrypt con *salt* (RF-03) |
| Contraseña de la base y clave de las copias | Publicación accidental en GitHub, lectura de un archivo | Alto | Guardadas en el Administrador de credenciales de Windows, nunca en el repositorio (RNF-05.2) |
| Base de datos | Inyección SQL | Alto | Consultas parametrizadas y validación (RNF-05.3) |
| Aplicación | Librerías con vulnerabilidades conocidas | Medio | Control de dependencias (RNF-05.5) |

#### 6.1.3 Controles en el sistema
- **RNF-05.1 Mínimo privilegio en la base:** la aplicación se conecta con un login propio (`app_carpinteria`, rol `rol_app`), que solo puede leer y modificar datos, ejecutar procedimientos y hacer copias de seguridad. No puede crear, modificar ni borrar tablas, ni modificar o borrar la auditoría. La cuenta de administrador se usa solo para instalar, mantener y restaurar. La cuenta `sa` queda deshabilitada (script `05_seguridad.sql`).
- **RNF-05.2 Gestión de secretos:** la contraseña del login de la aplicación y la clave de cifrado de las copias se guardan en el Administrador de credenciales de Windows (librería `keyring`). Los archivos de configuración no contienen secretos y el repositorio de GitHub nunca contiene contraseñas ni claves (`.gitignore`, revisión antes de cada commit).
- **RNF-05.3 Prevención de inyección SQL:** todas las consultas son parametrizadas (marcadores `?` de pyodbc); nunca se arma SQL concatenando datos ingresados. La capa de negocio valida tipos, rangos y largos antes de llegar a la base. Hay pruebas automatizadas que intentan inyectar SQL en búsquedas y altas y verifican que no tenga efecto.
- **RNF-05.4 Manejo de errores:** el usuario ve mensajes claros y sin detalles técnicos (ej.: "No se pudo guardar el trabajo"). El detalle técnico se escribe en un archivo de log local con rotación, sin contraseñas ni datos personales.
- **RNF-05.5 Control de dependencias:** las versiones de las librerías quedan fijadas en `requirements.txt` y se revisan con `pip-audit` antes de cada versión del sistema. Si aparece una vulnerabilidad conocida (CVE), se actualiza la librería.
- **RNF-05.6 Superficie de ataque mínima:** SQL Server acepta solo conexiones locales (protocolo TCP/IP deshabilitado hacia la red), ya que la base y la aplicación están en la misma PC.
- **RNF-05.7 Hash de contraseñas:** bcrypt con costo 12 (incluye *salt* aleatorio por contraseña).
- **RNF-05.8 Plan de respuesta a incidentes:** documento `docs/plan_respuesta_incidentes.md` con los pasos ante robo o pérdida de la PC, ransomware, falla del disco, olvido de contraseñas, sospecha de acceso no autorizado, copia dañada y pérdida de la clave de cifrado.

#### 6.1.4 Verificación de la PC de instalación
Cuando se defina la PC, antes de instalar el sistema:
- [ ] Windows con las actualizaciones al día y actualizaciones automáticas activas.
- [ ] Cuenta de Windows con contraseña o PIN, y bloqueo automático de la pantalla a los pocos minutos sin uso.
- [ ] Cifrado del disco activo: BitLocker (Windows Pro) o "Cifrado de dispositivo" (Windows Home, si el equipo lo admite). La clave de recuperación se guarda fuera de la PC.
- [ ] Microsoft Defender (u otro antivirus) activo y actualizado.
- [ ] Carpeta sincronizada en la nube (OneDrive o Google Drive) para las copias de seguridad.
- [ ] SQL Server Express en modo mixto, solo con conexiones locales, y la cuenta `sa` deshabilitada.
- [ ] Ideal: uso diario con un usuario de Windows sin permisos de administrador.

#### 6.1.5 Fuera de alcance (por proporcionalidad)
Roles y permisos diferenciados, autenticación de dos factores y cifrado de toda la base (TDE no está disponible en SQL Server Express). Con dos usuarios en una PC sumarían complejidad sin reducir de forma significativa los riesgos de 6.1.2; el cifrado del disco cubre el robo de la PC.

---

## 7. Pendientes
- [ ] Cajones de lateral oculto: cargar el alto del contrafrente de cada marca de guía (dato).
- [ ] Largos disponibles de cada guía, telescópica y ocultas (datos).
- [x] Motor de base de datos: SQL Server Express.
- [ ] Definir la PC de instalación y aplicar la verificación de la sección 6.1.4.
- [ ] (V2) Fórmula de presupuesto.
