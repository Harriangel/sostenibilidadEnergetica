r"""Ejecución por consola de la solar fotovoltaica por horas solares pico.

Uso, desde la raíz del repositorio y con el paquete instalado (python -m pip install -e .):
    python scripts\ejecutarFotovoltaica.py

Edita los parámetros de abajo. Con fuenteRadiacion = "nasa" usa la GHI mensual de NASA POWER para
Bogotá (caso del Excel); con "tmy", la radiación en el plano del panel calculada con el TMY de
data/solar/. Guarda la tabla mensual y la gráfica en outputs/solar/.
"""
from pathlib import Path

import polars as pl

from energias.solar.fotovoltaica.horasSolaresPico import SistemaFotovoltaicoHsp
from energias.solar.graficadorSolar import GraficadorSolar
from energias.solar.recursoSolar import RecursoSolar

# Parámetros editables
fuenteRadiacion = "nasa"       # "nasa" (GHI de Bogotá, caso del Excel) o "tmy"
inclinacion = None             # solo con "tmy": grados; None usa la inclinación óptima anual
parametrosSistema = {
    "potenciaNominal": 5.0,    # kWp
    "perdidasSistema": 0.14,   # fracción
    "eficienciaInversor": 1.0, # 1,0 reproduce el Excel; 0,96 es un valor típico
    "unidadEnergia": "kWh",    # kWh, MWh o GWh
}


class EjecucionFotovoltaica:
    """Calcula, imprime y guarda la energía útil del sistema fotovoltaico."""

    carpetaSalidas = Path(__file__).resolve().parent.parent / "outputs" / "solar"

    def __init__(self, fuenteRadiacion: str, inclinacion, parametrosSistema: dict):
        if fuenteRadiacion not in ("nasa", "tmy"):
            raise ValueError(f"Fuente de radiación '{fuenteRadiacion}' no válida. Opciones: nasa o tmy.")
        if fuenteRadiacion == "tmy":
            recurso = RecursoSolar()
            self.inclinacion = recurso.inclinacionOptima()["inclinacion"] if inclinacion is None else inclinacion
            self.sistema = SistemaFotovoltaicoHsp.desdeRecursoSolar(recurso, self.inclinacion, **parametrosSistema)
            self.descripcionFuente = f"TMY {recurso.rutaTmy.name}, plano de {self.inclinacion:g}° orientado al sur"
        else:
            self.inclinacion = 0
            self.sistema = SistemaFotovoltaicoHsp(**parametrosSistema)
            self.descripcionFuente = "GHI horizontal de NASA POWER, Bogotá (2001–2020)"
        self.graficador = GraficadorSolar(self.carpetaSalidas)

    def imprimir(self, resultados: dict) -> None:
        sistema = self.sistema
        print(f"Sistema fotovoltaico por horas solares pico | radiación: {self.descripcionFuente}")
        print(
            f"  Potencia nominal {sistema.potenciaNominal:g} kWp | pérdidas {sistema.perdidasSistema:.0%} | "
            f"inversor {sistema.eficienciaInversor:.0%} | rendimiento global {resultados['rendimientoGlobal']:.3f}"
        )
        print("\nTabla mensual:")
        with pl.Config(tbl_cols=-1, tbl_rows=12, float_precision=4, tbl_hide_dataframe_shape=True, tbl_width_chars=160):
            print(resultados["dfMensual"])
        unidad = resultados["unidadEnergia"]
        print("\nResultados anuales:")
        print(f"  Radiación máxima / mínima:  {resultados['radiacionMaxima_kWhm2dia']:.4f} / {resultados['radiacionMinima_kWhm2dia']:.4f} kWh/m²·día")
        print(f"  Radiación anual:            {resultados['radiacionAnual_kWhm2']:,.4f} kWh/m²·año")
        print(f"  Energía útil anual:         {resultados['energiaAnual']:,.5f} {unidad}/año")
        print(f"  Promedio diario:            {resultados['promedioDiario_kWh']:,.4f} kWh/día")
        print(f"  Rendimiento específico:     {resultados['rendimientoAnual_kWhkWp']:,.4f} kWh/kWp·año")
        print(f"  Factor de planta:           {resultados['factorPlanta']:.4%}")

    def guardarResultados(self, resultados: dict) -> Path:
        self.carpetaSalidas.mkdir(parents=True, exist_ok=True)
        resultados["dfMensual"].write_csv(self.carpetaSalidas / "fotovoltaicaMensual.csv")
        figura = self.graficador.crearFiguraEnergiaFotovoltaica(resultados["dfMensual"], resultados["unidadEnergia"])
        self.graficador.guardarFigura(figura, "fotovoltaicaEnergiaMensual")
        return self.carpetaSalidas

    def ejecutar(self) -> dict:
        resultados = self.sistema.calcular()
        self.imprimir(resultados)
        print(f"\nResultados exportados en: {self.guardarResultados(resultados)}")
        return resultados


if __name__ == "__main__":
    EjecucionFotovoltaica(fuenteRadiacion, inclinacion, parametrosSistema).ejecutar()
