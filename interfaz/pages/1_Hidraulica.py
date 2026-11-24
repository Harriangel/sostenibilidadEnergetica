import tempfile
from pathlib import Path

import polars as pl
import streamlit as st

from energias.hidraulica.analisisCaudalDiseno import AnalisisCaudalDiseno
from energias.hidraulica.calculadoraPotencia import CalculadoraPotencia
from energias.hidraulica.disenoCanal import DisenoCanal
from energias.hidraulica.disenoTuberiaForzada import DisenoTuberiaForzada
from energias.hidraulica.graficador import Graficador

# interfaz/pages/1_Hidraulica.py -> raíz del repositorio
carpetaRaiz = Path(__file__).resolve().parents[2]
carpetaOutputs = carpetaRaiz / "outputs" / "hidraulica"


class InterfazStreamlit:
    """Interfaz web (Streamlit) para ejecutar el análisis de caudal de diseño.

    Página de la hidráulica dentro de la interfaz multipágina.
    Barra lateral: fuente, archivo y parámetros. Zona central: resultados.
    Ejecución (desde la carpeta raíz del proyecto):
        python -m streamlit run interfaz/app.py
    Las claves de st.session_state llevan el prefijo de la tecnología ('hidraulica_').
    """

    prefijoEstado = "hidraulica_"

    nombresTurbinas = ["Pelton", "Ossberger", "Kaplan", "Semikaplan", "Francis", "Hélice"]
    unidadesEnergia = ["W", "kW", "MW", "GW"]
    nombresFiguras = {
        "caudalesPorPeriodo": "Caudales por periodo",
        "caudalesClasificados": "Caudales clasificados",
        "energiaDiariaClasificada": "Energía diaria",
        "energiaAnualVsCaudalEquipamiento": "Energía vs Qe",
    }

    def __init__(self):
        self.carpetaRaiz = carpetaRaiz
        self.carpetaData = self.carpetaRaiz / "data" / "hidraulica"

    @classmethod
    def clave(cls, nombre: str) -> str:
        """Clave de st.session_state (o de un widget) con el prefijo de la tecnología."""
        return f"{cls.prefijoEstado}{nombre}"

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
        barra.title("Parámetros del módulo 1")

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
            st.session_state.pop(self.clave("resultadosAnalisis"), None)
            st.error(f"No se pudo completar el análisis: {error}")
            return

        st.session_state[self.clave("resultadosAnalisis")] = {
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
            "Descargar PNG", bytesFiguras[nombre]["png"], f"{nombre}.png", "image/png", key=self.clave(f"png_{nombre}")
        )
        columnaSvg.download_button(
            "Descargar SVG", bytesFiguras[nombre]["svg"], f"{nombre}.svg", "image/svg+xml", key=self.clave(f"svg_{nombre}")
        )

    def mostrarTabla(self, titulo: str, df, nombreArchivo: str) -> None:
        st.subheader(titulo)
        st.dataframe(df)
        st.download_button(
            "Descargar CSV", df.write_csv().encode("utf-8"), nombreArchivo, "text/csv", key=self.clave(f"csv_{nombreArchivo}")
        )

    def mostrarResultados(self) -> None:
        estado = st.session_state[self.clave("resultadosAnalisis")]
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

    # ------------------------------------------------------------------
    # Figuras de los módulos 2 y 3 (se generan al vuelo y se guardan en caché)
    # ------------------------------------------------------------------
    @staticmethod
    @st.cache_data(show_spinner=False)
    def crearBytesSeccion(seccion: dict) -> dict:
        graficador = Graficador(carpetaOutputs)
        fig = graficador.crearFiguraSeccionCanal(seccion)
        return {formato: graficador.figuraABytes(fig, formato) for formato in ("png", "svg")}

    @staticmethod
    @st.cache_data(show_spinner=False)
    def crearBytesMoody(reynolds: float, factorFriccion: float, rugosidadRelativa: float, metodo: str) -> dict:
        graficador = Graficador(carpetaOutputs)
        fig = graficador.crearFiguraMoody(reynolds, factorFriccion, rugosidadRelativa, metodo)
        return {formato: graficador.figuraABytes(fig, formato) for formato in ("png", "svg")}

    @staticmethod
    @st.cache_data(show_spinner=False)
    def crearBytesConvergencia(iteraciones: list, diametros: list, errores: list, tolerancia: float) -> dict:
        graficador = Graficador(carpetaOutputs)
        dfHistorial = pl.DataFrame(
            {"Iteracion": iteraciones, "DiametroCalculado_m": diametros, "ErrorRelativo_pct": errores}
        )
        fig = graficador.crearFiguraConvergencia(dfHistorial, tolerancia)
        return {formato: graficador.figuraABytes(fig, formato) for formato in ("png", "svg")}

    def mostrarFiguraConBytes(self, bytesFigura: dict, nombre: str) -> None:
        st.image(bytesFigura["png"])
        columnaPng, columnaSvg, _ = st.columns([1, 1, 4])
        columnaPng.download_button(
            "Descargar PNG", bytesFigura["png"], f"{nombre}.png", "image/png", key=self.clave(f"png_{nombre}")
        )
        columnaSvg.download_button(
            "Descargar SVG", bytesFigura["svg"], f"{nombre}.svg", "image/svg+xml", key=self.clave(f"svg_{nombre}")
        )

    def guardarEnOutputs(self, tablas: dict, figuras: dict) -> None:
        """Guarda csv ({nombre: dataframe}) y figuras ({nombre: bytes png/svg}) en outputs."""
        carpetaOutputs.mkdir(parents=True, exist_ok=True)
        for nombre, df in tablas.items():
            df.write_csv(carpetaOutputs / f"{nombre}.csv")
        for nombre, bytesFigura in figuras.items():
            for formato, contenido in bytesFigura.items():
                (carpetaOutputs / f"{nombre}.{formato}").write_bytes(contenido)
        st.success(f"Resultados guardados en {carpetaOutputs} (se sobrescriben los anteriores).")

    def obtenerCaudalDiseno(self):
        """Caudal de equipamiento (m³/s) del módulo 1, o None si aún no se calculó."""
        estado = st.session_state.get(self.clave("resultadosAnalisis"))
        if estado is None:
            st.info(
                "Primero calcula el módulo 1: el caudal de diseño es el caudal de equipamiento (Qe) "
                "de energía máxima."
            )
            return None, None
        return estado["resultados"]["maximo"]["CaudalEquipamiento"], estado["analisis"].calculadora

    # ------------------------------------------------------------------
    # Módulo 2: canal de derivación
    # ------------------------------------------------------------------
    def mostrarCanal(self) -> None:
        st.subheader("Canal de derivación (sección trapezoidal)")
        caudalDiseno, calculadora = self.obtenerCaudalDiseno()
        if caudalDiseno is None:
            return
        st.metric("Caudal de diseño (Qe del módulo 1)", f"{caudalDiseno:.2f} m³/s")

        columnaDatos, columnaMaterial, columnaPendiente = st.columns(3)
        with columnaDatos:
            modo = st.radio("Qué calcular", ["Dimensionar para el caudal de diseño", "Verificar una sección dada"])
            dimensionar = modo.startswith("Dimensionar")
            base = st.number_input("Ancho de la base y (m)", min_value=0.1, value=1.2, step=0.1)
            if dimensionar:
                talud = st.number_input("Talud (proyección horizontal / altura)", min_value=0.0, value=2.0, step=0.25)
            else:
                anchoSuperior = st.number_input("Ancho superior x (m)", min_value=0.1, value=5.2, step=0.1)
                profundidad = st.number_input("Profundidad z (m)", min_value=0.1, value=1.0, step=0.1)
        with columnaMaterial:
            material = st.selectbox("Material del canal", list(DisenoCanal.coeficientesManning) + ["Otro"])
            if material == "Otro":
                coeficienteManning = st.number_input(
                    "Coeficiente de Manning n", min_value=0.005, max_value=0.2, value=0.015, step=0.001, format="%.3f"
                )
            else:
                coeficienteManning = DisenoCanal.coeficientesManning[material]
                st.caption(f"n = {coeficienteManning}")
        with columnaPendiente:
            definePorCotas = st.radio("Pendiente", ["Por cotas y longitud", "Directa"]).startswith("Por")
            if definePorCotas:
                cotaArriba = st.number_input("Cota aguas arriba (m)", value=1.1, step=0.1)
                cotaAbajo = st.number_input("Cota aguas abajo (m)", value=1.0, step=0.1)
                longitud = st.number_input("Longitud del canal L (m)", min_value=0.1, value=100.0, step=10.0)
                pendiente = DisenoCanal.calcularPendiente(cotaArriba, cotaAbajo, longitud)
                st.caption(f"s = {pendiente:.5f}")
            else:
                pendiente = st.number_input("Pendiente s (m/m)", min_value=0.00001, value=0.001, step=0.0001, format="%.5f")

        try:
            canal = DisenoCanal(coeficienteManning, pendiente, calculadora.gravedad)
            if dimensionar:
                seccion = canal.dimensionarParaCaudal(caudalDiseno, base, talud)
            else:
                seccion = canal.evaluarSeccion(anchoSuperior, base, profundidad)
        except ValueError as error:
            st.error(f"No se pudo calcular el canal: {error}")
            return

        columnas = st.columns(5)
        columnas[0].metric("Caudal Q (m³/s)", f"{seccion['Q']:.3f}")
        columnas[1].metric("Profundidad z (m)", f"{seccion['z']:.3f}")
        columnas[2].metric("Ancho superior x (m)", f"{seccion['x']:.3f}")
        columnas[3].metric("Velocidad v (m/s)", f"{seccion['v']:.3f}")
        columnas[4].metric("Número de Froude", f"{seccion['Froude']:.3f}")

        if not dimensionar:
            if seccion["Q"] >= caudalDiseno:
                st.success(f"La sección conduce {seccion['Q']:.2f} m³/s, suficiente para el caudal de diseño ({caudalDiseno:.2f} m³/s).")
            else:
                st.warning(f"La sección solo conduce {seccion['Q']:.2f} m³/s y no alcanza el caudal de diseño ({caudalDiseno:.2f} m³/s).")
        st.info(f"Con Fr = {seccion['Froude']:.3f} el flujo es {seccion['tipoFlujo']}.")
        with st.expander("¿Qué es el número de Froude y para qué se usa?"):
            st.markdown(
                "El número de Froude compara la velocidad del agua con la velocidad con la que viaja una "
                "pequeña onda sobre su superficie: **Fr = v / √(g·A/x)**. "
                "Con Fr < 1 el flujo es **subcrítico** (lento y profundo; es el régimen habitual y estable de un canal de "
                "derivación). Con Fr > 1 es **supercrítico** (rápido y somero; puede erosionar y formar resaltos hidráulicos). "
                "Cerca de 1 el flujo es inestable y con oleaje, por lo que, como regla práctica, se evitan valores "
                "aproximadamente entre 0,8 y 1,2."
            )

        figura = self.crearBytesSeccion(seccion)
        st.image(figura["png"])
        dfCanal = pl.DataFrame(
            {
                "Variable": [
                    "Ancho superior x", "Ancho de la base y", "Profundidad z", "Lado inclinado w",
                    "Talud (proyección/altura)", "Área A", "Perímetro mojado Pm", "Radio hidráulico Rh",
                    "Pendiente s", "Coeficiente de Manning n", "Caudal Q", "Velocidad v",
                    "Profundidad hidráulica A/x", "Número de Froude Fr",
                ],
                "Valor": [
                    seccion["x"], seccion["y"], seccion["z"], seccion["w"], seccion["talud"], seccion["A"],
                    seccion["Pm"], seccion["Rh"], pendiente, coeficienteManning, seccion["Q"], seccion["v"],
                    seccion["profundidadHidraulica"], seccion["Froude"],
                ],
                "Unidad": ["m", "m", "m", "m", "-", "m²", "m", "m", "m/m", "-", "m³/s", "m/s", "m", "-"],
            }
        )
        columnaPng, columnaSvg, _ = st.columns([1, 1, 4])
        columnaPng.download_button("Descargar PNG", figura["png"], "seccionCanal.png", "image/png", key=self.clave("png_seccionCanal"))
        columnaSvg.download_button("Descargar SVG", figura["svg"], "seccionCanal.svg", "image/svg+xml", key=self.clave("svg_seccionCanal"))
        st.dataframe(dfCanal)
        st.download_button("Descargar CSV", dfCanal.write_csv().encode("utf-8"), "canalDerivacion.csv", "text/csv", key=self.clave("csv_canal"))
        if st.button("Guardar el canal en la carpeta outputs"):
            self.guardarEnOutputs({"canalDerivacion": dfCanal}, {"seccionCanal": figura})

        with st.expander("Fórmulas utilizadas"):
            st.latex(r"s = \frac{\text{cota aguas arriba} - \text{cota aguas abajo}}{L}")
            st.latex(r"w = \sqrt{z^{2} + \left(\frac{x - y}{2}\right)^{2}} \qquad A = \frac{x + y}{2}\, z")
            st.latex(r"P_m = 2w + y \qquad R_h = \frac{A}{P_m}")
            st.latex(r"Q = \frac{R_h^{2/3}\, A\, s^{1/2}}{n} \qquad v = \frac{Q}{A}")
            st.latex(r"Fr = \frac{v}{\sqrt{g\, A / x}}")
            st.caption(
                "x: ancho superior; y: ancho de la base; z: profundidad del agua; w: lado inclinado; "
                "A: área; Pm: perímetro mojado; Rh: radio hidráulico; n: coeficiente de Manning; s: pendiente. "
                "Al dimensionar, z se obtiene resolviendo la ecuación de Manning para el caudal de diseño."
            )

    # ------------------------------------------------------------------
    # Módulo 3: tubería forzada
    # ------------------------------------------------------------------
    def mostrarTuberia(self) -> None:
        st.subheader("Tubería forzada: diámetro económico")
        caudalDiseno, calculadora = self.obtenerCaudalDiseno()
        if caudalDiseno is None:
            return
        st.metric("Caudal de diseño (Qe del módulo 1)", f"{caudalDiseno:.2f} m³/s")

        columnaMaterial, columnaEconomia, columnaMoneda = st.columns(3)
        with columnaMaterial:
            materiales = DisenoTuberiaForzada.rugosidadPorMaterial()
            material = st.selectbox("Material de la tubería", list(materiales) + ["Otro (ingresar ε en mm)"], index=6)
            if material.startswith("Otro"):
                rugosidadMm = st.number_input("Rugosidad absoluta ε (mm)", min_value=0.0, value=0.2, step=0.01, format="%.4f")
            else:
                rugosidadMm = materiales[material]
                st.caption(f"ε = {rugosidadMm:g} mm")
            viscosidad = st.number_input("Viscosidad dinámica μ (Pa·s)", min_value=0.00001, value=0.001, step=0.0001, format="%.5f")
            metodoFriccion = st.selectbox("Método para el factor de fricción f", DisenoTuberiaForzada.metodosFriccion)
            tolerancia = st.number_input("Tolerancia del error relativo (%)", min_value=0.001, max_value=50.0, value=5.0, step=0.5) / 100
        with columnaMoneda:
            moneda = st.text_input("Moneda", value="USD").strip().upper() or "USD"
            tasaCambio = 1.0
            if moneda != "USD":
                tasaCambio = st.number_input(
                    f"Tasa de cambio ({moneda} por 1 USD)", min_value=0.000001, value=1.0, format="%.4f"
                )
                st.caption("La correlación de costos de la tubería está en dólares y se convierte con esta tasa.")
            velocidadInicial = st.number_input("Velocidad inicial supuesta (m/s)", min_value=0.1, value=2.5, step=0.1)
        with columnaEconomia:
            horasFuncionamiento = st.number_input("Horas de funcionamiento por año h", min_value=1.0, max_value=8760.0, value=6000.0, step=100.0)
            precioEnergia = st.number_input(f"Precio de la energía p ({moneda}/kWh)", min_value=0.0001, value=0.27, step=0.01, format="%.4f")
            eficienciaGlobal = st.number_input(
                "Eficiencia global η (por defecto la del módulo 1)",
                min_value=0.01, max_value=1.0, value=round(calculadora.eficienciaTotal, 4), step=0.01, format="%.3f",
            )
            factorAmortizacion = st.number_input("Factor de amortización a", min_value=0.001, max_value=1.0, value=0.064, step=0.001, format="%.3f")

        try:
            tuberia = DisenoTuberiaForzada(
                rugosidadMm=rugosidadMm,
                densidadAgua=calculadora.densidadAgua,
                viscosidad=viscosidad,
                horasFuncionamiento=horasFuncionamiento,
                precioEnergia=precioEnergia,
                eficienciaGlobal=eficienciaGlobal,
                factorAmortizacion=factorAmortizacion,
                metodoFriccion=metodoFriccion,
                tolerancia=tolerancia,
                velocidadInicial=velocidadInicial,
                moneda=moneda,
                tasaCambio=tasaCambio,
            )
            iteracion = tuberia.iterarDiametro(caudalDiseno)
        except ValueError as error:
            st.error(f"No se pudo calcular la tubería: {error}")
            return

        resultado = iteracion["resultado"]
        dfHistorial = iteracion["historial"]
        columnas = st.columns(6)
        columnas[0].metric("Diámetro económico D (m)", f"{resultado['diametro']:.3f}")
        columnas[1].metric("Diámetro (mm)", f"{resultado['diametro'] * 1000:,.0f}")
        columnas[2].metric("Velocidad v (m/s)", f"{resultado['velocidad']:.3f}")
        columnas[3].metric("Factor de fricción f", f"{resultado['factorFriccion']:.4f}")
        columnas[4].metric(f"Costo ({moneda}/m)", f"{resultado['costoTuberia']:,.2f}")
        columnas[5].metric("Espesor e (mm)", f"{resultado['espesor']:.2f}")

        if iteracion["converge"]:
            st.success(
                f"Convergió en {iteracion['iteraciones']} iteraciones con un error relativo de "
                f"{iteracion['errorFinal'] * 100:.2f} % (tolerancia {tolerancia * 100:g} %). "
                f"Re = {resultado['reynolds']:,.0f} (flujo {resultado['regimen']})."
            )
        else:
            st.warning(
                f"No convergió en {tuberia.maxIteraciones} iteraciones (error {iteracion['errorFinal'] * 100:.2f} %)."
            )
        if resultado["regimen"] != "turbulento":
            st.caption("Con Re < 4000 el flujo no es turbulento y las ecuaciones de fricción de Colebrook y Swamee-Jain pierden validez.")

        st.markdown("**Factor de fricción con cada método** (al diámetro final)")
        dfMetodos = tuberia.compararMetodosFriccion(resultado["reynolds"], resultado["rugosidadRelativa"])
        st.dataframe(dfMetodos)

        figuraMoody = self.crearBytesMoody(
            resultado["reynolds"], resultado["factorFriccion"], resultado["rugosidadRelativa"], metodoFriccion
        )
        st.markdown("**Diagrama de Moody**")
        self.mostrarFiguraConBytes(figuraMoody, "diagramaMoody")

        figuraConvergencia = self.crearBytesConvergencia(
            dfHistorial["Iteracion"].to_list(),
            dfHistorial["DiametroCalculado_m"].to_list(),
            dfHistorial["ErrorRelativo_pct"].to_list(),
            tolerancia,
        )
        st.markdown("**Iteraciones del diámetro económico**")
        self.mostrarFiguraConBytes(figuraConvergencia, "convergenciaDiametro")
        st.dataframe(dfHistorial)
        st.download_button(
            "Descargar CSV", dfHistorial.write_csv().encode("utf-8"), "tuberiaForzadaIteraciones.csv", "text/csv", key=self.clave("csv_tuberia")
        )

        if st.button("Guardar la tubería forzada en la carpeta outputs"):
            self.guardarEnOutputs(
                {"tuberiaForzadaIteraciones": dfHistorial, "tuberiaForzadaMetodosFriccion": dfMetodos},
                {"diagramaMoody": figuraMoody, "convergenciaDiametro": figuraConvergencia},
            )

        with st.expander("Fórmulas utilizadas"):
            st.latex(r"v = \frac{4Q}{\pi D^{2}} \qquad Re = \frac{\rho\, v\, D}{\mu} \qquad \varepsilon_r = \frac{\varepsilon}{D}")
            st.latex(r"\text{Laminar } (Re < 2000):\quad f = \frac{64}{Re}")
            st.latex(r"\text{Colebrook-White:}\quad \frac{1}{\sqrt{f}} = -2\log_{10}\left(\frac{\varepsilon_r}{3{,}7} + \frac{2{,}51}{Re\sqrt{f}}\right)")
            st.latex(r"\text{Swamee-Jain:}\quad f = \frac{0{,}25}{\left[\log_{10}\left(\dfrac{\varepsilon_r}{3{,}7} + \dfrac{5{,}74}{Re^{0{,}9}}\right)\right]^{2}}")
            st.latex(r"c = k\,\left(12{,}16 + 513{,}5\, D^{1{,}5}\right) \qquad e = \frac{D + 508}{400}\ \ (D \text{ y } e \text{ en mm})")
            st.latex(r"D_{eco} = 1{,}106\left(\frac{f\, h\, p}{\eta\, a\, c}\right)^{0{,}143} Q^{0{,}43}")
            st.latex(r"\text{Error relativo} = \frac{|D_{n+1} - D_{n}|}{D_{n+1}} \le \text{tolerancia}")
            st.caption(
                "Q: caudal de diseño (m³/s); D: diámetro (m); ρ: densidad del agua; μ: viscosidad dinámica; "
                "ε: rugosidad absoluta; f: factor de fricción de Darcy; h: horas de funcionamiento al año; "
                "p: precio de la energía; η: eficiencia global; a: factor de amortización; c: costo por metro; "
                "k: tasa de cambio desde dólares (1 si la moneda es USD). En cada iteración se recalculan v, Re, f y c "
                "con el diámetro del paso anterior."
            )
        with st.expander("Tabla de rugosidad absoluta de materiales"):
            st.dataframe(DisenoTuberiaForzada.tablaRugosidadDataFrame())
            st.caption("Del concreto, que se da como rango, se usa el valor medio; con «Otro» puedes ingresar un valor propio.")

    def ejecutar(self) -> None:
        st.set_page_config(page_title="Hidráulica · caudal de diseño", layout="wide")
        st.title("Análisis de caudal de diseño para una central hidroeléctrica")

        parametros, calcularPresionado = self.mostrarBarraLateral()
        if calcularPresionado:
            self.calcular(parametros)

        pestanaModulo1, pestanaCanal, pestanaTuberia = st.tabs(
            ["1. Caudal de equipamiento", "2. Canal de derivación", "3. Tubería forzada"]
        )
        with pestanaModulo1:
            if self.clave("resultadosAnalisis") in st.session_state:
                self.mostrarResultados()
            else:
                st.info(
                    "Elige la fuente y el archivo en la barra lateral, ajusta los parámetros y pulsa **Calcular**."
                )
        with pestanaCanal:
            self.mostrarCanal()
        with pestanaTuberia:
            self.mostrarTuberia()


InterfazStreamlit().ejecutar()
