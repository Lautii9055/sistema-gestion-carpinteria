"""Trabajos: listado con filtros (RF-06, RF-28) y alta de un trabajo nuevo (RF-12)."""
from __future__ import annotations

import asyncio
from datetime import date
from typing import TYPE_CHECKING

import flet as ft

from carpinteria.negocio.entidades import Cliente, DetalleTrabajo, Obra
from carpinteria.negocio.trabajos import (ESTADOS_SIN_COBRO, PERIODOS, formatear_al_escribir, formato_fecha,
                                          formato_pesos, leer_fecha, leer_monto)
from carpinteria.presentacion import componentes, tema
from carpinteria.presentacion.tema import SANS_MEDIA, SANS_SEMI

if TYPE_CHECKING:
    from carpinteria.presentacion.app import Aplicacion

ESPERA_BUSQUEDA = 0.3
TODOS = "todos"


def campos_montos(app: Aplicacion, total_inicial: str = "", sena_inicial: str = ""
                  ) -> tuple[ft.TextField, ft.TextField, ft.Text]:
    """Monto total y seña, con la seña sugerida a la vista (RF-27).

    Mientras la seña no se toque a mano, se completa sola con el porcentaje sugerido.
    """
    p = app.paleta
    porcentaje, _ = app.ejecutar(app.trabajos.porcentaje_sena)
    texto_porcentaje = f"{porcentaje.normalize():f}" if porcentaje is not None else "60"
    filtro = ft.InputFilter(regex_string=r"^[0-9., ]*$", allow=True, replacement_string="")
    total = tema.campo("Monto total (opcional)", p, value=total_inicial, prefix_icon=ft.Icons.ATTACH_MONEY,
                       hint_text="por ejemplo: 2.800.000 (decimales con coma)", input_filter=filtro)
    sena = tema.campo("Seña", p, value=sena_inicial, prefix_icon=ft.Icons.ATTACH_MONEY,
                      input_filter=filtro)
    ayuda = ft.Text("", size=13, color=p.texto_tenue)
    estado = {"sena_tocada": bool(sena_inicial)}

    def al_cambiar_total(_) -> None:
        con_puntos = formatear_al_escribir(total.value)
        if con_puntos != total.value:
            total.value = con_puntos
        try:
            monto = leer_monto(total.value)
        except Exception:
            monto = None
        if monto is None:
            ayuda.value = ""
        else:
            sugerida, _ = app.ejecutar(app.trabajos.sena_sugerida, monto)
            ayuda.value = (f"Seña sugerida ({texto_porcentaje}%): {formato_pesos(sugerida)}"
                           f"  ·  Saldo: {formato_pesos(monto - sugerida)}") if sugerida is not None else ""
            if not estado["sena_tocada"] and sugerida is not None:
                sena.value = formato_pesos(sugerida).replace("$ ", "")
        app.page.update()

    def al_cambiar_sena(_) -> None:
        con_puntos = formatear_al_escribir(sena.value)
        if con_puntos != sena.value:
            sena.value = con_puntos
            app.page.update()
        estado["sena_tocada"] = bool(sena.value)

    total.on_change = al_cambiar_total
    sena.on_change = al_cambiar_sena
    return total, sena, ayuda


def campos_entrega(p: tema.Paleta, fecha: date | None = None, aproximada: bool = False,
                   etiqueta: str = "Entrega pactada (opcional)"):
    """Fecha de entrega pactada y si lo pactado es solo la semana.

    Devuelve el control y una función leer() → (fecha, aproximada).
    """
    campo = componentes.campo_fecha(etiqueta, formato_fecha(fecha), p,
                                    helper="El día en que tiene que estar instalado.")
    semana = ft.Checkbox(label="Solo se sabe la semana", value=aproximada, active_color=p.acento,
                         check_color=p.sobre_acento, label_style=ft.TextStyle(color=p.texto_secundario, size=14))

    def actualizar_ayuda(_=None) -> None:
        campo.helper = ("Cualquier día de esa semana: se muestra «Semana del lunes»."
                        if semana.value else "El día en que tiene que estar instalado.")
        campo.update()

    semana.on_change = actualizar_ayuda

    def leer():
        return leer_fecha(campo.value, "la entrega pactada"), bool(semana.value)

    control = ft.Row([ft.Container(campo, expand=True), ft.Container(semana, padding=ft.Padding.only(top=12))],
                     spacing=12, vertical_alignment=ft.CrossAxisAlignment.START)
    return control, leer


# ---------- alta ----------
def abrir_nuevo(app: Aplicacion, cliente: Cliente | None = None, obra: Obra | None = None) -> None:
    """Nuevo trabajo. Desde la ficha llega con cliente y obra; desde el listado se eligen acá."""
    p = app.paleta
    elegido: dict = {"cliente": cliente, "obra": obra}
    caja_error = ft.Container(visible=False)
    descripcion = tema.campo("Descripción", p, autofocus=cliente is not None, max_length=200,
                             hint_text="por ejemplo: Cocina completa, Placard dormitorio")
    total, sena, ayuda = campos_montos(app)
    entrega, leer_entrega = campos_entrega(p)
    observaciones = tema.campo("Observaciones (opcional)", p, multiline=True, min_lines=2, max_lines=4,
                               max_length=500)
    fecha_presupuesto = componentes.campo_fecha("Fecha de presupuesto", formato_fecha(date.today()), p,
                                                helper="Si lo anotás tarde, poné la fecha real.")

    # --- elección del cliente y la obra ---
    zona_cliente = ft.Column(spacing=10, tight=True)
    buscador = tema.campo("Cliente", p, autofocus=True, prefix_icon=ft.Icons.SEARCH,
                          hint_text="Buscá por nombre, teléfono o dirección")
    sugerencias = ft.Column(spacing=4, tight=True)
    obras_cliente = componentes.desplegable("Obra", [], "", p)
    pedido = {"numero": 0}

    def mostrar_elegido() -> None:
        c = elegido["cliente"]
        if c is None:
            zona_cliente.controls = [buscador, sugerencias]
            return
        cambiar = ft.TextButton(content=ft.Text("Cambiar", color=p.acento_texto, size=14),
                                on_click=lambda _: (elegido.update(cliente=None, obra=None),
                                                    mostrar_elegido(), app.page.update()),
                                visible=cliente is None)
        fila_cliente = ft.Row([componentes.avatar(c.nombre_completo, p, 36),
                               ft.Text(c.nombre_completo, font_family=SANS_MEDIA, size=16, color=p.texto,
                                       expand=True), cambiar], spacing=12)
        if obra is not None:
            zona_cliente.controls = [fila_cliente, componentes.dato(
                ft.Icons.HOME_WORK_OUTLINED, f"{obra.titulo} · {obra.direccion}, {obra.localidad}", p)]
            return
        lista, error = app.ejecutar(app.clientes.ficha, c.id)
        obras = [o.obra for o in lista.obras] if lista else []
        if error or not obras:
            elegido["obra"] = None
            zona_cliente.controls = [fila_cliente, tema.aviso(
                error or "Este cliente no tiene obras cargadas. Agregá la dirección desde su ficha.", p)]
            return
        obras_cliente.options = [ft.DropdownOption(key=str(o.id), text=f"{o.titulo} · {o.localidad}"
                                                   if o.alias else f"{o.direccion}, {o.localidad}")
                                 for o in obras]
        obras_cliente.value = str(obras[0].id)
        elegido["obra"] = obras[0]
        obras_cliente.on_select = lambda _: elegido.update(
            obra=next(o for o in obras if str(o.id) == obras_cliente.value))
        zona_cliente.controls = [fila_cliente, obras_cliente]

    def elegir(c: Cliente) -> None:
        elegido["cliente"] = c
        mostrar_elegido()
        app.page.update()
        descripcion.focus()

    def cargar_sugerencias() -> None:
        texto = buscador.value or ""
        if not texto.strip():
            sugerencias.controls = []
        else:
            lista, error = app.ejecutar(app.clientes.buscar, texto)
            if error:
                sugerencias.controls = [tema.aviso(error, p)]
            elif not lista:
                sugerencias.controls = [ft.Text("No hay clientes con esos datos. Si es nuevo, cargalo "
                                                "primero en Clientes.", size=13, color=p.texto_tenue)]
            else:
                sugerencias.controls = [
                    ft.Container(
                        content=ft.Row([componentes.avatar(r.cliente.nombre_completo, p, 32),
                                        ft.Column([ft.Text(r.cliente.nombre_completo, size=15, color=p.texto),
                                                   ft.Text(r.primera_direccion or r.cliente.telefono, size=12,
                                                           color=p.texto_tenue)], spacing=0, expand=True)],
                                       spacing=10),
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6), border_radius=10,
                        on_click=lambda _, c=r.cliente: elegir(c), ink=True,
                    )
                    for r in lista[:5]
                ]
        app.page.update()

    async def buscar_luego(numero: int) -> None:
        await asyncio.sleep(ESPERA_BUSQUEDA)
        if numero == pedido["numero"]:
            cargar_sugerencias()

    def al_tipear(_) -> None:
        pedido["numero"] += 1
        app.page.run_task(buscar_luego, pedido["numero"])

    buscador.on_change = al_tipear
    mostrar_elegido()

    def guardar(_=None) -> None:
        def crear():
            fecha_entrega, aproximada = leer_entrega()
            return app.trabajos.crear(
                app.sesion, elegido["obra"].id if elegido["obra"] else None, descripcion.value or "",
                leer_monto(total.value, "el monto total"), leer_monto(sena.value, "la seña"),
                observaciones.value, leer_fecha(fecha_presupuesto.value, "la fecha de presupuesto"),
                fecha_entrega, aproximada)

        if elegido["cliente"] is None:
            nuevo, error = None, "Elegí el cliente del trabajo."
        else:
            nuevo, error = app.ejecutar(crear)
        if error:
            caja_error.content = tema.aviso(error, p)
            caja_error.visible = True
            app.page.update()
            return
        app.cerrar_dialogo()
        app.ir_a("trabajo", id_trabajo=nuevo)
        componentes.aviso_flotante(app.page, "Trabajo creado como presupuestado.", p)

    app.mostrar_dialogo(componentes.dialogo(
        p, "Nuevo trabajo",
        ft.Column([caja_error, zona_cliente, ft.Divider(color=p.borde),
                   ft.Row([ft.Container(descripcion, expand=3), ft.Container(fecha_presupuesto, expand=2)],
                          spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
                   ft.Row([ft.Container(total, expand=True), ft.Container(sena, expand=True)], spacing=12),
                   ayuda, entrega, observaciones],
                  spacing=14, tight=True, scroll=ft.ScrollMode.AUTO),
        [componentes.boton_cancelar(p, lambda _: app.cerrar_dialogo()),
         tema.boton_principal("Crear trabajo", p, guardar)],
        ancho=580,
    ))


# ---------- listado ----------
def fila_trabajo(app: Aplicacion, d: DetalleTrabajo, mostrar_cliente: bool = True) -> ft.Container:
    p = app.paleta
    t = d.trabajo
    detalle = (f"{d.cliente.nombre_completo} · {d.obra.titulo}" if mostrar_cliente
               else f"Presupuesto: {formato_fecha(t.fecha_presupuesto)}")
    importes: list[ft.Control] = []
    if t.monto_total is not None:
        importes.append(ft.Text(formato_pesos(t.monto_total), size=15, color=p.texto,
                                text_align=ft.TextAlign.RIGHT))
        if d.estado.nombre not in ESTADOS_SIN_COBRO and t.pendiente_de_cobro > 0:
            importes.append(ft.Text(f"Falta cobrar {formato_pesos(t.pendiente_de_cobro)}", size=12,
                                    color=p.acento_texto, text_align=ft.TextAlign.RIGHT))
    else:
        importes.append(ft.Text("Sin monto", size=13, color=p.texto_tenue))

    return ft.Container(
        content=ft.Row([
            ft.Container(ft.Text(f"#{t.id}", size=13, font_family=SANS_SEMI, color=p.acento_texto),
                         width=52, height=40, border_radius=8, bgcolor=p.superficie_alta,
                         alignment=ft.Alignment.CENTER),
            ft.Column([
                ft.Text(t.descripcion, font_family=SANS_MEDIA, size=16, color=p.texto, max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(detalle, size=13, color=p.texto_tenue, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ], spacing=2, expand=True),
            componentes.etiqueta_estado_trabajo(d.estado.nombre, p),
            ft.Column(importes, spacing=0, horizontal_alignment=ft.CrossAxisAlignment.END, width=150),
            ft.Icon(ft.Icons.CHEVRON_RIGHT, color=p.texto_tenue),
        ], spacing=16),
        bgcolor=p.superficie, border=ft.Border.all(1, p.borde), border_radius=14,
        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        on_click=lambda _: app.ir_a("trabajo", id_trabajo=t.id), ink=True,
        tooltip="Ver el trabajo",
    )


def construir(app: Aplicacion) -> ft.Control:
    p = app.paleta
    estado = app.recuerdos.setdefault("trabajos", {"texto": "", "estado": TODOS, "periodo": "Todos",
                                                    "por_cobrar": False})
    estados, error_estados = app.ejecutar(app.trabajos.estados)

    busqueda = tema.campo("Buscar", p, value=estado["texto"], autofocus=True, prefix_icon=ft.Icons.SEARCH,
                          hint_text="Número, descripción, cliente, dirección o estado")
    filtro_estado = componentes.desplegable(
        "Estado", [(TODOS, "Todos")] + [(str(e.id), e.nombre) for e in estados or []], estado["estado"], p)
    filtro_periodo = componentes.desplegable("Fecha de presupuesto", [(k, k) for k in PERIODOS], estado["periodo"], p)
    por_cobrar = ft.Switch(label="Solo con cobros pendientes", value=estado["por_cobrar"],
                           active_color=p.acento,
                           label_text_style=ft.TextStyle(color=p.texto_secundario, size=14))
    resultados = ft.Column(spacing=10)
    contador = ft.Text("", size=13, color=p.texto_tenue)
    total_pendiente = ft.Text("", size=13, color=p.acento_texto)

    def cargar() -> None:
        lista, error = app.ejecutar(
            app.trabajos.buscar, estado["texto"],
            None if estado["estado"] == TODOS else int(estado["estado"]),
            estado["por_cobrar"], estado["periodo"])
        hay_filtros = (estado["texto"] or estado["estado"] != TODOS or estado["por_cobrar"]
                       or estado["periodo"] != "Todos")
        total_pendiente.value = ""
        if error or error_estados:
            resultados.controls = [tema.aviso(error or error_estados, p)]
            contador.value = ""
        elif not lista and not hay_filtros:
            resultados.controls = [componentes.estado_vacio(
                ft.Icons.TABLE_CHART_OUTLINED, "Todavía no hay trabajos",
                "Creá el primero eligiendo el cliente y la obra.", p,
                componentes.boton_con_icono("Nuevo trabajo", ft.Icons.ADD, p, lambda _: abrir_nuevo(app)))]
            contador.value = ""
        elif not lista:
            resultados.controls = [componentes.estado_vacio(
                ft.Icons.SEARCH_OFF, "Sin resultados", "Probá con menos palabras o sacando algún filtro.", p)]
            contador.value = ""
        else:
            resultados.controls = [fila_trabajo(app, d) for d in lista]
            contador.value = (f"{len(lista)} trabajo{'s' if len(lista) != 1 else ''}"
                              + (" (se muestran los primeros)" if len(lista) >= 100 else ""))
            if estado["por_cobrar"]:
                suma = sum(d.trabajo.pendiente_de_cobro for d in lista)
                total_pendiente.value = f"Total por cobrar: {formato_pesos(suma)}"
        app.page.update()

    pedido = {"numero": 0}

    async def buscar_luego(numero: int) -> None:
        await asyncio.sleep(ESPERA_BUSQUEDA)
        if numero == pedido["numero"]:
            cargar()

    def al_tipear(_) -> None:
        estado["texto"] = busqueda.value or ""
        pedido["numero"] += 1
        app.page.run_task(buscar_luego, pedido["numero"])

    def al_filtrar(_) -> None:
        estado.update(estado=filtro_estado.value or TODOS, periodo=filtro_periodo.value or "Todos",
                      por_cobrar=bool(por_cobrar.value))
        cargar()

    busqueda.on_change = al_tipear
    busqueda.on_submit = lambda _: cargar()
    filtro_estado.on_select = al_filtrar
    filtro_periodo.on_select = al_filtrar
    por_cobrar.on_change = al_filtrar
    app.al_mostrar(cargar)

    return ft.Column([
        componentes.encabezado_seccion(
            "Taller", "Trabajos",
            "Todos los trabajos con su estado y lo que falta cobrar.", p,
            componentes.boton_con_icono("Nuevo trabajo", ft.Icons.ADD, p, lambda _: abrir_nuevo(app))),
        busqueda,
        ft.ResponsiveRow([
            ft.Container(filtro_estado, col={"xs": 12, "md": 4}),
            ft.Container(filtro_periodo, col={"xs": 12, "md": 4}),
            ft.Container(por_cobrar, col={"xs": 12, "md": 4}, alignment=ft.Alignment.CENTER_LEFT, height=56),
        ], spacing=12, run_spacing=12),
        ft.Row([contador, ft.Container(expand=True), total_pendiente]),
        resultados,
    ], spacing=16)
