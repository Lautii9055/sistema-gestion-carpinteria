"""Listado de corte para la maderera y listado para el laqueador (M6, RF-21 a RF-24.1).

Lógica pura: recibe las piezas guardadas y los datos del catálogo, y devuelve
las secciones y filas listas para imprimir. No sabe nada de PDF ni de la base.

- Una sección por placa (marca, color y espesor) y otra por cada listón.
- La medida de corte resta el filo de cada canto que lo lleva (RN-03.1).
- Las piezas idénticas se juntan en una fila con su cantidad (RF-24).
- Los colores lisos se marcan como rotables (RN-02): la maderera elige el
  sentido para desperdiciar menos. Para poder juntarlas, se ponen con la
  medida mayor primero (y los cantos girados con ellas).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from carpinteria.negocio.despiece import medida_de_corte
from carpinteria.negocio.filos import TIPOS_SIN_FILO
from carpinteria.negocio.entidades import (Cantos, ColorLaca, ColorPlaca, Liston, PiezaGuardada, Placa,
                                           TerminacionLaca, TipoFilo)
from carpinteria.negocio.materiales import formato_numero, texto_seccion

SIN_FILO = "Sin filo"


@dataclass(frozen=True)
class FilaCorte:
    cantidad: int
    medida_1: Decimal                  # de corte, sentido de la veta
    medida_2: Decimal | None           # None en listones
    filo: str | None                   # None = sin filo
    cantos: Cantos
    color_filo: str | None             # solo si es distinto al de la pieza
    rotable: bool                      # color liso: la maderera puede girarla
    piezas: str                        # "Lateral, Estante"
    laca: str | None = None            # se corta para laquear
    final_1: Decimal | None = None     # medida terminada, con el filo (para el control del taller)
    final_2: Decimal | None = None


@dataclass(frozen=True)
class SeccionCorte:
    titulo: str                        # "Faplac Blanco Nieve · 18 mm"
    detalle: str                       # "Placa de 183 × 260" o "Sección 2 × 1\""
    filas: list[FilaCorte]
    es_liston: bool = False

    @property
    def total(self) -> int:
        return sum(f.cantidad for f in self.filas)


@dataclass(frozen=True)
class FilaLaca:
    cantidad: int
    medida_1: Decimal                  # final (el laqueador trabaja sobre la pieza terminada)
    medida_2: Decimal
    piezas: str
    placa: str


@dataclass(frozen=True)
class SeccionLaca:
    titulo: str                        # "Sherwin Williams Gris Topo (SW 7062)"
    terminacion: str
    filas: list[FilaLaca]

    @property
    def total(self) -> int:
        return sum(f.cantidad for f in self.filas)


@dataclass
class _Acumulado:
    cantidad: int = 0
    nombres: list[str] = field(default_factory=list)

    def sumar(self, cantidad: int, nombre: str) -> None:
        self.cantidad += cantidad
        if nombre not in self.nombres:
            self.nombres.append(nombre)


def _nombre(p: PiezaGuardada) -> str:
    return p.descripcion or p.tipo


def _texto_color(c: ColorPlaca | None) -> str:
    return f"{c.marca} {c.descripcion}".strip() if c else "Placa"


def armar_listado(piezas: list[PiezaGuardada], placas: dict[int, Placa], listones: dict[int, Liston],
                  filos: dict[int, TipoFilo], colores: dict[int, ColorPlaca],
                  lacas: dict[int, ColorLaca] | None = None) -> list[SeccionCorte]:
    """Secciones del listado de corte. Las piezas sin filo definido no deberían
    llegar acá (el servicio lo controla antes, RN-08.1)."""
    lacas = lacas or {}
    por_material: dict[int, dict[tuple, _Acumulado]] = {}
    listones_usados: dict[int, dict[tuple, _Acumulado]] = {}
    for p in piezas:
        filo = filos.get(p.id_tipo_filo) if p.id_tipo_filo is not None else None
        con_filo = (filo is not None and filo.nombre != SIN_FILO and p.tipo not in TIPOS_SIN_FILO
                    and not p.sin_filo_fijo)
        if p.medida_2 is None:   # listón: solo el largo
            clave = (p.medida_1,)
            listones_usados.setdefault(p.id_material, {}).setdefault(clave, _Acumulado()).sumar(p.total, _nombre(p))
            continue
        cantos = p.cantos if con_filo else Cantos()
        m1, m2 = medida_de_corte(p.medida_1, p.medida_2, filo.descuento_cm if con_filo else Decimal(0),
                                 cantos.superior, cantos.inferior, cantos.izquierdo, cantos.derecho)
        placa = placas.get(p.id_material)
        rotable = not (placa and placa.color and placa.color.tiene_veta)
        f1, f2 = p.medida_1, p.medida_2
        if rotable and m2 is not None and m2 > m1:   # liso: la mayor primero, girando los cantos
            m1, m2, f1, f2, cantos = m2, m1, f2, f1, cantos.rotados()
        color_filo = None
        if con_filo and p.id_color_filo is not None and placa and p.id_color_filo != placa.id_color:
            color_filo = _texto_color(colores.get(p.id_color_filo))
        laca = lacas.get(p.id_color_laca) if p.id_color_laca is not None else None
        clave = (m1, m2, filo.nombre if con_filo else None, cantos, color_filo, rotable,
                 laca.descripcion if laca else None, p.id_terminacion, f1, f2)
        por_material.setdefault(p.id_material, {}).setdefault(clave, _Acumulado()).sumar(p.total, _nombre(p))

    secciones: list[SeccionCorte] = []
    orden_placas = sorted(por_material, key=lambda i: (
        -(placas[i].espesor if i in placas else Decimal(0)),
        _texto_color(placas[i].color) if i in placas else ""))
    for id_placa in orden_placas:
        placa = placas.get(id_placa)
        filas = [FilaCorte(a.cantidad, c[0], c[1], c[2], c[3], c[4], c[5], ", ".join(a.nombres),
                           f"para laquear ({c[6]})" if c[6] else None, c[8], c[9])
                 for c, a in por_material[id_placa].items()]
        filas.sort(key=lambda f: (-f.medida_1, -(f.medida_2 or 0)))
        titulo = (f"{_texto_color(placa.color)} · {formato_numero(placa.espesor_mm)} mm" if placa else "Placa")
        detalle = f"Placa de {formato_numero(placa.largo)} × {formato_numero(placa.ancho)}" if placa else ""
        secciones.append(SeccionCorte(titulo, detalle, filas))
    for id_liston, grupos in listones_usados.items():
        liston = listones.get(id_liston)
        filas = sorted((FilaCorte(a.cantidad, c[0], None, None, Cantos(), None, False, ", ".join(a.nombres),
                                  final_1=c[0])
                        for c, a in grupos.items()), key=lambda f: -f.medida_1)
        secciones.append(SeccionCorte(liston.nombre if liston else "Listón",
                                      f"Sección {texto_seccion(liston)}" if liston else "", filas, es_liston=True))
    return secciones


def armar_laqueador(piezas: list[PiezaGuardada], lacas: dict[int, ColorLaca],
                    terminaciones: dict[int, TerminacionLaca], placas: dict[int, Placa]) -> list[SeccionLaca]:
    """Piezas a laquear agrupadas por color y terminación, con medidas finales (RF-24.1)."""
    grupos: dict[tuple[int, int | None], dict[tuple, _Acumulado]] = {}
    for p in piezas:
        if p.id_color_laca is None or p.medida_2 is None:
            continue
        placa = placas.get(p.id_material)
        clave = (p.medida_1, p.medida_2, _texto_color(placa.color) + f" {formato_numero(placa.espesor_mm)} mm"
                 if placa else "")
        grupos.setdefault((p.id_color_laca, p.id_terminacion), {}).setdefault(clave, _Acumulado()).sumar(
            p.total, _nombre(p))
    secciones = []
    for (id_laca, id_term), filas in grupos.items():
        laca = lacas.get(id_laca)
        terminacion = terminaciones.get(id_term)
        titulo = f"{laca.marca} {laca.descripcion}".strip() if laca else "Laca"
        lista = sorted((FilaLaca(a.cantidad, c[0], c[1], ", ".join(a.nombres), c[2]) for c, a in filas.items()),
                       key=lambda f: (-f.medida_1, -f.medida_2))
        secciones.append(SeccionLaca(titulo, terminacion.nombre if terminacion else "", lista))
    secciones.sort(key=lambda s: (s.titulo, s.terminacion))
    return secciones


def nombre_de_archivo(id_trabajo: int, descripcion: str, que: str) -> str:
    """"Trabajo 12 - Cocina Ferreyra - Listado de corte.pdf", sin caracteres que Windows no acepta."""
    limpio = "".join(c for c in descripcion if c not in '<>:"/\\|?*' and ord(c) >= 32).strip(" .")[:60]
    return f"Trabajo {id_trabajo} - {limpio or 'sin nombre'} - {que}.pdf"
