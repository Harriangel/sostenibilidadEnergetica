r"""Ejecución por consola de la central mareomotriz (energía anual y LCOE).

Uso, desde la raíz del repositorio y con el paquete instalado (python -m pip install -e .):
    python scripts\ejecutarMareomotriz.py

Edita los parámetros de abajo; los valores por defecto son los del Excel de origen
(docs/especificaciones/mar/). Imprime los resultados como la sección 4 de la especificación
y guarda la tabla de escenarios y las gráficas en outputs/mareomotriz/.
"""
from pathlib import Path

import polars as pl

from energias.mar.graficadorMareomotriz import GraficadorMareomotriz
from energias.mar.mareomotriz import CentralMareomotriz

# Parámetros editables
parametros = {
    # Marea y turbina
    "tipoMarea": "Semidiurna",         # Diurna o Semidiurna
    "direccion": "Bidireccional",      # Unidireccional o Bidireccional
    "tipoTurbina": "Eje horizontal",   # descriptivo
    "duracionDiaLunar": 24.8,          # h
    "duracionDiaSolar": 24.0,          # h
    "diasAnio": 365,                   # días de operación al año
    "eficiencia": 0.38,                # rendimiento global η (hidráulico + eléctrico)
    "numeroTurbinas": 1,               # multiplica energía, CAPEX y OPEX
    "disponibilidad": 1.0,             # fracción del año en operación (multiplica la energía útil)
    # Constantes físicas
    "masaAgua": 8.7e9,                 # kg por ciclo y turbina
    "gravedad": 9.81,                  # m/s²
    "desnivel": 3.6,                   # m
    # Economía
    "vidaUtil": 25,                    # años
    "tasaDescuento": 0.07,             # fracción (0.07 = 7 %)
    "capex": 14_500_000.0,             # moneda por turbina (inversión en el año 0)
    "opex": 450_000.0,                 # moneda por turbina y año
    "factorCapexEscenarioA": 1.15,     # escenario A: CAPEX × factor
    "factorEnergiaEscenarioB": 0.90,   # escenario B: energía × factor
    "moneda": "EUR",                   # etiqueta de la moneda
}
parametroSensibilidad = "tasaDescuento"  # tasaDescuento, eficiencia, desnivel o capex


class EjecucionMareomotriz:
    """Calcula, imprime y guarda los resultados de la central mareomotriz."""

    carpetaSalidas = Path(__file__).resolve().parent.parent / "outputs" / "mareomotriz"

    def __init__(self, parametros: dict, parametroSensibilidad: str):
        self.central = CentralMareomotriz(**parametros)
        self.parametroSensibilidad = parametroSensibilidad
        self.graficador = GraficadorMareomotriz(self.carpetaSalidas)

    def imprimirSalidas(self, resultados: dict) -> None:
        """Tabla de la sección 4 de la especificación (celda del Excel, descripción, unidad y valor)."""
        moneda = resultados["moneda"]
        filas = (
            ("K12", "Duración del ciclo de marea", "h/ciclo", resultados["cicloMarea_h"], 3),
            ("K13", "Ciclos por día solar", "ciclos/día", resultados["ciclosPorDia"], 3),
            ("K14", "Ciclos por año", "ciclos/año", resultados["ciclosPorAnio"], 3),
            ("K15", "Pasos por turbina y año", "pasos/año", resultados["pasosPorAnio"], 3),
            ("K19", "Energía potencial anual", "J/año", resultados["energiaPotencial_J"], 0),
            ("K20", "Energía potencial anual", "kWh/año", resultados["energiaPotencial_kWh"], 2),
            ("K21", "Energía eléctrica anual", "kWh/año", resultados["energiaUtil_kWh"], 2),
            ("K23", "Energía eléctrica anual", "MWh/año", resultados["energiaUtil_MWh"], 2),
            ("K24", "Energía eléctrica anual", "GWh/año", resultados["energiaUtil_GWh"], 2),
            ("K30", "LCOE del caso base", f"{moneda}/kWh", resultados["lcoeBase_porKWh"], 7),
            ("K35", "LCOE con CAPEX +15 %", f"{moneda}/kWh", resultados["lcoeEscenarioA_porKWh"], 7),
            ("K40", "LCOE con energía −10 %", f"{moneda}/kWh", resultados["lcoeEscenarioB_porKWh"], 7),
        )
        print(
            f"Central mareomotriz: marea {self.central.tipoMarea.lower()}, turbina {self.central.direccion.lower()} "
            f"({self.central.tipoTurbina}), {self.central.numeroTurbinas} turbina(s), "
            f"disponibilidad {self.central.disponibilidad:g}"
        )
        print("\nSalidas (sección 4 de la especificación):")
        print(f"{'Celda':<6}{'Descripción':<30}{'Unidad':<12}{'Valor':>26}")
        print("-" * 74)
        for celda, descripcion, unidad, valor, decimales in filas:
            print(f"{celda:<6}{descripcion:<30}{unidad:<12}{valor:>26,.{decimales}f}")

        print("\nValor presente (caso base):")
        print(f"  Factor de valor presente FVP:          {resultados['factorValorPresente']:,.6f} años")
        print(f"  Factor de recuperación de capital CRF: {resultados['factorRecuperacionCapital']:,.7f} 1/año")
        print(f"  VP del OPEX:                           {resultados['valorPresenteOpex']:,.2f} {moneda}")
        print(f"  VP de los costos:                      {resultados['valorPresenteCostos']:,.2f} {moneda}")
        print(f"  VP de la energía:                      {resultados['valorPresenteEnergia_kWh']:,.2f} kWh")
        print(f"  Potencia media:                        {resultados['potenciaMedia_MW']:,.3f} MW")
        print(f"  LCOE base:                             {resultados['lcoeBase_porMWh']:,.2f} {moneda}/MWh")

    def imprimirEscenarios(self, dfEscenarios: pl.DataFrame) -> None:
        print("\nEscenarios de sensibilidad (sección 3.4):")
        with pl.Config(tbl_cols=-1, tbl_width_chars=160, float_precision=7, tbl_hide_dataframe_shape=True):
            print(dfEscenarios)

    def guardarResultados(self, resultados: dict) -> Path:
        """Guarda la tabla de escenarios, el barrido de sensibilidad y las gráficas en outputs/mareomotriz."""
        self.carpetaSalidas.mkdir(parents=True, exist_ok=True)
        moneda = resultados["moneda"]
        resultados["dfEscenarios"].write_csv(self.carpetaSalidas / "escenariosLcoe.csv")
        dfBarrido = self.central.barridoSensibilidad(self.parametroSensibilidad)
        dfBarrido.write_csv(self.carpetaSalidas / f"sensibilidadLcoe_{self.parametroSensibilidad}.csv")
        self.graficador.guardarFigura(
            self.graficador.crearFiguraEscenarios(resultados["dfEscenarios"], moneda), "lcoeEscenarios"
        )
        self.graficador.guardarFigura(
            self.graficador.crearFiguraSensibilidad(
                dfBarrido,
                self.parametroSensibilidad,
                self.central.parametros[self.parametroSensibilidad],
                resultados["lcoeBase_porKWh"],
                moneda,
            ),
            f"sensibilidadLcoe_{self.parametroSensibilidad}",
        )
        return self.carpetaSalidas

    def ejecutar(self) -> dict:
        resultados = self.central.calcular()
        self.imprimirSalidas(resultados)
        self.imprimirEscenarios(resultados["dfEscenarios"])
        carpeta = self.guardarResultados(resultados)
        print(f"\nResultados exportados en: {carpeta}")
        return resultados


if __name__ == "__main__":
    EjecucionMareomotriz(parametros, parametroSensibilidad).ejecutar()
