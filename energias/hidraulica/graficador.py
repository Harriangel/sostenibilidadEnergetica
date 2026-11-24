from pathlib import Path

import matplotlib
import numpy as np
import polars as pl
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from energias.comun.graficos import Graficos
from energias.hidraulica.disenoTuberiaForzada import DisenoTuberiaForzada


class Graficador:
    """Crea las gráficas específicas de la hidráulica y las guarda en png y svg.

    Las figuras se crean con la API orientada a objetos de matplotlib (Figure),
    sin pyplot, para poder usarlas tanto en scripts como en la interfaz web.
    El guardado, la conversión a bytes y los formatos de eje vienen de
    energias.comun.graficos.
    """

    formatosSalida = Graficos.formatosSalida

    def __init__(self, carpetaSalidas: Path):
        self.carpetaSalidas = Path(carpetaSalidas)
        self.carpetaSalidas.mkdir(parents=True, exist_ok=True)

    def etiquetaPeriodo(self, periodo: int) -> str:
        return f"{periodo}-{periodo + 1}"

    def crearColores(self, nColores: int):
        """Paleta continua para distinguir muchos periodos."""
        return matplotlib.colormaps["turbo"](np.linspace(0.05, 0.95, nColores))

    def guardarFigura(self, fig: Figure, nombreArchivo: str) -> None:
        Graficos.guardarFigura(fig, self.carpetaSalidas, nombreArchivo)

    def figuraABytes(self, fig: Figure, formato: str) -> bytes:
        """Figura en memoria (png o svg), por ejemplo para botones de descarga."""
        return Graficos.figuraABytes(fig, formato)

    def crearFiguraCaudalesPorPeriodo(self, df: pl.DataFrame) -> Figure:
        """Paso 6: NumDia vs Caudal, una línea por periodo."""
        fig = Figure(figsize=(12, 6))
        ax = fig.subplots()

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
        return fig

    def crearFiguraCaudalesClasificados(self, df: pl.DataFrame) -> Figure:
        """Paso 9: NumDia vs CaudalClasificado por periodo, más el promedio."""
        fig = Figure(figsize=(12, 6))
        ax = fig.subplots()

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
        return fig

    def crearFiguraEnergia(self, df: pl.DataFrame, columnaEnergia: str, unidadEnergia: str) -> Figure:
        """Qe vs energía anual, resaltando el caudal de equipamiento de energía máxima."""
        fig = Figure(figsize=(10, 6))
        ax = fig.subplots()

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
        ax.yaxis.set_major_formatter(Graficos.formatoMiles())
        ax.grid(True, alpha=0.3)
        ax.legend()
        return fig

    def crearFiguraEnergiaDiaria(
        self, df: pl.DataFrame, columnaEnergiaDiaria: str, unidadEnergia: str, caudalEquipamiento: float
    ) -> Figure:
        """NumDia vs energía generada cada día con la serie de caudal clasificado promedio."""
        fig = Figure(figsize=(12, 6))
        ax = fig.subplots()

        dias = df["NumDia"].to_numpy()
        energias = df[columnaEnergiaDiaria].to_numpy()
        energiaAnual = df[columnaEnergiaDiaria].sum()

        ax.fill_between(dias, energias, color="tab:green", alpha=0.25)
        ax.plot(
            dias,
            energias,
            color="tab:green",
            linewidth=1.8,
            label=f"Energía anual: {energiaAnual:,.0f} {unidadEnergia}h/año",
        )

        ax.set_title(
            f"Energía generada por día con el caudal clasificado promedio (Qe = {caudalEquipamiento:.2f} m³/s)"
        )
        ax.set_xlabel("Número de día (posición en la clasificación)")
        ax.set_ylabel(f"Energía diaria ({unidadEnergia}h/día)")
        ax.yaxis.set_major_formatter(Graficos.formatoMiles())
        ax.set_xlim(1, 365)
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)
        ax.legend()
        return fig

    def crearFiguraSeccionCanal(self, seccion: dict) -> Figure:
        """Sección trapezoidal del canal con los lados x, y, z y w."""
        x, y, z, w = seccion["x"], seccion["y"], seccion["z"], seccion["w"]
        proyeccion = seccion["proyeccionTalud"]
        margen = max(x, 2 * z) * 0.25
        fondoTerreno = -0.6 * z
        xMinimo, xMaximo = -margen * 1.9, x + margen * 1.9
        yMinimo, yMaximo = fondoTerreno * 1.05, z * 1.45

        # El tamaño de la figura sigue la proporción de los datos para evitar espacios vacíos
        alto = min(6.0, max(3.2, 9 * (yMaximo - yMinimo) / (xMaximo - xMinimo)))
        fig = Figure(figsize=(9, alto))
        ax = fig.subplots()
        ax.fill(
            [-margen, 0, proyeccion, proyeccion + y, x, x + margen, x + margen, -margen],
            [z, z, 0, 0, z, z, fondoTerreno, fondoTerreno],
            color="#c8b38a",
        )
        ax.fill([0, x, proyeccion + y, proyeccion], [z, z, 0, 0], color="#9fd3f5")
        ax.plot([0, proyeccion, proyeccion + y, x], [z, 0, 0, z], color="black", linewidth=2)
        ax.plot([0, x], [z, z], color="#1f77b4", linewidth=2)

        flecha = dict(arrowstyle="<->", color="black", linewidth=1.2)
        caja = dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1.5)
        # x: ancho superior
        ax.annotate("", xy=(0, z * 1.18), xytext=(x, z * 1.18), arrowprops=flecha)
        ax.text(x / 2, z * 1.22, f"x = {x:.2f} m", ha="center", va="bottom", fontsize=11)
        # y: base
        ax.annotate("", xy=(proyeccion, fondoTerreno * 0.5), xytext=(proyeccion + y, fondoTerreno * 0.5), arrowprops=flecha)
        ax.text(proyeccion + y / 2, fondoTerreno * 0.5 - 0.05 * z, f"y = {y:.2f} m", ha="center", va="top", fontsize=11)
        # z: profundidad (a la derecha)
        ax.annotate("", xy=(x + margen * 0.45, 0), xytext=(x + margen * 0.45, z), arrowprops=flecha)
        ax.text(x + margen * 0.52, z / 2, f"z = {z:.2f} m", ha="left", va="center", fontsize=11)
        # w: lado inclinado (a la izquierda, fuera del agua)
        ax.text(proyeccion / 2 - 0.03 * x, z / 2, f"w = {w:.2f} m", ha="right", va="center", fontsize=11, bbox=caja)
        # A: área
        ax.text(x / 2, z * 0.4, f"A = {seccion['A']:.2f} m²", ha="center", va="center", fontsize=11, bbox=caja)

        ax.set_title("Sección trapezoidal del canal de derivación")
        ax.set_xlim(xMinimo, xMaximo)
        ax.set_ylim(yMinimo, yMaximo)
        ax.set_aspect("equal")
        ax.axis("off")
        return fig

    def crearFiguraMoody(self, reynolds: float, factorFriccion: float, rugosidadRelativa: float, metodo: str) -> Figure:
        """Diagrama de Moody (calculado con Colebrook-White) con el punto de operación."""
        fig = Figure(figsize=(11, 8))
        ax = fig.subplots()

        valoresRelativos = [
            1e-6, 5e-6, 1e-5, 2e-5, 5e-5, 1e-4, 2e-4, 5e-4, 1e-3, 2e-3,
            4e-3, 6e-3, 8e-3, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05,
        ]
        reynoldsTurbulento = np.logspace(np.log10(4000), 8, 200)
        etiquetas = []
        for valor in [0.0] + valoresRelativos:
            factores = [DisenoTuberiaForzada.friccionColebrook(re, valor) for re in reynoldsTurbulento]
            ax.plot(reynoldsTurbulento, factores, color="tab:blue", linewidth=0.9, alpha=0.8)
            if valor > 0 and factores[-1] > 0.0082:
                etiquetas.append((factores[-1], valor))
            elif valor == 0:
                ax.text(4e6, 0.0094, "tubería lisa", fontsize=8, color="tab:blue", rotation=-12)

        # Etiquetas de ε/D a la derecha, omitiendo las que quedarían encimadas
        ultimoNivel = None
        for nivel, valor in sorted(etiquetas, reverse=True):
            if ultimoNivel is None or np.log10(ultimoNivel / nivel) > 0.03:
                texto = np.format_float_positional(valor, trim="-").replace(".", ",")
                ax.text(1.08e8, nivel, texto, fontsize=7, va="center")
                ultimoNivel = nivel

        reynoldsLaminar = np.logspace(np.log10(600), np.log10(2000), 30)
        ax.plot(reynoldsLaminar, 64 / reynoldsLaminar, color="tab:red", linewidth=2, label="Flujo laminar f = 64/Re")
        ax.axvspan(2000, 4000, color="gray", alpha=0.25, label="Zona crítica (2000 a 4000)")

        if reynolds >= 4000:
            factoresPunto = [DisenoTuberiaForzada.friccionColebrook(re, rugosidadRelativa) for re in reynoldsTurbulento]
            ax.plot(reynoldsTurbulento, factoresPunto, color="tab:orange", linewidth=2.2, label=f"Curva de εr = {rugosidadRelativa:.5f}")

        ax.plot(
            reynolds, factorFriccion, marker="o", markersize=11, color="tab:red", markeredgecolor="black",
            linestyle="none", zorder=5,
            label=f"Punto de operación: Re = {reynolds:,.0f}; f = {factorFriccion:.4f} ({metodo})",
        )

        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(600, 1e8)
        ax.set_ylim(0.008, 0.1)
        ax.set_xlabel("Número de Reynolds Re")
        ax.set_ylabel("Factor de fricción de Darcy f")
        ax.text(3.2e8, 0.029, "Rugosidad relativa ε/D", rotation=90, fontsize=9, va="center")
        ax.set_title("Diagrama de Moody")
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(loc="lower left", fontsize=9)
        formatoComa = Graficos.formatoComaDecimal()
        ax.yaxis.set_major_formatter(formatoComa)
        ax.yaxis.set_minor_formatter(formatoComa)
        ax.tick_params(axis="y", which="minor", labelsize=7)
        return fig

    def crearFiguraConvergencia(self, dfHistorial: pl.DataFrame, tolerancia: float) -> Figure:
        """Diámetro calculado y error relativo en cada iteración."""
        fig = Figure(figsize=(10, 6))
        axDiametro, axError = fig.subplots(2, 1, sharex=True)

        iteraciones = dfHistorial["Iteracion"].to_numpy()
        axDiametro.plot(iteraciones, dfHistorial["DiametroCalculado_m"].to_numpy(), marker="o", color="tab:green")
        axDiametro.set_ylabel("Diámetro calculado (m)")
        axDiametro.set_title("Convergencia del diámetro económico")
        axDiametro.grid(True, alpha=0.3)

        axError.plot(iteraciones, dfHistorial["ErrorRelativo_pct"].to_numpy(), marker="o", color="tab:purple", label="Error relativo")
        axError.axhline(tolerancia * 100, color="tab:red", linestyle="--", label=f"Tolerancia ({tolerancia * 100:g} %)")
        axError.set_yscale("log")
        axError.yaxis.set_major_formatter(Graficos.formatoGeneral())
        axError.yaxis.set_minor_formatter(FuncFormatter(lambda valor, _: f"{valor:g}" if valor in (2, 3, 5, 20, 30, 50) else ""))
        axError.set_xlabel("Iteración")
        axError.set_ylabel("Error relativo (%)")
        axError.set_xticks(iteraciones)
        axError.grid(True, which="both", alpha=0.3)
        axError.legend()
        return fig
