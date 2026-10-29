# Sistema de Gestión para Carpintería — Modelo de Datos

**Versión del documento:** 1.7 (parámetro descuento_fondo, migración `09`; piso de cajón con guía oculta: largo − 0,9, migración `08`; fecha de presupuesto del trabajo, migración `06`; entrega pactada por semana, migración `07`)
**Normalización:** 3FN
**Motor:** SQL Server 2025 Express (conexión desde Python con pyodbc). Base `Carpinteria` con collation `Modern_Spanish_CI_AI` (las búsquedas ignoran mayúsculas y tildes).
**Scripts:** `database/00_crear_base_de_datos.sql` … `05_seguridad.sql`.
**Tablas:** 29.

---

## 1. Convenciones

### 1.1 Tablas
- Nombre en singular, cada palabra con inicial mayúscula, separadas por guion bajo: `Cliente`, `Estado_Trabajo`, `Color_Placa`.
- Sin tildes ni ñ.

### 1.2 Atributos
- En minúscula y `snake_case`, terminados en el **sufijo de su tabla** (ver 1.3): `nombre_cli`, `fecha_alta_tra`.
- **Clave primaria:** `id_<tabla>`, sin sufijo (ya lleva el nombre de la tabla). Entera y autoincremental.
- **Clave foránea:** sin sufijo, con el mismo nombre que la PK que referencia (`id_cliente` en `Trabajo`). Si una tabla tiene dos FK hacia la misma tabla, se agrega el rol: `id_placa_fondo`, `id_trabajo_origen`.
- Booleanos con prefijo `es_`, `lleva_` o `tiene_`: `lleva_techo_mod`.
- Si el nombre del atributo repite el de la tabla, se omite la repetición: en `Placa`, `largo_pla` y no `largo_placa_pla`.

### 1.3 Sufijos por tabla
- Tablas de una palabra: las 3 primeras letras (`Cliente` → `_cli`).
- Tablas de dos palabras: inicial de la primera + 2 primeras letras de la segunda (`Tipo_Guia` → `_tgu`).
- Si dos tablas coinciden, a una se le agrega una cuarta letra.

| Tabla | Sufijo | | Tabla | Sufijo |
|-------|--------|-|-------|--------|
| Usuario | `_usu` | | Marca_Placa | `_mpl` |
| Parametro | `_par` | | Color_Placa | `_cpl` |
| Cliente | `_cli` | | Marca_Pintura | `_mpi` |
| Obra | `_obr` | | | |
| Estado_Trabajo | `_etr` | | Color_Laca | `_cla` |
| Trabajo | `_tra` | | Material | `_mat` |
| Mueble | `_mue` | | Placa | `_pla` |
| Modulo | `_mod` | | Liston | `_lis` |
| Tipo_Guia | `_tgu` | | Tipo_Filo | `_tfi` |
| Pieza_Guia | `_pgu` | | Tipo_Armado | `_tar` |
| Largo_Guia | `_lgu` | | Estilo_Frente | `_efr` |
| Cajon | `_caj` | | Tipo_Pieza | `_tpi` |
| Retazo | `_ret` | | Pieza | `_pie` |
| Terminacion_Laca | `_tla` | | Zocalo | `_zoc` |
| Tipo_Evento | `_tev` | | Auditoria | `_aud` |

### 1.4 Tipos de datos
- **Medidas en centímetros** con `DECIMAL(6,1)` (ej.: 73,2). Descuentos y luces con `DECIMAL(5,2)` (ej.: 0,2 · 0,65).
- **Importes** con `DECIMAL(12,2)`.
- **En SQL Server:** textos en `NVARCHAR` (Unicode, para ñ y tildes), booleanos en `BIT`, fechas con hora en `DATETIME2(0)`. Las restricciones tienen nombre (`PK_`, `FK_`, `UQ_`, `CK_`, `DF_`), así los errores indican qué regla falló.

### 1.5 Relaciones opcionales en lugar de booleanos redundantes
Cuando un dato opcional ya indica por sí mismo si algo existe, no se agrega un booleano aparte. Ejemplos: una pieza es laqueada si tiene `id_color_laca`; un módulo lleva fondo si tiene `id_placa_fondo`; un retazo está disponible si no tiene `fecha_baja_ret`. La capa de negocio expone esos conceptos como propiedades (`es_laqueada`, `lleva_fondo`, `esta_disponible`).

Abreviaturas: **PK** clave primaria · **FK** clave foránea · **NN** no nulo · **UQ** único.

---

## 2. Seguridad y configuración

### `Usuario`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_usuario | INT | PK |
| nombre_usuario_usu | VARCHAR(50) | NN, UQ |
| hash_contrasena_usu | VARCHAR(255) | NN |
| debe_cambiar_contrasena_usu | BOOLEAN | NN, default falso (verdadero en el usuario inicial) |
| nombre_completo_usu | VARCHAR(100) | NN |
| es_activo_usu | BOOLEAN | NN, default verdadero |
| fecha_alta_usu | DATETIME | NN, default fecha actual |
| intentos_fallidos_usu | INT | NN, default 0, ≥ 0. Contraseñas incorrectas seguidas; vuelve a 0 al ingresar bien |
| bloqueado_hasta_usu | DATETIME | Nulo o fecha pasada = no bloqueado |
| ultimo_ingreso_usu | DATETIME | Se muestra al ingresar (RF-03.7) |
| fecha_cambio_contrasena_usu | DATETIME | |

> El bloqueo se guarda como fecha de vencimiento y no como booleano: así se desbloquea solo al pasar el tiempo, sin un proceso que lo libere.

### `Tipo_Evento`
Catálogo de eventos de auditoría.

| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_tipo_evento | INT | PK |
| codigo_tev | VARCHAR(30) | NN, UQ (ej.: `LOGIN_FALLIDO`) |
| descripcion_tev | VARCHAR(100) | NN |
| es_critico_tev | BOOLEAN | NN, default falso. La pantalla de auditoría resalta los críticos |

### `Auditoria`
Registro de quién hizo qué y cuándo (RF-03.5). Solo se agregan filas, con el procedimiento `sp_registrar_evento`; el usuario de la aplicación no puede modificarlas ni borrarlas.

| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_auditoria | BIGINT | PK |
| fecha_hora_aud | DATETIME | NN, default fecha y hora actual |
| id_tipo_evento | INT | FK → Tipo_Evento, NN |
| id_usuario | INT | FK → Usuario. Nulo si el usuario ingresado no existe |
| usuario_ingresado_aud | VARCHAR(50) | Nombre tipeado en un ingreso fallido |
| entidad_aud | VARCHAR(30) | Tabla afectada (ej.: `Trabajo`) |
| id_entidad_aud | INT | Id del registro afectado; si se informa, `entidad_aud` es obligatoria |
| detalle_aud | VARCHAR(500) | Ej.: `monto_total_tra: 500000.00 → 550000.00` |
| equipo_aud | VARCHAR(100) | Nombre de la PC |

> `entidad_aud` + `id_entidad_aud` es una referencia genérica, sin FK: la auditoría tiene que conservar el registro aunque el trabajo se haya borrado. Por eso no se relaciona con cada tabla.

### `Parametro`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_parametro | INT | PK |
| clave_par | VARCHAR(50) | NN, UQ (ej.: `luz_lateral_frente`) |
| valor_par | DECIMAL(8,2) | NN |
| unidad_par | VARCHAR(10) | NN (ej.: `cm`, `%`) |
| descripcion_par | VARCHAR(200) | |

---

## 3. Clientes y trabajos

### `Cliente`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_cliente | INT | PK |
| nombre_cli | VARCHAR(50) | NN |
| apellido_cli | VARCHAR(50) | NN |
| telefono_cli | VARCHAR(25) | NN |
| email_cli | VARCHAR(100) | |
| observaciones_cli | VARCHAR(500) | |
| es_activo_cli | BOOLEAN | NN, default verdadero (baja lógica) |
| fecha_alta_cli | DATETIME | NN, default fecha actual |

### `Obra`
Una casa o inmueble donde se realizan trabajos. Permite consultar todo lo hecho en un mismo lugar y crear trabajos nuevos años después.

| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_obra | INT | PK |
| id_cliente | INT | FK → Cliente, NN |
| nombre_obr | VARCHAR(100) | (alias opcional, ej.: "Casa Nordelta") |
| direccion_obr | VARCHAR(150) | NN |
| localidad_obr | VARCHAR(80) | NN |
| observaciones_obr | VARCHAR(500) | (ej.: acceso, horarios, portero) |
| fecha_alta_obr | DATETIME | NN, default fecha actual |

> UQ (id_cliente, direccion_obr, localidad_obr): evita cargar dos veces la misma casa de un cliente.

### `Estado_Trabajo`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_estado_trabajo | INT | PK |
| nombre_etr | VARCHAR(30) | NN, UQ |
| orden_etr | INT | NN, UQ (para ordenar el flujo) |

> Valores y fecha que se sugiere completar al pasar a cada estado en la sección 9 (datos iniciales).

### `Trabajo`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_trabajo | INT | PK |
| id_obra | INT | FK → Obra, NN |
| id_estado_trabajo | INT | FK → Estado_Trabajo, NN |
| descripcion_tra | VARCHAR(200) | NN (ej.: "Cocina completa") |
| monto_total_tra | DECIMAL(12,2) | ≥ 0 |
| monto_sena_tra | DECIMAL(12,2) | ≥ 0 y ≤ monto_total_tra |
| fecha_alta_tra | DATETIME | NN, default fecha actual. Cuándo se cargó en el sistema: no se edita |
| fecha_presupuesto_tra | DATE | NN, default fecha actual. Editable hacia el pasado (trabajo anotado tarde) |
| fecha_cobro_sena_tra | DATE | |
| fecha_comienzo_tra | DATE | |
| fecha_finalizacion_tra | DATE | ≥ fecha_comienzo_tra |
| fecha_entrega_tra | DATE | ≥ fecha_finalizacion_tra. Antes de instalar: entrega pactada; después: la real |
| entrega_aproximada_tra | BIT | NN, default 0. 1 = de la entrega pactada solo se sabe la semana |
| fecha_cobro_saldo_tra | DATE | |
| observaciones_tra | VARCHAR(500) | |

> CHECK: ninguna de las cinco fechas es anterior a `fecha_presupuesto_tra` (`CK_Trabajo_fechas_desde_presupuesto`).
> El saldo no se almacena: se calcula como `monto_total_tra − monto_sena_tra`.
> El cliente del trabajo se obtiene a través de la obra (`Trabajo → Obra → Cliente`). No se guarda `id_cliente` en el trabajo para evitar una dependencia transitiva (3FN).
> Una obra puede tener varios trabajos: todo junto en un solo trabajo, o por etapas (cada una con su seña, saldo, estado y fechas).

### `Mueble`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_mueble | INT | PK |
| id_trabajo | INT | FK → Trabajo, NN |
| nombre_mue | VARCHAR(100) | NN (ej.: "Bajo mesada cocina") |
| observaciones_mue | VARCHAR(500) | |

### `Zocalo`
Estructura de melamina sobre la que apoyan los módulos. Pertenece al mueble porque puede abarcar un módulo, varios o el mueble entero.

| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_zocalo | INT | PK |
| id_mueble | INT | FK → Mueble, NN |
| id_placa | INT | FK → Placa, NN (partes visibles) |
| id_placa_oculta | INT | FK → Placa (laterales o refuerzos que no se ven; nulo = misma placa) |
| descripcion_zoc | VARCHAR(100) | (ej.: "Zócalo bajo mesada completo") |
| largo_zoc | DECIMAL(6,1) | NN, > 0 |
| alto_zoc | DECIMAL(6,1) | NN, > 0 (5, 8, 10 cm, etc.) |
| profundidad_zoc | DECIMAL(6,1) | NN, > 0 |
| cantidad_refuerzos_zoc | INT | NN, ≥ 0, default 0 (se define en la fabricación; se carga a mano) |

> Un mueble puede tener varios zócalos (ej.: uno por tramo).
> El alto de los módulos se mide **sin** zócalo; el alto final del mueble = alto del módulo + alto del zócalo.
> El zócalo es opcional: un mueble no tiene ninguno salvo que se agregue (ej.: los bajo mesadas habitualmente no llevan).
> `largo_zoc` y `profundidad_zoc` son las medidas finales del zócalo. El asistente las propone a partir del tramo que cubre: la profundidad se retira `retiro_zocalo` (1,5 cm) del frente; el largo se propone **completo, sin retiro a los costados**, para que ante un error sobre (se puede cortar) y no falte. Si un costado queda libre, el usuario reduce el largo.
> Es un marco: frente y trasera enteros, laterales y refuerzos entre ellos. Por defecto, la trasera y los refuerzos usan `id_placa_oculta`; cada lateral se puede cambiar si no se ve.

### `Modulo`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_modulo | INT | PK |
| id_mueble | INT | FK → Mueble, NN |
| id_tipo_armado | INT | FK → Tipo_Armado, NN |
| id_estilo_frente | INT | FK → Estilo_Frente (estilo elegido al cargar; nulo = luces personalizadas) |
| id_placa | INT | FK → Placa, NN (material de la estructura) |
| id_placa_frentes | INT | FK → Placa (puertas y frentes de cajón; nulo = misma placa que la estructura) |
| id_placa_cajones | INT | FK → Placa (caja de los cajones: laterales, contrafrente y frente interno; nulo = misma placa que la estructura) |
| id_placa_fondo | INT | FK → Placa (nulo = no lleva fondo) |
| id_liston | INT | FK → Liston (nulo = no lleva pinos) |
| id_color_laca_frentes | INT | FK → Color_Laca (nulo = frentes sin laquear) |
| id_terminacion_laca_frentes | INT | FK → Terminacion_Laca (obligatoria si hay laca de frentes) |
| nombre_mod | VARCHAR(100) | (ej.: "Módulo bacha") |
| ancho_mod | DECIMAL(6,1) | NN, > 0 |
| alto_mod | DECIMAL(6,1) | NN, > 0 (sin zócalo) |
| profundidad_mod | DECIMAL(6,1) | NN, > 0 |
| lleva_techo_mod | BOOLEAN | NN (solo aplica al tipo Módulo) |
| ancho_faja_mod | DECIMAL(6,1) | > 0 (solo cajoneras, ej.: 10 o 12; nulo en módulos) |
| cantidad_estantes_mod | INT | NN, ≥ 0 |
| cantidad_puertas_mod | INT | NN, ≥ 0 |
| luz_superior_mod | DECIMAL(5,2) | NN (luz arriba del primer frente; negativa = el frente sobresale) |
| luz_inferior_mod | DECIMAL(5,2) | NN (luz abajo del último frente; 0 = a filo; negativa = sobresale, ej.: −1,3 en alacenas) |
| luz_entre_frentes_mod | DECIMAL(5,2) | NN, ≥ 0 (0,3 con tirador; 3 con gola; según diseño) |

> **Materiales del módulo:** la estructura usa `id_placa`; puertas y frentes de cajón usan `id_placa_frentes` (ej.: módulo blanco con frentes de color, enchapados, o cortados de crudo para laquear); la caja de los cajones usa `id_placa_cajones` (puede ser blanca aunque el mueble sea de color). Son valores por defecto: cada pieza guarda su propio material y se puede cambiar.
> Si `id_color_laca_frentes` tiene valor, las puertas y frentes de cajón se generan laqueados y sin filo.
> **Luces:** al cargar el módulo se elige un estilo de frente (`Estilo_Frente`) y sus luces se copian al módulo, donde se pueden ajustar. Al quedar guardadas en el módulo, un cambio futuro en los estilos no altera trabajos anteriores. `id_estilo_frente` registra el diseño elegido (ej.: "Bajo mesada con gola" indica al taller que los laterales llevan rebajes); si se modifican las luces, se conserva como referencia.
> **Signo de las luces:** positiva = el frente queda adentro del borde del módulo; 0 = a filo; negativa = sobresale. La misma fórmula sirve para todos los casos.
> La luz lateral (0,3 cm) y la luz entre puertas (0,3 cm) son siempre las mismas y se toman de `Parametro`.

> Si el módulo tiene cajones y puertas, las puertas ocupan el alto que dejan libre los frentes de los cajones.
> **Validado en la capa de negocio:** `ancho_faja_mod` es obligatorio si el tipo de armado es cajonera y debe ser nulo en caso contrario. En una cajonera no aplican techo, estantes, puertas ni pinos (se guardan en falso / 0 / nulo).

### `Tipo_Armado`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_tipo_armado | INT | PK |
| nombre_tar | VARCHAR(50) | NN, UQ |
| es_cajonera_tar | BOOLEAN | NN (define si se pide el ancho de faja) |
| descripcion_tar | VARCHAR(200) | |

> Valores:
> - **Módulo:** piso y techo enteros, laterales de luz (se agujerean pisos y techos). Aplica a todos los módulos que no son cajonera.
> - **Cajonera con fajas de luz:** laterales enteros, 4 fajas entre ellos (se agujerean los laterales).
> - **Cajonera con laterales de luz:** 4 fajas enteras, laterales entre ellas.
> Cada tipo tiene su propia regla de despiece en la capa de negocio.

### `Estilo_Frente`
Estilos de frente predefinidos con sus luces. Al cargar un módulo, el asistente copia las luces del estilo elegido.

| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_estilo_frente | INT | PK |
| nombre_efr | VARCHAR(50) | NN, UQ (ej.: "Bajo mesada con gola") |
| luz_superior_efr | DECIMAL(5,2) | NN (negativa = sobresale) |
| luz_inferior_efr | DECIMAL(5,2) | NN (negativa = sobresale) |
| luz_entre_frentes_efr | DECIMAL(5,2) | NN, ≥ 0 |
| descripcion_efr | VARCHAR(200) | (ej.: indicaciones de fabricación, como los rebajes de la gola) |
| es_activo_efr | BOOLEAN | NN, default verdadero (baja lógica) |

> Valores en la sección 9 (datos iniciales).

### `Tipo_Guia`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_tipo_guia | INT | PK |
| nombre_tgu | VARCHAR(50) | NN, UQ (ej.: "Telescópica cierre suave", "Lateral oculto marca X") |
| marca_tgu | VARCHAR(50) | (fabricante, opcional) |
| espacio_adicional_tgu | DECIMAL(5,2) | NN, ≥ 0, default 0 (profundidad extra que necesita la guía: 0,2 cm en telescópica; en lateral oculto depende de la marca: 0,8 o 1,1 cm) |
| es_activo_tgu | BOOLEAN | NN, default verdadero (baja lógica) |

> Cada marca o modelo de guía con medidas distintas es un registro propio, con sus constantes en `Pieza_Guia` y sus largos en `Largo_Guia`.

### `Largo_Guia`
Largos comerciales disponibles de cada tipo de guía. Se cargan como lista porque no siempre van de 5 en 5 (ej.: 27, 47 cm).

| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_largo_guia | INT | PK |
| id_tipo_guia | INT | FK → Tipo_Guia, NN |
| largo_lgu | DECIMAL(6,1) | NN, > 0 (cm) |

> UQ (id_tipo_guia, largo_lgu).
> **Regla de selección (capa de negocio):** se propone el mayor `largo_lgu` tal que `largo_lgu + espacio_adicional_tgu ≤ profundidad_mod + tolerancia`, donde la tolerancia es el parámetro `tolerancia_sobresale_guia` (0,5 cm). El valor elegido se guarda en `Cajon.largo_guia_caj` y se puede cambiar.

### `Pieza_Guia`
Define qué piezas lleva un cajón según su tipo de guía y qué constante se descuenta en cada medida. Agregar una guía nueva es cargar datos, no modificar código.

Medidas de referencia:
- **Ancho:** ancho interior del módulo (ancho_mod − 2 × espesor de placa).
- **Largo:** largo de la guía (`largo_guia_caj`).
- **Alto:** alto del cajón (`alto_caj`).

Cada pieza usa dos de las tres referencias: la que no usa queda en nulo.

| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_pieza_guia | INT | PK |
| id_tipo_guia | INT | FK → Tipo_Guia, NN |
| id_tipo_pieza | INT | FK → Tipo_Pieza, NN |
| cantidad_pgu | INT | NN, > 0 |
| descuento_ancho_pgu | DECIMAL(5,2) | ≥ 0 (nulo = la pieza no usa el ancho) |
| descuento_largo_pgu | DECIMAL(5,2) | ≥ 0 (nulo = la pieza no usa el largo) |
| descuento_alto_pgu | DECIMAL(5,2) | ≥ 0 (nulo = la pieza no usa el alto o usa un alto fijo) |
| alto_fijo_pgu | DECIMAL(6,1) | > 0 (alto fijo definido por la marca de la guía, ej.: contrafrente de guía oculta) |

> UQ (id_tipo_guia, id_tipo_pieza).
> CHECK: `descuento_alto_pgu` y `alto_fijo_pgu` no pueden estar completos a la vez. La pieza usa exactamente dos medidas entre ancho, largo y alto (por descuento o fijo).
> El frente visible no figura acá: no depende de la guía, se calcula con las luces del módulo (como las puertas).

**Ejemplo — Telescópica cierre suave** (guía 1,35 cm por lado, laterales de 1,8 cm):

| Pieza | Cant. | Desc. ancho | Desc. largo | Desc. alto |
|-------|-------|-------------|-------------|------------|
| Lateral de cajón | 2 | — | 0 | 0 |
| Contrafrente de cajón | 1 | 6,3 | — | 0 |
| Frente interno de cajón | 1 | 6,3 | — | 3 |
| Piso de cajón (5,5 mm) | 1 | 2,7 | 0 | — |

> 6,3 = 2 × 1,35 (guías) + 2 × 1,8 (laterales). 2,7 = 2 × 1,35 (guías).
> El piso se calcula sin rebaje (clavado por debajo de la caja). Si las piezas llevan rebaje, la medida se ajusta manualmente.

**Ejemplo — Lateral oculto (Rincón del Herraje, Eurohard y Häfele):**

| Pieza | Cant. | Desc. ancho | Desc. largo | Desc. alto | Alto fijo |
|-------|-------|-------------|-------------|------------|-----------|
| Contrafrente de cajón | 1 | 8,7 | — | — | según marca |
| Piso de cajón (18 o 15 mm) | 1 | 7,5 | 0,9 | — | — |

> Al no tener fila para Lateral de cajón ni Frente interno, el sistema no los genera.

**Material de cada pieza del cajón:** el piso usa `Cajon.id_placa_piso`; laterales, contrafrente y frente interno usan la placa de cajones del módulo; el frente visible usa la placa de frentes. Las constantes de la telescópica suponen una caja de 18 mm.

### `Cajon`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_cajon | INT | PK |
| id_modulo | INT | FK → Modulo, NN |
| id_tipo_guia | INT | FK → Tipo_Guia, NN |
| id_placa_piso | INT | FK → Placa, NN (telescópica: siempre placa de 5,5 mm; lateral oculto: 18 o 15 mm según el caso) |
| orden_caj | INT | NN (posición de arriba hacia abajo) |
| alto_caj | DECIMAL(6,1) | NN, > 0 (alto estimado de la caja, ej.: 12) |
| alto_frente_caj | DECIMAL(6,1) | > 0 (nulo = reparto en partes iguales del alto disponible) |
| largo_guia_caj | DECIMAL(6,1) | NN, > 0 (propuesto según `Largo_Guia`, editable; ej.: 45) |

> UQ (id_modulo, orden_caj).
> Todas las piezas se piden en un solo pedido. Los frentes se calculan exactos; las piezas de la caja usan el alto estimado y se pueden ajustar.
> **Validado en la capa de negocio:** si el módulo tiene puertas, todos sus cajones deben tener `alto_frente_caj`. Si no tiene puertas, los cajones con `alto_frente_caj` nulo se reparten en partes iguales el alto que dejan libre los que sí lo tienen.

---

## 4. Materiales

### `Marca_Placa`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_marca_placa | INT | PK |
| nombre_mpl | VARCHAR(50) | NN, UQ |
| es_activo_mpl | BOOLEAN | NN, default verdadero (baja lógica) |

### `Color_Placa`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_color_placa | INT | PK |
| id_marca_placa | INT | FK → Marca_Placa, NN |
| nombre_cpl | VARCHAR(60) | |
| codigo_cpl | VARCHAR(30) | |
| tiene_veta_cpl | BOOLEAN | NN, default falso |
| es_activo_cpl | BOOLEAN | NN, default verdadero (baja lógica) |

> CHECK (nombre_cpl IS NOT NULL OR codigo_cpl IS NOT NULL) · Código único por marca con un **índice único filtrado** (`WHERE codigo_cpl IS NOT NULL`): un UNIQUE común trata los NULL como iguales y no permitiría dos colores sin código en la misma marca.
> "Crudo" es un color de placa más.

### `Marca_Pintura`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_marca_pintura | INT | PK |
| nombre_mpi | VARCHAR(50) | NN, UQ (Alba, Sherwin Williams) |
| es_activo_mpi | BOOLEAN | NN, default verdadero (baja lógica) |

### `Color_Laca`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_color_laca | INT | PK |
| id_marca_pintura | INT | FK → Marca_Pintura, NN |
| nombre_cla | VARCHAR(60) | |
| codigo_cla | VARCHAR(30) | |
| es_activo_cla | BOOLEAN | NN, default verdadero (baja lógica) |

> CHECK (nombre_cla IS NOT NULL OR codigo_cla IS NOT NULL) · Código único por marca con índice único filtrado (igual que `Color_Placa`).
> Entidad separada de `Color_Placa`: la laca es pintura y no tiene relación con los colores de placa.

### `Terminacion_Laca`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_terminacion_laca | INT | PK |
| nombre_tla | VARCHAR(30) | NN, UQ (Mate, Semimate, Brillante…) |
| es_activo_tla | BOOLEAN | NN, default verdadero (baja lógica) |

> La terminación no es parte del color: un mismo color puede laquearse mate o brillante. Se elige por pieza (o por defecto para los frentes del módulo).

### `Material` (generalización)
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_material | INT | PK |
| tipo_mat | VARCHAR(10) | NN, CHECK IN ('PLACA', 'LISTON') |

### `Placa` (especialización de Material)
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_placa | INT | PK, FK → Material (id_material) |
| tipo_mat | VARCHAR(10) | NN, default 'PLACA', CHECK = 'PLACA' (parte de la FK compuesta) |
| id_color_placa | INT | FK → Color_Placa, NN |
| espesor_pla | DECIMAL(4,2) | NN, > 0 (cm: 1,8 · 1,5 · 0,9 · 0,55) |
| largo_pla | DECIMAL(6,1) | NN, > 0 (medida de la placa entera, en el sentido de la veta) |
| ancho_pla | DECIMAL(6,1) | NN, > 0 (medida de la placa entera) |
| es_activo_pla | BOOLEAN | NN, default verdadero (baja lógica) |

> UQ (id_color_placa, espesor_pla, largo_pla, ancho_pla): un mismo color y espesor puede venir en más de un tamaño de placa.
> `id_placa` es a la vez PK de Placa y FK a `Material`: toma el mismo valor que el `id_material` correspondiente.
> **Integridad de la generalización:** la FK es compuesta, (`id_placa`, `tipo_mat`) → `Material` (`id_material`, `tipo_mat`), con `tipo_mat` fijo en 'PLACA'. Así la base impide que una placa cuelgue de un material de tipo listón. `Material` tiene UQ (`id_material`, `tipo_mat`) como destino de esa FK. Lo mismo en `Liston` con 'LISTON'.
> El alta se hace con el procedimiento `sp_alta_placa` (inserta Material y Placa en una transacción).

### `Liston` (especialización de Material)
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_liston | INT | PK, FK → Material (id_material) |
| tipo_mat | VARCHAR(10) | NN, default 'LISTON', CHECK = 'LISTON' (parte de la FK compuesta) |
| nombre_lis | VARCHAR(50) | NN (ej.: "Pino") |
| seccion_ancho_pulg_lis | DECIMAL(4,2) | NN, > 0 (ej.: 2) |
| seccion_alto_pulg_lis | DECIMAL(4,2) | NN, > 0 (ej.: 1) |
| es_activo_lis | BOOLEAN | NN, default verdadero (baja lógica) |

### `Tipo_Filo`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_tipo_filo | INT | PK |
| nombre_tfi | VARCHAR(30) | NN, UQ (Sin filo, 0,45 mm, 2 mm) |
| espesor_mm_tfi | DECIMAL(4,2) | NN, ≥ 0 |
| descuento_por_canto_tfi | DECIMAL(5,2) | NN, ≥ 0 (cm: 0,2 en filo de 2 mm; 0 en 0,45 mm y sin filo) |

---

## 5. Despiece

### `Tipo_Pieza`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_tipo_pieza | INT | PK |
| nombre_tpi | VARCHAR(50) | NN, UQ |
| es_frente_tpi | BOOLEAN | NN (puertas y frentes de cajón: usan la placa y la laca de frentes del módulo) |
| veta_vertical_tpi | BOOLEAN | NN (sentido de la veta por defecto: verdadero = en el alto; falso = en el largo) |

> Valores en la sección 9 (datos iniciales).

### `Pieza`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_pieza | INT | PK |
| id_mueble | INT | FK → Mueble (pieza suelta) |
| id_modulo | INT | FK → Modulo (pieza de la estructura o de los frentes del módulo) |
| id_cajon | INT | FK → Cajon (pieza de la caja o frente de un cajón) |
| id_zocalo | INT | FK → Zocalo (pieza del zócalo) |
| id_tipo_pieza | INT | FK → Tipo_Pieza, NN |
| id_material | INT | FK → Material, NN |
| id_tipo_filo | INT | FK → Tipo_Filo (nulo = filo sin definir; "Sin filo" = decidido que no lleva) |
| id_color_placa_filo | INT | FK → Color_Placa (nulo = mismo color que la pieza) |
| id_color_laca | INT | FK → Color_Laca (nulo = no se laquea) |
| id_terminacion_laca | INT | FK → Terminacion_Laca (obligatoria si la pieza se laquea) |
| descripcion_pie | VARCHAR(100) | (para piezas sueltas) |
| cantidad_pie | INT | NN, > 0 |
| medida_1_pie | DECIMAL(6,1) | NN, > 0 (medida final terminada, con filo incluido; sentido de la veta) |
| medida_2_pie | DECIMAL(6,1) | > 0 (medida final terminada; nulo solo para listones) |
| lleva_filo_superior_pie | BOOLEAN | NN, default falso |
| lleva_filo_inferior_pie | BOOLEAN | NN, default falso |
| lleva_filo_izquierdo_pie | BOOLEAN | NN, default falso |
| lleva_filo_derecho_pie | BOOLEAN | NN, default falso |
| es_editada_manualmente_pie | BOOLEAN | NN, default falso |

> CHECK: exactamente uno de `id_mueble`, `id_modulo`, `id_cajon` o `id_zocalo` es no nulo. Una pieza de cajón no guarda el módulo: se obtiene a través del cajón (evita una dependencia transitiva).
> **Recálculo:** al recalcular un módulo o un cajón se regeneran solo sus piezas con `es_editada_manualmente_pie` falso; las editadas se conservan y el sistema avisa para revisarlas.
> **Valores por defecto al generar:** el material sale del módulo según la pieza (estructura, frentes o cajones) y el sentido de la veta de `veta_vertical_tpi`. **Los filos no tienen valor por defecto:** toda pieza nace con `id_tipo_filo` nulo (sin definir), salvo las laqueadas, que nacen con "Sin filo". Todo es editable.
> **Dividir una fila:** se resta la cantidad a separar de la fila original y se crea una pieza nueva igual con esa cantidad, que puede editarse por separado. Ambas quedan marcadas como editadas manualmente (no las pisa un recálculo).
> **Control de filos:** no se puede generar el listado para la maderera mientras alguna pieza del trabajo tenga `id_tipo_filo` nulo. Evita tanto filos de más (costo) como filos olvidados.
> **Medida final y medida de corte:** las medidas guardadas son las finales (la pieza terminada, con filo). La medida de corte que se manda a la maderera no se guarda: se calcula al generar el listado, restando el descuento del tipo de filo por cada canto con filo:
> - corte medida 1 = `medida_1_pie` − descuento × (cantos izquierdo + derecho con filo)
> - corte medida 2 = `medida_2_pie` − descuento × (cantos superior + inferior con filo)
> Ej.: puerta final 59,2 × 44,5 con 2 mm en los 4 cantos → corte 58,8 × 44,1. Lateral visto final 73,2 × 55 con 2 mm en un canto corto → corte 73,0 × 55.
> **Convención de cantos:** la pieza se dibuja con `medida_1_pie` en horizontal. Superior e inferior son los cantos paralelos a la veta; izquierdo y derecho, los de `medida_2_pie`. Es la misma referencia que se usa para dibujar la L, la U o el cuadrado en el listado.
> **Validado en la capa de negocio:** una pieza laqueada no lleva filo y debe tener terminación; si el tipo de filo es "Sin filo", ningún canto lo lleva; al rotar la veta se intercambian las medidas y también los filos (superior/inferior ↔ izquierdo/derecho); `medida_2_pie` es obligatoria si el material es una placa.

---

## 6. Inventario

### `Retazo`
| Atributo | Tipo | Restricciones |
|----------|------|---------------|
| id_retazo | INT | PK |
| id_placa | INT | FK → Placa, NN (define marca, color y espesor) |
| id_trabajo_origen | INT | FK → Trabajo (de qué trabajo sobró, opcional) |
| id_retazo_origen | INT | FK → Retazo (si surge de cortar otro retazo) |
| medida_1_ret | DECIMAL(6,1) | NN, > 0 (sentido de la veta) |
| medida_2_ret | DECIMAL(6,1) | NN, > 0 |
| ubicacion_ret | VARCHAR(100) | (lugar en el taller) |
| fecha_alta_ret | DATE | NN |
| fecha_baja_ret | DATE | ≥ fecha_alta_ret (nulo = disponible) |

---

## 7. Resumen de relaciones

| Relación | Cardinalidad |
|----------|--------------|
| Cliente → Obra | 1 : N |
| Obra → Trabajo | 1 : N |
| Estado_Trabajo → Trabajo | 1 : N |
| Trabajo → Mueble | 1 : N |
| Mueble → Modulo | 1 : N |
| Tipo_Armado → Modulo | 1 : N |
| Estilo_Frente → Modulo | 1 : N (opcional) |
| Mueble → Pieza (sueltas) | 1 : N (opcional) |
| Modulo → Pieza | 1 : N (opcional) |
| Modulo → Cajon | 1 : N |
| Tipo_Guia → Cajon | 1 : N |
| Tipo_Guia → Pieza_Guia | 1 : N |
| Tipo_Guia → Largo_Guia | 1 : N |
| Tipo_Pieza → Pieza_Guia | 1 : N |
| Placa → Cajon (piso) | 1 : N |
| Placa → Modulo (estructura) | 1 : N |
| Placa → Modulo (frentes) | 1 : N (opcional) |
| Placa → Modulo (cajones) | 1 : N (opcional) |
| Placa → Modulo (fondo) | 1 : N (opcional) |
| Liston → Modulo (pinos) | 1 : N (opcional) |
| Color_Laca → Modulo (frentes) | 1 : N (opcional) |
| Cajon → Pieza | 1 : N (opcional) |
| Mueble → Zocalo | 1 : N (opcional) |
| Zocalo → Pieza | 1 : N (opcional) |
| Placa → Zocalo (visible) | 1 : N |
| Placa → Zocalo (oculta) | 1 : N (opcional) |
| Marca_Placa → Color_Placa | 1 : N |
| Color_Placa → Placa | 1 : N |
| Material → Placa / Liston | 1 : 1 (generalización) |
| Material → Pieza | 1 : N |
| Tipo_Pieza → Pieza | 1 : N |
| Tipo_Filo → Pieza | 1 : N (opcional hasta definir el filo) |
| Color_Placa → Pieza (filo) | 1 : N (opcional) |
| Marca_Pintura → Color_Laca | 1 : N |
| Color_Laca → Pieza | 1 : N (opcional) |
| Terminacion_Laca → Pieza | 1 : N (opcional) |
| Terminacion_Laca → Modulo (frentes) | 1 : N (opcional) |
| Placa → Retazo | 1 : N |
| Trabajo → Retazo | 1 : N (opcional) |
| Retazo → Retazo | 1 : N (opcional, autorrelación) |
| Tipo_Evento → Auditoria | 1 : N |
| Usuario → Auditoria | 1 : N (opcional) |

---

## 8. Integridad, borrado e índices

### 8.1 Baja lógica
- Las tablas de catálogo (`Marca_Placa`, `Color_Placa`, `Placa`, `Liston`, `Marca_Pintura`, `Color_Laca`, `Terminacion_Laca`, `Tipo_Guia`, `Estilo_Frente`) y `Cliente` / `Usuario` tienen `es_activo`. Un registro inactivo no se ofrece para cargas nuevas, pero los trabajos anteriores lo siguen mostrando.

### 8.2 Reglas de borrado (ON DELETE)
| Relación | Regla | Motivo |
|----------|-------|--------|
| Trabajo → Mueble → Modulo → Cajon | CASCADE | La estructura no existe sin su trabajo |
| Mueble → Zocalo | CASCADE | Ídem |
| Mueble / Modulo / Cajon / Zocalo → Pieza | NO ACTION | Ver nota |
| Tipo_Guia → Pieza_Guia / Largo_Guia | CASCADE | Son datos propios de la guía |
| Trabajo → Retazo (origen) | SET NULL | El retazo sigue existiendo aunque se borre el trabajo |
| Retazo → Retazo (origen) | NO ACTION | Ver nota |
| Catálogo (placas, colores, lacas, guías, estilos, tipos) → cualquier tabla | NO ACTION | No se puede borrar algo en uso; se da de baja lógica |
| Cliente → Obra → Trabajo | NO ACTION | Los clientes y obras con trabajos no se borran; se dan de baja lógica |
| Usuario / Tipo_Evento → Auditoria | NO ACTION | La auditoría no se pierde: los usuarios se dan de baja lógica y los tipos de evento son fijos |

> **Limitación de SQL Server (error 1785):** no admite dos caminos de borrado en cascada hacia una misma tabla. `Pieza` depende de `Mueble`, `Modulo`, `Cajon` y `Zocalo`, que a su vez dependen de `Mueble`, así que sus FK son NO ACTION. Para borrar un trabajo completo se usa el procedimiento `sp_eliminar_trabajo`, que en una transacción borra primero sus piezas y después el trabajo (el resto cae en cascada). Al recalcular un módulo o un cajón, la capa de negocio borra antes sus piezas no editadas.
> Tampoco admite acciones en cascada en una autorrelación: `Retazo → Retazo` es NO ACTION. Los retazos no se borran, se dan de baja con `fecha_baja_ret`.

### 8.3 Índices
Además de las PK, FK y UQ:
- `Cliente`: nombre_cli, apellido_cli, telefono_cli.
- `Obra`: direccion_obr, localidad_obr, nombre_obr.
- `Trabajo`: id_estado_trabajo, fecha_alta_tra, fecha_presupuesto_tra.
- `Color_Placa` / `Color_Laca`: nombre y código.
- `Retazo`: (id_placa, fecha_baja_ret), para buscar retazos disponibles.
- `Auditoria`: fecha_hora_aud descendente (lo último que pasó), (id_tipo_evento, fecha) y id_usuario.

### 8.4 Validaciones que no puede hacer la base
Se resuelven en la capa de negocio:
- Reglas de `Pieza`, `Modulo` y `Cajon` que dependen de otra tabla (ej.: ancho de faja solo en cajoneras; pieza laqueada sin filo; `medida_2_pie` obligatoria si el material es placa).

Reglas que sí controla la base con restricciones (además de PK, FK y UQ):
- Generalización `Material` → `Placa` / `Liston` (FK compuesta con `tipo_mat`).
- Exactamente un dueño por pieza; laca y terminación juntas (en `Pieza` y en `Modulo`).
- Dos medidas por fila de `Pieza_Guia`; alto de la caja ≤ alto del frente del cajón.
- Montos y fechas coherentes en `Trabajo`; medidas positivas en todas las tablas.

### 8.5 Permisos (mínimo privilegio)
La aplicación se conecta con el login `app_carpinteria`, miembro del rol `rol_app` (script `05_seguridad.sql`):

| Permiso | Sobre | Motivo |
|---------|-------|--------|
| SELECT, INSERT, UPDATE, DELETE, EXECUTE | esquema `dbo` | Uso normal del sistema |
| Miembro de `db_backupoperator` | base | Copias de seguridad automáticas |
| DENY UPDATE, DELETE | `Auditoria` | La auditoría solo crece |
| DENY INSERT, UPDATE, DELETE | `Tipo_Evento` | Catálogo fijo |
| (sin permisos) | estructura (CREATE, ALTER, DROP) | La aplicación no puede modificar ni borrar tablas |

La restauración de una copia y los cambios de estructura se hacen con la cuenta de administrador.

---

## 9. Datos iniciales

Registros que se insertan al crear la base de datos.

### `Usuario`
Usuario `admin` con contraseña provisoria `Cambiar.123` (guardada como hash **bcrypt**, costo 12) y `debe_cambiar_contrasena_usu` = 1: el sistema obliga a cambiarla en el primer ingreso.

### `Tipo_Evento`
| codigo_tev | Crítico |
|------------|---------|
| LOGIN_OK, LOGIN_FALLIDO, LOGOUT, CIERRE_INACTIVIDAD, CAMBIO_CONTRASENA, CAMBIO_ESTADO_TRABAJO, BACKUP_OK | no |
| USUARIO_BLOQUEADO, BLANQUEO_CONTRASENA, ALTA_USUARIO, BAJA_USUARIO, REACTIVACION_USUARIO, ELIMINACION_TRABAJO, CAMBIO_MONTO, CAMBIO_PARAMETRO, BACKUP_ERROR | sí |

### `Terminacion_Laca`
Mate, Semimate, Brillante.

### `Tipo_Guia`
| nombre_tgu | marca_tgu | espacio_adicional_tgu |
|------------|-----------|-----------------------|
| Telescópica cierre suave | — | 0,2 |
| Lateral oculto Rincón del Herraje | Rincón del Herraje | 1,1 |
| Lateral oculto Eurohard | Eurohard | 0,8 |
| Lateral oculto Häfele | Häfele | 0,8 |

### `Estado_Trabajo`
| orden_etr | nombre_etr | Fecha que se sugiere completar |
|-----------|------------|--------------------------------|
| 1 | Presupuestado | — |
| 2 | Confirmado | Cobro de la seña |
| 3 | En producción | Comienzo |
| 4 | Terminado | Finalización |
| 5 | Instalado | Entrega |
| 6 | Cobrado | Cobro del saldo |
| 7 | Cancelado | — |

### `Tipo_Pieza`
| nombre_tpi | es_frente_tpi | veta_vertical_tpi |
|------------|---------------|-------------------|
| Piso | no | no |
| Techo | no | no |
| Lateral | no | sí |
| Estante | no | no |
| Faja | no | no |
| Fondo | no | sí |
| Puerta | sí | sí |
| Frente de cajón | sí | no |
| Pino | no | no |
| Lateral de cajón | no | no |
| Contrafrente de cajón | no | no |
| Frente interno de cajón | no | no |
| Piso de cajón | no | no |
| Frente de zócalo | no | no |
| Trasera de zócalo | no | no |
| Lateral de zócalo | no | no |
| Refuerzo de zócalo | no | no |
| Ajuste | no | sí |
| Otra | no | no |

> En el fondo y en las piezas de la caja del cajón la veta no suele importar (habitualmente son lisas); el valor es solo un punto de partida.

### `Tipo_Filo`
| nombre_tfi | espesor_mm_tfi | descuento_por_canto_tfi |
|------------|----------------|-------------------------|
| Sin filo | 0 | 0 |
| 0,45 mm | 0,45 | 0 |
| 2 mm | 2 | 0,2 |

### `Estilo_Frente`
| nombre_efr | luz_superior_efr | luz_inferior_efr | luz_entre_frentes_efr | descripcion_efr |
|------------|------------------|------------------|-----------------------|-----------------|
| Con tirador | 0,4 | 0,4 | 0,3 | |
| Cajonera con tirador | 0,6 | 0,6 | 0,3 | |
| Alacena (sobresale abajo) | 0 | −1,3 | 0,3 | Puertas parejas arriba, sobresalen 1,3 cm abajo para abrirlas |
| Bajo mesada con gola | 3 | 0 | 3 | Rebajes en los laterales hechos en el taller: 5 × 3,6 cm arriba y 7 × 3,6 cm entre frentes de cajón |

### `Parametro` (luces fijas, tolerancias y seguridad)
| clave_par | valor_par | unidad_par |
|-----------|-----------|------------|
| luz_lateral_frente | 0,3 | cm |
| luz_entre_puertas | 0,3 | cm |
| tolerancia_sobresale_guia | 0,5 | cm |
| retiro_zocalo | 1,5 | cm |
| descuento_fondo | 0,3 | cm |
| porcentaje_sena | 60 | % |
| max_intentos_login | 5 | intentos |
| minutos_bloqueo | 15 | min |
| minutos_inactividad | 15 | min |
| largo_minimo_contrasena | 10 | caracteres |

> Las constantes de piezas de lateral oculto son las mismas para las tres marcas y se cargan en `Pieza_Guia` para cada una: contrafrente (trasera) = ancho interior − 8,7 × alto según la marca; piso = (ancho interior − 7,5) × (largo guía − 0,9). Solo el alto de la trasera varía por marca.

---

## 10. Pendientes
- [ ] Cajones de lateral oculto: alto fijo del contrafrente de cada marca (dato).
- [ ] Largos disponibles de cada guía, telescópica y ocultas (datos para `Largo_Guia`).
- [x] Motor de base de datos: SQL Server Express.
- [ ] (V2) Tablas de presupuesto: precios por m² y por metro lineal, herrajes, mano de obra y flete.
