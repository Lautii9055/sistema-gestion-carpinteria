"""Piezas y filos (diseño 4b, RF-15 a RF-19).

A la izquierda, las piezas agrupadas (estructura, frentes, cada cajón, zócalos,
piezas sueltas) con su estado de filo. A la derecha, el editor: la pieza dibujada
con la medida 1 (sentido de la veta) en horizontal; se toca cada canto para
marcarlo, se elige el tipo de filo y se ve la medida de corte al instante.
Se pueden marcar varias piezas y darles el mismo filo de una vez.
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import flet as ft

from carpinteria.negocio.despiece import medida_de_corte
from carpinteria.negocio.entidades import Cantos, PiezaGuardada
from carpinteria.negocio.materiales import formato_numero, leer_numero, texto_placa
from carpinteria.presentacion import componentes, tema
from carpinteria.presentacion.tema import SANS_MEDIA, SANS_SEMI
from carpinteria.presentacion.vista_muebles import FILTRO_NUMERO, resumen_modulo

if TYPE_CHECKING:
    from carpinteria.presentacion.app import Aplicacion

SIN_FILO = "Sin filo"
FRENTES = {"Puerta", "Frente de cajón"}
LADOS = ("superior", "inferior", "izquierdo", "derecho")


def _f(numero: Decimal | None) -> str:
    return formato_numero(numero) if numero is not None else "—"


def _medidas(x: PiezaGuardada) -> str:
    return f"{_f(x.medida_1)} × {_f(x.medida_2)}" if x.medida_2 is not None else f"largo {_f(x.medida_1)}"


# ---------- datos de la pantalla ----------
class _Datos:
    """Lo que la pantalla necesita del catálogo, leído una sola vez."""

    def __init__(self, app: Aplicacion) -> None:
        filos, _ = app.ejecutar(app.catalogo.filos)
        placas, _ = app.ejecutar(app.materiales.placas, "", True)
        listones, _ = app.ejecutar(app.materiales.listones, True)
        colores, _ = app.ejecutar(app.materiales.colores, "", None, True)
        lacas, _ = app.ejecutar(app.catalogo.colores_laca, "", True)
        terminaciones, _ = app.ejecutar(app.catalogo.terminaciones, True)
        self.filos = {f.id: f for f in filos or []}
        self.placas = {p.id: p for p in placas or []}
        self.listones = {x.id: x for x in listones or []}
        self.colores = {c.id: c for c in colores or []}
        self.lacas = {c.id: c for c in lacas or []}
        self.terminaciones = {t.id: t for t in terminaciones or []}
        self.sin_filo = next((f.id for f in self.filos.values() if f.nombre == SIN_FILO), None)

    def material(self, x: PiezaGuardada) -> str:
        if x.medida_2 is None:
            liston = self.listones.get(x.id_material)
            return liston.nombre if liston else "Listón"
        placa = self.placas.get(x.id_material)
        return texto_placa(placa) if placa else "Placa"

    def con_veta(self, x: PiezaGuardada) -> bool:
        placa = self.placas.get(x.id_material)
        return bool(placa and placa.color and placa.color.tiene_veta)

    def estado(self, x: PiezaGuardada) -> tuple[str, bool]:
        """(texto de la etiqueta, ¿falta definir?)."""
        if x.id_color_laca is not None:
            laca = self.lacas.get(x.id_color_laca)
            return f"Laqueada{' · ' + laca.descripcion if laca else ''}", False
        if x.id_tipo_filo is None:
            return "Falta filo", True
        filo = self.filos.get(x.id_tipo_filo)
        if filo is None or filo.nombre == SIN_FILO:
            return "Sin filo", False
        n = x.cantos.cantidad
        return f"✓ {filo.nombre} · {n} canto{'s' if n != 1 else ''}", False


def _grupos(app: Aplicacion, id_trabajo: int, id_modulo: int | None, id_zocalo: int | None
            ) -> tuple[str, list[tuple[str, list[PiezaGuardada]]]]:
    """Subtítulo de la pantalla y las piezas agrupadas, en el orden del listado."""
    muebles, _ = app.ejecutar(app.muebles.muebles, id_trabajo)
    grupos: list[tuple[str, list[PiezaGuardada]]] = []

    def de_modulo(piezas: list[PiezaGuardada], prefijo: str = "") -> None:
        estructura = [x for x in piezas if x.orden_cajon is None and x.tipo not in FRENTES]
        frentes = [x for x in piezas if x.tipo in FRENTES]
        for titulo, lista in ((f"{prefijo}Estructura", estructura), (f"{prefijo}Frentes", frentes)):
            if lista:
                grupos.append((titulo, lista))
        for orden in sorted({x.orden_cajon for x in piezas if x.orden_cajon and x.tipo not in FRENTES}):
            grupos.append((f"{prefijo}Cajón {orden}",
                           [x for x in piezas if x.orden_cajon == orden and x.tipo not in FRENTES]))

    if id_modulo is not None:
        for mueble in muebles or []:
            modulos, _ = app.ejecutar(app.muebles.modulos, mueble.id)
            for i, m in enumerate(modulos or [], 1):
                if m.id == id_modulo:
                    piezas, _ = app.ejecutar(app.muebles.piezas_de_modulo, m.id)
                    de_modulo(piezas or [])
                    return f"{mueble.nombre} › {m.nombre or f'Módulo {i}'} · {resumen_modulo(m)}", grupos
        return "", grupos
    if id_zocalo is not None:
        piezas, _ = app.ejecutar(app.muebles.piezas_de_zocalo, id_zocalo)
        grupos.append(("Zócalo", piezas or []))
        return "Zócalo", grupos
    # Todo el trabajo: mueble por mueble.
    todas, _ = app.ejecutar(app.muebles.piezas_del_trabajo, id_trabajo)
    for mueble in muebles or []:
        modulos, _ = app.ejecutar(app.muebles.modulos, mueble.id)
        for i, m in enumerate(modulos or [], 1):
            piezas, _ = app.ejecutar(app.muebles.piezas_de_modulo, m.id)
            de_modulo(piezas or [], f"{mueble.nombre} › {m.nombre or f'Módulo {i}'} · ")
        zocalos, _ = app.ejecutar(app.muebles.zocalos, mueble.id)
        for z in zocalos or []:
            piezas, _ = app.ejecutar(app.muebles.piezas_de_zocalo, z.id)
            grupos.append((f"{mueble.nombre} › {z.descripcion or 'Zócalo'}", piezas or []))
        sueltas = [x for x in todas or [] if x.id_mueble == mueble.id]
        if sueltas:
            grupos.append((f"{mueble.nombre} › Piezas sueltas", sueltas))
    return "Todas las piezas del trabajo", grupos


# ---------- dibujo de la pieza ----------
def _dibujo_pieza(app: Aplicacion, x: PiezaGuardada, cantos: Cantos, con_veta: bool, al_tocar) -> ft.Control:
    """La pieza con la medida 1 en horizontal. Cada canto es una barra que se toca
    para poner o sacar el filo."""
    p = app.paleta
    ancho_max, alto_max, grosor = 320.0, 190.0, 12.0
    m1, m2 = float(x.medida_1), float(x.medida_2 or 1)
    escala = min(ancho_max / m1, alto_max / m2)
    w, h = max(m1 * escala, 70), max(m2 * escala, 46)
    x0, y0 = (ancho_max - w) / 2 + 40, 26

    def barra(lado: str, left: float, top: float, ancho: float, alto: float) -> ft.Container:
        activo = getattr(cantos, lado)
        return ft.Container(left=left, top=top, width=ancho, height=alto, border_radius=4,
                            bgcolor=p.acento if activo else p.borde_fuerte, ink=True,
                            tooltip=f"Canto {lado}: {'con filo' if activo else 'sin filo'}",
                            on_click=lambda _: al_tocar(lado))

    vetas = []
    if con_veta:   # rayas en el sentido de la veta (la medida 1)
        for i in range(1, 5):
            vetas.append(ft.Container(left=x0 + 14, top=y0 + h * i / 5, width=w - 28, height=1,
                                      bgcolor=p.borde_fuerte))
    figuras: list[ft.Control] = [
        ft.Container(left=x0, top=y0, width=w, height=h, bgcolor=p.superficie_alta, border_radius=2),
        *vetas,
        barra("superior", x0, y0 - grosor / 2, w, grosor),
        barra("inferior", x0, y0 + h - grosor / 2, w, grosor),
        barra("izquierdo", x0 - grosor / 2, y0, grosor, h),
        barra("derecho", x0 + w - grosor / 2, y0, grosor, h),
        ft.Container(left=x0, top=y0 + h + 12, width=w,
                     content=ft.Text(f"{_f(x.medida_1)} cm{'  · veta ↔' if con_veta else ''}", size=13,
                                     color=p.texto_secundario, text_align=ft.TextAlign.CENTER)),
        ft.Container(left=x0 + w + 12, top=y0 + h / 2 - 10,
                     content=ft.Text(f"{_f(x.medida_2)} cm", size=13, color=p.texto_secundario)),
    ]
    return ft.Stack(figuras, width=ancho_max + 120, height=alto_max + 64)


# ---------- pantalla ----------
def construir(app: Aplicacion, id_trabajo: int, id_modulo: int | None = None,
              id_zocalo: int | None = None) -> ft.Control:
    p = app.paleta
    datos = _Datos(app)
    editable = app.muebles.puede_modificarse(id_trabajo)
    clave = f"piezas:{id_trabajo}:{id_modulo}:{id_zocalo}"
    estado = app.recuerdos.get("piezas")
    if not estado or estado.get("_clave") != clave:
        estado = {"_clave": clave, "sel": [], "cantos": Cantos(), "id_filo": None, "id_color": ""}
        app.recuerdos["piezas"] = estado

    lista_cont = ft.Container()
    editor_cont = ft.Container()
    resumen = ft.Text(size=14)

    def volver(_=None) -> None:
        app.recuerdos.pop("piezas", None)
        app.ir_a("trabajo", id_trabajo=id_trabajo)

    def piezas_actuales() -> tuple[str, list[tuple[str, list[PiezaGuardada]]]]:
        return _grupos(app, id_trabajo, id_modulo, id_zocalo)

    def por_id() -> dict[int, PiezaGuardada]:
        return {x.id: x for _, lista in piezas_actuales()[1] for x in lista}

    def cargar_desde(x: PiezaGuardada) -> None:
        """Al elegir una pieza, el editor arranca con su filo (o el último usado)."""
        if x.id_tipo_filo is not None and x.id_color_laca is None:
            estado["id_filo"], estado["cantos"] = x.id_tipo_filo, x.cantos
            estado["id_color"] = str(x.id_color_filo or "")
        elif estado["id_filo"] is None:
            otro = next((f for f in datos.filos.values() if f.nombre != SIN_FILO), None)
            estado["id_filo"] = otro.id if otro else datos.sin_filo
            estado["cantos"] = Cantos(True, True, True, True) if otro else Cantos()

    def elegir(x: PiezaGuardada, sumar: bool) -> None:
        sel = estado["sel"]
        if sumar:
            if x.id in sel:
                sel.remove(x.id)
            else:
                sel.append(x.id)
                if len(sel) == 1:
                    cargar_desde(x)
        else:
            estado["sel"] = [x.id]
            cargar_desde(x)
        actualizar()

    def elegir_faltantes(_=None) -> None:
        faltan = [x for _, lista in piezas_actuales()[1] for x in lista
                  if x.id_tipo_filo is None and x.id_color_laca is None and x.medida_2 is not None]
        estado["sel"] = [x.id for x in faltan]
        if faltan:
            cargar_desde(faltan[0])
        actualizar()

    # ----- lista -----
    def fila(x: PiezaGuardada) -> ft.Container:
        texto, falta = datos.estado(x)
        elegida = x.id in estado["sel"]
        etiqueta = componentes.etiqueta_estado(texto, p.error_texto if falta else
                                               (p.exito if texto.startswith("✓") else p.texto_secundario),
                                               p.error_fondo if falta else p.superficie_alta)
        return ft.Container(
            content=ft.Row([
                ft.Checkbox(value=elegida, active_color=p.acento, check_color=p.sobre_acento,
                            on_change=lambda _, x=x: elegir(x, True), visible=editable),
                ft.Column([ft.Text(f"{x.descripcion or x.tipo} × {x.cantidad}", size=15, font_family=SANS_MEDIA,
                                   color=p.texto),
                           ft.Text(f"{_medidas(x)} · {datos.material(x)}", size=12, color=p.texto_tenue)],
                          spacing=0, expand=True),
                etiqueta,
            ], spacing=8),
            padding=ft.Padding.symmetric(horizontal=8, vertical=6), border_radius=10,
            bgcolor=p.superficie_alta if elegida else None,
            border=ft.Border.all(1, p.acento if elegida else p.borde), ink=True,
            on_click=(lambda _, x=x: elegir(x, False)) if editable else None)

    def armar_lista() -> ft.Control:
        subtitulo, grupos = piezas_actuales()
        todas = [x for _, lista in grupos for x in lista]
        faltan = sum(1 for x in todas if datos.estado(x)[1])
        resumen.value = (f"{sum(x.cantidad for x in todas)} piezas · faltan {faltan} fila{'s' if faltan != 1 else ''}"
                         if faltan else f"{sum(x.cantidad for x in todas)} piezas · todos los filos definidos ✓")
        resumen.color = p.error_texto if faltan else p.exito
        controles: list[ft.Control] = [ft.Text(subtitulo, size=13, color=p.texto_tenue)]
        if not todas:
            controles.append(ft.Text("No hay piezas.", size=14, color=p.texto_tenue))
        for titulo, lista in grupos:
            if lista:
                controles += [tema.etiqueta_superior(titulo, p), *[fila(x) for x in lista]]
        if editable and faltan:
            controles.insert(1, ft.TextButton(content=ft.Text(f"Marcar las {faltan} que faltan", size=14,
                                                              color=p.acento_texto), on_click=elegir_faltantes))
        return ft.Column(controles, spacing=8)

    # ----- editor -----
    def tocar_canto(lado: str) -> None:
        c = estado["cantos"]
        estado["cantos"] = Cantos(**{**{k: getattr(c, k) for k in LADOS}, lado: not getattr(c, lado)})
        filo = datos.filos.get(estado["id_filo"])
        if filo and filo.nombre == SIN_FILO and estado["cantos"].cantidad:
            # Marcó un canto con «Sin filo» elegido: pasa al primer filo real.
            otro = next((f for f in datos.filos.values() if f.nombre != SIN_FILO), None)
            estado["id_filo"] = otro.id if otro else estado["id_filo"]
        actualizar()

    def elegir_filo(id_filo: int) -> None:
        estado["id_filo"] = id_filo
        if id_filo == datos.sin_filo:
            estado["cantos"] = Cantos()
        elif not estado["cantos"].cantidad:
            estado["cantos"] = Cantos(True, True, True, True)
        actualizar()

    def todos_los_cantos(valor: bool) -> None:
        estado["cantos"] = Cantos(valor, valor, valor, valor)
        if valor and estado["id_filo"] == datos.sin_filo:
            otro = next((f for f in datos.filos.values() if f.nombre != SIN_FILO), None)
            estado["id_filo"] = otro.id if otro else estado["id_filo"]
        actualizar()

    def aplicar(_=None) -> None:
        ids = list(estado["sel"])
        _, error = app.ejecutar(app.muebles.definir_filo, ids, estado["id_filo"], estado["cantos"],
                                int(estado["id_color"]) if estado["id_color"] else None)
        if error:
            mostrar_error(error)
            return
        # Sigue con la próxima pieza que falte, en el orden de la lista.
        orden = [x for _, lista in piezas_actuales()[1] for x in lista]
        siguiente = next((x for x in orden if datos.estado(x)[1] and x.medida_2 is not None), None)
        estado["sel"] = [siguiente.id] if siguiente else []
        if siguiente and siguiente.id_tipo_filo is not None:
            cargar_desde(siguiente)
        actualizar()
        componentes.aviso_flotante(app.page, f"Filo aplicado a {len(ids)} fila{'s' if len(ids) != 1 else ''}.", p)

    def mostrar_error(texto: str) -> None:
        caja_error.content, caja_error.visible = tema.aviso(texto, p), True
        app.page.update()

    caja_error = ft.Container(visible=False)

    def boton_filo(f) -> ft.Container:
        activo = estado["id_filo"] == f.id
        texto = f.nombre if f.nombre == SIN_FILO else f"{f.nombre}"
        detalle = "" if f.nombre == SIN_FILO else f"−{formato_numero(f.descuento_cm)} cm por canto"
        return ft.Container(
            content=ft.Column([ft.Text(texto, size=15, font_family=SANS_SEMI, color=p.texto),
                               *([ft.Text(detalle, size=11, color=p.texto_tenue)] if detalle else [])],
                              spacing=0, tight=True),
            padding=ft.Padding.symmetric(horizontal=14, vertical=8), border_radius=10, ink=True,
            border=ft.Border.all(2 if activo else 1, p.acento if activo else p.borde_fuerte),
            bgcolor=p.superficie_alta if activo else None, on_click=lambda _: elegir_filo(f.id))

    def armar_editor() -> ft.Control:
        caja_error.visible = False
        piezas = por_id()
        estado["sel"] = [i for i in estado["sel"] if i in piezas]
        elegidas = [piezas[i] for i in estado["sel"]]
        if not editable:
            return ft.Column([tema.aviso("El trabajo ya no se puede modificar: las piezas se ven, pero no se "
                                         "cambian.", p, "info")], spacing=12)
        if not elegidas:
            return componentes.estado_vacio(ft.Icons.TOUCH_APP_OUTLINED, "Elegí una pieza",
                                            "Tocá una pieza de la lista para definir su filo. Con las casillas "
                                            "marcás varias y les das el mismo filo de una vez.", p)
        primera = elegidas[0]
        controles: list[ft.Control] = [caja_error]
        varias = len(elegidas) > 1
        controles.append(ft.Text(
            f"{len(elegidas)} filas elegidas · mismo filo para todas" if varias
            else f"{primera.descripcion or primera.tipo} × {primera.cantidad}", size=20, font_family=SANS_SEMI,
            color=p.texto))
        if any(x.medida_2 is None for x in elegidas):
            controles.append(tema.aviso("Los listones no llevan filo.", p, "info"))
            return ft.Column(controles, spacing=12)
        if any(x.id_color_laca is not None for x in elegidas):
            controles += [tema.aviso("Laqueada: no lleva filo. Para ponerle filo, quitale la laca.", p, "info"),
                          _acciones(app, elegidas, datos, id_trabajo, actualizar)]
            return ft.Column(controles, spacing=12)

        cantos = estado["cantos"]
        filo = datos.filos.get(estado["id_filo"])
        descuento = filo.descuento_cm if filo and filo.nombre != SIN_FILO else Decimal(0)
        corte_1, corte_2 = medida_de_corte(primera.medida_1, primera.medida_2, descuento,
                                           **{k: getattr(cantos, k) for k in LADOS})
        controles += [
            ft.Container(_dibujo_pieza(app, primera, cantos, datos.con_veta(primera), tocar_canto),
                         alignment=ft.Alignment.CENTER),
            _ayuda(p, "Tocá cada canto para ponerle o sacarle filo." + (
                f" El dibujo es de {primera.tipo.lower()}; el filo se aplica igual a las {len(elegidas)} filas."
                if varias else "")),
            ft.Row([ft.TextButton(content=ft.Text("Los 4 cantos", color=p.acento_texto),
                                  on_click=lambda _: todos_los_cantos(True)),
                    ft.TextButton(content=ft.Text("Ninguno", color=p.acento_texto),
                                  on_click=lambda _: todos_los_cantos(False))], spacing=4),
            tema.etiqueta_superior("Tipo de filo", p),
            ft.Row([boton_filo(f) for f in datos.filos.values()], spacing=8, wrap=True, run_spacing=8),
        ]
        if filo and filo.nombre != SIN_FILO:
            colores = [("", "Del mismo color que la pieza")] + [
                (str(c.id), f"{c.marca} {c.descripcion}") for c in datos.colores.values()
                if c.es_activo or str(c.id) == estado["id_color"]]
            color = componentes.desplegable("Color del filo", colores, estado["id_color"], p)

            def al_elegir_color(_):
                estado["id_color"] = color.value or ""
            color.on_select = al_elegir_color
            controles.append(color)
        controles.append(componentes.tarjeta(ft.Row([
            ft.Column([ft.Text("Medida final", size=12, color=p.texto_tenue),
                       ft.Text(f"{_f(primera.medida_1)} × {_f(primera.medida_2)}", size=18, color=p.texto,
                               font_family=SANS_MEDIA)], spacing=0, expand=True),
            ft.Icon(ft.Icons.ARROW_FORWARD, color=p.texto_tenue),
            ft.Column([ft.Text("Medida de corte", size=12, color=p.texto_tenue),
                       ft.Text(f"{_f(corte_1)} × {_f(corte_2)}", size=18, color=p.acento_texto,
                               font_family=SANS_SEMI)], spacing=0, expand=True,
                      horizontal_alignment=ft.CrossAxisAlignment.END),
        ]), p, padding=14))
        controles += [
            tema.boton_principal(f"Aplicar a {len(elegidas)} fila{'s' if varias else ''}", p, aplicar,
                                 disabled=filo is None),
            ft.Divider(color=p.borde, height=1),
            _acciones(app, elegidas, datos, id_trabajo, actualizar),
        ]
        return ft.Column(controles, spacing=12)

    def actualizar() -> None:
        lista_cont.content = armar_lista()
        editor_cont.content = armar_editor()
        app.page.update()

    lista_cont.content = armar_lista()
    editor_cont.content = armar_editor()

    atras = ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color=p.texto, icon_size=26, tooltip="Volver al trabajo",
                          on_click=volver)
    otro_alcance = None
    if id_modulo is not None or id_zocalo is not None:
        otro_alcance = ft.TextButton(content=ft.Text("Ver todas las del trabajo", color=p.acento_texto, size=14),
                                     on_click=lambda _: (app.recuerdos.pop("piezas", None),
                                                         app.ir_a("piezas", id_trabajo=id_trabajo)))
    return ft.Column([
        ft.Row([atras,
                ft.Column([tema.titulo("Piezas y filos", p, 36), resumen], spacing=0, expand=True),
                *([otro_alcance] if otro_alcance else []),
                tema.boton_secundario("Listo", p, volver)], spacing=8),
        ft.ResponsiveRow([
            componentes.tarjeta(lista_cont, p, padding=18, col={"xs": 12, "lg": 6}),
            componentes.tarjeta(editor_cont, p, padding=22, col={"xs": 12, "lg": 6}),
        ], spacing=20, run_spacing=20, vertical_alignment=ft.CrossAxisAlignment.START),
    ], spacing=18)


def _ayuda(p, texto: str) -> ft.Text:
    return ft.Text(texto, size=13, color=p.texto_tenue)


# ---------- acciones sobre las piezas elegidas ----------
def _acciones(app: Aplicacion, elegidas: list[PiezaGuardada], datos: _Datos, id_trabajo: int, actualizar
              ) -> ft.Control:
    p = app.paleta
    una = elegidas[0] if len(elegidas) == 1 else None

    def hacer(funcion, *args, mensaje: str) -> None:
        _, error = app.ejecutar(funcion, *args)
        if error:
            componentes.aviso_flotante(app.page, error, p)
            return
        actualizar()
        componentes.aviso_flotante(app.page, mensaje, p)

    def boton(texto: str, icono, al_tocar, visible: bool = True) -> ft.TextButton:
        return ft.TextButton(content=ft.Row([ft.Icon(icono, size=18, color=p.texto_secundario),
                                             ft.Text(texto, size=14, color=p.texto_secundario)],
                                            spacing=4, tight=True), on_click=lambda _: al_tocar(), visible=visible)

    botones = [
        boton("Rotar veta", ft.Icons.SCREEN_ROTATION_OUTLINED,
              lambda: hacer(app.muebles.rotar_pieza, una.id, mensaje="Veta rotada: se intercambiaron las medidas."),
              visible=una is not None and una.medida_2 is not None),
        boton("Separar piezas", ft.Icons.CALL_SPLIT, lambda: _dialogo_dividir(app, una, actualizar),
              visible=una is not None and una.cantidad > 1),
        boton("Editar medidas", ft.Icons.EDIT_OUTLINED, lambda: _dialogo_editar(app, una, actualizar),
              visible=una is not None),
        boton("Laquear", ft.Icons.FORMAT_PAINT_OUTLINED, lambda: _dialogo_laquear(app, elegidas, datos, actualizar),
              visible=all(x.medida_2 is not None for x in elegidas)),
        boton("Eliminar", ft.Icons.DELETE_OUTLINE,
              lambda: hacer(app.muebles.eliminar_pieza, una.id, mensaje="Pieza eliminada."),
              visible=una is not None and una.id_mueble is not None),
    ]
    return ft.Column([tema.etiqueta_superior("Más acciones", p),
                      ft.Row(botones, spacing=0, wrap=True, run_spacing=0),
                      _ayuda(p, "Al rotar, separar o editar, la pieza queda «editada a mano»: si después cambiás el "
                                "módulo, no se recalcula y el sistema te avisa.")], spacing=6)


def _dialogo(app: Aplicacion, titulo: str, controles: list[ft.Control], accion) -> None:
    p = app.paleta
    caja_error = ft.Container(visible=False)

    def confirmar(_=None) -> None:
        error = accion()
        if error:
            caja_error.content, caja_error.visible = tema.aviso(error, p), True
            app.page.update()

    app.mostrar_dialogo(componentes.dialogo(
        p, titulo, ft.Column([caja_error, *controles], spacing=14, tight=True),
        [componentes.boton_cancelar(p, lambda _: app.cerrar_dialogo()), tema.boton_principal("Guardar", p, confirmar)],
        ancho=480))


def _dialogo_dividir(app: Aplicacion, x: PiezaGuardada, actualizar) -> None:
    p = app.paleta
    cantidad = tema.campo("Cuántas separar", p, value="1", autofocus=True, input_filter=ft.NumbersOnlyInputFilter(),
                          helper=f"Entre 1 y {x.cantidad - 1}: quedan en otra fila para darles otro filo")

    def guardar() -> str | None:
        _, error = app.ejecutar(app.muebles.dividir_fila, x.id, int(cantidad.value or 0))
        if error:
            return error
        app.cerrar_dialogo()
        actualizar()
        return None
    _dialogo(app, f"Separar · {x.tipo} × {x.cantidad}", [cantidad], guardar)


def _dialogo_editar(app: Aplicacion, x: PiezaGuardada, actualizar) -> None:
    p = app.paleta
    cantidad = tema.campo("Cantidad", p, value=str(x.cantidad), input_filter=ft.NumbersOnlyInputFilter())
    m1 = tema.campo("Medida 1 (cm)", p, value=_f(x.medida_1), input_filter=FILTRO_NUMERO,
                    helper="En el sentido de la veta")
    m2 = tema.campo("Medida 2 (cm)", p, value=_f(x.medida_2) if x.medida_2 is not None else "",
                    input_filter=FILTRO_NUMERO, visible=x.medida_2 is not None)

    def guardar() -> str | None:
        _, error = app.ejecutar(lambda: app.muebles.editar_pieza(
            x.id, int(cantidad.value or 0), leer_numero(m1.value, "la medida 1"),
            leer_numero(m2.value, "la medida 2") if x.medida_2 is not None else None))
        if error:
            return error
        app.cerrar_dialogo()
        actualizar()
        return None
    _dialogo(app, f"Editar · {x.descripcion or x.tipo}", [cantidad, m1, m2], guardar)


def _dialogo_laquear(app: Aplicacion, elegidas: list[PiezaGuardada], datos: _Datos, actualizar) -> None:
    p = app.paleta
    actual = elegidas[0]
    colores = [("", "Sin laquear")] + [(str(c.id), f"{c.marca} {c.descripcion}") for c in datos.lacas.values()
                                       if c.es_activo or c.id == actual.id_color_laca]
    terminaciones = [(str(t.id), t.nombre) for t in datos.terminaciones.values()
                     if t.es_activo or t.id == actual.id_terminacion]
    color = componentes.desplegable("Color de laca", colores, str(actual.id_color_laca or ""), p)
    terminacion = componentes.desplegable("Terminación", terminaciones,
                                          str(actual.id_terminacion or (terminaciones[0][0] if terminaciones else "")),
                                          p)

    def guardar() -> str | None:
        id_color = int(color.value) if color.value else None
        id_term = int(terminacion.value) if id_color and terminacion.value else None
        _, error = app.ejecutar(app.muebles.laquear, [x.id for x in elegidas], id_color, id_term)
        if error:
            return error
        app.cerrar_dialogo()
        actualizar()
        return None
    _dialogo(app, "Laquear", [color, terminacion,
                              _ayuda(p, "Laqueada no lleva filo. «Sin laquear» la deja con el filo por definir.")],
             guardar)
