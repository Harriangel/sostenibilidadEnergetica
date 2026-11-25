r"""Ejecución por consola de la solar térmica: recurso solar y dimensionamiento de ACS por F-Chart.

Uso, desde la raíz del repositorio y con el paquete instalado (python -m pip install -e .):
    python scripts\ejecutarSolarTermica.py

Edita los parámetros de abajo. Lee el TMY de data/solar/, calcula la radiación en el plano de los
colectores y dimensiona el sistema; guarda tablas y gráficas en outputs/solar/.
"""
from pathlib import Path

import polars as pl

from energias.solar.graficadorSolar import GraficadorSolar
from energias.solar.recursoSolar import RecursoSolar
from energias.solar.termica.fChartAcs import SistemaFChart

# Parámetros editables
parametrosRecurso = {
    "rutaTmy": None,           # None: data/solar/tmyCiudadMexico.csv
    "acimutPanel": 180.0,      # grados desde el norte (180 = sur)
    "usarCenitArchivo": True,  # cenit del TMY (True) o calculado (False)
}
inclinacion = None             # grados; None usa la inclinación óptima anual
parametrosFChart = {
    "numeroHabitaciones": 30,
    "ocupacionPorHabitacion": 2,        # personas por habitación
    "consumoPorPersona": 50,            # L/persona·día
    "temperaturaUso": 45,               # °C
    "temperaturaRed": 15,               # °C
    "areaColector": 2,                  # m² por colector
    "eficienciaOptica": 0.75,           # η0
    "coeficientePerdidas": 4.5,         # a1 (W/m²·K)
    "fraccionObjetivoMinima": 0.6,
    "fraccionObjetivoMaxima": 0.7,
    "eficienciaSistema": 0.45,          # solo para el área inicial
    "correlacion": "klein",             # "klein" (por defecto) o "informe"
    "correccionAcs": True,              # solo Klein
}


class EjecucionSolarTermica:
    """Calcula, imprime y guarda el recurso solar y el dimensionamiento por F-Chart."""

    carpetaSalidas = Path(__file__).resolve().parent.parent / "outputs" / "solar"

    def __init__(self, parametrosRecurso: dict, inclinacion, parametrosFChart: dict):
        self.recurso = RecursoSolar(**parametrosRecurso)
        self.optima = self.recurso.inclinacionOptima()
        self.inclinacion = self.optima["inclinacion"] if inclinacion is None else inclinacion
        self.climaMensual = self.recurso.radiacionMensual(self.inclinacion)
        self.sistema = SistemaFChart(self.climaMensual, **parametrosFChart)
        self.graficador = GraficadorSolar(self.carpetaSalidas)

    def imprimirRecurso(self) -> None:
        metadatos = self.recurso.metadatos
        print(
            f"Recurso solar: TMY {self.recurso.rutaTmy.name} (lat {metadatos['latitud']}°, lon {metadatos['longitud']}°, "
            f"zona horaria {metadatos['zonaHoraria']:g} h, {metadatos['elevacion']:g} m)"
        )
        print(
            f"  Inclinación óptima: {self.optima['inclinacion']:g}° con {self.optima['radiacionAnual_kWhm2']:,.1f} kWh/m²·año | "
            f"inclinación usada: {self.inclinacion:g}° (acimut {self.recurso.acimutPanel:g}°)"
        )
        print("\nRadiación en el plano y temperatura ambiente por mes:")
        with pl.Config(tbl_rows=12, float_precision=3, tbl_hide_dataframe_shape=True):
            print(self.climaMensual)

    def imprimirFChart(self, resultados: dict) -> None:
        sistema = self.sistema
        dimensionamiento = resultados["dimensionamiento"]
        print(f"\nF-Chart (correlación {sistema.correlacion})")
        print(
            f"  Demanda: {resultados['volumenDiario_L']:,.0f} L/día de {sistema.temperaturaRed:g} a {sistema.temperaturaUso:g} °C → "
            f"{resultados['demandaDiaria_kWh']:.2f} kWh/día | {resultados['demandaAnual_kWh']:,.1f} kWh/año"
        )
        print(f"  Área inicial: {resultados['areaInicial_m2']:.2f} m² (fracción anual {resultados['fraccionAreaInicial']:.3f})")
        print("\nCasos de análisis:")
        with pl.Config(tbl_cols=-1, float_precision=4, tbl_hide_dataframe_shape=True, tbl_width_chars=160):
            print(resultados["dfCasos"])
        print("\nDimensionamiento:")
        print(
            f"  {dimensionamiento['iteraciones']} iteraciones → área {dimensionamiento['area_m2']:.2f} m², "
            f"fracción solar anual {dimensionamiento['fraccionAnual']:.4f}"
        )
        print(
            f"  {dimensionamiento['numeroColectores']} colectores de {sistema.areaColector:g} m² "
            f"({dimensionamiento['areaInstalada_m2']:g} m² instalados)"
        )
        print(
            f"  Energía solar {dimensionamiento['energiaSolarAnual_kWh']:,.1f} kWh/año | "
            f"auxiliar {dimensionamiento['energiaAuxiliarAnual_kWh']:,.1f} kWh/año"
        )
        for advertencia in dimensionamiento["advertencias"]:
            print(f"  Advertencia: {advertencia}")
        print("\nTabla mensual:")
        with pl.Config(tbl_cols=-1, tbl_rows=12, float_precision=4, tbl_hide_dataframe_shape=True, tbl_width_chars=180):
            print(dimensionamiento["dfMensual"])

    def guardarResultados(self, resultados: dict) -> Path:
        self.carpetaSalidas.mkdir(parents=True, exist_ok=True)
        dimensionamiento = resultados["dimensionamiento"]
        dfBarrido = self.recurso.barridoInclinacion()
        self.climaMensual.write_csv(self.carpetaSalidas / "radiacionMensualPlano.csv")
        dfBarrido.write_csv(self.carpetaSalidas / "barridoInclinacion.csv")
        resultados["dfCasos"].write_csv(self.carpetaSalidas / "fChartCasos.csv")
        dimensionamiento["dfMensual"].write_csv(self.carpetaSalidas / "fChartMensual.csv")
        plano = self.recurso.calcularPlano(self.inclinacion)
        figuras = {
            "barridoInclinacion": self.graficador.crearFiguraBarridoInclinacion(
                dfBarrido, self.optima["inclinacion"], {"Latitud + 23,5°": self.recurso.latitud + 23.5}
            ),
            "radiacionMensualPlano": self.graficador.crearFiguraRadiacionMensual(self.climaMensual, self.inclinacion),
            "perfilHorarioPlano": self.graficador.crearFiguraPerfilHorario(
                self.recurso.perfilHorario(plano), list(RecursoSolar.componentesInclinadas),
                f"Irradiancia promedio por hora en el plano de {self.inclinacion:g}°",
            ),
            "fChartMensual": self.graficador.crearFiguraFChartMensual(dimensionamiento["dfMensual"]),
            "fChartFraccionArea": self.graficador.crearFiguraFraccionArea(
                self.sistema.curvaFraccionArea(), dimensionamiento["area_m2"], dimensionamiento["fraccionAnual"],
                self.sistema.fraccionObjetivoMinima, self.sistema.fraccionObjetivoMaxima,
            ),
        }
        for nombre, figura in figuras.items():
            self.graficador.guardarFigura(figura, nombre)
        return self.carpetaSalidas

    def ejecutar(self) -> dict:
        self.imprimirRecurso()
        resultados = self.sistema.calcular()
        self.imprimirFChart(resultados)
        print(f"\nResultados exportados en: {self.guardarResultados(resultados)}")
        return resultados


if __name__ == "__main__":
    EjecucionSolarTermica(parametrosRecurso, inclinacion, parametrosFChart).ejecutar()
