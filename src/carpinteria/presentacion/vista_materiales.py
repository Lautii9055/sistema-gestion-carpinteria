"""Materiales: placas, colores y marcas, y listones (RF-08 a RF-11.1)."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import flet as ft

from carpinteria.negocio.entidades import ColorPlaca, Liston, MarcaPlaca, Placa
from carpinteria.negocio.materiales import ESPESORES_HABITUALES_MM, formato_numero, texto_seccion
from carpinteria.presentacion import componentes, tema
from carpinteria.presentacion.tema import SANS_MEDIA, SANS_SEMI

if TYPE_CHECKING:
    from carpinteria.presentacion.app import Aplicacion

PESTANAS = [("placas", "Placas", ft.Icons.LAYERS_OUTLINED), ("colores", "Colores y marcas", ft.Icons.PALETTE_OUTLINED),
            ("listones", "Listones", ft.Icons.STRAIGHTEN), ("filos", "Filos", ft.Icons.BORDER_OUTER),
            ("lacas", "Lacas", ft.Icons.FORMAT_PAINT_OUTLINED), ("frentes", "Estilos de frente", ft.Icons.DOOR_SLIDING_OUTLINED),
            ("guias", "Guías", ft.Icons.VIEW_AGENDA_OUTLINED)]
BUSQUEDA = {"placas": "Color, código, marca o espesor (ej.: blanco 18mm)", "colores": "Color, código o marca",
            "lacas": "Color de laca, código o marca"}
ESPERA_BUSQUEDA = 0.3
FILTRO_NUMERO = ft.InputFilter(regex_string=r"^[0-9.,]{0,7}$", allow=True, replacement_string="")


def _estado(app: Aplicacion) -> dict:
    return app.recuerdos.setdefault("materiales", {"pestana": "placas", "texto": "", "bajas": False})


def _recargar(app: Aplicacion, mensaje: str | None = None) -> None:
    app.ir_a("materiales")
    if mensaje:
        componentes.aviso_flotante(app.page, mensaje, app.paleta)


def _dialogo(app: Aplicacion, titulo: str, controles: list[ft.Control], boton: str, accion,
             ancho: int = 520) -> None:
    """accion() devuelve un mensaje de error o None si salió bien."""
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


def _hacer(app: Aplicacion, funcion, *argumentos, mensaje: str) -> str | None:
    """Ejecuta, y si salió bien cierra el diálogo y recarga la pantalla."""
    _, error = app.ejecutar(funcion, *argumentos)
    if error:
        return error
    app.cerrar_dialogo()
    _recargar(app, mensaje)
    return None


def _confirmar_eliminar(app: Aplicacion, que: str, funcion, id_: int) -> None:
    p = app.paleta
    _dialogo(app, "Eliminar", [ft.Text(f"Se elimina {que}. Como nunca se usó, no afecta ningún trabajo.",
                                       size=15, color=p.texto_secundario)],
             "Eliminar", lambda: _hacer(app, funcion, id_, mensaje="Eliminado."))


def _cambiar_estado(app: Aplicacion, funcion, id_: int, activo: bool, nombre: str) -> None:
    _, error = app.ejecutar(funcion, id_, activo)
    if error:
        componentes.aviso_flotante(app.page, error, app.paleta)
        return
    _recargar(app, f"{nombre}: {'reactivado' if activo else 'dado de baja'}.")


def _acciones(app: Aplicacion, activo: bool, en_uso: bool, editar, cambiar_estado, eliminar) -> list[ft.Control]:
    p = app.paleta
    controles: list[ft.Control] = [
        ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_color=p.texto_secundario, tooltip="Editar",
                      on_click=lambda _: editar()),
        ft.TextButton(content=ft.Text("Dar de baja" if activo else "Reactivar", size=14,
                                      color=p.error_texto if activo else p.acento_texto),
                      on_click=lambda _: cambiar_estado(), height=40,
                      tooltip="Deja de ofrecerse para cargas nuevas; los trabajos anteriores lo siguen mostrando"
                      if activo else None),
    ]
    if not en_uso:
        controles.append(ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=p.texto_tenue,
                                       tooltip="Eliminar (nunca se usó)", on_click=lambda _: eliminar()))
    return controles


def _fila(app: Aplicacion, insignia: ft.Control, titulo: str, detalle: str, etiquetas: list[ft.Control],
          acciones: list[ft.Control], activo: bool) -> ft.Container:
    p = app.paleta
    return ft.Container(
        content=ft.Row([
            insignia,
            ft.Column([
                ft.Row([ft.Text(titulo, size=15, font_family=SANS_MEDIA, color=p.texto if activo else p.texto_tenue),
                        *etiquetas], spacing=8),
                ft.Text(detalle, size=13, color=p.texto_tenue),
            ], spacing=2, expand=True),
            *acciones,
        ], spacing=14),
        bgcolor=p.superficie, border=ft.Border.all(1, p.borde), border_radius=12,
        padding=ft.Padding.symmetric(horizontal=16, vertical=10),
    )


def _insignia(app: Aplicacion, texto: str, subtexto: str = "") -> ft.Container:
    p = app.paleta
    return ft.Container(
        content=ft.Column([ft.Text(texto, size=15, font_family=SANS_SEMI, color=p.acento_texto),
                           *([ft.Text(subtexto, size=10, color=p.texto_tenue)] if subtexto else [])],
                          spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                          alignment=ft.MainAxisAlignment.CENTER),
        width=56, height=48, border_radius=10, bgcolor=p.superficie_alta, alignment=ft.Alignment.CENTER)


def _etiquetas(app: Aplicacion, activo: bool, en_uso: bool, veta: bool = False) -> list[ft.Control]:
    p = app.paleta
    etiquetas = []
    if veta:
        etiquetas.append(componentes.etiqueta_estado("Con veta", p.acento_texto, p.superficie_alta))
    if not activo:
        etiquetas.append(componentes.etiqueta_estado("Dado de baja", p.texto_tenue, p.fondo))
    elif en_uso:
        etiquetas.append(componentes.etiqueta_estado("En uso", p.texto_secundario, p.fondo))
    return etiquetas


# ---------- marcas y colores ----------
def _dialogo_marca(app: Aplicacion, marca: MarcaPlaca | None = None) -> None:
    p = app.paleta
    nombre = tema.campo("Marca", p, value=marca.nombre if marca else "", autofocus=True, max_length=50,
                        hint_text="por ejemplo: Faplac, Egger, Masisa")
    _dialogo(app, "Editar marca" if marca else "Nueva marca", [nombre], "Guardar",
             lambda: _hacer(app, app.materiales.guardar_marca,
                            MarcaPlaca(marca.id if marca else None, nombre.value or "",
                                       marca.es_activo if marca else True), mensaje="Marca guardada."))


def _campos_color(app: Aplicacion, color: ColorPlaca | None = None):
    p = app.paleta
    nombre = tema.campo("Nombre del color", p, value=(color.nombre or "") if color else "", max_length=60,
                        hint_text="por ejemplo: Blanco Nieve")
    codigo = tema.campo("Código del fabricante", p, value=(color.codigo or "") if color else "", max_length=30,
                        hint_text="opcional si tiene nombre")
    veta = ft.Checkbox(label="Tiene veta (las piezas respetan el sentido)", value=color.tiene_veta if color else False,
                       active_color=p.acento, check_color=p.sobre_acento,
                       label_style=ft.TextStyle(color=p.texto_secundario, size=14))
    fila = ft.Row([ft.Container(nombre, expand=3), ft.Container(codigo, expand=2)], spacing=12,
                  vertical_alignment=ft.CrossAxisAlignment.START)
    return [fila, veta], (nombre, codigo, veta)


def _opciones_marcas(app: Aplicacion, incluir: int | None = None) -> list[tuple[str, str]]:
    marcas, _ = app.ejecutar(app.materiales.marcas, True)
    return [(str(m.id), m.nombre) for m in marcas or [] if m.es_activo or m.id == incluir]


def _dialogo_color(app: Aplicacion, color: ColorPlaca | None = None, id_marca: int | None = None) -> None:
    p = app.paleta
    opciones = _opciones_marcas(app, color.id_marca if color else None)
    if not opciones:
        componentes.aviso_flotante(app.page, "Primero cargá una marca.", p)
        return
    elegida = str(color.id_marca if color else (id_marca or opciones[0][0]))
    marca = componentes.desplegable("Marca", opciones, elegida, p)
    controles, (nombre, codigo, veta) = _campos_color(app, color)

    def guardar() -> str | None:
        datos = ColorPlaca(color.id if color else None, int(marca.value), nombre.value, codigo.value,
                           bool(veta.value), color.es_activo if color else True)
        return _hacer(app, app.materiales.guardar_color, datos, mensaje="Color guardado.")

    _dialogo(app, "Editar color" if color else "Nuevo color", [marca, *controles], "Guardar", guardar, 560)


def _vista_colores(app: Aplicacion, estado: dict) -> list[ft.Control]:
    p = app.paleta
    marcas, error = app.ejecutar(app.materiales.marcas, estado["bajas"])
    colores, error2 = app.ejecutar(app.materiales.colores, estado["texto"], None, True)
    if error or error2:
        return [tema.aviso(error or error2, p)]
    if not marcas:
        return [componentes.estado_vacio(ft.Icons.PALETTE_OUTLINED, "Todavía no hay marcas",
                                         "Empezá cargando las marcas de placa que usan en el taller.", p,
                                         componentes.boton_con_icono("Nueva marca", ft.Icons.ADD, p,
                                                                     lambda _: _dialogo_marca(app)))]
    placas, _ = app.ejecutar(app.materiales.placas, "", True)
    colores_con_placas = {pl.id_color for pl in placas or []}
    controles: list[ft.Control] = []
    for m in marcas:
        propios = [c for c in colores if c.id_marca == m.id and (estado["bajas"] or c.es_activo)]
        if estado["texto"] and not propios:
            continue
        cabecera = ft.Row([
            ft.Text(m.nombre, font_family=tema.SERIF, size=26, color=p.texto if m.es_activo else p.texto_tenue),
            *_etiquetas(app, m.es_activo, False),
            ft.Container(expand=True),
            ft.TextButton(content=ft.Row([ft.Icon(ft.Icons.ADD, size=18, color=p.acento_texto),
                                          ft.Text("Color", size=14, color=p.acento_texto)], spacing=4, tight=True),
                          on_click=lambda _, i=m.id: _dialogo_color(app, id_marca=i), visible=m.es_activo),
            *_acciones(app, m.es_activo, bool([c for c in colores if c.id_marca == m.id]),
                       lambda m=m: _dialogo_marca(app, m),
                       lambda m=m: _cambiar_estado(app, app.materiales.cambiar_estado_marca, m.id,
                                                   not m.es_activo, m.nombre),
                       lambda m=m: _confirmar_eliminar(app, f"la marca {m.nombre}", app.materiales.eliminar_marca,
                                                       m.id)),
        ], spacing=8)
        controles.append(cabecera)
        if not propios:
            controles.append(ft.Text("Sin colores cargados.", size=14, color=p.texto_tenue))
        for c in propios:
            en_uso = c.id in colores_con_placas
            controles.append(_fila(
                app, _insignia(app, (c.codigo or c.nombre or "?")[:4].upper()), c.descripcion,
                "Con veta: las piezas respetan el sentido" if c.tiene_veta else "Sin veta: las piezas se pueden rotar",
                _etiquetas(app, c.es_activo, en_uso), _acciones(
                    app, c.es_activo, en_uso, lambda c=c: _dialogo_color(app, c),
                    lambda c=c: _cambiar_estado(app, app.materiales.cambiar_estado_color, c.id, not c.es_activo,
                                                c.descripcion),
                    lambda c=c: _confirmar_eliminar(app, f"el color {c.descripcion}",
                                                    app.materiales.eliminar_color, c.id)),
                c.es_activo))
    if not controles:
        controles.append(componentes.estado_vacio(ft.Icons.SEARCH_OFF, "Sin resultados",
                                                  "Probá con el nombre o con parte del código.", p))
    return controles


# ---------- placas ----------
def _dialogo_placa(app: Aplicacion, placa: Placa | None = None) -> None:
    p = app.paleta
    opciones_marcas = _opciones_marcas(app, placa.color.id_marca if placa and placa.color else None)
    if not opciones_marcas:
        componentes.aviso_flotante(app.page, "Primero cargá una marca en «Colores y marcas».", p)
        return
    marca = componentes.desplegable("Marca", opciones_marcas,
                                    str(placa.color.id_marca) if placa and placa.color else opciones_marcas[0][0], p)
    color = componentes.desplegable("Color", [], "", p)
    color_nuevo = ft.Checkbox(label="Es un color nuevo", value=False, active_color=p.acento, check_color=p.sobre_acento,
                              label_style=ft.TextStyle(color=p.texto_secundario, size=14), visible=placa is None)
    campos_nuevo, (nombre, codigo, veta) = _campos_color(app)
    bloque_nuevo = ft.Column(campos_nuevo, spacing=12, visible=False)

    espesor = tema.campo("Espesor (mm)", p, value=formato_numero(placa.espesor_mm) if placa else "18",
                         input_filter=FILTRO_NUMERO)
    largo = tema.campo("Largo (cm)", p, value=formato_numero(placa.largo) if placa else "", input_filter=FILTRO_NUMERO,
                       helper="En el sentido de la veta")
    ancho = tema.campo("Ancho (cm)", p, value=formato_numero(placa.ancho) if placa else "", input_filter=FILTRO_NUMERO)

    def elegir_espesor(valor: str) -> None:
        espesor.value = valor
        app.page.update()

    chips = ft.Row([ft.OutlinedButton(content=ft.Text(f"{formato_numero(e)} mm", size=13, color=p.texto),
                                      on_click=lambda _, v=formato_numero(e): elegir_espesor(v), height=34,
                                      style=ft.ButtonStyle(side=ft.BorderSide(1, p.borde_fuerte),
                                                           shape=ft.RoundedRectangleBorder(radius=99)))
                    for e in ESPESORES_HABITUALES_MM], spacing=8)

    def cargar_colores(_=None) -> None:
        id_marca = int(marca.value)
        lista, _ = app.ejecutar(app.materiales.colores, "", id_marca, False)
        lista = lista or []
        if placa and placa.color and placa.color.id_marca == id_marca and all(c.id != placa.id_color for c in lista):
            lista = [placa.color, *lista]   # su color, aunque esté dado de baja
        color.options = [ft.DropdownOption(key=str(c.id), text=c.descripcion + (" · con veta" if c.tiene_veta else ""))
                         for c in lista]
        actual = str(placa.id_color) if placa else ""
        color.value = actual if any(o.key == actual for o in color.options) else (
            color.options[0].key if color.options else None)
        if placa is None and not lista:
            color_nuevo.value = True
        bloque_nuevo.visible = bool(color_nuevo.value)
        color.visible = not color_nuevo.value
        if placa is None and not largo.value:
            medidas, _ = app.ejecutar(app.materiales.medidas_habituales, id_marca)
            if medidas:   # se propone la medida que más usa la marca (RF-11)
                largo.value, ancho.value = formato_numero(medidas[0]), formato_numero(medidas[1])
        app.page.update()

    def alternar_nuevo(_) -> None:
        bloque_nuevo.visible = bool(color_nuevo.value)
        color.visible = not color_nuevo.value
        app.page.update()

    marca.on_select = cargar_colores
    color_nuevo.on_change = alternar_nuevo

    def guardar() -> str | None:
        def hacer():
            id_color = int(color.value) if color.value else None
            if color_nuevo.value:
                id_color = app.materiales.guardar_color(ColorPlaca(None, int(marca.value), nombre.value, codigo.value,
                                                                   bool(veta.value)))
            return app.materiales.guardar_placa(placa.id if placa else None, id_color, espesor.value,
                                                largo.value, ancho.value)
        return _hacer(app, hacer, mensaje="Placa guardada.")

    aviso_uso = ([tema.aviso("Esta placa ya se usa en trabajos: el color, el espesor y las medidas no se pueden cambiar.",
                             p, tipo="info")] if placa and placa.en_uso else [])
    _dialogo(app, "Editar placa" if placa else "Nueva placa", [
        *aviso_uso, marca, color, color_nuevo, bloque_nuevo,
        tema.etiqueta_superior("Espesor", p), chips, espesor,
        tema.etiqueta_superior("Placa entera", p),
        ft.Row([ft.Container(largo, expand=True), ft.Container(ancho, expand=True)], spacing=12,
               vertical_alignment=ft.CrossAxisAlignment.START),
    ], "Guardar", guardar, 580)
    cargar_colores()


def _vista_placas(app: Aplicacion, estado: dict) -> list[ft.Control]:
    p = app.paleta
    placas, error = app.ejecutar(app.materiales.placas, estado["texto"], estado["bajas"])
    if error:
        return [tema.aviso(error, p)]
    if not placas:
        if estado["texto"]:
            return [componentes.estado_vacio(ft.Icons.SEARCH_OFF, "Sin resultados",
                                             "Probá con el color, el código, la marca o el espesor (ej.: 18mm).", p)]
        return [componentes.estado_vacio(ft.Icons.LAYERS_OUTLINED, "Todavía no hay placas",
                                         "Cargá las placas que usan: marca, color, espesor y medida de la placa entera.",
                                         p, componentes.boton_con_icono("Nueva placa", ft.Icons.ADD, p,
                                                                        lambda _: _dialogo_placa(app)))]
    filas = []
    for pl in placas:
        c = pl.color
        activa = pl.es_activo and c.es_activo and c.marca_activa
        filas.append(_fila(
            app, _insignia(app, formato_numero(pl.espesor_mm), "mm"), c.descripcion,
            f"{c.marca} · placa {formato_numero(pl.largo)} × {formato_numero(pl.ancho)} cm",
            _etiquetas(app, activa, pl.en_uso, c.tiene_veta),
            _acciones(app, pl.es_activo, pl.en_uso, lambda pl=pl: _dialogo_placa(app, pl),
                      lambda pl=pl: _cambiar_estado(app, app.materiales.cambiar_estado_placa, pl.id,
                                                    not pl.es_activo, "Placa"),
                      lambda pl=pl: _confirmar_eliminar(app, f"la placa {c.descripcion} "
                                                             f"{formato_numero(pl.espesor_mm)} mm",
                                                        app.materiales.eliminar_placa, pl.id)),
            activa))
    return filas


# ---------- listones ----------
def _dialogo_liston(app: Aplicacion, liston: Liston | None = None) -> None:
    p = app.paleta
    nombre = tema.campo("Nombre", p, value=liston.nombre if liston else "Pino", max_length=50, autofocus=True)
    ancho = tema.campo("Ancho (pulgadas)", p, value=formato_numero(liston.ancho_pulgadas) if liston else "",
                       input_filter=FILTRO_NUMERO)
    alto = tema.campo("Alto (pulgadas)", p, value=formato_numero(liston.alto_pulgadas) if liston else "",
                      input_filter=FILTRO_NUMERO)
    _dialogo(app, "Editar listón" if liston else "Nuevo listón", [
        nombre, ft.Row([ft.Container(ancho, expand=True), ft.Text("×", size=20, color=p.texto_tenue),
                        ft.Container(alto, expand=True)], spacing=12),
        ft.Text('Sección en pulgadas, por ejemplo 2 × 1".', size=13, color=p.texto_tenue)],
        "Guardar", lambda: _hacer(app, app.materiales.guardar_liston, liston.id if liston else None,
                                  nombre.value or "", ancho.value, alto.value, mensaje="Listón guardado."))


def _vista_listones(app: Aplicacion, estado: dict) -> list[ft.Control]:
    p = app.paleta
    listones, error = app.ejecutar(app.materiales.listones, estado["bajas"])
    if error:
        return [tema.aviso(error, p)]
    if not listones:
        return [componentes.estado_vacio(ft.Icons.STRAIGHTEN, "Sin listones",
                                         'Cargá los listones que usan, con su sección (ej.: pino 2 × 1").', p)]
    return [_fila(app, _insignia(app, texto_seccion(x).replace(" ", "")), x.nombre, f"Sección {texto_seccion(x)}",
                  _etiquetas(app, x.es_activo, x.en_uso),
                  _acciones(app, x.es_activo, x.en_uso, lambda x=x: _dialogo_liston(app, x),
                            lambda x=x: _cambiar_estado(app, app.materiales.cambiar_estado_liston, x.id,
                                                        not x.es_activo, x.nombre),
                            lambda x=x: _confirmar_eliminar(app, f"el listón {x.nombre}",
                                                            app.materiales.eliminar_liston, x.id)),
                  x.es_activo) for x in listones]


# ---------- pantalla ----------
def construir(app: Aplicacion) -> ft.Control:
    from carpinteria.presentacion import vista_catalogo as vc   # aquí para evitar una importación circular
    p = app.paleta
    estado = _estado(app)
    pestana = estado["pestana"]

    def cambiar_pestana(clave: str) -> None:
        estado.update(pestana=clave, texto="")
        app.ir_a("materiales")

    barra = ft.Row([
        ft.Container(
            content=ft.Row([ft.Icon(icono, size=18, color=p.sobre_acento if clave == pestana else p.texto_secundario),
                            ft.Text(texto, size=14, font_family=SANS_MEDIA,
                                    color=p.sobre_acento if clave == pestana else p.texto_secundario)],
                           spacing=8, tight=True),
            bgcolor=p.acento if clave == pestana else None, border=ft.Border.all(1, p.borde_fuerte),
            border_radius=99, padding=ft.Padding.symmetric(horizontal=16, vertical=10), ink=True,
            on_click=lambda _, c=clave: cambiar_pestana(c))
        for clave, texto, icono in PESTANAS], spacing=10, run_spacing=10, wrap=True)

    nuevo = {
        "placas": ("Nueva placa", lambda _: _dialogo_placa(app)),
        "colores": ("Nueva marca", lambda _: _dialogo_marca(app)),
        "listones": ("Nuevo listón", lambda _: _dialogo_liston(app)),
        "filos": ("Nuevo filo", lambda _: vc.dialogo_filo(app)),
        "lacas": ("Nuevo color de laca", lambda _: vc.dialogo_color_laca(app)),
        "frentes": ("Nuevo estilo", lambda _: vc.dialogo_estilo(app)),
        "guias": ("Nueva guía", lambda _: vc.dialogo_guia(app)),
    }[pestana]
    acciones = [componentes.boton_con_icono(nuevo[0], ft.Icons.ADD, p, nuevo[1])]
    if pestana == "colores":
        acciones.insert(0, componentes.boton_con_icono("Nuevo color", ft.Icons.PALETTE_OUTLINED, p,
                                                       lambda _: _dialogo_color(app), principal=False))
    if pestana == "lacas":
        acciones.insert(0, componentes.boton_con_icono("Nueva marca", ft.Icons.ADD, p,
                                                       lambda _: vc.dialogo_marca_pintura(app), principal=False))

    resultados = ft.Column(spacing=10)
    construir_lista = {"placas": _vista_placas, "colores": _vista_colores, "listones": _vista_listones,
                       "filos": vc.vista_filos, "lacas": vc.vista_lacas, "frentes": vc.vista_estilos,
                       "guias": vc.vista_guias}[pestana]

    def cargar() -> None:
        resultados.controls = construir_lista(app, estado)
        app.page.update()

    busqueda = tema.campo("Buscar", p, value=estado["texto"], prefix_icon=ft.Icons.SEARCH,
                          hint_text=BUSQUEDA.get(pestana, ""), visible=pestana in BUSQUEDA)
    pedido = {"numero": 0}

    async def buscar_luego(numero: int) -> None:
        await asyncio.sleep(ESPERA_BUSQUEDA)
        if numero == pedido["numero"]:
            cargar()

    def al_tipear(_) -> None:
        estado["texto"] = busqueda.value or ""
        pedido["numero"] += 1
        app.page.run_task(buscar_luego, pedido["numero"])

    busqueda.on_change = al_tipear
    ver_bajas = ft.Switch(label="Mostrar dados de baja", value=estado["bajas"], active_color=p.acento,
                          label_text_style=ft.TextStyle(color=p.texto_secundario, size=14),
                          visible=pestana != "filos")   # los filos no tienen baja

    def al_cambiar_bajas(_) -> None:
        estado["bajas"] = bool(ver_bajas.value)
        cargar()

    ver_bajas.on_change = al_cambiar_bajas
    app.al_mostrar(cargar)

    return ft.Column([
        componentes.encabezado_seccion(
            "Catálogo", "Materiales",
            "Todo lo que usa el despiece. Lo que nunca se usó se puede eliminar; lo que ya está en trabajos "
            "se da de baja y deja de ofrecerse.",
            p, ft.Row(acciones, spacing=10, tight=True)),
        barra,
        busqueda,
        ft.Row([ft.Container(expand=True), ver_bajas]),
        resultados,
    ], spacing=16)
