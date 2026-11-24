from pathlib import Path

import polars as pl
import streamlit as st

from energias.comun.unidades import Unidades
from energias.mar.graficadorMareomotriz import GraficadorMareomotriz
from energias.mar.mareomotriz import CentralMareomotriz

# interfaz/pages/2_Mareomotriz.py -> raíz del repositorio
carpetaRaiz = Path(__file__).resolve().parents[2]
carpetaOutputs = carpetaRaiz / "outputs" / "mareomotriz"


class InterfazMareomotriz:
    """Página de la central mareomotriz: energía anual por energía potencial y LCOE.

    Barra lateral: entradas de marea, turbina, constantes físicas y economía. Zona central:
    métricas, tablas, gráficas, fórmulas y supuestos, con descargas en CSV, PNG y SVG.
    El cálculo se rehace en cada cambio de las entradas (es instantáneo).
    Las claves de st.session_state llevan el prefijo de la tecnología ('mareomotriz_').
    """

    prefijoEstado = "mareomotriz_"
    unidadesEnergia = ["kWh", "MWh", "GWh"]
    unidadesLcoe = ["kWh", "MWh"]
    nombresParametrosSensibilidad = {
        parametro: etiqueta for parametro, (etiqueta, _) in CentralMareomotriz.parametrosSensibilidad.items()
    }

    @classmethod
    def clave(cls, nombre: str) -> str:
        """Clave de st.session_state (o de un widget) con el prefijo de la tecnología."""
        return f"{cls.prefijoEstado}{nombre}"

    # ------------------------------------------------------------------
    # Entradas
    # ------------------------------------------------------------------
    def mostrarBarraLateral(self) -> tuple:
        """Dibuja las entradas. Devuelve (parámetros de CentralMareomotriz, opciones de presentación)."""
        barra = st.sidebar
        barra.title("Parámetros de la mareomotriz")

        barra.subheader("Marea")
        tipoMarea = barra.selectbox("Tipo de marea", ["Semidiurna", "Diurna"], key=self.clave("tipoMarea"))
        duracionDiaLunar = barra.number_input(
            "Duración del día lunar (h)", min_value=0.1, value=24.8, step=0.1, key=self.clave("duracionDiaLunar")
        )
        duracionDiaSolar = barra.number_input(
            "Duración del día solar (h)", min_value=0.1, value=24.0, step=0.1, key=self.clave("duracionDiaSolar")
        )
        diasAnio = barra.number_input(
            "Días de operación al año", min_value=1, max_value=366, value=365, step=1, key=self.clave("diasAnio")
        )

        barra.subheader("Turbina")
        tipoTurbina = barra.text_input("Tipo de turbina (descriptivo)", value="Eje horizontal", key=self.clave("tipoTurbina"))
        direccion = barra.selectbox("Dirección", ["Bidireccional", "Unidireccional"], key=self.clave("direccion"))
        eficiencia = barra.number_input(
            "Rendimiento global η", min_value=0.01, max_value=1.0, value=0.38, step=0.01, key=self.clave("eficiencia")
        )
        numeroTurbinas = barra.number_input(
            "Número de turbinas", min_value=1, value=1, step=1, key=self.clave("numeroTurbinas")
        )
        disponibilidad = barra.number_input(
            "Disponibilidad anual", min_value=0.01, max_value=1.0, value=1.0, step=0.01, key=self.clave("disponibilidad")
        )

        with barra.expander("Constantes físicas"):
            masaAgua = st.number_input(
                "Masa de agua por ciclo y turbina m (kg)", min_value=1.0, value=8.7e9, step=1e8, format="%.4e",
                key=self.clave("masaAgua"),
            )
            gravedad = st.number_input("Gravedad g (m/s²)", min_value=0.1, value=9.81, step=0.01, key=self.clave("gravedad"))
            desnivel = st.number_input("Desnivel efectivo medio h (m)", min_value=0.01, value=3.6, step=0.1, key=self.clave("desnivel"))

        barra.subheader("Economía")
        moneda = barra.text_input("Moneda", value="EUR", key=self.clave("moneda")).strip().upper() or "EUR"
        vidaUtil = barra.number_input("Vida útil (años)", min_value=1, value=25, step=1, key=self.clave("vidaUtil"))
        tasaPorcentaje = barra.number_input(
            "Tasa de descuento (%)", min_value=0.0, max_value=100.0, value=7.0, step=0.5, key=self.clave("tasaDescuento")
        )
        capex = barra.number_input(
            f"CAPEX ({moneda}/turbina)", min_value=0.0, value=14_500_000.0, step=500_000.0, format="%.2f", key=self.clave("capex")
        )
        opex = barra.number_input(
            f"OPEX ({moneda}/año por turbina)", min_value=0.0, value=450_000.0, step=10_000.0, format="%.2f", key=self.clave("opex")
        )
        with barra.expander("Escenarios de sensibilidad"):
            factorCapexEscenarioA = st.number_input(
                "Escenario A: factor del CAPEX", min_value=0.01, value=1.15, step=0.05, key=self.clave("factorCapexEscenarioA")
            )
            factorEnergiaEscenarioB = st.number_input(
                "Escenario B: factor de la energía", min_value=0.01, value=0.90, step=0.05, key=self.clave("factorEnergiaEscenarioB")
            )

        barra.subheader("Resultados")
        unidadEnergia = barra.selectbox("Unidad de energía", self.unidadesEnergia, key=self.clave("unidadEnergia"))
        unidadLcoe = barra.selectbox("Unidad del LCOE", self.unidadesLcoe, format_func=lambda u: f"{moneda}/{u}", key=self.clave("unidadLcoe"))

        parametros = {
            "tipoMarea": tipoMarea,
            "direccion": direccion,
            "tipoTurbina": tipoTurbina,
            "duracionDiaLunar": duracionDiaLunar,
            "duracionDiaSolar": duracionDiaSolar,
            "diasAnio": int(diasAnio),
            "masaAgua": masaAgua,
            "gravedad": gravedad,
            "desnivel": desnivel,
            "eficiencia": eficiencia,
            "vidaUtil": int(vidaUtil),
            "tasaDescuento": tasaPorcentaje / 100,
            "capex": capex,
            "opex": opex,
            "factorCapexEscenarioA": factorCapexEscenarioA,
            "factorEnergiaEscenarioB": factorEnergiaEscenarioB,
            "numeroTurbinas": int(numeroTurbinas),
            "disponibilidad": disponibilidad,
            "moneda": moneda,
        }
        return parametros, {"unidadEnergia": unidadEnergia, "unidadLcoe": unidadLcoe}

    # ------------------------------------------------------------------
    # Cálculo
    # ------------------------------------------------------------------
    def calcular(self, parametros: dict):
        """Calcula y guarda los resultados en st.session_state. Devuelve (central, resultados) o (None, None)."""
        try:
            central = CentralMareomotriz(**parametros)
            resultados = central.calcular()
        except ValueError as error:
            st.session_state.pop(self.clave("resultados"), None)
            st.error(f"No se pudo calcular la central mareomotriz: {error}")
            return None, None
        st.session_state[self.clave("resultados")] = resultados
        return central, resultados

    # ------------------------------------------------------------------
    # Figuras (en caché: solo se regeneran si cambian sus datos)
    # ------------------------------------------------------------------
    @staticmethod
    @st.cache_data(show_spinner=False)
    def crearBytesEscenarios(filasEscenarios: list, moneda: str, unidadLcoe: str) -> dict:
        graficador = GraficadorMareomotriz()
        fig = graficador.crearFiguraEscenarios(pl.DataFrame(filasEscenarios), moneda, unidadLcoe)
        return {formato: graficador.figuraABytes(fig, formato) for formato in ("png", "svg")}

    @staticmethod
    @st.cache_data(show_spinner=False)
    def crearBytesSensibilidad(filasBarrido: list, parametro: str, valorBase: float, lcoeBase: float, moneda: str, unidadLcoe: str) -> dict:
        graficador = GraficadorMareomotriz()
        fig = graficador.crearFiguraSensibilidad(pl.DataFrame(filasBarrido), parametro, valorBase, lcoeBase, moneda, unidadLcoe)
        return {formato: graficador.figuraABytes(fig, formato) for formato in ("png", "svg")}

    # ------------------------------------------------------------------
    # Salidas
    # ------------------------------------------------------------------
    def botonesDescargaFigura(self, bytesFigura: dict, nombre: str) -> None:
        columnaPng, columnaSvg, _ = st.columns([1, 1, 4])
        columnaPng.download_button("Descargar PNG", bytesFigura["png"], f"{nombre}.png", "image/png", key=self.clave(f"png_{nombre}"))
        columnaSvg.download_button("Descargar SVG", bytesFigura["svg"], f"{nombre}.svg", "image/svg+xml", key=self.clave(f"svg_{nombre}"))

    def mostrarTabla(self, df: pl.DataFrame, nombreArchivo: str) -> None:
        st.dataframe(df, hide_index=True)
        st.download_button(
            "Descargar CSV", df.write_csv().encode("utf-8"), nombreArchivo, "text/csv", key=self.clave(f"csv_{nombreArchivo}")
        )

    def tablaPasosYEnergia(self, resultados: dict, unidadEnergia: str) -> pl.DataFrame:
        """Pasos por turbina y energía de la central, con la energía en la unidad elegida."""
        factor = Unidades.convertirEnergia(1.0, "kWh", unidadEnergia)
        return pl.DataFrame(
            {
                "Variable": [
                    "Duración del ciclo de marea",
                    "Ciclos por día solar",
                    "Ciclos por año",
                    "Pasos por turbina y año",
                    "Energía por paso y turbina",
                    "Energía potencial anual",
                    "Energía potencial anual",
                    "Energía útil anual",
                    "Potencia media",
                ],
                "Valor": [
                    resultados["cicloMarea_h"],
                    resultados["ciclosPorDia"],
                    resultados["ciclosPorAnio"],
                    resultados["pasosPorAnio"],
                    resultados["energiaPorPaso_J"],
                    resultados["energiaPotencial_J"],
                    resultados["energiaPotencial_kWh"] * factor,
                    resultados["energiaUtil_kWh"] * factor,
                    resultados["potenciaMedia_MW"],
                ],
                "Unidad": [
                    "h/ciclo",
                    "ciclos/día",
                    "ciclos/año",
                    "pasos/año",
                    "J/paso",
                    "J/año",
                    f"{unidadEnergia}/año",
                    f"{unidadEnergia}/año",
                    "MW",
                ],
            }
        )

    def tablaValorPresente(self, resultados: dict) -> pl.DataFrame:
        moneda = resultados["moneda"]
        return pl.DataFrame(
            {
                "Variable": [
                    "CAPEX total (año 0)",
                    "OPEX total anual",
                    "Factor de valor presente FVP",
                    "Factor de recuperación de capital CRF",
                    "Valor presente del OPEX",
                    "Valor presente de los costos",
                    "Valor presente de la energía",
                ],
                "Valor": [
                    resultados["capexTotal"],
                    resultados["opexTotal"],
                    resultados["factorValorPresente"],
                    resultados["factorRecuperacionCapital"],
                    resultados["valorPresenteOpex"],
                    resultados["valorPresenteCostos"],
                    resultados["valorPresenteEnergia_kWh"],
                ],
                "Unidad": [moneda, f"{moneda}/año", "años", "1/año", moneda, moneda, "kWh"],
            }
        )

    def mostrarMetricas(self, central: CentralMareomotriz, resultados: dict, opciones: dict) -> None:
        moneda = resultados["moneda"]
        unidadEnergia, unidadLcoe = opciones["unidadEnergia"], opciones["unidadLcoe"]
        energia = Unidades.convertirEnergia(resultados["energiaUtil_kWh"], "kWh", unidadEnergia)
        lcoe = resultados["lcoeBase_porKWh"] * (1000 if unidadLcoe == "MWh" else 1)
        st.caption(
            f"Marea {central.tipoMarea.lower()} · turbina {central.direccion.lower()} ({central.tipoTurbina}) · "
            f"{central.numeroTurbinas} turbina(s) · disponibilidad {central.disponibilidad:g} · η = {central.eficiencia:g}"
        )
        columnas = st.columns(4)
        columnas[0].metric("Pasos por turbina al año", f"{resultados['pasosPorAnio']:,.1f}")
        columnas[1].metric(f"Energía útil anual ({unidadEnergia}/año)", f"{energia:,.2f}")
        columnas[2].metric("Potencia media (MW)", f"{resultados['potenciaMedia_MW']:,.3f}")
        columnas[3].metric(f"LCOE base ({moneda}/{unidadLcoe})", f"{lcoe:,.4f}" if unidadLcoe == "kWh" else f"{lcoe:,.2f}")

    def mostrarResultados(self, central: CentralMareomotriz, resultados: dict, opciones: dict) -> None:
        moneda = resultados["moneda"]
        unidadEnergia, unidadLcoe = opciones["unidadEnergia"], opciones["unidadLcoe"]
        dfEnergia = self.tablaPasosYEnergia(resultados, unidadEnergia)
        dfValorPresente = self.tablaValorPresente(resultados)
        dfEscenarios = resultados["dfEscenarios"]

        pestanaTablas, pestanaGraficas, pestanaFormulas, pestanaSupuestos = st.tabs(
            ["Pasos, energía y escenarios", "Gráficas", "Fórmulas", "Supuestos del modelo"]
        )
        with pestanaTablas:
            st.subheader("Pasos por turbina y energía de la central")
            self.mostrarTabla(dfEnergia, "pasosYEnergia.csv")
            st.subheader("Valor presente (caso base)")
            self.mostrarTabla(dfValorPresente, "valorPresente.csv")
            st.subheader("Escenarios de sensibilidad")
            self.mostrarTabla(dfEscenarios, "escenariosLcoe.csv")

        with pestanaGraficas:
            st.subheader("LCOE por escenario")
            bytesEscenarios = self.crearBytesEscenarios(dfEscenarios.to_dicts(), moneda, unidadLcoe)
            st.image(bytesEscenarios["png"])
            self.botonesDescargaFigura(bytesEscenarios, "lcoeEscenarios")

            st.subheader("Sensibilidad del LCOE")
            parametro = st.selectbox(
                "Parámetro",
                list(self.nombresParametrosSensibilidad),
                format_func=self.nombresParametrosSensibilidad.get,
                key=self.clave("parametroSensibilidad"),
            )
            dfBarrido = central.barridoSensibilidad(parametro)
            bytesSensibilidad = self.crearBytesSensibilidad(
                dfBarrido.to_dicts(), parametro, float(central.parametros[parametro]), resultados["lcoeBase_porKWh"], moneda, unidadLcoe
            )
            st.image(bytesSensibilidad["png"])
            self.botonesDescargaFigura(bytesSensibilidad, f"sensibilidadLcoe_{parametro}")
            with st.expander("Datos del barrido"):
                self.mostrarTabla(dfBarrido, f"sensibilidadLcoe_{parametro}.csv")

            if st.button("Guardar resultados en la carpeta outputs", key=self.clave("guardar")):
                self.guardarEnOutputs(
                    {"pasosYEnergia": dfEnergia, "valorPresente": dfValorPresente, "escenariosLcoe": dfEscenarios,
                     f"sensibilidadLcoe_{parametro}": dfBarrido},
                    {"lcoeEscenarios": bytesEscenarios, f"sensibilidadLcoe_{parametro}": bytesSensibilidad},
                )

        with pestanaFormulas:
            self.mostrarFormulas()
        with pestanaSupuestos:
            self.mostrarSupuestos()

    def guardarEnOutputs(self, tablas: dict, figuras: dict) -> None:
        """Guarda csv ({nombre: dataframe}) y figuras ({nombre: bytes png/svg}) en outputs/mareomotriz."""
        carpetaOutputs.mkdir(parents=True, exist_ok=True)
        for nombre, df in tablas.items():
            df.write_csv(carpetaOutputs / f"{nombre}.csv")
        for nombre, bytesFigura in figuras.items():
            for formato, contenido in bytesFigura.items():
                (carpetaOutputs / f"{nombre}.{formato}").write_bytes(contenido)
        st.success(f"Resultados guardados en {carpetaOutputs} (se sobrescriben los anteriores).")

    def mostrarFormulas(self) -> None:
        st.markdown("**Pasos de agua por turbina y año**")
        st.latex(r"T_{\text{ciclo}} = \frac{T_{\text{lunar}}}{c} \qquad c = \begin{cases} 1 & \text{diurna} \\ 2 & \text{semidiurna} \end{cases}")
        st.latex(r"\text{ciclos/día} = \frac{T_{\text{solar}}}{T_{\text{ciclo}}} \qquad \text{ciclos/año} = \text{ciclos/día} \cdot d")
        st.latex(r"n = \text{ciclos/año} \cdot k \qquad k = \begin{cases} 1 & \text{unidireccional} \\ 2 & \text{bidireccional} \end{cases}")
        st.markdown("**Energía anual**")
        st.latex(r"E_{\text{paso}} = \tfrac{1}{2}\, m\, g\, h \qquad E_p = n \cdot E_{\text{paso}} \cdot N_t \quad [\text{J/año}]")
        st.latex(r"E_p\,[\text{kWh}] = \frac{E_p\,[\text{J}]}{3{,}6 \times 10^{6}} \qquad E_u = \eta \cdot D \cdot E_p")
        st.markdown("**LCOE por valor presente**")
        st.latex(r"FVP = \sum_{t=1}^{VU} \frac{1}{(1+r)^{t}} = \frac{1 - (1+r)^{-VU}}{r} \quad (FVP = VU \text{ si } r = 0) \qquad CRF = \frac{1}{FVP}")
        st.latex(r"VP_{\text{costos}} = CAPEX \cdot N_t + OPEX \cdot N_t \cdot FVP \qquad VP_{\text{energía}} = E_u \cdot FVP")
        st.latex(r"LCOE = \frac{VP_{\text{costos}}}{VP_{\text{energía}}} \quad [\text{moneda/kWh}]")
        st.latex(r"\text{A: } CAPEX \times f_A \qquad \text{B: } E_u \times f_B \qquad \Delta = \frac{LCOE_X}{LCOE_{\text{base}}} - 1")
        st.caption(
            "T: duraciones (h); d: días por año; m: masa de agua por ciclo y turbina (kg); g: gravedad (m/s²); "
            "h: desnivel efectivo medio (m); η: rendimiento global; D: disponibilidad; Nₜ: número de turbinas; "
            "r: tasa de descuento; VU: vida útil (años); CAPEX en moneda por turbina (año 0); OPEX en moneda por "
            "turbina y año. El factor ½ indica que el centro de masas del agua desciende, en promedio, la mitad del desnivel."
        )

    def mostrarSupuestos(self) -> None:
        st.markdown(
            "- La masa de agua, el desnivel y el rendimiento son constantes en todos los ciclos.\n"
            "- La central opera todos los días indicados del año; la disponibilidad reduce la energía útil de forma proporcional.\n"
            "- Las turbinas son iguales: el número de turbinas multiplica la energía, el CAPEX y el OPEX, por lo que no cambia el LCOE.\n"
            "- El CAPEX se invierte íntegro en el año 0; el OPEX y la energía son constantes y ocurren al final de cada año "
            "(anualidad vencida), sin inflación, impuestos, degradación ni reposición de equipos.\n"
            "- El LCOE se calcula por valor presente. Las fórmulas alternativas del Excel (celdas K31, K36 y K41), que "
            "anualizan el CAPEX solo con la tasa, no se usan porque subestiman el LCOE.\n"
            "- El LCOE está en moneda por kWh (o por MWh) y el CAPEX en moneda por turbina; las leyendas del Excel original "
            "(«€/MWh», «€/año») son erratas.\n"
            "- La moneda es solo una etiqueta: no se convierte. Los datos del caso de referencia están en euros."
        )

    def ejecutar(self) -> None:
        st.set_page_config(page_title="Mareomotriz · energía y LCOE", layout="wide")
        st.title("Central mareomotriz: energía anual y LCOE")
        parametros, opciones = self.mostrarBarraLateral()
        central, resultados = self.calcular(parametros)
        if resultados is None:
            return
        self.mostrarMetricas(central, resultados, opciones)
        self.mostrarResultados(central, resultados, opciones)


InterfazMareomotriz().ejecutar()
