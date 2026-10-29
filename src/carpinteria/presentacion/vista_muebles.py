"""Sección "Muebles y módulos" del detalle del trabajo (diseño 3): muebles, sus
módulos, zócalos y piezas sueltas."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import flet as ft

from carpinteria.negocio.entidades import ModuloGuardado, Mueble, ZocaloGuardado
from carpinteria.negocio.materiales import formato_numero, leer_numero, texto_placa
from carpinteria.presentacion import componentes, tema
from carpinteria.presentacion.tema import SANS_MEDIA, SANS_SEMI

if TYPE_CHECKING:
    from carpinteria.presentacion.app import Aplicacion

FILTRO_NUMERO = ft.InputFilter(regex_string=r"^[0-9.,]{0,7}$", allow=True, replacement_string="")


def opciones_placas(app: Aplicacion, incluir: tuple[int | None, ...] = (), solo_espesor_mm: Decimal | None = None
                    ) -> list[tuple[str, str]]:
    """Placas activas para elegir (y las ya elegidas, aunque estén dadas de baja)."""
    todas, _ = app.ejecutar(app.materiales.placas, "", True)
    activas = [p for p in todas or [] if p.es_activo and p.color and p.color.es_activo and p.color.marca_activa]
    elegidas = [p for p in todas or [] if p.id in incluir and p not in activas]
    lista = [*activas, *elegidas]
    if solo_espesor_mm is not None:
        lista = [p for p in lista if p.espesor_mm == solo_espesor_mm or p.id in incluir]
    return [(str(p.id), texto_placa(p)) for p in lista]


def _recargar(app: Aplicacion, id_trabajo: int, mensaje: str | None = None) -> None:
    app.ir_a("trabajo", id_trabajo=id_trabajo)
    if mensaje:
        componentes.aviso_flotante(app.page, mensaje, app.paleta)


def _dialogo(app: Aplicacion, titulo: str, controles: list[ft.Control], boton: str, accion, ancho: int = 520) -> None:
    p = app.paleta
    caja_error = ft.Container(visible=False)

    def confirmar(_=None) -> None:
        error = accion()
        if error:
            caja_error.content = tema.aviso(error, p)
            caja_error.visible = True
            app.page.update()

    app.mostrar_dialogo(componentes.dialogo(
        p, titulo, ft.Column([caja_error, *controles], spacing=14, tight=True, scroll=ft.ScrollMode.AUTO),
        [componentes.boton_cancelar(p, lambda _: app.cerrar_dialogo()), tema.boton_principal(boton, p, confirmar)],
        ancho=ancho))


def mostrar_avisos(app: Aplicacion, avisos: list[str], titulo: str = "Revisá estas piezas") -> None:
    p = app.paleta
    app.mostrar_dialogo(componentes.dialogo(
        p, titulo, ft.Column([ft.Row([ft.Icon(ft.Icons.INFO_OUTLINE, size=18, color=p.acento_texto),
                                      ft.Text(a, size=14, color=p.texto_secundario, expand=True)],
                                     spacing=8, vertical_alignment=ft.CrossAxisAlignment.START) for a in avisos],
                             spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
        [tema.boton_principal("Entendido", p, lambda _: app.cerrar_dialogo())], ancho=560))


# ---------- diálogos ----------
def dialogo_mueble(app: Aplicacion, id_trabajo: int, mueble: Mueble | None = None) -> None:
    p = app.paleta
    nombre = tema.campo("Nombre del mueble", p, value=mueble.nombre if mueble else "", autofocus=True, max_length=100,
                        hint_text="por ejemplo: Bajo mesada cocina, Alacena, Placard")
    observaciones = tema.campo("Observaciones (opcional)", p, value=(mueble.observaciones or "") if mueble else "",
                               multiline=True, min_lines=2, max_lines=4, max_length=500)

    def guardar() -> str | None:
        _, error = app.ejecutar(app.muebles.guardar_mueble, mueble.id if mueble else None, id_trabajo,
                                nombre.value or "", observaciones.value)
        if error:
            return error
        app.cerrar_dialogo()
        _recargar(app, id_trabajo, "Mueble guardado.")
        return None

    _dialogo(app, "Editar mueble" if mueble else "Nuevo mueble", [nombre, observaciones], "Guardar", guardar)


def dialogo_zocalo(app: Aplicacion, id_trabajo: int, mueble: Mueble, zocalo: ZocaloGuardado | None = None) -> None:
    p = app.paleta
    opciones = opciones_placas(app, (zocalo.id_placa, zocalo.id_placa_oculta) if zocalo else ())
    if not opciones:
        componentes.aviso_flotante(app.page, "Primero cargá las placas en Materiales.", p)
        return
    descripcion = tema.campo("Descripción (opcional)", p, value=(zocalo.descripcion or "") if zocalo else "",
                             max_length=100, hint_text="por ejemplo: Zócalo bajo mesada completo")
    tramo = tema.campo("Largo del tramo (cm)", p, input_filter=FILTRO_NUMERO, visible=zocalo is None,
                       helper="Lo que cubre (un módulo, varios o el mueble)")
    prof_tramo = tema.campo("Profundidad del mueble (cm)", p, input_filter=FILTRO_NUMERO, visible=zocalo is None)
    largo = tema.campo("Largo del zócalo (cm)", p, value=formato_numero(zocalo.largo) if zocalo else "",
                       input_filter=FILTRO_NUMERO)
    profundidad = tema.campo("Profundidad del zócalo (cm)", p,
                             value=formato_numero(zocalo.profundidad) if zocalo else "", input_filter=FILTRO_NUMERO)
    alto = tema.campo("Alto (cm)", p, value=formato_numero(zocalo.alto) if zocalo else "10", input_filter=FILTRO_NUMERO)
    refuerzos = tema.campo("Refuerzos", p, value=str(zocalo.refuerzos) if zocalo else "0",
                           input_filter=ft.NumbersOnlyInputFilter(), helper="Se definen en la fabricación (puede ser 0)")
    placa = componentes.desplegable("Placa (partes a la vista)", opciones,
                                    str(zocalo.id_placa) if zocalo else opciones[0][0], p)
    oculta = componentes.desplegable("Placa de trasera y refuerzos", [("", "La misma"), *opciones],
                                     str(zocalo.id_placa_oculta) if zocalo and zocalo.id_placa_oculta else "", p)

    def proponer(_=None) -> None:
        try:
            l_, pz = app.muebles.proponer_zocalo(leer_numero(tramo.value, "el largo"),
                                                 leer_numero(prof_tramo.value, "la profundidad"))
        except Exception:
            return
        largo.value, profundidad.value = formato_numero(l_), formato_numero(pz)
        app.page.update()

    tramo.on_change = proponer
    prof_tramo.on_change = proponer

    def guardar() -> str | None:
        def hacer():
            z = ZocaloGuardado(zocalo.id if zocalo else None, mueble.id, int(placa.value),
                               leer_numero(largo.value, "el largo"), leer_numero(alto.value, "el alto"),
                               leer_numero(profundidad.value, "la profundidad"), int(refuerzos.value or 0),
                               int(oculta.value) if oculta.value else None, descripcion.value)
            return app.muebles.guardar_zocalo(z)
        resultado, error = app.ejecutar(hacer)
        if error:
            return error
        app.cerrar_dialogo()
        _recargar(app, id_trabajo, "Zócalo guardado.")
        if resultado[1]:
            mostrar_avisos(app, resultado[1])
        return None

    par = lambda a, b: ft.Row([ft.Container(a, expand=True), ft.Container(b, expand=True)], spacing=12,  # noqa: E731
                              vertical_alignment=ft.CrossAxisAlignment.START)
    _dialogo(app, "Editar zócalo" if zocalo else "Nuevo zócalo", [
        descripcion,
        *([ft.Text("Cargá el tramo y el sistema propone el zócalo: retira 1,5 cm del frente y deja el largo "
                   "completo. Si un costado queda libre, descontale 1,5.", size=13, color=p.texto_tenue),
           par(tramo, prof_tramo)] if zocalo is None else []),
        par(largo, profundidad), par(alto, refuerzos), placa, oculta,
    ], "Guardar", guardar, 600)


def dialogo_pieza_suelta(app: Aplicacion, id_trabajo: int, mueble: Mueble) -> None:
    p = app.paleta
    opciones = opciones_placas(app)
    if not opciones:
        componentes.aviso_flotante(app.page, "Primero cargá las placas en Materiales.", p)
        return
    tipo = componentes.desplegable("Tipo", [("Ajuste", "Ajuste"), ("Otra", "Otra")], "Ajuste", p)
    descripcion = tema.campo("Descripción", p, max_length=100, hint_text="por ejemplo: Revestimiento heladera")
    placa = componentes.desplegable("Placa", opciones, opciones[0][0], p)
    cantidad = tema.campo("Cantidad", p, value="1", input_filter=ft.NumbersOnlyInputFilter())
    m1 = tema.campo("Medida 1 (cm)", p, input_filter=FILTRO_NUMERO, helper="En el sentido de la veta")
    m2 = tema.campo("Medida 2 (cm)", p, input_filter=FILTRO_NUMERO)

    def guardar() -> str | None:
        _, error = app.ejecutar(lambda: app.muebles.agregar_pieza_suelta(
            mueble.id, tipo.value, descripcion.value, int(placa.value), int(cantidad.value or 0),
            leer_numero(m1.value, "la medida 1"), leer_numero(m2.value, "la medida 2")))
        if error:
            return error
        app.cerrar_dialogo()
        _recargar(app, id_trabajo, "Pieza agregada.")
        return None

    par = lambda a, b: ft.Row([ft.Container(a, expand=True), ft.Container(b, expand=True)], spacing=12,  # noqa: E731
                              vertical_alignment=ft.CrossAxisAlignment.START)
    _dialogo(app, f"Pieza suelta · {mueble.nombre}", [par(tipo, cantidad), descripcion, placa, par(m1, m2)],
             "Agregar", guardar, 560)


def _confirmar(app: Aplicacion, titulo: str, texto: str, accion) -> None:
    p = app.paleta
    _dialogo(app, titulo, [ft.Text(texto, size=15, color=p.texto_secundario)], "Eliminar", accion, 480)


def _eliminar(app: Aplicacion, id_trabajo: int, funcion, id_: int, que: str) -> None:
    def accion() -> str | None:
        _, error = app.ejecutar(funcion, id_)
        if error:
            return error
        app.cerrar_dialogo()
        _recargar(app, id_trabajo, f"{que[0].upper()}{que[1:]} eliminado.")
        return None
    _confirmar(app, "Eliminar", f"Se elimina {que} con todas sus piezas. No se puede deshacer.", accion)


# ---------- sección ----------
def resumen_modulo(m: ModuloGuardado) -> str:
    partes = [f"{formato_numero(m.ancho)} × {formato_numero(m.alto)} × {formato_numero(m.profundidad)}"]
    if m.armado != "Módulo":
        partes.append(m.armado.replace("Cajonera con ", "cajonera, "))
    if m.puertas:
        partes.append(f"{m.puertas} puerta{'s' if m.puertas > 1 else ''}")
    if m.cajones:
        partes.append(f"{len(m.cajones)} cajón" if len(m.cajones) == 1 else f"{len(m.cajones)} cajones")
    if m.estantes:
        partes.append(f"{m.estantes} estante{'s' if m.estantes > 1 else ''}")
    if m.id_placa_fondo:
        partes.append("con fondo")
    if m.armado == "Módulo" and not m.lleva_techo:
        partes.append("sin techo")
    return " · ".join(partes)


def _fila(app: Aplicacion, insignia: str, titulo: str, detalle: str, estado: ft.Control | None,
          abrir, eliminar, editable: bool, filos=None) -> ft.Container:
    p = app.paleta
    if estado is not None and filos is not None:   # la etiqueta de filos abre «Piezas y filos»
        estado = ft.Container(estado, on_click=lambda _: filos(), ink=True, border_radius=20,
                              tooltip="Definir los filos")
    return ft.Container(
        content=ft.Row([
            ft.Container(ft.Text(insignia, size=13, font_family=SANS_SEMI, color=p.acento_texto), width=44, height=40,
                         border_radius=8, bgcolor=p.superficie_alta, alignment=ft.Alignment.CENTER),
            ft.Column([ft.Text(titulo, size=15, font_family=SANS_MEDIA, color=p.texto),
                       ft.Text(detalle, size=13, color=p.texto_tenue)], spacing=0, expand=True),
            *([estado] if estado else []),
            ft.TextButton(content=ft.Text("Filos" if editable else "Piezas", size=14, color=p.acento_texto),
                          on_click=lambda _: filos()) if filos else ft.Container(),
            ft.TextButton(content=ft.Text("Abrir" if editable else "Ver", size=14, color=p.acento_texto),
                          on_click=lambda _: abrir()) if abrir else ft.Container(),
            ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=p.texto_tenue, tooltip="Eliminar",
                          on_click=lambda _: eliminar(), visible=editable and eliminar is not None),
        ], spacing=12),
        padding=ft.Padding.symmetric(horizontal=12, vertical=8), border_radius=10,
    )


def _estado_filos(app: Aplicacion, piezas) -> ft.Control:
    p = app.paleta
    faltan = sum(1 for x in piezas if x.id_tipo_filo is None)
    if not piezas:
        return componentes.etiqueta_estado("Sin piezas", p.texto_tenue, p.fondo)
    if faltan:
        return componentes.etiqueta_estado(f"{faltan} sin filo", p.error_texto, p.error_fondo)
    return componentes.etiqueta_estado("✓ filos definidos", p.exito, p.superficie_alta)


def _tarjeta_mueble(app: Aplicacion, id_trabajo: int, mueble: Mueble, sueltas, editable: bool) -> ft.Container:
    p = app.paleta
    modulos, _ = app.ejecutar(app.muebles.modulos, mueble.id)
    zocalos, _ = app.ejecutar(app.muebles.zocalos, mueble.id)
    filas: list[ft.Control] = []
    for i, m in enumerate(modulos or [], 1):
        piezas, _ = app.ejecutar(app.muebles.piezas_de_modulo, m.id)
        filas.append(_fila(app, f"M{i}", m.nombre or f"Módulo {i}", resumen_modulo(m), _estado_filos(app, piezas or []),
                           lambda m=m: app.ir_a("modulo", id_mueble=mueble.id, id_modulo=m.id),
                           lambda m=m: _eliminar(app, id_trabajo, app.muebles.eliminar_modulo, m.id,
                                                 f"el módulo {m.nombre or ''}".strip()), editable,
                           filos=lambda m=m: app.ir_a("piezas", id_trabajo=id_trabajo, id_modulo=m.id)))
    for z in zocalos or []:
        piezas, _ = app.ejecutar(app.muebles.piezas_de_zocalo, z.id)
        filas.append(_fila(app, "Z", z.descripcion or "Zócalo",
                           f"{formato_numero(z.largo)} × {formato_numero(z.profundidad)} · alto {formato_numero(z.alto)}"
                           f" · {z.refuerzos} refuerzo{'s' if z.refuerzos != 1 else ''}",
                           _estado_filos(app, piezas or []),
                           (lambda z=z: dialogo_zocalo(app, id_trabajo, mueble, z)) if editable else None,
                           lambda z=z: _eliminar(app, id_trabajo, app.muebles.eliminar_zocalo, z.id, "el zócalo"),
                           editable, filos=lambda z=z: app.ir_a("piezas", id_trabajo=id_trabajo, id_zocalo=z.id)))
    for s in sueltas:
        filas.append(_fila(app, "P", s.descripcion or s.tipo,
                           f"{s.tipo} × {s.cantidad} · {formato_numero(s.medida_1)} × {formato_numero(s.medida_2)}",
                           _estado_filos(app, [s]), None,
                           lambda s=s: _eliminar(app, id_trabajo, app.muebles.eliminar_pieza, s.id, "la pieza suelta"),
                           editable, filos=lambda: app.ir_a("piezas", id_trabajo=id_trabajo)))
    if not filas:
        filas.append(ft.Text("Todavía no tiene módulos.", size=14, color=p.texto_tenue))

    def accion(texto: str, icono, al_tocar) -> ft.TextButton:
        return ft.TextButton(content=ft.Row([ft.Icon(icono, size=18, color=p.acento_texto),
                                             ft.Text(texto, size=14, color=p.acento_texto)], spacing=4, tight=True),
                             on_click=lambda _: al_tocar(), visible=editable)

    return componentes.tarjeta(ft.Column([
        ft.Row([
            ft.Column([ft.Text(mueble.nombre, size=18, font_family=SANS_SEMI, color=p.texto),
                       *([ft.Text(mueble.observaciones, size=13, color=p.texto_tenue)] if mueble.observaciones else [])],
                      spacing=0, expand=True),
            ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_color=p.texto_secundario, tooltip="Renombrar",
                          on_click=lambda _: dialogo_mueble(app, id_trabajo, mueble), visible=editable),
            ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=p.texto_tenue, tooltip="Eliminar el mueble",
                          on_click=lambda _: _eliminar(app, id_trabajo, app.muebles.eliminar_mueble, mueble.id,
                                                       f"el mueble {mueble.nombre}"), visible=editable),
        ]),
        ft.Divider(color=p.borde, height=1),
        *filas,
        ft.Row([accion("Módulo", ft.Icons.ADD, lambda: app.ir_a("modulo", id_mueble=mueble.id, id_modulo=None)),
                accion("Zócalo", ft.Icons.ADD, lambda: dialogo_zocalo(app, id_trabajo, mueble)),
                accion("Pieza suelta", ft.Icons.ADD, lambda: dialogo_pieza_suelta(app, id_trabajo, mueble))],
               spacing=4, wrap=True),
    ], spacing=8), p, padding=18)


def construir_seccion(app: Aplicacion, id_trabajo: int) -> list[ft.Control]:
    p = app.paleta
    editable = app.muebles.puede_modificarse(id_trabajo)
    muebles, error = app.ejecutar(app.muebles.muebles, id_trabajo)
    piezas, _ = app.ejecutar(app.muebles.piezas_del_trabajo, id_trabajo)
    piezas = piezas or []
    faltan = sum(1 for x in piezas if x.id_tipo_filo is None)
    cabecera = ft.Row([
        ft.Column([tema.titulo("Muebles y módulos", p, 30),
                   ft.Text(f"{sum(x.cantidad for x in piezas)} piezas"
                           + (f" · {faltan} fila{'s' if faltan != 1 else ''} sin filo definido" if faltan else "")
                           if piezas else "Cargá cada mueble y sus módulos: el sistema calcula las piezas.",
                           size=14, color=p.error_texto if faltan else p.texto_tenue)], spacing=0, expand=True),
        componentes.boton_con_icono("Piezas y filos", ft.Icons.BORDER_STYLE, p,
                                    lambda _: app.ir_a("piezas", id_trabajo=id_trabajo), principal=False,
                                    visible=bool(piezas)),
        componentes.boton_con_icono("Agregar mueble", ft.Icons.ADD, p, lambda _: dialogo_mueble(app, id_trabajo),
                                    principal=False, visible=editable),
    ], vertical_alignment=ft.CrossAxisAlignment.END, spacing=10)
    if error:
        return [cabecera, tema.aviso(error, p)]
    if not muebles:
        return [cabecera, componentes.estado_vacio(
            ft.Icons.CHAIR_OUTLINED, "Sin muebles",
            "Agregá un mueble (por ejemplo «Bajo mesada») y después sus módulos.", p,
            componentes.boton_con_icono("Agregar mueble", ft.Icons.ADD, p,
                                        lambda _: dialogo_mueble(app, id_trabajo)) if editable else None)]
    return [cabecera, *[_tarjeta_mueble(app, id_trabajo, m, [x for x in piezas if x.id_mueble == m.id], editable)
                        for m in muebles]]
