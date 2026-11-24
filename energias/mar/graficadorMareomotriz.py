"""Gráficas de la central mareomotriz (API Figure de matplotlib, sin pyplot)."""
from pathlib import Path

import polars as pl
from matplotlib.figure import Figure

from energias.comun.graficos import Graficos
from energias.mar.mareomotriz import CentralMareomotriz


class GraficadorMareomotriz:
    """Barras del LCOE por escenario y barrido de sensibilidad del LCOE.

    El guardado en png y svg y la conversión a bytes vienen de energias.comun.graficos.
    """

    coloresEscenarios = {"Base": "tab:blue", "A": "tab:orange", "B": "tab:green"}
    unidadesLcoe = {"kWh": 1.0, "MWh": 1000.0}  # factor desde moneda/kWh

    def __init__(self, carpetaSalidas: Path = None):
        # La carpeta se crea al guardar, no al construir el graficador
        self.carpetaSalidas = Path(carpetaSalidas) if carpetaSalidas is not None else None

    def validarUnidadLcoe(self, unidadLcoe: str) -> float:
        if unidadLcoe not in self.unidadesLcoe:
            raise ValueError(f"Unidad del LCOE '{unidadLcoe}' no válida. Opciones: kWh o MWh.")
        return self.unidadesLcoe[unidadLcoe]

    def crearFiguraEscenarios(self, dfEscenarios: pl.DataFrame, moneda: str, unidadLcoe: str = "kWh") -> Figure:
        """Barras del LCOE de los escenarios base, A y B, con su valor y su variación frente a la base."""
        factor = self.validarUnidadLcoe(unidadLcoe)
        columnaLcoe = f"LCOE_{moneda}_por_kWh"
        escenarios = dfEscenarios["Escenario"].to_list()
        etiquetas = [
            f"{escenario}\n({cambio})" if escenario != "Base" else "Base"
            for escenario, cambio in zip(escenarios, dfEscenarios["Cambio"].to_list())
        ]
        valores = [valor * factor for valor in dfEscenarios[columnaLcoe].to_list()]
        variaciones = dfEscenarios["VariacionFrenteBase_pct"].to_list()

        fig = Figure(figsize=(8, 5.5))
        ax = fig.subplots()
        barras = ax.bar(
            etiquetas,
            valores,
            color=[self.coloresEscenarios.get(escenario, "tab:gray") for escenario in escenarios],
            width=0.6,
        )
        decimales = 4 if unidadLcoe == "kWh" else 2
        for barra, valor, variacion in zip(barras, valores, variaciones):
            texto = f"{valor:,.{decimales}f}"
            if abs(variacion) > 1e-12:
                texto += f"\n({variacion:+.2f} %)"
            ax.annotate(
                texto,
                (barra.get_x() + barra.get_width() / 2, barra.get_height()),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=10,
            )
        ax.axhline(valores[0], color="tab:blue", linestyle="--", linewidth=1, alpha=0.6)
        ax.set_title("LCOE por escenario")
        ax.set_ylabel(f"LCOE ({moneda}/{unidadLcoe})")
        ax.set_ylim(0, max(valores) * 1.2)
        ax.grid(True, axis="y", alpha=0.3)
        return fig

    def crearFiguraSensibilidad(
        self,
        dfBarrido: pl.DataFrame,
        parametro: str,
        valorBase: float,
        lcoeBase: float,
        moneda: str,
        unidadLcoe: str = "kWh",
    ) -> Figure:
        """LCOE frente a un parámetro (tasa de descuento, eficiencia, desnivel o CAPEX), con el valor base marcado."""
        if parametro not in CentralMareomotriz.parametrosSensibilidad:
            raise ValueError(
                f"Parámetro '{parametro}' no válido. Opciones: {', '.join(CentralMareomotriz.parametrosSensibilidad)}."
            )
        factor = self.validarUnidadLcoe(unidadLcoe)
        etiqueta, unidad = CentralMareomotriz.parametrosSensibilidad[parametro]
        if unidad == "moneda/turbina":
            unidad = f"{moneda}/turbina"

        fig = Figure(figsize=(9, 5.5))
        ax = fig.subplots()
        valores = dfBarrido[parametro].to_numpy()
        lcoes = dfBarrido[f"LCOE_{moneda}_por_kWh"].to_numpy() * factor
        ax.plot(valores, lcoes, color="tab:blue", linewidth=2)

        decimales = 4 if unidadLcoe == "kWh" else 2
        if parametro in ("tasaDescuento", "eficiencia"):
            textoBase = f"{valorBase * 100:g} %"
            ax.xaxis.set_major_formatter(Graficos.formatoPorcentaje())
            etiquetaEje = etiqueta
        elif parametro == "capex":
            textoBase = f"{valorBase:,.0f} {moneda}"
            ax.xaxis.set_major_formatter(Graficos.formatoMillones())
            etiquetaEje = f"{etiqueta} (millones de {unidad})"
        else:
            textoBase = f"{valorBase:g} {unidad}"
            etiquetaEje = f"{etiqueta} ({unidad})"
        ax.plot(
            valorBase,
            lcoeBase * factor,
            marker="o",
            markersize=10,
            color="tab:red",
            linestyle="none",
            zorder=5,
            label=f"Base: {textoBase} → {lcoeBase * factor:,.{decimales}f} {moneda}/{unidadLcoe}",
        )
        ax.axvline(valorBase, color="tab:red", linestyle="--", linewidth=1, alpha=0.6)
        ax.axhline(lcoeBase * factor, color="tab:red", linestyle=":", linewidth=1, alpha=0.6)

        # Minúscula inicial salvo en siglas (CAPEX)
        etiquetaTitulo = etiqueta if etiqueta[:2].isupper() else etiqueta[0].lower() + etiqueta[1:]
        ax.set_title(f"Sensibilidad del LCOE a {etiquetaTitulo}")
        ax.set_xlabel(etiquetaEje)
        ax.set_ylabel(f"LCOE ({moneda}/{unidadLcoe})")
        ax.grid(True, alpha=0.3)
        ax.legend()
        return fig

    def guardarFigura(self, fig: Figure, nombreArchivo: str) -> list:
        """Guarda la figura en png y svg en la carpeta de salidas (la crea si no existe)."""
        if self.carpetaSalidas is None:
            raise ValueError("No se indicó la carpeta de salidas del graficador.")
        return Graficos.guardarFigura(fig, self.carpetaSalidas, nombreArchivo)

    @staticmethod
    def figuraABytes(fig: Figure, formato: str) -> bytes:
        return Graficos.figuraABytes(fig, formato)
