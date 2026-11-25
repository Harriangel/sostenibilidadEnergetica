from pathlib import Path

import polars as pl
import streamlit as st

from energias.solar.fotovoltaica.horasSolaresPico import SistemaFotovoltaicoHsp
from energias.solar.graficadorSolar import GraficadorSolar
from energias.solar.recursoSolar import RecursoSolar

# interfaz/pages/4_Fotovoltaica.py -> raíz del repositorio
carpetaRaiz = Path(__file__).resolve().parents[2]
carpetaData = carpetaRaiz / "data" / "solar"
carpetaOutputs = carpetaRaiz / "outputs" / "solar"


@st.cache_resource(show_spinner="Leyendo el TMY y calculando la posición del sol...")
def obtenerRecurso(rutaTmy: str, acimutPanel: float) -> RecursoSolar:
    return RecursoSolar(Path(rutaTmy), acimutPanel=acimutPanel)


@st.cache_data(show_spinner=False)
def radiacionTmy(rutaTmy: str, acimutPanel: float, inclinacion) -> tuple:
    """(radiación diaria media de cada mes en el plano, inclinación usada); inclinación None = óptima."""
    recurso = obtenerRecurso(rutaTmy, acimutPanel)
    if inclinacion is None:
        inclinacion = recurso.inclinacionOptima()["inclinacion"]
    return recurso.radiacionMensual(inclinacion)["HTdia_kWhm2dia"].to_list(), inclinacion


@st.cache_data(show_spinner=False)
def figuraEnergia(filasMensual: list, unidadEnergia: str) -> dict:
    graficador = GraficadorSolar()
    fig = graficador.crearFiguraEnergiaFotovoltaica(pl.DataFrame(filasMensual), unidadEnergia)
    return {formato: graficador.figuraABytes(fig, formato) for formato in ("png", "svg")}


class InterfazFotovoltaica:
    """Página de la solar fotovoltaica: energía útil por horas solares pico.

    Las claves de st.session_state llevan el prefijo de la tecnología ('fotovoltaica_').
    """

    prefijoEstado = "fotovoltaica_"
    fuentes = {
        "nasa": "NASA POWER, Bogotá (GHI horizontal; caso del Excel)",
        "tmy": "TMY de NSRDB (plano inclinado)",
        "manual": "Ingresar 12 valores",
    }
    unidadesEnergia = ["kWh", "MWh", "GWh"]

    @classmethod
    def clave(cls, nombre: str) -> str:
        """Clave de st.session_state (o de un widget) con el prefijo de la tecnología."""
        return f"{cls.prefijoEstado}{nombre}"

    def mostrarBarraLateral(self) -> dict:
        barra = st.sidebar
        barra.title("Parámetros de la fotovoltaica")

        barra.subheader("Radiación")
        fuente = barra.radio("Fuente de la radiación", list(self.fuentes), format_func=self.fuentes.get, key=self.clave("fuente"))
        entradasRadiacion = {"fuente": fuente}
        if fuente == "tmy":
            archivos = sorted(archivo.name for archivo in carpetaData.glob("*.csv"))
            if not archivos:
                barra.warning("No hay archivos .csv en data/solar.")
                entradasRadiacion["rutaTmy"] = None
            else:
                entradasRadiacion["rutaTmy"] = str(carpetaData / barra.selectbox("TMY", archivos, key=self.clave("archivoTmy")))
            entradasRadiacion["acimutPanel"] = float(barra.number_input("Acimut del campo (°, 180 = sur)", min_value=0.0, max_value=359.0, value=180.0, step=5.0, key=self.clave("acimutPanel")))
            optima = barra.checkbox("Inclinación óptima anual", value=True, key=self.clave("inclinacionOptima"))
            entradasRadiacion["inclinacion"] = None if optima else float(barra.slider("Inclinación (°)", 0, 90, 20, key=self.clave("inclinacion")))

        barra.subheader("Sistema")
        potenciaNominal = barra.number_input("Potencia nominal (kWp)", min_value=0.01, value=5.0, step=0.5, key=self.clave("potenciaNominal"))
        perdidas = barra.number_input("Pérdidas del sistema (%)", min_value=0.0, max_value=99.0, value=14.0, step=0.5, key=self.clave("perdidas"))
        inversor = barra.number_input("Eficiencia del inversor (%)", min_value=1.0, max_value=100.0, value=100.0, step=0.5, key=self.clave("inversor"))
        barra.caption("Con 100 % se reproduce el Excel; un valor típico es 96 %.")
        unidadEnergia = barra.selectbox("Unidad de energía", self.unidadesEnergia, key=self.clave("unidadEnergia"))
        return {
            "radiacion": entradasRadiacion,
            "sistema": {
                "potenciaNominal": potenciaNominal,
                "perdidasSistema": perdidas / 100,
                "eficienciaInversor": inversor / 100,
                "unidadEnergia": unidadEnergia,
            },
        }

    def obtenerRadiacion(self, entradasRadiacion: dict):
        """(12 valores de radiación diaria, descripción) o (None, None) si falta información."""
        fuente = entradasRadiacion["fuente"]
        if fuente == "nasa":
            return list(SistemaFotovoltaicoHsp.radiacionBogotaNasa), self.fuentes["nasa"]
        if fuente == "tmy":
            if entradasRadiacion["rutaTmy"] is None:
                return None, None
            radiacion, inclinacion = radiacionTmy(entradasRadiacion["rutaTmy"], entradasRadiacion["acimutPanel"], entradasRadiacion["inclinacion"])
            return radiacion, f"TMY {Path(entradasRadiacion['rutaTmy']).name}, plano de {inclinacion:g}° (acimut {entradasRadiacion['acimutPanel']:g}°)"
        st.markdown("**Radiación diaria media de cada mes (kWh/m²·día)**")
        dfEntrada = pl.DataFrame({"Mes": list(SistemaFotovoltaicoHsp.nombresMeses), "Radiacion_kWhm2dia": list(SistemaFotovoltaicoHsp.radiacionBogotaNasa)})
        dfEditado = st.data_editor(dfEntrada, disabled=["Mes"], hide_index=True, key=self.clave("radiacionManual"))
        return [float(valor) for valor in dfEditado["Radiacion_kWhm2dia"]], "Valores ingresados"

    def calcular(self, entradas: dict):
        radiacion, descripcion = self.obtenerRadiacion(entradas["radiacion"])
        if radiacion is None:
            st.info("Elige un archivo TMY en la barra lateral.")
            return None
        try:
            sistema = SistemaFotovoltaicoHsp(radiacionDiaria=radiacion, **entradas["sistema"])
            resultados = sistema.calcular()
        except (ValueError, FileNotFoundError) as error:
            st.session_state.pop(self.clave("resultados"), None)
            st.error(f"No se pudo calcular la fotovoltaica: {error}")
            return None
        estado = {"sistema": sistema, "resultados": resultados, "descripcionRadiacion": descripcion}
        st.session_state[self.clave("resultados")] = estado
        return estado

    def mostrarResultados(self, estado: dict) -> None:
        resultados, sistema = estado["resultados"], estado["sistema"]
        unidad = resultados["unidadEnergia"]
        st.caption(
            f"Radiación: {estado['descripcionRadiacion']} · {sistema.potenciaNominal:g} kWp · pérdidas {sistema.perdidasSistema:.1%} · "
            f"inversor {sistema.eficienciaInversor:.1%} · rendimiento global {resultados['rendimientoGlobal']:.3f}"
        )
        columnas = st.columns(4)
        decimales = 2 if unidad == "kWh" else 5
        columnas[0].metric(f"Energía útil anual ({unidad}/año)", f"{resultados['energiaAnual']:,.{decimales}f}")
        columnas[1].metric("Rendimiento específico (kWh/kWp·año)", f"{resultados['rendimientoAnual_kWhkWp']:,.1f}")
        columnas[2].metric("Factor de planta", f"{resultados['factorPlanta']:.2%}")
        columnas[3].metric("Promedio diario (kWh/día)", f"{resultados['promedioDiario_kWh']:,.2f}")

        pestanaResultados, pestanaFormulas, pestanaSupuestos = st.tabs(["Resultados", "Fórmulas", "Supuestos"])
        with pestanaResultados:
            bytesFigura = figuraEnergia(resultados["dfMensual"].to_dicts(), unidad)
            st.image(bytesFigura["png"])
            columnaPng, columnaSvg, _ = st.columns([1, 1, 4])
            columnaPng.download_button("Descargar PNG", bytesFigura["png"], "fotovoltaicaEnergiaMensual.png", "image/png", key=self.clave("png_energia"))
            columnaSvg.download_button("Descargar SVG", bytesFigura["svg"], "fotovoltaicaEnergiaMensual.svg", "image/svg+xml", key=self.clave("svg_energia"))
            st.subheader("Tabla mensual")
            st.dataframe(resultados["dfMensual"], hide_index=True)
            st.download_button(
                "Descargar CSV", resultados["dfMensual"].write_csv().encode("utf-8"), "fotovoltaicaMensual.csv", "text/csv",
                key=self.clave("csv_mensual"),
            )
            st.markdown(
                f"Radiación anual {resultados['radiacionAnual_kWhm2']:,.2f} kWh/m²·año · máxima "
                f"{resultados['radiacionMaxima_kWhm2dia']:.3f} y mínima {resultados['radiacionMinima_kWhm2dia']:.3f} kWh/m²·día."
            )
            if st.button("Guardar resultados en la carpeta outputs", key=self.clave("guardar")):
                carpetaOutputs.mkdir(parents=True, exist_ok=True)
                resultados["dfMensual"].write_csv(carpetaOutputs / "fotovoltaicaMensual.csv")
                for formato, contenido in bytesFigura.items():
                    (carpetaOutputs / f"fotovoltaicaEnergiaMensual.{formato}").write_bytes(contenido)
                st.success(f"Resultados guardados en {carpetaOutputs} (se sobrescriben los anteriores).")
        with pestanaFormulas:
            st.latex(r"H_m = H \cdot d \qquad [\text{kWh/m}^2\cdot\text{mes}]")
            st.latex(r"E_m = H_m \cdot P_{nom} \cdot (1 - L) \cdot \eta_{inv} \qquad [\text{kWh/mes}]")
            st.latex(r"Y = \frac{E_a}{P_{nom}} \qquad FP = \frac{E_a}{P_{nom} \cdot 8760}")
            st.caption(
                "H: radiación diaria media del mes en el plano (kWh/m²·día), que equivale a horas solares pico con 1 kW/m²; "
                "d: días del mes; Pnom: potencia nominal (kWp); L: pérdidas del sistema; ηinv: eficiencia del inversor; "
                "Ea: energía útil anual; Y: rendimiento específico; FP: factor de planta."
            )
        with pestanaSupuestos:
            st.markdown(
                "- Método de horas solares pico: la producción es proporcional a la radiación del mes.\n"
                "- Las pérdidas del sistema agrupan cableado, suciedad, desajuste y temperatura en un solo factor.\n"
                "- Con la fuente NASA POWER se usa la radiación horizontal, como en el Excel; con el TMY, la del plano inclinado.\n"
                "- Frente a PVWatts (que modela la temperatura de las celdas y el inversor), este método sobrestima el rendimiento "
                "específico: en Bogotá, 1456 frente a 1290 kWh/kWp·año."
            )

    def ejecutar(self) -> None:
        st.set_page_config(page_title="Fotovoltaica · horas solares pico", layout="wide")
        st.title("Solar fotovoltaica: energía útil por horas solares pico")
        entradas = self.mostrarBarraLateral()
        estado = self.calcular(entradas)
        if estado is not None:
            self.mostrarResultados(estado)


InterfazFotovoltaica().ejecutar()
