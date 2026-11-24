import tempfile
from pathlib import Path

import streamlit as st

from analisisCaudalDiseno import AnalisisCaudalDiseno
from calculadoraPotencia import CalculadoraPotencia


class InterfazStreamlit:
    """Interfaz web (Streamlit) para ejecutar el análisis de caudal de diseño.

    Barra lateral: fuente, archivo y parámetros. Zona central: resultados.
    Ejecución (desde la carpeta raíz del proyecto):
        python -m streamlit run scripts/interfazStreamlit.py
    """

    nombresTurbinas = ["Pelton", "Ossberger", "Kaplan", "Semikaplan", "Francis", "Hélice"]
    unidadesEnergia = ["W", "kW", "MW", "GW"]
    nombresFiguras = {
        "caudalesPorPeriodo": "Caudales por periodo",
        "caudalesClasificados": "Caudales clasificados",
        "energiaDiariaClasificada": "Energía diaria",
        "energiaAnualVsCaudalEquipamiento": "Energía vs Qe",
    }

    def __init__(self):
        self.carpetaRaiz = Path(__file__).resolve().parent.parent
        self.carpetaData = self.carpetaRaiz / "data"

    # ------------------------------------------------------------------
    # Entradas
    # ------------------------------------------------------------------
    def listarArchivosData(self) -> list:
        if not self.carpetaData.exists():
            return []
        return sorted(archivo.name for archivo in self.carpetaData.glob("*.csv"))

    def guardarArchivoSubido(self, archivoSubido) -> Path:
        """Guarda el archivo subido en una carpeta temporal (no toca 'data')."""
        carpetaTemporal = Path(tempfile.mkdtemp(prefix="analisisCaudal_"))
        rutaTemporal = carpetaTemporal / archivoSubido.name
        rutaTemporal.write_bytes(archivoSubido.getvalue())
        return rutaTemporal

    def mostrarBarraLateral(self) -> tuple:
        """Dibuja los controles. Devuelve (parametros, calcularPresionado)."""
        barra = st.sidebar
        barra.title("Parámetros")

        barra.subheader("Datos")
        fuente = barra.selectbox("Fuente del archivo", ["IDEAM", "CONAGUA"])
        origenArchivo = barra.radio("Archivo", ["Carpeta data", "Subir archivo"], horizontal=True)

        nombreArchivo, archivoSubido = None, None
        if origenArchivo == "Carpeta data":
            archivos = self.listarArchivosData()
            if archivos:
                archivoPorDefecto = AnalisisCaudalDiseno.archivosPorDefecto[fuente]
                indice = archivos.index(archivoPorDefecto) if archivoPorDefecto in archivos else 0
                nombreArchivo = barra.selectbox("Archivo en la carpeta data", archivos, index=indice)
            else:
                barra.warning("No hay archivos .csv en la carpeta data.")
        else:
            archivoSubido = barra.file_uploader("Archivo .csv", type=["csv"])

        minDiasPorPeriodo = barra.number_input(
            "Días mínimos con dato por periodo", min_value=1, max_value=365, value=300, step=1
        )

        barra.subheader("Salto y turbina")
        saltoNeto = barra.number_input("Salto neto H (m)", min_value=0.1, value=10.0, step=1.0)
        tipoTurbina = barra.selectbox("Tipo de turbina", self.nombresTurbinas, index=2)
        factorK = CalculadoraPotencia.factoresK[CalculadoraPotencia.normalizarTexto(tipoTurbina)]
        barra.caption(f"Factor K = {factorK}  (Qmt = Qe × K)")

        barra.subheader("Eficiencia")
        modoEficiencia = barra.radio(
            "Definir", ["Eficiencia total (ηg·ηG)", "Turbina y generador por separado"]
        )
        eficienciaTotal, eficienciaTurbina, eficienciaGenerador = None, 0.85, 0.95
        if modoEficiencia.startswith("Eficiencia total"):
            eficienciaTotal = barra.number_input(
                "Eficiencia total", min_value=0.01, max_value=1.0, value=0.88, step=0.01
            )
        else:
            eficienciaTurbina = barra.number_input(
                "Eficiencia de la turbina ηg", min_value=0.01, max_value=1.0, value=0.85, step=0.01
            )
            eficienciaGenerador = barra.number_input(
                "Eficiencia del generador ηG", min_value=0.01, max_value=1.0, value=0.95, step=0.01
            )

        with barra.expander("Constantes físicas"):
            densidadAgua = st.number_input("Densidad del agua ρ (kg/m³)", min_value=1.0, value=1000.0)
            gravedad = st.number_input("Gravedad g (m/s²)", min_value=1.0, value=9.8, step=0.1)

        barra.subheader("Resultados")
        unidadEnergia = barra.selectbox("Unidad de potencia y energía", self.unidadesEnergia, index=1)
        pasoAutomatico = barra.checkbox("Paso de Qe automático", value=True)
        pasoQe = None
        if not pasoAutomatico:
            pasoQe = barra.number_input("Paso de Qe (m³/s)", min_value=0.001, value=1.0, format="%.3f")

        calcularPresionado = barra.button("Calcular", type="primary")

        parametros = {
            "fuente": fuente,
            "nombreArchivo": nombreArchivo,
            "archivoSubido": archivoSubido,
            "minDiasPorPeriodo": int(minDiasPorPeriodo),
            "saltoNeto": saltoNeto,
            "tipoTurbina": tipoTurbina,
            "eficienciaTotal": eficienciaTotal,
            "eficienciaTurbina": eficienciaTurbina,
            "eficienciaGenerador": eficienciaGenerador,
            "densidadAgua": densidadAgua,
            "gravedad": gravedad,
            "unidadEnergia": unidadEnergia,
            "pasoQe": pasoQe,
        }
        return parametros, calcularPresionado

    # ------------------------------------------------------------------
    # Cálculo
    # ------------------------------------------------------------------
    def calcular(self, parametros: dict) -> None:
        """Ejecuta el análisis y guarda los resultados en st.session_state."""
        parametrosAnalisis = {
            clave: valor for clave, valor in parametros.items() if clave not in ("nombreArchivo", "archivoSubido")
        }
        if parametros["archivoSubido"] is not None:
            parametrosAnalisis["rutaArchivo"] = self.guardarArchivoSubido(parametros["archivoSubido"])
        elif parametros["nombreArchivo"] is not None:
            parametrosAnalisis["nombreArchivo"] = parametros["nombreArchivo"]
        else:
            st.error("Selecciona o sube un archivo .csv antes de calcular.")
            return

        try:
            with st.spinner("Calculando..."):
                analisis = AnalisisCaudalDiseno(**parametrosAnalisis)
                resultados = analisis.calcular()
                figuras = analisis.crearFiguras(resultados)
                bytesFiguras = {
                    nombre: {
                        formato: analisis.graficador.figuraABytes(fig, formato) for formato in ("png", "svg")
                    }
                    for nombre, fig in figuras.items()
                }
        except (ValueError, FileNotFoundError, KeyError) as error:
            st.session_state.pop("resultadosAnalisis", None)
            st.error(f"No se pudo completar el análisis: {error}")
            return

        st.session_state["resultadosAnalisis"] = {
            "analisis": analisis,
            "resultados": resultados,
            "figuras": figuras,
            "bytesFiguras": bytesFiguras,
            "archivo": analisis.rutaDatos.name,
        }

    # ------------------------------------------------------------------
    # Salidas
    # ------------------------------------------------------------------
    def botonesDescargaFigura(self, nombre: str, bytesFiguras: dict) -> None:
        columnaPng, columnaSvg, _ = st.columns([1, 1, 4])
        columnaPng.download_button(
            "Descargar PNG", bytesFiguras[nombre]["png"], f"{nombre}.png", "image/png", key=f"png_{nombre}"
        )
        columnaSvg.download_button(
            "Descargar SVG", bytesFiguras[nombre]["svg"], f"{nombre}.svg", "image/svg+xml", key=f"svg_{nombre}"
        )

    def mostrarTabla(self, titulo: str, df, nombreArchivo: str) -> None:
        st.subheader(titulo)
        st.dataframe(df)
        st.download_button(
            "Descargar CSV", df.write_csv().encode("utf-8"), nombreArchivo, "text/csv", key=f"csv_{nombreArchivo}"
        )

    def mostrarResultados(self) -> None:
        estado = st.session_state["resultadosAnalisis"]
        analisis, resultados = estado["analisis"], estado["resultados"]
        calculadora, procesador = analisis.calculadora, analisis.procesador
        nombreEnergia = calculadora.nombreColumnaEnergia
        maximo = resultados["maximo"]
        dfResumen = resultados["dfResumenPeriodos"]

        st.caption(
            f"{analisis.fuente} · {estado['archivo']} · H = {calculadora.saltoNeto:g} m · "
            f"turbina {calculadora.tipoTurbina.capitalize()} (K = {calculadora.factorK}) · "
            f"η total = {calculadora.eficienciaTotal:.3f}"
        )

        columnas = st.columns(4)
        columnas[0].metric(f"Energía anual máxima ({calculadora.unidadEnergia}h/año)", f"{maximo[nombreEnergia]:,.0f}")
        columnas[1].metric("Qe de energía máxima (m³/s)", f"{maximo['CaudalEquipamiento']:.2f}")
        columnas[2].metric(
            "Periodos incluidos", f"{dfResumen.filter(dfResumen['Incluido']).height} de {dfResumen.height}"
        )
        columnas[3].metric("Paso de Qe (m³/s)", f"{calculadora.pasoQeUtilizado:g}")
        st.caption(f"Caudal mínimo técnico en el óptimo: {maximo['CaudalMinimoTecnico']:.2f} m³/s")

        if st.button("Guardar resultados en la carpeta outputs"):
            carpeta = analisis.guardarResultados(resultados, estado["figuras"])
            st.success(f"Resultados guardados en {carpeta} (se sobrescriben los anteriores).")

        pestanas = st.tabs(list(self.nombresFiguras.values()) + ["Tablas"])
        for pestana, (nombre, titulo) in zip(pestanas, self.nombresFiguras.items()):
            with pestana:
                st.pyplot(estado["figuras"][nombre])
                self.botonesDescargaFigura(nombre, estado["bytesFiguras"])

        with pestanas[-1]:
            self.mostrarTabla("Cobertura por periodo", dfResumen, "coberturaPorPeriodo.csv")
            self.mostrarTabla("Caudal clasificado promedio", resultados["dfPromedio"], "caudalClasificadoPromedio.csv")
            self.mostrarTabla("Energía anual por caudal de equipamiento", resultados["dfEnergia"], "energiaAnualPorCaudalEquipamiento.csv")
            self.mostrarTabla(
                f"Energía diaria con Qe = {maximo['CaudalEquipamiento']:.2f} m³/s",
                resultados["dfEnergiaDiaria"],
                "energiaDiariaCaudalOptimo.csv",
            )

    def ejecutar(self) -> None:
        st.set_page_config(page_title="Caudal de diseño", layout="wide")
        st.title("Análisis de caudal de diseño para una central hidroeléctrica")

        parametros, calcularPresionado = self.mostrarBarraLateral()
        if calcularPresionado:
            self.calcular(parametros)

        if "resultadosAnalisis" in st.session_state:
            self.mostrarResultados()
        else:
            st.info(
                "Elige la fuente y el archivo en la barra lateral, ajusta los parámetros y pulsa **Calcular**."
            )


InterfazStreamlit().ejecutar()
