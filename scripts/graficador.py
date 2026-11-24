from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.ticker import FuncFormatter


class Graficador:
    """Genera las gráficas del análisis y las guarda en png y svg."""

    formatosSalida = ("png", "svg")

    def __init__(self, carpetaSalidas: Path):
        self.carpetaSalidas = Path(carpetaSalidas)
        self.carpetaSalidas.mkdir(parents=True, exist_ok=True)

    def etiquetaPeriodo(self, periodo: int) -> str:
        return f"{periodo}-{periodo + 1}"

    def crearColores(self, nColores: int):
        """Paleta continua para distinguir muchos periodos."""
        return plt.cm.turbo(np.linspace(0.05, 0.95, nColores))

    def guardarFigura(self, fig, nombreArchivo: str) -> None:
        for formato in self.formatosSalida:
            fig.savefig(
                self.carpetaSalidas / f"{nombreArchivo}.{formato}",
                dpi=200,
                bbox_inches="tight",
            )
        plt.close(fig)

    def graficarCaudalesPorPeriodo(self, df: pl.DataFrame, nombreArchivo: str) -> None:
        """Paso 6: NumDia vs Caudal, una línea por periodo."""
        fig, ax = plt.subplots(figsize=(12, 6))

        periodos = df["Periodo"].unique(maintain_order=True)
        colores = self.crearColores(len(periodos))
        for i, periodo in enumerate(periodos):
            dfPeriodo = df.filter(pl.col("Periodo") == periodo)
            ax.plot(
                dfPeriodo["NumDia"].to_numpy(),
                dfPeriodo["Caudal"].to_numpy(),
                color=colores[i],
                linewidth=1,
                label=self.etiquetaPeriodo(periodo),
            )

        ax.set_title("Caudal medio diario por periodo (octubre - septiembre)")
        ax.set_xlabel("Número de día (1 = 1° de octubre)")
        ax.set_ylabel("Caudal (m³/s)")
        ax.set_xlim(1, 365)
        ax.grid(True, alpha=0.3)
        ax.legend(title="Periodo", loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8, ncol=2)
        self.guardarFigura(fig, nombreArchivo)

    def graficarCaudalesClasificados(self, df: pl.DataFrame, nombreArchivo: str) -> None:
        """Paso 9: NumDia vs CaudalClasificado por periodo, más el promedio."""
        fig, ax = plt.subplots(figsize=(12, 6))

        periodos = df["Periodo"].unique(maintain_order=True)
        colores = self.crearColores(len(periodos))
        for i, periodo in enumerate(periodos):
            dfPeriodo = df.filter(pl.col("Periodo") == periodo)
            ax.plot(
                dfPeriodo["NumDia"].to_numpy(),
                dfPeriodo["CaudalClasificado"].to_numpy(),
                color=colores[i],
                linewidth=1,
                alpha=0.7,
                label=self.etiquetaPeriodo(periodo),
            )

        dfPromedio = df.filter(pl.col("Periodo") == df["Periodo"].min())
        ax.plot(
            dfPromedio["NumDia"].to_numpy(),
            dfPromedio["CaudalClasificadoPromedio"].to_numpy(),
            color="black",
            linewidth=2.5,
            linestyle=":",
            label="Promedio",
        )

        ax.set_title("Caudales clasificados por periodo y promedio")
        ax.set_xlabel("Número de día (posición en la clasificación)")
        ax.set_ylabel("Caudal clasificado (m³/s)")
        ax.set_xlim(1, 365)
        ax.grid(True, alpha=0.3)
        ax.legend(title="Periodo", loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8, ncol=2)
        self.guardarFigura(fig, nombreArchivo)

    def graficarEnergiaVsCaudalEquipamiento(
        self, df: pl.DataFrame, columnaEnergia: str, unidadEnergia: str, nombreArchivo: str
    ) -> None:
        """Qe vs energía anual, resaltando el caudal de equipamiento de energía máxima."""
        fig, ax = plt.subplots(figsize=(10, 6))

        caudales = df["CaudalEquipamiento"].to_numpy()
        energias = df[columnaEnergia].to_numpy()
        # Con muchos puntos los marcadores saturan la curva, por lo que se omiten
        marcador = "o" if len(caudales) <= 60 else None
        ax.plot(caudales, energias, marker=marcador, markersize=4, linewidth=1.5, color="tab:blue")

        maximo = df.sort(columnaEnergia, descending=True).row(0, named=True)
        ax.plot(
            maximo["CaudalEquipamiento"],
            maximo[columnaEnergia],
            marker="o",
            markersize=10,
            color="tab:red",
            linestyle="none",
            label=(
                f"Máxima: {maximo[columnaEnergia]:,.0f} {unidadEnergia}h/año "
                f"con Qe = {maximo['CaudalEquipamiento']:.2f} m³/s"
            ),
        )
        ax.axvline(maximo["CaudalEquipamiento"], color="tab:red", linestyle="--", linewidth=1, alpha=0.6)

        ax.set_title("Energía anual generada vs caudal de equipamiento")
        ax.set_xlabel("Caudal de equipamiento Qe (m³/s)")
        ax.set_ylabel(f"Energía anual ({unidadEnergia}h/año)")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, _: f"{valor:,.0f}"))
        ax.grid(True, alpha=0.3)
        ax.legend()
        self.guardarFigura(fig, nombreArchivo)
