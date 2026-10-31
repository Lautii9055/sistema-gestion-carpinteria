"""Muebles, módulos, zócalos y piezas de un trabajo (RF-12 a RF-19).

Une el motor de despiece (cálculo puro) con lo guardado:
- Al guardar un módulo se calculan sus piezas con los materiales elegidos y se
  guardan con su medida final y su sentido de veta. Los filos nacen sin definir
  (RN-08), salvo los frentes laqueados, que nacen "Sin filo" (RF-15.2).
- Recalcular regenera las piezas que nadie tocó, conservando los filos que ya se
  les habían definido (si cambió la medida, el patrón de filos sigue valiendo).
  Las piezas editadas a mano no se pisan: el sistema avisa para revisarlas.
- Un trabajo instalado, cobrado o cancelado, o de un cliente dado de baja, ya
  no cambia sus muebles.
"""
from dataclasses import replace
from decimal import Decimal

from carpinteria.negocio import despiece as motor
from carpinteria.negocio.autenticacion import ErrorAutenticacion
from carpinteria.negocio.catalogo import SIN_FILO
from carpinteria.negocio.entidades import (Cantos, ModuloGuardado, Mueble, PiezaGuardada, Placa, TipoGuia,
                                          ZocaloGuardado)
from carpinteria.negocio.estados import CANCELADO, COBRADO, INSTALADO
from carpinteria.negocio.filos import PISO_DE_CAJON, TIPOS_SIN_FILO, cantos_de_patron
from carpinteria.negocio.listado import SeccionCorte, SeccionLaca, armar_laqueador, armar_listado
from carpinteria.negocio.puertos import (RepositorioCatalogo, RepositorioMateriales, RepositorioMuebles,
                                         RepositorioParametros, RepositorioTrabajos)

ESTADOS_SIN_CAMBIOS = (INSTALADO, COBRADO, CANCELADO)


def nunca_lleva_filo(p: PiezaGuardada) -> bool:
    """Fondos, pisos de cajón (con cualquier guía) y listones: no llevan filo nunca."""
    return p.tipo in TIPOS_SIN_FILO or p.medida_2 is None or p.sin_filo_fijo


def guia_oculta(guia: TipoGuia) -> bool:
    """Lateral oculto (cualquier marca): la guía no lleva laterales de cajón."""
    return not any(x.pieza == "Lateral de cajón" for x in guia.piezas)
TIPOS_SUELTOS = ("Ajuste", "Otra")
PISO_TELESCOPICA_MM = Decimal("5.5")


MAXIMO_MODULOS_IGUALES = 50

class ErrorMuebles(ErrorAutenticacion):
    """Error de validación de muebles y piezas; se muestra tal cual."""


def _texto(valor: str | None, campo: str, maximo: int, obligatorio: bool = True) -> str | None:
    limpio = " ".join((valor or "").split()) or None
    if obligatorio and not limpio:
        raise ErrorMuebles(f"Completá {campo}.")
    if limpio and len(limpio) > maximo:
        raise ErrorMuebles(f"{campo[0].upper()}{campo[1:]} puede tener hasta {maximo} caracteres.")
    return limpio


class ServicioMuebles:
    def __init__(self, muebles: RepositorioMuebles, trabajos: RepositorioTrabajos,
                 materiales: RepositorioMateriales, catalogo: RepositorioCatalogo,
                 parametros: RepositorioParametros) -> None:
        self._repo = muebles
        self._trabajos = trabajos
        self._materiales = materiales
        self._catalogo = catalogo
        self._parametros = parametros

    # ---------- reglas y controles ----------
    def reglas(self) -> motor.Reglas:
        def valor(clave: str, defecto: Decimal) -> Decimal:
            v = self._parametros.obtener(clave)
            return Decimal(v) if v is not None else defecto
        base = motor.Reglas()
        return motor.Reglas(valor("luz_lateral_frente", base.luz_lateral),
                            valor("luz_entre_puertas", base.luz_entre_puertas),
                            valor("tolerancia_sobresale_guia", base.tolerancia_guia),
                            valor("retiro_zocalo", base.retiro_zocalo),
                            valor("descuento_fondo", base.descuento_fondo))

    def _controlar_trabajo(self, id_trabajo: int) -> None:
        detalle = self._trabajos.obtener(id_trabajo)
        if detalle is None:
            raise ErrorMuebles("El trabajo ya no existe.")
        if not detalle.cliente.es_activo:
            raise ErrorMuebles("El cliente está dado de baja: el trabajo queda como historial.")
        if detalle.estado.nombre in ESTADOS_SIN_CAMBIOS:
            raise ErrorMuebles(f"El trabajo está «{detalle.estado.nombre.lower()}»: sus muebles ya no se modifican.")

    def _mueble_editable(self, id_mueble: int) -> Mueble:
        mueble = self._repo.mueble(id_mueble)
        if mueble is None:
            raise ErrorMuebles("El mueble ya no existe.")
        self._controlar_trabajo(mueble.id_trabajo)
        return mueble

    def _pieza_editable(self, id_pieza: int) -> PiezaGuardada:
        pieza = self._repo.pieza(id_pieza)
        pieza = self._marcar([pieza])[0] if pieza else None
        id_trabajo = self._repo.trabajo_de_pieza(id_pieza)
        if pieza is None or id_trabajo is None:
            raise ErrorMuebles("La pieza ya no existe.")
        self._controlar_trabajo(id_trabajo)
        return pieza

    def _placas(self) -> dict[int, Placa]:
        return {p.id: p for p in self._materiales.placas()}

    def _sin_filo(self) -> int:
        filo = next((f for f in self._catalogo.filos() if f.nombre == SIN_FILO), None)
        if filo is None:
            raise ErrorMuebles("Falta el tipo de filo «Sin filo» en el catálogo.")
        return filo.id

    # ---------- muebles ----------
    def muebles(self, id_trabajo: int) -> list[Mueble]:
        return self._repo.muebles(id_trabajo)

    def mueble(self, id_mueble: int) -> Mueble | None:
        return self._repo.mueble(id_mueble)

    def guardar_mueble(self, id_mueble: int | None, id_trabajo: int, nombre: str,
                       observaciones: str | None = None) -> int:
        self._controlar_trabajo(id_trabajo)
        nombre = _texto(nombre, "el nombre del mueble", 100)
        observaciones = _texto(observaciones, "las observaciones", 500, obligatorio=False)
        return self._repo.guardar_mueble(Mueble(id_mueble, id_trabajo, nombre, observaciones))

    def eliminar_mueble(self, id_mueble: int) -> None:
        self._mueble_editable(id_mueble)
        self._repo.eliminar_mueble(id_mueble)

    # ---------- módulos ----------
    def modulos(self, id_mueble: int) -> list[ModuloGuardado]:
        return self._repo.modulos(id_mueble)

    def proponer_largo_guia(self, id_guia: int, profundidad: Decimal,
                            espesor_frentes: Decimal = Decimal("1.8")) -> Decimal | None:
        """La guía va dentro de la caja: profundidad total menos el espesor de los frentes."""
        return motor.proponer_largo_guia(self._guia(id_guia), profundidad - espesor_frentes, self.reglas())

    def largos_que_entran(self, id_guia: int, profundidad: Decimal,
                          espesor_frentes: Decimal = Decimal("1.8")) -> list[Decimal]:
        """Los largos cargados de la guía que entran en la caja (de mayor a menor)."""
        return motor.largos_que_entran(self._guia(id_guia), profundidad - espesor_frentes, self.reglas())

    def espesor_frentes(self, id_placa_frentes: int | None, id_placa: int | None) -> Decimal:
        placas = self._placas()
        placa = placas.get(id_placa_frentes) or placas.get(id_placa)
        return placa.espesor if placa else Decimal("1.8")

    def _guia(self, id_guia: int) -> TipoGuia:
        guia = next((g for g in self._catalogo.guias() if g.id == id_guia), None)
        if guia is None:
            raise ErrorMuebles("La guía elegida ya no existe.")
        return guia

    def _material_por_rol(self, m: ModuloGuardado) -> dict[motor.Material, int | None]:
        return {
            motor.Material.ESTRUCTURA: m.id_placa,
            motor.Material.FRENTES: m.id_placa_frentes or m.id_placa,
            motor.Material.CAJONES: m.id_placa_cajones or m.id_placa,
            motor.Material.FONDO: m.id_placa_fondo,
            motor.Material.LISTON: m.id_liston,
        }

    def a_motor(self, m: ModuloGuardado) -> motor.Modulo:
        """Traduce lo guardado a los datos del motor (espesor, guías, colores lisos)."""
        try:
            armado = motor.Armado(m.armado)
        except ValueError:
            raise ErrorMuebles(f"Tipo de armado desconocido: {m.armado}.") from None
        placas = self._placas()
        estructura = placas.get(m.id_placa)
        if estructura is None:
            raise ErrorMuebles("Elegí la placa de la estructura.")
        for id_placa in (m.id_placa_frentes, m.id_placa_cajones, m.id_placa_fondo,
                         *(c.id_placa_piso for c in m.cajones)):
            if id_placa is not None and id_placa not in placas:
                raise ErrorMuebles("Una de las placas elegidas ya no existe.")
        if (m.id_color_laca is None) != (m.id_terminacion is None):
            raise ErrorMuebles("Para laquear los frentes elegí el color de laca y la terminación.")
        for i, c in enumerate(m.cajones, 1):
            # Con telescópica el piso es un fondo de 5,5 mm clavado abajo (con oculta, 18 o 15 mm).
            if not guia_oculta(self._guia(c.id_guia)) and placas[c.id_placa_piso].espesor_mm != PISO_TELESCOPICA_MM:
                raise ErrorMuebles(f"Cajón {i}: con guía telescópica, el piso del cajón va en placa de 5,5 mm. "
                                   "Elegila en el paso Cajones (si no hay, cargala en Materiales).")
        roles = self._material_por_rol(m)
        sin_veta = {rol for rol, id_placa in roles.items()
                    if id_placa in placas and placas[id_placa].color and not placas[id_placa].color.tiene_veta}
        if all(c.id_placa_piso in placas and placas[c.id_placa_piso].color
               and not placas[c.id_placa_piso].color.tiene_veta for c in m.cajones) and m.cajones:
            sin_veta.add(motor.Material.PISO_CAJON)
        frentes = placas.get(m.id_placa_frentes) or estructura
        return motor.Modulo(
            armado, m.ancho, m.alto, m.profundidad, espesor=estructura.espesor, lleva_techo=m.lleva_techo,
            ancho_faja=m.ancho_faja, estantes=m.estantes, puertas=m.puertas,
            lleva_fondo=m.id_placa_fondo is not None, lleva_pinos=m.id_liston is not None,
            luz_superior=m.luz_superior, luz_inferior=m.luz_inferior, luz_entre_frentes=m.luz_entre_frentes,
            cajones=tuple(motor.Cajon(self._guia(c.id_guia), c.largo_guia, c.alto_caja, c.alto_frente)
                          for c in m.cajones),
            rotar=frozenset(m.rotar), espesor_frentes=frentes.espesor,
            luz_izquierda=m.luz_izquierda, luz_derecha=m.luz_derecha, sin_veta=frozenset(sin_veta))

    def previsualizar(self, m: ModuloGuardado) -> motor.Despiece:
        """Cálculo sin guardar, para ver las piezas mientras se carga el módulo."""
        return motor.calcular_modulo(self.a_motor(m), self.reglas())

    def guardar_modulo(self, m: ModuloGuardado) -> tuple[int, list[str]]:
        """Guarda (o recalcula) el módulo y sus piezas. Devuelve (id, avisos para revisar)."""
        self._mueble_editable(m.id_mueble)
        m = replace(m, nombre=_texto(m.nombre, "el nombre del módulo", 100, obligatorio=False))
        if not 1 <= m.cantidad <= MAXIMO_MODULOS_IGUALES:
            raise ErrorMuebles(f"La cantidad de módulos iguales va de 1 a {MAXIMO_MODULOS_IGUALES}.")
        resultado = self.previsualizar(m)
        roles = self._material_por_rol(m)
        # Frentes laqueados y listones (pinos) nacen «Sin filo»: no llevan.
        def piso_oculto(p) -> bool:
            return p.tipo == PISO_DE_CAJON and p.cajon is not None and guia_oculta(self._guia(m.cajones[p.cajon - 1].id_guia))

        def nunca(p) -> bool:
            return p.medida_2 is None or p.tipo in TIPOS_SIN_FILO or piso_oculto(p)
        sin_filo = self._sin_filo() if m.id_color_laca or any(nunca(p) for p in resultado.piezas) else None

        generadas = []
        for p in resultado.piezas:
            if p.material is motor.Material.PISO_CAJON:
                id_material = m.cajones[p.cajon - 1].id_placa_piso
            else:
                id_material = roles[p.material]
            laqueada = m.id_color_laca is not None and p.material is motor.Material.FRENTES
            generadas.append(PiezaGuardada(
                None, p.tipo, id_material, p.cantidad, p.medida_1, p.medida_2,
                id_modulo=None if p.cajon else m.id, orden_cajon=p.cajon,
                id_tipo_filo=sin_filo if laqueada or nunca(p) else None,
                id_color_laca=m.id_color_laca if laqueada else None,
                id_terminacion=m.id_terminacion if laqueada else None))

        avisos: list[str] = []
        nuevas = generadas
        if m.id is not None:
            anteriores = self._repo.piezas_de_modulo(m.id)
            nuevas, avisos = self._combinar(anteriores, generadas)
            cajones_que_se_van = {p.orden_cajon for p in anteriores
                                  if p.orden_cajon and p.orden_cajon > len(m.cajones) and p.editada}
            for orden in sorted(cajones_que_se_van):
                avisos.append(f"Se quitó el cajón {orden}: sus piezas editadas a mano también se borraron.")
        return self._repo.guardar_modulo(m, nuevas), avisos

    @staticmethod
    def _combinar(anteriores: list[PiezaGuardada], generadas: list[PiezaGuardada]
                  ) -> tuple[list[PiezaGuardada], list[str]]:
        """Recálculo: no se generan las piezas de un grupo (tipo, cajón) que alguien editó;
        a las demás se les pasan los filos que ya tenían definidos."""
        editadas = {(p.tipo, p.orden_cajon) for p in anteriores if p.editada}
        filos = {(p.tipo, p.orden_cajon): p for p in anteriores
                 if not p.editada and p.id_tipo_filo is not None and p.id_color_laca is None}
        nuevas, avisos = [], []
        for p in generadas:
            grupo = (p.tipo, p.orden_cajon)
            if grupo in editadas:
                donde = f" del cajón {p.orden_cajon}" if p.orden_cajon else ""
                medida = f"{p.medida_1} × {p.medida_2}" if p.medida_2 is not None else f"{p.medida_1}"
                avisos.append(f"{p.tipo}{donde}: la editaste a mano y no se recalculó. "
                              f"El cálculo nuevo da {medida} (×{p.cantidad}); revisala.")
                continue
            anterior = filos.get(grupo)
            # Solo a las que nacen con el filo por definir: las que nunca llevan (fondos,
            # pisos con guía oculta, listones, laqueadas) quedan «Sin filo».
            if anterior is not None and p.id_color_laca is None and p.id_tipo_filo is None:
                p = replace(p, id_tipo_filo=anterior.id_tipo_filo, cantos=anterior.cantos,
                            id_color_filo=anterior.id_color_filo)
            nuevas.append(p)
        return nuevas, avisos

    def eliminar_modulo(self, id_modulo: int) -> None:
        modulo = self._repo.modulo(id_modulo)
        if modulo is None:
            raise ErrorMuebles("El módulo ya no existe.")
        self._mueble_editable(modulo.id_mueble)
        self._repo.eliminar_modulo(id_modulo)

    # ---------- zócalos ----------
    def zocalos(self, id_mueble: int) -> list[ZocaloGuardado]:
        return self._repo.zocalos(id_mueble)

    def proponer_zocalo(self, largo_tramo: Decimal, profundidad_tramo: Decimal) -> tuple[Decimal, Decimal]:
        return motor.proponer_zocalo(largo_tramo, profundidad_tramo, self.reglas())

    def guardar_zocalo(self, z: ZocaloGuardado) -> tuple[int, list[str]]:
        self._mueble_editable(z.id_mueble)
        placas = self._placas()
        if z.id_placa not in placas or (z.id_placa_oculta is not None and z.id_placa_oculta not in placas):
            raise ErrorMuebles("Elegí la placa del zócalo.")
        z = replace(z, descripcion=_texto(z.descripcion, "la descripción", 100, obligatorio=False))
        calculadas = motor.calcular_zocalo(z.largo, z.alto, z.profundidad, z.refuerzos, placas[z.id_placa].espesor)
        oculta = z.id_placa_oculta or z.id_placa
        generadas = [PiezaGuardada(None, p.tipo, oculta if p.material is motor.Material.ZOCALO_OCULTO else z.id_placa,
                                   p.cantidad, p.medida_1, p.medida_2, id_zocalo=z.id) for p in calculadas]
        avisos: list[str] = []
        if z.id is not None:
            generadas, avisos = self._combinar(self._repo.piezas_de_zocalo(z.id), generadas)
        return self._repo.guardar_zocalo(z, generadas), avisos

    def eliminar_zocalo(self, id_zocalo: int) -> None:
        zocalo = self._repo.zocalo(id_zocalo)
        if zocalo is None:
            raise ErrorMuebles("El zócalo ya no existe.")
        self._mueble_editable(zocalo.id_mueble)
        self._repo.eliminar_zocalo(id_zocalo)

    # ---------- piezas (RF-15 a RF-19) ----------
    def _marcar(self, piezas: list[PiezaGuardada]) -> list[PiezaGuardada]:
        """Marca los pisos de cajón con guía oculta: nunca llevan filo (RN-08.4)."""
        if not any(p.tipo == PISO_DE_CAJON and p.id_guia_cajon for p in piezas):
            return piezas
        ocultas = {g.id for g in self._catalogo.guias() if guia_oculta(g)}
        return [replace(p, sin_filo_fijo=True) if p.tipo == PISO_DE_CAJON and p.id_guia_cajon in ocultas else p
                for p in piezas]

    def piezas_del_trabajo(self, id_trabajo: int) -> list[PiezaGuardada]:
        return self._marcar(self._repo.piezas_de_trabajo(id_trabajo))

    def piezas_de_modulo(self, id_modulo: int) -> list[PiezaGuardada]:
        return self._marcar(self._repo.piezas_de_modulo(id_modulo))

    def piezas_de_zocalo(self, id_zocalo: int) -> list[PiezaGuardada]:
        return self._repo.piezas_de_zocalo(id_zocalo)

    def puede_modificarse(self, id_trabajo: int) -> bool:
        try:
            self._controlar_trabajo(id_trabajo)
        except ErrorMuebles:
            return False
        return True

    def piezas_sin_filo(self, id_trabajo: int) -> list[PiezaGuardada]:
        """Las que todavía no tienen filo definido: bloquean el listado (RN-08.1)."""
        return [p for p in self.piezas_del_trabajo(id_trabajo) if p.id_tipo_filo is None and not nunca_lleva_filo(p)]

    # ---------- listados (M6) ----------
    def listado_de_corte(self, id_trabajo: int) -> list[SeccionCorte]:
        """Listado para la maderera. No se genera mientras falte algún filo (RN-08.1)."""
        piezas = self.piezas_del_trabajo(id_trabajo)
        if not piezas:
            raise ErrorMuebles("El trabajo todavía no tiene piezas: cargá sus muebles y módulos.")
        faltan = [p for p in piezas if p.id_tipo_filo is None and not nunca_lleva_filo(p)]
        if faltan:
            nombres = list(dict.fromkeys(p.descripcion or p.tipo for p in faltan))
            lista = ", ".join(nombres[:6]) + ("…" if len(nombres) > 6 else "")
            raise ErrorMuebles(f"Faltan definir los filos de {len(faltan)} fila{'s' if len(faltan) != 1 else ''} "
                               f"({lista}). Completalos en «Piezas y filos» para generar el listado.")
        return armar_listado(piezas, self._placas(), {x.id: x for x in self._materiales.listones()},
                             {f.id: f for f in self._catalogo.filos()},
                             {c.id: c for c in self._materiales.colores()},
                             {c.id: c for c in self._catalogo.colores_laca()})

    def listado_laqueador(self, id_trabajo: int) -> list[SeccionLaca]:
        secciones = armar_laqueador(self._repo.piezas_de_trabajo(id_trabajo),
                                    {c.id: c for c in self._catalogo.colores_laca()},
                                    {t.id: t for t in self._catalogo.terminaciones()}, self._placas())
        if not secciones:
            raise ErrorMuebles("El trabajo no tiene piezas laqueadas.")
        return secciones

    def tiene_laqueadas(self, id_trabajo: int) -> bool:
        return any(p.id_color_laca is not None for p in self._repo.piezas_de_trabajo(id_trabajo))

    def definir_filo(self, ids: list[int], id_tipo_filo: int, cantos: Cantos,
                     id_color_filo: int | None = None) -> None:
        """Mismo filo para una o varias piezas (RF-15.3)."""
        filo = next((f for f in self._catalogo.filos() if f.id == id_tipo_filo), None)
        if filo is None:
            raise ErrorMuebles("Elegí el tipo de filo.")
        if filo.nombre == SIN_FILO and cantos.cantidad:
            raise ErrorMuebles("«Sin filo» no lleva cantos marcados.")
        if filo.nombre != SIN_FILO and not cantos.cantidad:
            raise ErrorMuebles("Marcá qué cantos llevan filo, o elegí «Sin filo».")
        piezas = [self._pieza_editable(i) for i in ids]
        for p in piezas:
            if p.id_color_laca is not None and filo.nombre != SIN_FILO:
                raise ErrorMuebles(f"{p.tipo}: está laqueada y las piezas laqueadas no llevan filo.")
            if p.medida_2 is None and filo.nombre != SIN_FILO:
                raise ErrorMuebles(f"{p.tipo}: es un listón, no lleva filo.")
            if p.tipo in TIPOS_SIN_FILO and filo.nombre != SIN_FILO:
                raise ErrorMuebles("Los fondos y los pisos de cajón no llevan filo.")
            if p.sin_filo_fijo and filo.nombre != SIN_FILO:
                raise ErrorMuebles("Con guía de lateral oculto, el piso del cajón no lleva filo (como los fondos).")
        for p in piezas:
            self._repo.guardar_pieza(replace(p, id_tipo_filo=id_tipo_filo, cantos=cantos,
                                             id_color_filo=None if filo.nombre == SIN_FILO else id_color_filo))

    def definir_filo_por_patron(self, ids: list[int], id_tipo_filo: int, patron: str | None,
                                id_color_filo: int | None = None) -> None:
        """Mismo filo y mismo patrón de cantos («2 largos», «1 corto»…) para varias
        piezas: los cantos se calculan en cada una según cuál es su lado largo (RF-15.5)."""
        filo = next((f for f in self._catalogo.filos() if f.id == id_tipo_filo), None)
        if filo is None:
            raise ErrorMuebles("Elegí el tipo de filo.")
        if filo.nombre != SIN_FILO and not patron:
            raise ErrorMuebles("Elegí qué cantos llevan filo (1 largo, 2 cortos…).")
        piezas = [self._pieza_editable(i) for i in ids]
        for p in piezas:   # todo o nada: primero se controla, después se guarda
            if p.id_color_laca is not None and filo.nombre != SIN_FILO:
                raise ErrorMuebles(f"{p.descripcion or p.tipo}: está laqueada y las piezas laqueadas no llevan filo.")
            if p.medida_2 is None and filo.nombre != SIN_FILO:
                raise ErrorMuebles(f"{p.descripcion or p.tipo}: es un listón, no lleva filo.")
            if p.tipo in TIPOS_SIN_FILO and filo.nombre != SIN_FILO:
                raise ErrorMuebles("Los fondos y los pisos de cajón no llevan filo.")
            if p.sin_filo_fijo and filo.nombre != SIN_FILO:
                raise ErrorMuebles("Con guía de lateral oculto, el piso del cajón no lleva filo (como los fondos).")
        for p in piezas:
            cantos = Cantos() if filo.nombre == SIN_FILO else cantos_de_patron(patron, p.medida_1, p.medida_2)
            self._repo.guardar_pieza(replace(p, id_tipo_filo=id_tipo_filo, cantos=cantos,
                                             id_color_filo=None if filo.nombre == SIN_FILO else id_color_filo))

    def laquear(self, ids: list[int], id_color_laca: int | None, id_terminacion: int | None) -> None:
        """Laquear (con terminación obligatoria) deja la pieza sin filo; quitar la laca
        vuelve el filo a sin definir (RF-15.2)."""
        if (id_color_laca is None) != (id_terminacion is None):
            raise ErrorMuebles("Para laquear elegí el color de laca y la terminación.")
        sin_filo = self._sin_filo() if id_color_laca else None
        for p in [self._pieza_editable(i) for i in ids]:
            self._repo.guardar_pieza(replace(p, id_color_laca=id_color_laca, id_terminacion=id_terminacion,
                                             id_tipo_filo=sin_filo, cantos=Cantos(), id_color_filo=None))

    def rotar_pieza(self, id_pieza: int) -> None:
        """Cambia el sentido de la veta: se intercambian las medidas y también los cantos (RF-19)."""
        p = self._pieza_editable(id_pieza)
        if p.medida_2 is None:
            raise ErrorMuebles("Un listón no se rota.")
        self._repo.guardar_pieza(replace(p, medida_1=p.medida_2, medida_2=p.medida_1, cantos=p.cantos.rotados(),
                                         editada=True))

    def editar_pieza(self, id_pieza: int, cantidad: int, medida_1: Decimal, medida_2: Decimal | None,
                     id_material: int | None = None) -> None:
        p = self._pieza_editable(id_pieza)
        if cantidad <= 0 or medida_1 <= 0 or (medida_2 is not None and medida_2 <= 0):
            raise ErrorMuebles("La cantidad y las medidas tienen que ser mayores que cero.")
        if (medida_2 is None) != (p.medida_2 is None):
            raise ErrorMuebles("Las piezas de placa llevan dos medidas; los listones, una.")
        self._repo.guardar_pieza(replace(p, cantidad=cantidad, medida_1=motor.redondear(medida_1),
                                         medida_2=motor.redondear(medida_2) if medida_2 is not None else None,
                                         id_material=id_material or p.id_material, editada=True))

    def dividir_fila(self, id_pieza: int, cantidad: int, descripcion: str | None = None) -> int:
        """Separa piezas de una fila para darles otro filo o laca (RF-15.3). La fila nueva
        puede llevar un nombre (ej.: «Lateral visto») para reconocerla. Las dos quedan editadas."""
        p = self._pieza_editable(id_pieza)
        if not 0 < cantidad < p.cantidad:
            raise ErrorMuebles(f"Podés separar entre 1 y {p.cantidad - 1} piezas.")
        nombre = _texto(descripcion, "el nombre de la fila nueva", 100, obligatorio=False)
        self._repo.guardar_pieza(replace(p, cantidad=p.cantidad - cantidad, editada=True))
        return self._repo.guardar_pieza(replace(p, id=None, cantidad=cantidad, editada=True,
                                                descripcion=nombre or p.descripcion))

    def agregar_pieza_suelta(self, id_mueble: int, tipo: str, descripcion: str | None, id_material: int,
                             cantidad: int, medida_1: Decimal, medida_2: Decimal | None) -> int:
        """Ajustes, revestimientos u otras piezas que no salen de un módulo (RF-13)."""
        self._mueble_editable(id_mueble)
        if tipo not in TIPOS_SUELTOS:
            raise ErrorMuebles("Elegí el tipo de pieza (Ajuste u Otra).")
        if cantidad <= 0 or medida_1 <= 0 or medida_2 is None or medida_2 <= 0:
            raise ErrorMuebles("Completá la cantidad y las dos medidas.")
        if id_material not in self._placas():
            raise ErrorMuebles("Elegí la placa de la pieza.")
        return self._repo.guardar_pieza(PiezaGuardada(
            None, tipo, id_material, cantidad, motor.redondear(medida_1), motor.redondear(medida_2),
            id_mueble=id_mueble, descripcion=_texto(descripcion, "la descripción", 100, obligatorio=False),
            editada=True))

    def eliminar_pieza(self, id_pieza: int) -> None:
        p = self._pieza_editable(id_pieza)
        if p.id_mueble is None:
            raise ErrorMuebles("Esta pieza sale del cálculo de un módulo o zócalo: para quitarla, cambiá el módulo.")
        self._repo.eliminar_pieza(id_pieza)
