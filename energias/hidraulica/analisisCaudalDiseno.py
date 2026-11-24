from pathlib import Path

import polars as pl

from energias.hidraulica.calculadoraPotencia import CalculadoraPotencia
from energias.hidraulica.graficador import Graficador
from energias.hidraulica.lectorDatos import LectorDatos
from energias.hidraulica.procesadorCaudales import ProcesadorCaudales


class AnalisisCaudalDiseno:
    """Clase principal: ejecuta el pipeline de análisis de caudales históricos
    para determinar el caudal de diseño de una potencial central hidroeléctrica."""

    # Archivo que se busca en 'data' si no se indica nombreArchivo
    archivosPorDefecto = {"IDEAM": "descargaDhime.csv", "CONAGUA": "SAACP.csv"}

    def __init__(
        self,
        fuente: str = "IDEAM",
        nombreArchivo: str = None,
        rutaArchivo: Path = None,
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
        self.carpetaRaiz = Path(__file__).resolve().parents[2]
        self.carpetaData = self.carpetaRaiz / "data"
        self.carpetaSalidas = self.carpetaRaiz / "outputs"
        self.fuente = fuente.strip().upper()
        if nombreArchivo is None:
            nombreArchivo = self.archivosPorDefecto.get(self.fuente, "")
        # rutaArchivo (completa) tiene prioridad sobre nombreArchivo (dentro de 'data')
        self.rutaDatos = Path(rutaArchivo) if rutaArchivo is not None else self.carpetaData / nombreArchivo

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

    def calcular(self) -> dict:
        """Pipeline completo sin imprimir ni guardar: devuelve los resultados."""
        # 1 y 2. Leer el archivo (según la fuente) y extraer Fecha (date) y Valor (float)
        dfDatos = self.lector.leer()
        dfDatos = self.procesador.renombrarCaudal(dfDatos)

        # 3. Añadir Ano, Mes y Dia
        dfDatos = self.procesador.agregarColumnasFecha(dfDatos)

        # 4. Asignar los periodos anuales de octubre a septiembre (mínimo de días)
        dfDatos = self.procesador.asignarPeriodosAnuales(dfDatos)

        # 5. Numerar los días de 1 a 365 (incluye las fechas faltantes)
        dfCaudales = self.procesador.numerarDias(dfDatos)

        # 7. Caudal clasificado de mayor a menor dentro de cada periodo
        dfClasificado = self.procesador.clasificarCaudales(dfCaudales)

        # 8. Promedio del caudal clasificado de todos los periodos
        dfClasificado = self.procesador.calcularPromedioClasificado(dfClasificado)

        # 10. NumDia y CaudalClasificadoPromedio
        dfPromedio = self.procesador.construirResultado(dfClasificado)

        # 11. Energía anual para cada caudal de equipamiento y máximo
        dfEnergia = self.calculadora.calcularEnergiaPorCaudalEquipamiento(dfPromedio)

        # Energía de cada día para el caudal de equipamiento de energía máxima
        maximo = self.calculadora.identificarMaximo(dfEnergia)
        dfEnergiaDiaria = self.calculadora.calcularEnergiaDiariaEnUnidad(
            dfPromedio, maximo["CaudalEquipamiento"]
        )

        return {
            "dfResumenPeriodos": self.procesador.dfResumenPeriodos,
            "dfCaudales": dfCaudales,
            "dfClasificado": dfClasificado,
            "dfPromedio": dfPromedio,
            "dfEnergia": dfEnergia,
            "dfEnergiaDiaria": dfEnergiaDiaria,
            "maximo": maximo,
        }

    def crearFiguras(self, resultados: dict) -> dict:
        """Pasos 6 y 9 y gráfica de energía vs Qe. Devuelve {nombreArchivo: figura}."""
        return {
            "caudalesPorPeriodo": self.graficador.crearFiguraCaudalesPorPeriodo(resultados["dfCaudales"]),
            "caudalesClasificados": self.graficador.crearFiguraCaudalesClasificados(resultados["dfClasificado"]),
            "energiaDiariaClasificada": self.graficador.crearFiguraEnergiaDiaria(
                resultados["dfEnergiaDiaria"],
                self.calculadora.nombreColumnaEnergiaDiaria,
                self.calculadora.unidadEnergia,
                resultados["maximo"]["CaudalEquipamiento"],
            ),
            "energiaAnualVsCaudalEquipamiento": self.graficador.crearFiguraEnergia(
                resultados["dfEnergia"],
                self.calculadora.nombreColumnaEnergia,
                self.calculadora.unidadEnergia,
            ),
        }

    def guardarResultados(self, resultados: dict, figuras: dict) -> Path:
        """Exporta los csv y las figuras (png y svg) a la carpeta outputs."""
        resultados["dfPromedio"].write_csv(self.carpetaSalidas / "caudalClasificadoPromedio.csv")
        resultados["dfEnergia"].write_csv(self.carpetaSalidas / "energiaAnualPorCaudalEquipamiento.csv")
        resultados["dfEnergiaDiaria"].write_csv(self.carpetaSalidas / "energiaDiariaCaudalOptimo.csv")
        for nombreArchivo, fig in figuras.items():
            self.graficador.guardarFigura(fig, nombreArchivo)
        return self.carpetaSalidas

    def ejecutar(self) -> pl.DataFrame:
        """Ejecuta el pipeline desde la consola: calcula, imprime y guarda."""
        print(f"Fuente: {self.fuente} | archivo: {self.rutaDatos.name}")
        resultados = self.calcular()
        self.imprimirResumenPeriodos()

        figuras = self.crearFiguras(resultados)
        self.guardarResultados(resultados, figuras)

        dfEnergia = resultados["dfEnergia"]
        with pl.Config(tbl_rows=25):
            print(f"\nEnergía anual por caudal de equipamiento:\n{dfEnergia}")
        self.imprimirMaximo(dfEnergia)

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
