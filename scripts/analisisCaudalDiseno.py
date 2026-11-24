from pathlib import Path

import polars as pl

from calculadoraPotencia import CalculadoraPotencia
from graficador import Graficador
from lectorDatos import LectorDatos
from procesadorCaudales import ProcesadorCaudales


class AnalisisCaudalDiseno:
    """Clase principal: ejecuta el pipeline de análisis de caudales históricos
    para determinar el caudal de diseño de una potencial central hidroeléctrica."""

    # Archivo que se busca en 'data' si no se indica nombreArchivo
    archivosPorDefecto = {"IDEAM": "descargaDhime.csv", "CONAGUA": "SAACP.csv"}

    def __init__(
        self,
        fuente: str = "IDEAM",
        nombreArchivo: str = None,
        saltoNeto: float = 10,
        tipoTurbina: str = "Kaplan",
        unidadEnergia: str = "kW",
        densidadAgua: float = 1000,
        gravedad: float = 9.8,
        eficienciaTurbina: float = 0.85,
        eficienciaGenerador: float = 0.95,
        eficienciaTotal: float = None,
        pasoQe: float = None,
        minDiasPorPeriodo: int = 300,
    ):
        self.carpetaRaiz = Path(__file__).resolve().parent.parent
        self.carpetaData = self.carpetaRaiz / "data"
        self.carpetaSalidas = self.carpetaRaiz / "outputs"
        self.fuente = fuente.strip().upper()
        if nombreArchivo is None:
            nombreArchivo = self.archivosPorDefecto.get(self.fuente, "")
        self.rutaDatos = self.carpetaData / nombreArchivo

        self.lector = LectorDatos(self.rutaDatos, self.fuente)
        self.procesador = ProcesadorCaudales(minDiasPorPeriodo=minDiasPorPeriodo)
        self.graficador = Graficador(self.carpetaSalidas)
        self.calculadora = CalculadoraPotencia(
            saltoNeto=saltoNeto,
            tipoTurbina=tipoTurbina,
            unidadEnergia=unidadEnergia,
            densidadAgua=densidadAgua,
            gravedad=gravedad,
            eficienciaTurbina=eficienciaTurbina,
            eficienciaGenerador=eficienciaGenerador,
            eficienciaTotal=eficienciaTotal,
            pasoQe=pasoQe,
        )

    def imprimirResumenPeriodos(self) -> None:
        dfResumen = self.procesador.dfResumenPeriodos
        print("\nCobertura por periodo (29 de febrero excluido):")
        with pl.Config(tbl_rows=-1):
            print(dfResumen)
        dfIncluidos = dfResumen.filter(pl.col("Incluido"))
        print(
            f"\nPeriodos incluidos (mínimo {self.procesador.minDiasPorPeriodo} días): "
            f"{dfIncluidos.height} de {dfResumen.height} | "
            f"días faltantes por completar: {dfIncluidos['DiasFaltantes'].sum()}"
        )

    def imprimirMaximo(self, dfEnergia: pl.DataFrame) -> None:
        maximo = self.calculadora.identificarMaximo(dfEnergia)
        nombreEnergia = self.calculadora.nombreColumnaEnergia
        print(
            f"\nTurbina {self.calculadora.tipoTurbina.capitalize()} (K = {self.calculadora.factorK}), "
            f"salto neto {self.calculadora.saltoNeto} m, "
            f"eficiencia total {self.calculadora.eficienciaTotal:.3f}, "
            f"paso de Qe {self.calculadora.pasoQeUtilizado} m³/s"
        )
        print(
            f"Energía anual máxima: {maximo[nombreEnergia]:,.1f} "
            f"{self.calculadora.unidadEnergia}h/año con Qe = {maximo['CaudalEquipamiento']:.2f} m³/s"
        )

    def ejecutar(self) -> pl.DataFrame:
        # 1 y 2. Leer el archivo (según la fuente) y extraer Fecha (date) y Valor (float)
        print(f"Fuente: {self.fuente} | archivo: {self.rutaDatos.name}")
        dfDatos = self.lector.leer()
        dfDatos = self.procesador.renombrarCaudal(dfDatos)

        # 3. Añadir Ano, Mes y Dia
        dfDatos = self.procesador.agregarColumnasFecha(dfDatos)

        # 4. Asignar los periodos anuales de octubre a septiembre (mínimo de días)
        dfDatos = self.procesador.asignarPeriodosAnuales(dfDatos)
        self.imprimirResumenPeriodos()

        # 5. Numerar los días de 1 a 365 (incluye las fechas faltantes)
        dfDatos = self.procesador.numerarDias(dfDatos)

        # 6. Gráfica NumDia vs Caudal de todos los periodos
        self.graficador.graficarCaudalesPorPeriodo(dfDatos, "caudalesPorPeriodo")

        # 7. Caudal clasificado de mayor a menor dentro de cada periodo
        dfDatos = self.procesador.clasificarCaudales(dfDatos)

        # 8. Promedio del caudal clasificado de todos los periodos
        dfDatos = self.procesador.calcularPromedioClasificado(dfDatos)

        # 9. Gráfica NumDia vs CaudalClasificado con la línea promedio
        self.graficador.graficarCaudalesClasificados(dfDatos, "caudalesClasificados")

        # 10. Exportar NumDia y CaudalClasificadoPromedio
        dfResultado = self.procesador.construirResultado(dfDatos)
        dfResultado.write_csv(self.carpetaSalidas / "caudalClasificadoPromedio.csv")

        # 11. Energía anual para cada caudal de equipamiento y máximo
        dfEnergia = self.calculadora.calcularEnergiaPorCaudalEquipamiento(dfResultado)
        dfEnergia.write_csv(self.carpetaSalidas / "energiaAnualPorCaudalEquipamiento.csv")
        with pl.Config(tbl_rows=25):
            print(f"\nEnergía anual por caudal de equipamiento:\n{dfEnergia}")
        self.imprimirMaximo(dfEnergia)
        self.graficador.graficarEnergiaVsCaudalEquipamiento(
            dfEnergia,
            self.calculadora.nombreColumnaEnergia,
            self.calculadora.unidadEnergia,
            "energiaAnualVsCaudalEquipamiento",
        )

        print(f"\nResultados exportados en: {self.carpetaSalidas}")
        return dfEnergia


if __name__ == "__main__":
    # Parámetros editables
    AnalisisCaudalDiseno(
        fuente="CONAGUA",        # IDEAM (Colombia) o CONAGUA (México)
        nombreArchivo=None,      # None usa el archivo por defecto de la fuente; o ej. "SAACP.csv"
        minDiasPorPeriodo=300,   # días con dato mínimos para incluir un periodo
        saltoNeto=150,           # metros
        tipoTurbina="Francis",   # Pelton, Ossberger, Kaplan, Semikaplan, Francis o Hélice
        unidadEnergia="kW",      # W, kW, MW o GW (la energía se expresa en Wh, kWh, MWh o GWh)
        densidadAgua=1000,       # kg/m³
        gravedad=9.8,            # m/s²
        eficienciaTurbina=0.85,  # ηg (se ignora si se indica eficienciaTotal)
        eficienciaGenerador=0.95,  # ηG (se ignora si se indica eficienciaTotal)
        eficienciaTotal=0.88,    # ηg*ηG; con None se usa ηg*ηG
        pasoQe=None,             # None: automático según el caudal máximo; o un valor en m³/s
    ).ejecutar()
