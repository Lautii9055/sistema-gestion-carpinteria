"""PDF del listado de corte (diseño 5, RF-21 a RF-24) y del laqueador (RF-24.1).

Recibe las secciones ya armadas por negocio/listado.py y solo se ocupa de
dibujarlas: A4 vertical, una tabla por placa, el dibujo de los cantos con
filo (cuadrado, U, L o línea, como se marca hoy a mano) y el pie con el
número de página. Usa las tipografías del sistema (Inter y Cormorant).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from fpdf import FPDF

from carpinteria.negocio.entidades import Cantos, DetalleTrabajo
from carpinteria.negocio.listado import SeccionCorte, SeccionLaca
from carpinteria.negocio.materiales import formato_numero
from carpinteria.presentacion.tema import CARPETA_RECURSOS

FUENTES = CARPETA_RECURSOS / "fonts"
TINTA = (28, 25, 21)
GRIS = (110, 104, 96)
GRIS_CLARO = (205, 200, 192)
FONDO_SECCION = (240, 234, 222)
FONDO_ALTERNO = (248, 246, 242)
DORADO = (150, 112, 40)


def _f(numero: Decimal | None) -> str:
    return formato_numero(numero) if numero is not None else ""


class _Documento(FPDF):
    def __init__(self, titulo: str, detalle: DetalleTrabajo, con_cliente: bool = False) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.titulo_doc = titulo
        self.detalle = detalle
        # Solo el control del taller muestra trabajo, cliente y obra; lo que sale del
        # taller (maderera, laqueador) lleva solo el número de trabajo y la fecha.
        self.con_cliente = con_cliente
        self.generado = datetime.now()
        self.set_margins(12, 12, 12)
        self.set_auto_page_break(auto=False)
        self.add_font("Inter", "", str(FUENTES / "Inter-Regular.ttf"))
        self.add_font("Inter", "B", str(FUENTES / "Inter-SemiBold.ttf"))
        self.add_font("InterMedia", "", str(FUENTES / "Inter-Medium.ttf"))
        self.add_font("Cormorant", "", str(FUENTES / "CormorantGaramond-SemiBold.ttf"))
        self.set_title(f"{titulo} · Trabajo {detalle.trabajo.id}")
        self.set_author("Carpintería Zanino")
        self.set_creator("Sistema de Gestión para Carpintería")
        self.columnas: list[tuple[str, float, str]] = []   # (título, ancho, alineación)

    # ----- encabezado y pie de cada página -----
    def header(self) -> None:
        t, c, o = self.detalle.trabajo, self.detalle.cliente, self.detalle.obra
        self.set_text_color(*TINTA)
        self.set_font("Cormorant", size=20)
        self.cell(0, 8, "Carpintería Zanino", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Inter", "B", 13)
        self.cell(120, 7, self.titulo_doc)
        self.set_font("Inter", "", 9)
        self.set_text_color(*GRIS)
        self.cell(0, 7, f"Trabajo #{t.id} · {self.generado:%d/%m/%Y}", align="R", new_x="LMARGIN", new_y="NEXT")
        if self.con_cliente:
            self.cell(0, 5, f"{t.descripcion} · {c.nombre_completo} · {o.direccion}, {o.localidad}",
                      new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*DORADO)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y() + 2, self.w - self.r_margin, self.get_y() + 2)
        self.ln(5)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Inter", "", 8)
        self.set_text_color(*GRIS)
        self.cell(0, 5, f"Generado el {self.generado:%d/%m/%Y %H:%M}", align="L")
        self.set_x(self.l_margin)
        self.cell(0, 5, f"Página {self.page_no()} de {{nb}}", align="R")

    # ----- utilidades -----
    def espacio_restante(self) -> float:
        return self.h - 16 - self.get_y()

    def recortar(self, texto: str, ancho: float) -> str:
        if self.get_string_width(texto) <= ancho:
            return texto
        while texto and self.get_string_width(texto + "…") > ancho:
            texto = texto[:-1]
        return texto + "…"

    def encabezado_tabla(self) -> None:
        self.set_font("Inter", "B", 8)
        self.set_text_color(*GRIS)
        for titulo, ancho, alineacion in self.columnas:
            self.cell(ancho, 6, titulo, align=alineacion)
        self.ln(6)
        self.set_draw_color(*GRIS_CLARO)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())

    def titulo_seccion(self, titulo: str, detalle: str, total: int) -> None:
        self.set_fill_color(*FONDO_SECCION)
        self.set_text_color(*TINTA)
        self.set_font("Inter", "B", 11)
        ancho = self.w - self.l_margin - self.r_margin
        self.cell(ancho * 0.6, 9, "  " + titulo, fill=True)
        self.set_font("Inter", "", 9)
        self.set_text_color(*GRIS)
        self.cell(ancho * 0.4, 9, f"{detalle}  ·  {total} pieza{'s' if total != 1 else ''}  ", fill=True, align="R",
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def nueva_pagina_si_hace_falta(self, alto: float, repetir_encabezado: bool = True) -> None:
        if self.espacio_restante() < alto:
            self.add_page()
            if repetir_encabezado:
                self.encabezado_tabla()

    def cantos(self, x: float, y: float, cantos: Cantos) -> None:
        """La pieza con la medida 1 en horizontal; trazo grueso = canto con filo."""
        ancho, alto = 14.0, 7.0
        self.set_draw_color(*GRIS_CLARO)
        self.set_line_width(0.2)
        self.rect(x, y, ancho, alto)
        self.set_draw_color(*TINTA)
        self.set_line_width(0.9)
        if cantos.superior:
            self.line(x, y, x + ancho, y)
        if cantos.inferior:
            self.line(x, y + alto, x + ancho, y + alto)
        if cantos.izquierdo:
            self.line(x, y, x, y + alto)
        if cantos.derecho:
            self.line(x + ancho, y, x + ancho, y + alto)


def generar_listado_de_corte(ruta: Path, detalle: DetalleTrabajo, secciones: list[SeccionCorte],
                             para_taller: bool = False) -> Path:
    """Para la maderera: solo la medida de corte (sin filo). Para el taller: la
    final (con filo) y la de corte, una al lado de la otra, para controlar."""
    pdf = _Documento("Control del taller · final y corte" if para_taller else "Listado de corte", detalle,
                     con_cliente=para_taller)
    if para_taller:
        medidas = [("Largo final", 22, "R"), ("Ancho final", 21, "R"), ("Largo", 19, "R"), ("Ancho", 19, "R")]
        ancho_pieza = 51
    else:
        medidas = [("Largo", 28, "R"), ("Ancho", 26, "R")]
        ancho_pieza = 70
    pdf.columnas = [("Cant.", 14, "C"), *medidas, ("", 4, "L"), ("Filo", 18 if para_taller else 22, "L"),
                    ("Cantos", 18 if para_taller else 22, "C"),
                    ("Pieza" if para_taller else "Observaciones", ancho_pieza, "L")]
    ancho_filo = pdf.columnas[-3][1]
    pdf.add_page()
    total = sum(s.total for s in secciones)
    pdf.set_font("Inter", "B", 10)
    pdf.set_text_color(*TINTA)
    pdf.cell(0, 6, f"{total} piezas en {len(secciones)} material{'es' if len(secciones) != 1 else ''}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Inter", "", 8.5)
    pdf.set_text_color(*GRIS)
    if para_taller:
        leyenda = ("Uso interno. Largo y ancho final = la pieza terminada, con el filo incluido. Largo y ancho = "
                   "lo que se pide a la maderera, sin filo (el filo de 2 mm se suma después). "
                   "El largo es el sentido de la veta.")
    else:
        leyenda = ("MEDIDAS DE CORTE, SIN FILO, en cm: cortar a esta medida y después aplicar el filo indicado. "
                   "El largo es el sentido de la veta. En el dibujo, el trazo grueso marca los cantos con filo "
                   "(largo en horizontal). «Liso»: color sin veta, se puede girar para aprovechar la placa.")
    pdf.multi_cell(0, 4.5, leyenda, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    alto_fila = 10.0
    for seccion in secciones:
        pdf.nueva_pagina_si_hace_falta(9 + 7 + alto_fila * min(2, len(seccion.filas)), repetir_encabezado=False)
        pdf.titulo_seccion(seccion.titulo, seccion.detalle, seccion.total)
        if seccion.es_liston:
            previas = pdf.columnas
            pdf.columnas = [("Cant.", 14, "C"), ("Largo", 28, "R"),
                            *([("", 102, "L"), ("Pieza", 42, "L")] if para_taller else [])]
        pdf.encabezado_tabla()
        for i, fila in enumerate(seccion.filas):
            pdf.nueva_pagina_si_hace_falta(alto_fila)
            x, y = pdf.get_x(), pdf.get_y()
            if i % 2:
                pdf.set_fill_color(*FONDO_ALTERNO)
                pdf.rect(x, y, pdf.w - pdf.l_margin - pdf.r_margin, alto_fila, style="F")
            pdf.set_text_color(*TINTA)
            pdf.set_font("Inter", "B", 11)
            pdf.cell(14, alto_fila, str(fila.cantidad), align="C")
            pdf.set_font("InterMedia", "", 11)
            if seccion.es_liston:
                pdf.cell(28, alto_fila, _f(fila.medida_1), align="R")
                if para_taller:
                    pdf.cell(102, alto_fila, "")
                    pdf.set_font("Inter", "", 9)
                    pdf.cell(42, alto_fila, pdf.recortar(fila.piezas, 41))
                pdf.set_xy(pdf.l_margin, y + alto_fila)
                continue
            if para_taller:
                pdf.set_text_color(*GRIS)
                pdf.cell(22, alto_fila, _f(fila.final_1), align="R")
                pdf.cell(19, alto_fila, _f(fila.final_2), align="R")
                pdf.set_text_color(*TINTA)
                pdf.set_font("Inter", "B", 11)
                pdf.cell(21, alto_fila, _f(fila.medida_1), align="R")
                pdf.cell(19, alto_fila, _f(fila.medida_2), align="R")
            else:
                pdf.cell(28, alto_fila, _f(fila.medida_1), align="R")
                pdf.cell(26, alto_fila, _f(fila.medida_2), align="R")
            pdf.cell(4, alto_fila, "")
            pdf.set_font("Inter", "", 9)
            pdf.cell(ancho_filo, alto_fila, fila.filo or "Sin filo")
            # Siempre se dibuja la pieza: sin trazos gruesos = ningún canto con filo.
            pdf.cantos(pdf.get_x() + (ancho_filo - 14) / 2, y + 1.5, fila.cantos)
            pdf.set_x(pdf.get_x() + ancho_filo)
            notas = [n for n in (fila.color_filo and f"filo {fila.color_filo}", "liso" if fila.rotable else None,
                                 fila.laca) if n]
            pdf.set_text_color(*TINTA)
            pdf.set_font("Inter", "", 9)
            if not para_taller:   # a la maderera no le importa qué pieza es: solo las aclaraciones
                pdf.set_text_color(*GRIS)
                pdf.cell(ancho_pieza, alto_fila, pdf.recortar(" · ".join(notas), ancho_pieza - 1),
                         new_x="LMARGIN", new_y="NEXT")
            elif notas:
                pdf.cell(ancho_pieza, alto_fila / 2 + 0.5, pdf.recortar(fila.piezas, ancho_pieza - 1),
                         new_x="LEFT", new_y="NEXT")
                pdf.set_text_color(*GRIS)
                pdf.set_font("Inter", "", 7.5)
                pdf.cell(ancho_pieza, alto_fila / 2 - 1.5, pdf.recortar(" · ".join(notas), ancho_pieza - 1))
                pdf.set_xy(pdf.l_margin, y + alto_fila)
            else:
                pdf.cell(ancho_pieza, alto_fila, pdf.recortar(fila.piezas, ancho_pieza - 1),
                         new_x="LMARGIN", new_y="NEXT")
        if seccion.es_liston:
            pdf.columnas = previas
        pdf.ln(5)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(ruta))
    return ruta


def generar_listado_laqueador(ruta: Path, detalle: DetalleTrabajo, secciones: list[SeccionLaca]) -> Path:
    pdf = _Documento("Piezas para laquear", detalle)
    pdf.columnas = [("Cant.", 14, "C"), ("Largo", 28, "R"), ("Ancho", 26, "R"), ("", 6, "L"),
                    ("Placa", 112, "L")]
    pdf.add_page()
    pdf.set_font("Inter", "", 8.5)
    pdf.set_text_color(*GRIS)
    pdf.multi_cell(0, 4.5, "Medidas finales en cm (la pieza terminada). Agrupadas por color de laca y terminación.",
                   new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    alto_fila = 9.0
    for seccion in secciones:
        pdf.nueva_pagina_si_hace_falta(9 + 7 + alto_fila, repetir_encabezado=False)
        pdf.titulo_seccion(seccion.titulo, seccion.terminacion, seccion.total)
        pdf.encabezado_tabla()
        for i, fila in enumerate(seccion.filas):
            pdf.nueva_pagina_si_hace_falta(alto_fila)
            if i % 2:
                pdf.set_fill_color(*FONDO_ALTERNO)
                pdf.rect(pdf.get_x(), pdf.get_y(), pdf.w - pdf.l_margin - pdf.r_margin, alto_fila, style="F")
            pdf.set_text_color(*TINTA)
            pdf.set_font("Inter", "B", 11)
            pdf.cell(14, alto_fila, str(fila.cantidad), align="C")
            pdf.set_font("InterMedia", "", 11)
            pdf.cell(28, alto_fila, _f(fila.medida_1), align="R")
            pdf.cell(26, alto_fila, _f(fila.medida_2), align="R")
            pdf.cell(6, alto_fila, "")
            pdf.set_font("Inter", "", 9)
            pdf.set_text_color(*GRIS)
            pdf.cell(112, alto_fila, pdf.recortar(fila.placa, 111), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(ruta))
    return ruta


def carpeta_de_listados() -> Path:
    """Documentos\\Carpintería Zanino\\Listados (o la carpeta del usuario si no hay Documentos)."""
    documentos = Path.home() / "Documents"
    base = documentos if documentos.is_dir() else Path.home()
    return base / "Carpintería Zanino" / "Listados"
