import tempfile
from pathlib import Path

import polars as pl
import streamlit as st

from energias.solar.graficadorSolar import GraficadorSolar
from energias.solar.recursoSolar import RecursoSolar
from energias.solar.termica.fChartAcs import SistemaFChart

# interfaz/pages/3_SolarTermica.py -> raíz del repositorio
carpetaRaiz = Path(__file__).resolve().parents[2]
carpetaData = carpetaRaiz / "data" / "solar"
carpetaOutputs = carpetaRaiz / "outputs" / "solar"
formatos = ("png", "svg")


@st.cache_resource(show_spinner="Leyendo el TMY y calculando la posición del sol...")
def obtenerRecurso(rutaTmy: str, acimutPanel: float, usarCenitArchivo: bool) -> RecursoSolar:
    return RecursoSolar(Path(rutaTmy), acimutPanel=acimutPanel, usarCenitArchivo=usarCenitArchivo)


@st.cache_data(show_spinner=False)
def barridoInclinacion(rutaTmy: str, acimutPanel: float, usarCenitArchivo: bool) -> pl.DataFrame:
    return obtenerRecurso(rutaTmy, acimutPanel, usarCenitArchivo).barridoInclinacion()


@st.cache_data(show_spinner="Generando las gráficas del recurso solar...")
def figurasRecurso(rutaTmy: str, acimutPanel: float, usarCenitArchivo: bool, inclinacion: float, componenteMensual: str) -> dict:
    """{nombre: {formato: bytes}} de las gráficas del recurso solar."""
    recurso = obtenerRecurso(rutaTmy, acimutPanel, usarCenitArchivo)
    graficador = GraficadorSolar()
    dfBarrido = barridoInclinacion(rutaTmy, acimutPanel, usarCenitArchivo)
    optima = dfBarrido.sort("RadiacionAnual_kWhm2", descending=True).row(0, named=True)["Inclinacion_grados"]
    plano = recurso.calcularPlano(inclinacion)
    figuras = {
        "barridoInclinacion": graficador.crearFiguraBarridoInclinacion(
            dfBarrido, optima, {"Latitud + 23,5°": min(recurso.latitud + 23.5, 90), "Inclinación usada": inclinacion}
        ),
        "radiacionMensualPlano": graficador.crearFiguraRadiacionMensual(recurso.radiacionMensual(inclinacion), inclinacion),
        "perfilHorarioPlano": graficador.crearFiguraPerfilHorario(
            recurso.perfilHorario(plano), list(RecursoSolar.componentesInclinadas),
            f"Irradiancia promedio por hora en el plano de {inclinacion:g}°",
        ),
        "perfilHorarioHorizontal": graficador.crearFiguraPerfilHorario(
            recurso.perfilHorario(plano, componentes=RecursoSolar.componentesHorizontales),
            list(RecursoSolar.componentesHorizontales), "Irradiancia horizontal promedio por hora",
        ),
        "perfilHorarioMensual": graficador.crearFiguraPerfilHorarioMensual(
            recurso.perfilHorario(plano, componentes=[componenteMensual], porMes=True), componenteMensual
        ),
        "radiacionDiaria": graficador.crearFiguraRadiacionDiaria(
            recurso.radiacionDiaria(plano), ["Gbi_kWhm2dia", "Gdi_kWhm2dia", "Gri_kWhm2dia", "GTI_kWhm2dia"]
        ),
    }
    return {nombre: {formato: graficador.figuraABytes(fig, formato) for formato in formatos} for nombre, fig in figuras.items()}


@st.cache_data(show_spinner="Generando las gráficas del F-Chart...")
def figurasFChart(filasMensual: list, filasCurva: list, area: float, fraccion: float, fraccionMinima: float, fraccionMaxima: float) -> dict:
    graficador = GraficadorSolar()
    figuras = {
        "fChartMensual": graficador.crearFiguraFChartMensual(pl.DataFrame(filasMensual)),
        "fChartFraccionArea": graficador.crearFiguraFraccionArea(pl.DataFrame(filasCurva), area, fraccion, fraccionMinima, fraccionMaxima),
    }
    return {nombre: {formato: graficador.figuraABytes(fig, formato) for formato in formatos} for nombre, fig in figuras.items()}


class InterfazSolarTermica:
    """Página de la solar térmica: recurso solar del TMY y dimensionamiento de ACS por F-Chart.

    El cálculo se rehace en cada cambio de las entradas; el TMY y las gráficas se guardan en caché.
    Las claves de st.session_state llevan el prefijo de la tecnología ('solarTermica_').
    """

    prefijoEstado = "solarTermica_"
    nombresCorrelacion = {"klein": "Klein, Beckman y Duffie (por defecto)", "informe": "Exponencial del informe del curso"}
    nombresFiguras = {
        "barridoInclinacion": "Radiación anual frente a la inclinación",
        "radiacionMensualPlano": "Radiación mensual en el plano y temperatura",
        "perfilHorarioPlano": "Perfil horario en el plano",
        "perfilHorarioHorizontal": "Perfil horario horizontal",
        "perfilHorarioMensual": "Perfil horario por mes",
        "radiacionDiaria": "Radiación diaria",
    }

    @classmethod
    def clave(cls, nombre: str) -> str:
        """Clave de st.session_state (o de un widget) con el prefijo de la tecnología."""
        return f"{cls.prefijoEstado}{nombre}"

    # ------------------------------------------------------------------
    # Entradas
    # ------------------------------------------------------------------
    def elegirTmy(self, barra):
        """Ruta del TMY elegido (carpeta data/solar o archivo subido), o None."""
        origen = barra.radio("Archivo TMY de NSRDB", ["Carpeta data/solar", "Subir archivo"], horizontal=True, key=self.clave("origenTmy"))
        if origen.startswith("Carpeta"):
            archivos = sorted(archivo.name for archivo in carpetaData.glob("*.csv"))
            if not archivos:
                barra.warning("No hay archivos .csv en data/solar.")
                return None
            return str(carpetaData / barra.selectbox("TMY", archivos, key=self.clave("archivoTmy")))
        archivoSubido = barra.file_uploader("TMY (.csv de NSRDB)", type=["csv"], key=self.clave("tmySubido"))
        if archivoSubido is None:
            return None
        ruta = Path(tempfile.gettempdir()) / f"plataformaEnergias_{archivoSubido.file_id}.csv"
        if not ruta.exists():
            ruta.write_bytes(archivoSubido.getvalue())
        return str(ruta)

    def mostrarBarraLateral(self) -> dict:
        barra = st.sidebar
        barra.title("Parámetros de la solar térmica")

        barra.subheader("Recurso solar")
        rutaTmy = self.elegirTmy(barra)
        acimutPanel = barra.number_input("Acimut de los colectores (°, 180 = sur)", min_value=0.0, max_value=359.0, value=180.0, step=5.0, key=self.clave("acimutPanel"))
        modoInclinacion = barra.radio("Inclinación", ["Óptima anual", "Manual"], horizontal=True, key=self.clave("modoInclinacion"))
        inclinacionManual = None
        if modoInclinacion == "Manual":
            inclinacionManual = barra.slider("Inclinación (°)", min_value=0, max_value=90, value=20, key=self.clave("inclinacion"))
        usarCenitArchivo = barra.checkbox("Usar el cenit del TMY", value=True, key=self.clave("usarCenitArchivo"))

        barra.subheader("Demanda de ACS")
        numeroHabitaciones = barra.number_input("Habitaciones", min_value=1, value=30, step=1, key=self.clave("numeroHabitaciones"))
        ocupacion = barra.number_input("Personas por habitación", min_value=0.1, value=2.0, step=0.5, key=self.clave("ocupacion"))
        consumo = barra.number_input("Consumo (L/persona·día)", min_value=1.0, value=50.0, step=5.0, key=self.clave("consumo"))
        temperaturaUso = barra.number_input("Temperatura de uso (°C)", min_value=1.0, max_value=99.0, value=45.0, step=1.0, key=self.clave("temperaturaUso"))
        temperaturaRed = barra.number_input("Temperatura de la red (°C)", min_value=0.0, max_value=98.0, value=15.0, step=1.0, key=self.clave("temperaturaRed"))

        barra.subheader("Colector")
        areaColector = barra.number_input("Área bruta por colector (m²)", min_value=0.1, value=2.0, step=0.1, key=self.clave("areaColector"))
        eficienciaOptica = barra.number_input("Eficiencia óptica η0", min_value=0.01, max_value=1.0, value=0.75, step=0.01, key=self.clave("eficienciaOptica"))
        coeficientePerdidas = barra.number_input("Coeficiente de pérdidas a1 (W/m²·K)", min_value=0.0, value=4.5, step=0.1, key=self.clave("coeficientePerdidas"))

        barra.subheader("Método F-Chart")
        correlacion = barra.selectbox("Correlación", list(self.nombresCorrelacion), format_func=self.nombresCorrelacion.get, key=self.clave("correlacion"))
        correccionAcs = True
        if correlacion == "klein":
            correccionAcs = barra.checkbox("Corrección para ACS", value=True, key=self.clave("correccionAcs"))
        rangoFraccion = barra.slider("Fracción solar objetivo", min_value=0.1, max_value=1.0, value=(0.6, 0.7), step=0.05, key=self.clave("rangoFraccion"))
        eficienciaSistema = barra.number_input("Eficiencia del sistema (área inicial)", min_value=0.05, max_value=1.0, value=0.45, step=0.05, key=self.clave("eficienciaSistema"))

        return {
            "recurso": {"rutaTmy": rutaTmy, "acimutPanel": float(acimutPanel), "usarCenitArchivo": usarCenitArchivo},
            "inclinacionManual": inclinacionManual,
            "fChart": {
                "numeroHabitaciones": int(numeroHabitaciones),
                "ocupacionPorHabitacion": ocupacion,
                "consumoPorPersona": consumo,
                "temperaturaUso": temperaturaUso,
                "temperaturaRed": temperaturaRed,
                "areaColector": areaColector,
                "eficienciaOptica": eficienciaOptica,
                "coeficientePerdidas": coeficientePerdidas,
                "fraccionObjetivoMinima": rangoFraccion[0],
                "fraccionObjetivoMaxima": rangoFraccion[1],
                "eficienciaSistema": eficienciaSistema,
                "correlacion": correlacion,
                "correccionAcs": correccionAcs,
            },
        }

    # ------------------------------------------------------------------
    # Cálculo
    # ------------------------------------------------------------------
    def calcular(self, entradas: dict):
        """Calcula y guarda los resultados en st.session_state. Devuelve el estado o None si hay un error."""
        parametrosRecurso = entradas["recurso"]
        if parametrosRecurso["rutaTmy"] is None:
            st.info("Elige o sube un archivo TMY de NSRDB en la barra lateral.")
            return None
        try:
            recurso = obtenerRecurso(**parametrosRecurso)
            dfBarrido = barridoInclinacion(**parametrosRecurso)
            optima = dfBarrido.sort("RadiacionAnual_kWhm2", descending=True).row(0, named=True)
            inclinacion = optima["Inclinacion_grados"] if entradas["inclinacionManual"] is None else float(entradas["inclinacionManual"])
            climaMensual = recurso.radiacionMensual(inclinacion)
            sistema = SistemaFChart(climaMensual, **entradas["fChart"])
            resultados = sistema.calcular()
        except (ValueError, FileNotFoundError) as error:
            st.session_state.pop(self.clave("resultados"), None)
            st.error(f"No se pudo calcular la solar térmica: {error}")
            return None
        estado = {
            "recurso": recurso,
            "parametrosRecurso": parametrosRecurso,
            "inclinacion": inclinacion,
            "optima": optima,
            "dfBarrido": dfBarrido,
            "climaMensual": climaMensual,
            "sistema": sistema,
            "resultados": resultados,
        }
        st.session_state[self.clave("resultados")] = estado
        return estado

    # ------------------------------------------------------------------
    # Salidas
    # ------------------------------------------------------------------
    def botonesDescargaFigura(self, bytesFigura: dict, nombre: str) -> None:
        columnaPng, columnaSvg, _ = st.columns([1, 1, 4])
        columnaPng.download_button("Descargar PNG", bytesFigura["png"], f"{nombre}.png", "image/png", key=self.clave(f"png_{nombre}"))
        columnaSvg.download_button("Descargar SVG", bytesFigura["svg"], f"{nombre}.svg", "image/svg+xml", key=self.clave(f"svg_{nombre}"))

    def mostrarFigura(self, bytesFigura: dict, nombre: str) -> None:
        st.image(bytesFigura["png"])
        self.botonesDescargaFigura(bytesFigura, nombre)

    def mostrarTabla(self, df: pl.DataFrame, nombreArchivo: str) -> None:
        st.dataframe(df, hide_index=True)
        st.download_button("Descargar CSV", df.write_csv().encode("utf-8"), nombreArchivo, "text/csv", key=self.clave(f"csv_{nombreArchivo}"))

    def mostrarMetricas(self, estado: dict) -> None:
        dimensionamiento = estado["resultados"]["dimensionamiento"]
        radiacionAnual = float(estado["climaMensual"]["HTmes_kWhm2mes"].sum())
        metadatos = estado["recurso"].metadatos
        st.caption(
            f"TMY {Path(estado['parametrosRecurso']['rutaTmy']).name} · lat {metadatos['latitud']}°, lon {metadatos['longitud']}° · "
            f"inclinación óptima {estado['optima']['Inclinacion_grados']:g}° · correlación {estado['sistema'].correlacion}"
        )
        columnas = st.columns(5)
        columnas[0].metric("Inclinación (°)", f"{estado['inclinacion']:g}")
        columnas[1].metric("Radiación en el plano (kWh/m²·año)", f"{radiacionAnual:,.1f}")
        columnas[2].metric("Área de captación (m²)", f"{dimensionamiento['area_m2']:.2f}")
        columnas[3].metric("Colectores", f"{dimensionamiento['numeroColectores']}")
        columnas[4].metric("Fracción solar anual", f"{dimensionamiento['fraccionAnual']:.1%}")
        for advertencia in dimensionamiento["advertencias"]:
            st.warning(advertencia)

    def mostrarRecurso(self, estado: dict, bytesRecurso: dict) -> None:
        st.subheader("Radiación anual frente a la inclinación")
        self.mostrarFigura(bytesRecurso["barridoInclinacion"], "barridoInclinacion")
        st.subheader("Radiación mensual en el plano de los colectores")
        self.mostrarFigura(bytesRecurso["radiacionMensualPlano"], "radiacionMensualPlano")
        self.mostrarTabla(estado["climaMensual"], "radiacionMensualPlano.csv")
        st.subheader("Perfiles horarios")
        for nombre in ("perfilHorarioPlano", "perfilHorarioHorizontal"):
            self.mostrarFigura(bytesRecurso[nombre], nombre)
        self.mostrarFigura(bytesRecurso["perfilHorarioMensual"], "perfilHorarioMensual")
        st.subheader("Radiación diaria")
        self.mostrarFigura(bytesRecurso["radiacionDiaria"], "radiacionDiaria")
        with st.expander("Barrido de inclinación (datos)"):
            self.mostrarTabla(estado["dfBarrido"], "barridoInclinacion.csv")

    def mostrarFChart(self, estado: dict) -> None:
        resultados = estado["resultados"]
        sistema = estado["sistema"]
        dimensionamiento = resultados["dimensionamiento"]
        st.markdown(
            f"**Demanda:** {resultados['volumenDiario_L']:,.0f} L/día de {sistema.temperaturaRed:g} a {sistema.temperaturaUso:g} °C → "
            f"{resultados['demandaDiaria_kWh']:.2f} kWh/día ({resultados['demandaAnual_kWh']:,.0f} kWh/año). "
            f"**Área inicial:** {resultados['areaInicial_m2']:.2f} m² (fracción anual {resultados['fraccionAreaInicial']:.1%})."
        )
        st.markdown(
            f"**Diseño:** {dimensionamiento['iteraciones']} iteraciones → {dimensionamiento['area_m2']:.2f} m², "
            f"{dimensionamiento['numeroColectores']} colectores ({dimensionamiento['areaInstalada_m2']:g} m² instalados), "
            f"energía solar {dimensionamiento['energiaSolarAnual_kWh']:,.0f} kWh/año y auxiliar "
            f"{dimensionamiento['energiaAuxiliarAnual_kWh']:,.0f} kWh/año."
        )
        curva = sistema.curvaFraccionArea()
        bytesFChart = figurasFChart(
            dimensionamiento["dfMensual"].to_dicts(), curva.to_dicts(), dimensionamiento["area_m2"], dimensionamiento["fraccionAnual"],
            sistema.fraccionObjetivoMinima, sistema.fraccionObjetivoMaxima,
        )
        st.subheader("Energía solar y auxiliar por mes")
        self.mostrarFigura(bytesFChart["fChartMensual"], "fChartMensual")
        self.mostrarTabla(dimensionamiento["dfMensual"], "fChartMensual.csv")
        st.subheader("Fracción solar anual frente al área")
        self.mostrarFigura(bytesFChart["fChartFraccionArea"], "fChartFraccionArea")
        st.subheader("Casos de análisis")
        self.mostrarTabla(resultados["dfCasos"], "fChartCasos.csv")
        st.subheader("Demanda mensual")
        self.mostrarTabla(resultados["dfDemanda"], "demandaAcs.csv")

        if st.button("Guardar resultados en la carpeta outputs", key=self.clave("guardar")):
            carpetaOutputs.mkdir(parents=True, exist_ok=True)
            for nombre, df in {
                "radiacionMensualPlano": estado["climaMensual"], "barridoInclinacion": estado["dfBarrido"],
                "fChartMensual": dimensionamiento["dfMensual"], "fChartCasos": resultados["dfCasos"],
            }.items():
                df.write_csv(carpetaOutputs / f"{nombre}.csv")
            for nombre, bytesFigura in bytesFChart.items():
                for formato, contenido in bytesFigura.items():
                    (carpetaOutputs / f"{nombre}.{formato}").write_bytes(contenido)
            st.success(f"Resultados guardados en {carpetaOutputs} (se sobrescriben los anteriores).")

    def mostrarFormulas(self) -> None:
        st.markdown("**Posición del sol (Spencer; Duffie y Beckman)**")
        st.latex(r"B = (n-1)\,\tfrac{360}{365} \qquad \omega = 15\,(t_s - 12) \qquad t_s = t + \frac{4\,(L - 15\,TZ) + E}{60}")
        st.latex(r"\cos\theta_z = \sin\phi\,\sin\delta + \cos\phi\,\cos\delta\,\cos\omega")
        st.markdown("**Irradiancia en el plano inclinado (modelo isotrópico)**")
        st.latex(r"\cos\theta = \cos\theta_z\cos\beta + \sin\theta_z\sin\beta\cos(\gamma_s - \gamma_p)")
        st.latex(r"G_{bi} = DNI\,\max(\cos\theta, 0) \qquad G_{di} = DHI\,\frac{1+\cos\beta}{2} \qquad G_{ri} = GHI\,\rho\,\frac{1-\cos\beta}{2}")
        st.latex(r"GTI = G_{bi} + G_{di} + G_{ri}")
        st.markdown("**Método F-Chart**")
        st.latex(r"Q_d = \rho\,V\,c_e\,(T_w - T_{red}) \qquad A_{c0} = \frac{f_{obj}\,\bar{Q}_m}{\eta_{sis}\,\bar{H}_T}")
        st.latex(r"D_1 = \frac{\eta_0\,H_T\,A_c}{Q_m} \qquad D_2 = \frac{a_1\,\Delta t\,A_c\,\Delta T}{Q_m}")
        st.latex(r"\text{Klein: } f = 1{,}029\,D_1 - 0{,}065\,D_2 - 0{,}245\,D_1^2 + 0{,}0018\,D_2^2 + 0{,}0215\,D_1^3")
        st.latex(r"\Delta T_{ACS} = 11{,}6 + 1{,}18\,T_w + 3{,}86\,T_{red} - 2{,}32\,T_{amb}")
        st.latex(r"\text{Informe: } f = 1 - e^{-(0{,}525 D_1 + 0{,}352 D_2 + 1{,}2008 D_1^2 + 0{,}0127 D_2^2 - 0{,}3319 D_1 D_2)},\ \ \Delta T = T_w - T_{amb}")
        st.latex(r"F = \frac{\sum f\,Q_m}{\sum Q_m} \qquad n_{col} = \left\lceil A_c / A_b \right\rceil")

    def mostrarSupuestos(self) -> None:
        st.markdown(
            "- La posición del sol se calcula a la hora de cada registro del TMY (hh:30, hora estándar local).\n"
            "- Modelo isotrópico de la difusa: subestima algo la irradiancia frente a Hay-Davies o HDKR; sin sombras, suciedad ni IAM.\n"
            "- Demanda de ACS constante todo el año y temperatura de la red constante.\n"
            "- El colector se caracteriza solo por η0 = FR(τα) y a1 = FRUL, sin correcciones del captador ni del intercambiador.\n"
            "- F-Chart de Klein válido para 0 < D1 < 3 y 0 < D2 < 18; volumen de acumulación estándar (75 L/m²).\n"
            "- La correlación exponencial del informe no tiene fuente publicada y su coeficiente de D2 es positivo "
            "(más pérdidas, más fracción); se mantiene solo para reproducir el informe.\n"
            "- El área se ajusta en pasos de 0,1 m² desde el área inicial hasta que la fracción anual entra en el rango objetivo."
        )

    def ejecutar(self) -> None:
        st.set_page_config(page_title="Solar térmica · F-Chart", layout="wide")
        st.title("Solar térmica: recurso solar y ACS por F-Chart")
        entradas = self.mostrarBarraLateral()
        estado = self.calcular(entradas)
        if estado is None:
            return
        self.mostrarMetricas(estado)
        pestanaRecurso, pestanaFChart, pestanaFormulas, pestanaSupuestos = st.tabs(
            ["Recurso solar", "F-Chart", "Fórmulas", "Supuestos"]
        )
        with pestanaRecurso:
            componenteMensual = st.selectbox(
                "Componente del perfil horario por mes",
                list(RecursoSolar.componentesInclinadas) + list(RecursoSolar.componentesHorizontales),
                format_func=GraficadorSolar.nombresComponentes.get,
                index=3,
                key=self.clave("componenteMensual"),
            )
            bytesRecurso = figurasRecurso(**estado["parametrosRecurso"], inclinacion=estado["inclinacion"], componenteMensual=componenteMensual)
            self.mostrarRecurso(estado, bytesRecurso)
        with pestanaFChart:
            self.mostrarFChart(estado)
        with pestanaFormulas:
            self.mostrarFormulas()
        with pestanaSupuestos:
            self.mostrarSupuestos()


InterfazSolarTermica().ejecutar()
