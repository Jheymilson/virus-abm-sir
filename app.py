"""Interfaz Solara para observar y controlar el modelo SIR."""

from pathlib import Path

import networkx as nx
import seaborn as sns
import solara
from ipywidgets import Layout, Play
from matplotlib.figure import Figure

from modelo import ModeloVirus


COLORES = {"S": "#198754", "I": "#d22f43", "R": "#2776c7"}
SALIDA = Path(__file__).resolve().parent


def figura_red(modelo, posiciones):
    fig = Figure(figsize=(9, 5.2), dpi=110)
    ax = fig.subplots()
    nx.draw_networkx_edges(
        modelo.red, posiciones, ax=ax, edge_color="#b8c5c8", alpha=0.46, width=0.8
    )
    nx.draw_networkx_nodes(
        modelo.red,
        posiciones,
        ax=ax,
        nodelist=list(modelo.red.nodes),
        node_color=[COLORES[modelo.personas_por_nodo[n].estado] for n in modelo.red.nodes],
        node_size=[
            (95 if modelo.num_personas <= 100 else 62)
            if modelo.personas_por_nodo[n].estado == "I"
            else (70 if modelo.num_personas <= 100 else 47)
            for n in modelo.red.nodes
        ],
        linewidths=0.5,
        edgecolors="white",
    )
    ax.set_axis_off()
    ax.margins(0.08)
    fig.tight_layout()
    return fig


def figura_sir(modelo):
    datos = modelo.datacollector.get_model_vars_dataframe()
    fig = Figure(figsize=(6.5, 3.4), dpi=110)
    ax = fig.subplots()
    for columna, estado in (("Sanos", "S"), ("Infectados", "I"), ("Recuperados", "R")):
        ax.plot(datos.index, datos[columna], color=COLORES[estado], label=columna, linewidth=2.4)
        ax.scatter(datos.index[-1], datos[columna].iloc[-1], color=COLORES[estado], s=32, zorder=3)
    ax.fill_between(datos.index, datos["Infectados"], color=COLORES["I"], alpha=0.07)
    ax.set(xlabel="Día", ylabel="Personas", xlim=(0, max(1, modelo.max_dias)), ylim=(0, modelo.num_personas))
    ax.grid(axis="y", color="#dce4e5", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["bottom", "left"]].set_color("#c4ced1")
    ax.tick_params(colors="#4c5a5e", labelsize=9)
    ax.legend(loc="upper right", ncol=3, fontsize=8, frameon=False)
    fig.tight_layout()
    return fig


def guardar_resultados(modelo, posiciones):
    """Genera el CSV y las tres figuras solicitadas para el informe."""
    datos = modelo.datacollector.get_model_vars_dataframe()
    datos.index.name = "Dia"
    datos = datos.reset_index()
    datos.to_csv(SALIDA / "resultados_simulacion.csv", index=False)

    with sns.axes_style("whitegrid"):
        fig = Figure(figsize=(10, 5), dpi=150)
        ax = fig.subplots()
        for columna, estado in (("Sanos", "S"), ("Infectados", "I"), ("Recuperados", "R")):
            sns.lineplot(data=datos, x="Dia", y=columna, ax=ax, color=COLORES[estado], label=columna)
        ax.set(xlabel="Día", ylabel="Personas", title="Curva epidémica SIR")
        fig.tight_layout()
        fig.savefig(SALIDA / "grafica_curva_epidemica.png")

    fig = figura_red(modelo, posiciones)
    fig.savefig(SALIDA / "grafica_red_final.png")

    fig = Figure(figsize=(10, 5), dpi=150)
    ax = fig.subplots()
    ax.stackplot(
        datos["Dia"], datos["Sanos"], datos["Infectados"], datos["Recuperados"],
        labels=["Sanos", "Infectados", "Recuperados"],
        colors=[COLORES["S"], COLORES["I"], COLORES["R"]], alpha=0.8,
    )
    ax.set(xlabel="Día", ylabel="Personas", title="Distribución de estados")
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(SALIDA / "grafica_apilada.png")


@solara.component
def Page():
    # El estado es local a esta página: cada sesión tiene su propia simulación.
    inicial = solara.use_memo(lambda: ModeloVirus(), [])
    modelo, set_modelo = solara.use_state(inicial)
    revision, set_revision = solara.use_state(0)
    estado = solara.use_reactive("DETENIDA")
    aviso = solara.use_reactive("")
    velocidad = solara.use_reactive(1.0)

    poblacion = solara.use_reactive(100)
    iniciales = solara.use_reactive(5)
    contagio = solara.use_reactive(0.15)
    recuperacion = solara.use_reactive(7)
    conexiones = solara.use_reactive(6)
    reconexion = solara.use_reactive(0.1)
    max_dias = solara.use_reactive(50)
    semilla = solara.use_reactive(42)

    posiciones = solara.use_memo(
        lambda: nx.spring_layout(modelo.red, seed=modelo.seed), [modelo]
    )
    reloj_ref = solara.use_memo(lambda: {"widget": None}, [modelo])
    reloj_elemento = Play.element(
        value=modelo.dia,
        min=0,
        max=modelo.max_dias,
        interval=int(1000 / velocidad.value),
        layout=Layout(display="none"),
    ).key(id(modelo))

    def avanzar():
        if not modelo.running:
            return
        modelo.step()
        set_revision(lambda n: n + 1)
        if not modelo.running:
            reloj_ref["widget"].playing = False
            estado.value = "FINALIZADA"

    # Play entrega un pulso por día desde el navegador, sin bloquear la página.
    def conectar_reloj():
        reloj = solara.get_widget(reloj_elemento)
        reloj_ref["widget"] = reloj

        def al_cambiar(cambio):
            if estado.value == "EJECUTÁNDOSE" and cambio["new"] > modelo.dia:
                avanzar()

        reloj.observe(al_cambiar, names="value")
        def desconectar():
            reloj.unobserve(al_cambiar, names="value")
            reloj.playing = False

        return desconectar

    solara.use_effect(conectar_reloj, dependencies=[modelo])

    def iniciar():
        if modelo.running:
            aviso.value = ""
            estado.value = "EJECUTÁNDOSE"
            reloj_ref["widget"].playing = True

    def pausar():
        estado.value = "PAUSADA"
        reloj_ref["widget"].playing = False

    def siguiente():
        pausar()
        avanzar()  # Un clic llama exactamente una vez a modelo.step().
        reloj_ref["widget"].value = modelo.dia

    def reiniciar():
        try:
            nuevo = ModeloVirus(
                num_personas=poblacion.value,
                num_infectados_iniciales=iniciales.value,
                probabilidad_contagio=contagio.value,
                dias_recuperacion=recuperacion.value,
                conexiones=conexiones.value,
                reconexion=reconexion.value,
                max_dias=max_dias.value,
                seed=semilla.value,
            )
        except (TypeError, ValueError) as exc:
            aviso.value = str(exc)
            return
        reloj_ref["widget"].playing = False
        estado.value = "DETENIDA" if nuevo.running else "FINALIZADA"
        aviso.value = ""
        set_modelo(nuevo)

    def guardar():
        try:
            guardar_resultados(modelo, posiciones)
            aviso.value = f"CSV y gráficas guardados en {SALIDA}"
        except OSError as exc:
            aviso.value = f"No se pudo guardar: {exc}"

    conteos = modelo.conteos()
    contagiados = conteos["I"] + conteos["R"]
    progreso = 100 * modelo.dia / modelo.max_dias
    estado_clase = {
        "DETENIDA": "idle",
        "EJECUTÁNDOSE": "running",
        "PAUSADA": "paused",
        "FINALIZADA": "finished",
    }[estado.value]
    pendientes = (
        poblacion.value,
        iniciales.value,
        contagio.value,
        recuperacion.value,
        conexiones.value,
        reconexion.value,
        max_dias.value,
        semilla.value,
    ) != (
        modelo.num_personas,
        modelo.num_infectados_iniciales,
        modelo.probabilidad_contagio,
        modelo.dias_recuperacion,
        modelo.conexiones,
        modelo.reconexion,
        modelo.max_dias,
        modelo.seed,
    )

    solara.Title("Virus en la ciudad | ABM")
    solara.Style(SALIDA / "ui.css")
    with solara.Column(classes=["virus-app"]):
        solara.HTML(
            tag="div",
            classes=["page-heading"],
            unsafe_innerHTML=(
                '<div><span class="eyebrow">SIMULACIÓN BASADA EN AGENTES</span>'
                '<h1>Virus en la ciudad</h1></div>'
                f'<span class="status status-{estado_clase}">{estado.value}</span>'
            ),
        )
        solara.HTML(
            tag="div",
            classes=["metrics"],
            unsafe_innerHTML=f"""
                <div class="metric metric-day"><span>DÍA ACTUAL</span>
                    <strong>{modelo.dia:02d}<small> / {modelo.max_dias}</small></strong></div>
                <div class="metric metric-s"><span>SANOS</span><strong>{conteos["S"]}</strong></div>
                <div class="metric metric-i"><span>INFECTADOS</span><strong>{conteos["I"]}</strong></div>
                <div class="metric metric-r"><span>RECUPERADOS</span><strong>{conteos["R"]}</strong></div>
                <div class="metric metric-total"><span>POBLACIÓN</span><strong>{modelo.num_personas}</strong></div>
            """,
        )
        solara.HTML(
            tag="div",
            classes=["day-progress"],
            unsafe_innerHTML=f'<div style="width: {progreso:.1f}%"></div>',
        )

        with solara.ColumnsResponsive(12, large=[9, 3], classes=["control-band"], gutters_dense=True):
            with solara.Row(classes=["control-actions"]):
                solara.Button(
                    "Iniciar / continuar", icon_name="mdi-play", on_click=iniciar,
                    disabled=not modelo.running or estado.value == "EJECUTÁNDOSE",
                    classes=["action-button", "action-primary"],
                )
                solara.Button(
                    "Pausar", icon_name="mdi-pause", on_click=pausar,
                    disabled=estado.value != "EJECUTÁNDOSE", classes=["action-button"],
                )
                solara.Button(
                    "Siguiente día", icon_name="mdi-skip-next", on_click=siguiente,
                    disabled=not modelo.running, classes=["action-button"],
                )
                solara.Button(
                    "Reiniciar", icon_name="mdi-restart", on_click=reiniciar,
                    classes=["action-button"],
                )
                solara.Button(
                    "Guardar", icon_name="mdi-download", on_click=guardar,
                    classes=["action-button", "action-save"],
                )
            with solara.Column(classes=["speed-control"]):
                solara.HTML(
                    tag="div", classes=["speed-heading"],
                    unsafe_innerHTML=f'<span>VELOCIDAD</span><strong>{velocidad.value:g}x</strong>',
                )
                solara.SliderValue("", value=velocidad, values=[0.25, 0.5, 1.0, 2.0, 4.0])
        reloj_elemento

        if aviso.value:
            solara.Info(aviso.value)
        if estado.value == "FINALIZADA":
            motivo = "no quedan personas infectadas" if conteos["I"] == 0 else "se alcanzó el máximo de días"
            solara.Success(
                f"Simulación finalizada: {motivo}. Duración: {modelo.dia} días. "
                f"Pico: {modelo.pico_infectados} (día {modelo.dia_pico}). "
                f"Contagiados: {contagiados}/{modelo.num_personas} "
                f"({100 * contagiados / modelo.num_personas:.1f} %)."
            )

        with solara.ColumnsResponsive(12, large=[8, 4], classes=["dashboard-grid"], gutters_dense=True):
            with solara.Column(classes=["network-section"]):
                solara.HTML(
                    tag="div", classes=["section-heading"],
                    unsafe_innerHTML=(
                        '<div><span class="section-kicker">CONTACTOS</span>'
                        '<h2>Red de personas</h2></div>'
                        f'<span class="section-count">{modelo.red.number_of_edges()} conexiones</span>'
                    ),
                )
                with solara.Column(classes=["network-figure"]):
                    solara.FigureMatplotlib(figura_red(modelo, posiciones), dependencies=[modelo, revision])
                solara.HTML(
                    tag="div", classes=["legend"],
                    unsafe_innerHTML=(
                        '<span><i class="dot dot-s"></i>Sano</span>'
                        '<span><i class="dot dot-i"></i>Infectado</span>'
                        '<span><i class="dot dot-r"></i>Recuperado</span>'
                    ),
                )
            with solara.Column(classes=["side-section"]):
                solara.HTML(
                    tag="div", classes=["section-heading"],
                    unsafe_innerHTML=(
                        '<div><span class="section-kicker">EVOLUCIÓN</span>'
                        '<h2>Curva SIR</h2></div>'
                    ),
                )
                with solara.Column(classes=["trend-figure"]):
                    solara.FigureMatplotlib(figura_sir(modelo), dependencies=[modelo, revision])
                solara.HTML(
                    tag="div", classes=["daily-activity"],
                    unsafe_innerHTML=(
                        f'<div><span>CONTAGIOS HOY</span><strong>+{modelo.nuevos_contagios}</strong></div>'
                        f'<div><span>RECUPERADOS HOY</span><strong>+{modelo.nuevos_recuperados}</strong></div>'
                    ),
                )
                solara.HTML(
                    tag="div", classes=["section-heading config-heading"],
                    unsafe_innerHTML=(
                        '<div><span class="section-kicker">ESCENARIO</span>'
                        '<h2>Parámetros</h2></div>'
                        + ('<span class="pending">Cambios pendientes</span>' if pendientes else '')
                    ),
                )
                with solara.Column(classes=["parameter-fields"]):
                    solara.InputInt("Población", value=poblacion, continuous_update=True, dense=True)
                    solara.InputInt("Infectados iniciales", value=iniciales, continuous_update=True, dense=True)
                    solara.InputFloat("Probabilidad de contagio", value=contagio, continuous_update=True, dense=True)
                    solara.InputInt("Días para recuperación", value=recuperacion, continuous_update=True, dense=True)
                    solara.InputInt("Conexiones por persona (par)", value=conexiones, continuous_update=True, dense=True)
                    solara.InputFloat("Probabilidad de reconexión", value=reconexion, continuous_update=True, dense=True)
                    solara.InputInt("Máximo de días", value=max_dias, continuous_update=True, dense=True)
                    solara.InputInt("Semilla aleatoria", value=semilla, continuous_update=True, dense=True)
                    solara.Button(
                        "Aplicar y reiniciar", icon_name="mdi-restart", on_click=reiniciar,
                        classes=["action-button", "apply-button"], disabled=not pendientes,
                    )
