"""Gráficas del módulo solar (API Figure de matplotlib, sin pyplot)."""
from pathlib import Path

import matplotlib
import numpy as np
import polars as pl
from matplotlib.figure import Figure

from energias.comun.graficos import Graficos


class GraficadorSolar:
    """Recurso solar, F-Chart y fotovoltaica. Guardado y bytes con energias.comun.graficos."""

    nombresComponentes = {
        "DNI_Wm2": "Directa normal (DNI)",
        "DHI_Wm2": "Difusa horizontal (DHI)",
        "GHI_Wm2": "Global horizontal (GHI)",
        "Gbi_Wm2": "Directa inclinada (Gbi)",
        "Gdi_Wm2": "Difusa inclinada (Gdi)",
        "Gri_Wm2": "Reflejada (Gri)",
        "GTI_Wm2": "Global inclinada (GTI)",
    }
    mesesCortos = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")

    def __init__(self, carpetaSalidas: Path = None):
        # La carpeta se crea al guardar, no al construir el graficador
        self.carpetaSalidas = Path(carpetaSalidas) if carpetaSalidas is not None else None

    def nombreComponente(self, columna: str) -> str:
        base = columna.replace("_kWhm2dia", "_Wm2")
        return self.nombresComponentes.get(base, columna)

    # ------------------------------------------------------------------
    # Recurso solar
    # ------------------------------------------------------------------
    def crearFiguraPerfilHorario(self, dfPerfil: pl.DataFrame, componentes: list, titulo: str) -> Figure:
        """Irradiancia promedio por hora del día, una línea por componente (perfil anual)."""
        fig = Figure(figsize=(10, 5.5))
        ax = fig.subplots()
        horas = dfPerfil["Hora"].to_numpy() + 0.5
        for componente in componentes:
            ax.plot(horas, dfPerfil[componente].to_numpy(), linewidth=2, label=self.nombreComponente(componente))
        ax.set_title(titulo)
        ax.set_xlabel("Hora del día (hora estándar local)")
        ax.set_ylabel("Irradiancia (W/m²)")
        ax.set_xlim(0, 24)
        ax.set_xticks(range(0, 25, 3))
        ax.grid(True, alpha=0.3)
        ax.legend()
        return fig

    def crearFiguraPerfilHorarioMensual(self, dfPerfilMensual: pl.DataFrame, componente: str) -> Figure:
        """Irradiancia promedio por hora del día de un componente, una línea por mes."""
        fig = Figure(figsize=(11, 6))
        ax = fig.subplots()
        colores = matplotlib.colormaps["twilight_shifted"](np.linspace(0.05, 0.95, 12))
        for mes in range(1, 13):
            dfMes = dfPerfilMensual.filter(pl.col("Mes") == mes)
            ax.plot(dfMes["Hora"].to_numpy() + 0.5, dfMes[componente].to_numpy(), color=colores[mes - 1], linewidth=1.6, label=self.mesesCortos[mes - 1])
        ax.set_title(f"{self.nombreComponente(componente)}: perfil horario promedio por mes")
        ax.set_xlabel("Hora del día (hora estándar local)")
        ax.set_ylabel("Irradiancia (W/m²)")
        ax.set_xlim(0, 24)
        ax.set_xticks(range(0, 25, 3))
        ax.grid(True, alpha=0.3)
        ax.legend(title="Mes", loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=9)
        return fig

    def crearFiguraRadiacionDiaria(self, dfDiaria: pl.DataFrame, componentes: list) -> Figure:
        """Radiación de cada día del año (kWh/m²·día) por componente."""
        fig = Figure(figsize=(12, 5.5))
        ax = fig.subplots()
        dias = dfDiaria["DiaAnio"].to_numpy()
        for componente in componentes:
            ax.plot(dias, dfDiaria[componente].to_numpy(), linewidth=1, label=self.nombreComponente(componente))
        inicioMes = np.concatenate(([1], np.cumsum([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30])[:] + 1))
        ax.set_xticks(inicioMes)
        ax.set_xticklabels(self.mesesCortos)
        ax.set_xlim(1, 365)
        ax.set_title("Radiación diaria del año meteorológico típico")
        ax.set_ylabel("Radiación (kWh/m²·día)")
        ax.grid(True, alpha=0.3)
        ax.legend()
        return fig

    def crearFiguraRadiacionMensual(self, dfMensual: pl.DataFrame, inclinacion: float) -> Figure:
        """Radiación diaria media de cada mes en el plano (barras) y temperatura ambiente (línea)."""
        fig = Figure(figsize=(10, 5.5))
        ax = fig.subplots()
        posiciones = np.arange(12)
        valores = dfMensual["HTdia_kWhm2dia"].to_numpy()
        barras = ax.bar(posiciones, valores, color="tab:orange", width=0.65, label="Radiación en el plano")
        for barra, valor in zip(barras, valores):
            ax.annotate(f"{valor:.2f}", (barra.get_x() + barra.get_width() / 2, valor), xytext=(0, 3),
                        textcoords="offset points", ha="center", fontsize=9)
        ax.set_ylabel("Radiación diaria media (kWh/m²·día)")
        ax.set_ylim(0, valores.max() * 1.2)
        ax.set_xticks(posiciones)
        ax.set_xticklabels(self.mesesCortos)
        ax.set_title(f"Radiación mensual en el plano inclinado {inclinacion:g}° y temperatura ambiente")
        axTemperatura = ax.twinx()
        axTemperatura.plot(posiciones, dfMensual["Tamb_C"].to_numpy(), color="tab:blue", marker="o", label="Temperatura ambiente")
        axTemperatura.set_ylabel("Temperatura ambiente (°C)")
        axTemperatura.set_ylim(0, max(dfMensual["Tamb_C"].max() * 1.8, 1))
        lineas = [barras, axTemperatura.lines[0]]
        ax.legend(lineas, [l.get_label() for l in lineas], loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=len(lineas), frameon=False)
        ax.grid(True, axis="y", alpha=0.3)
        return fig

    def crearFiguraBarridoInclinacion(self, dfBarrido: pl.DataFrame, inclinacionOptima: float, inclinacionesMarcadas: dict = None) -> Figure:
        """Radiación anual en el plano frente a la inclinación, con el óptimo y otras inclinaciones marcadas."""
        fig = Figure(figsize=(9, 5.5))
        ax = fig.subplots()
        inclinaciones = dfBarrido["Inclinacion_grados"].to_numpy()
        radiacion = dfBarrido["RadiacionAnual_kWhm2"].to_numpy()
        ax.plot(inclinaciones, radiacion, color="tab:blue", linewidth=2)
        maximo = radiacion[np.argmin(np.abs(inclinaciones - inclinacionOptima))]
        ax.plot(inclinacionOptima, maximo, marker="o", markersize=10, color="tab:red", linestyle="none",
                label=f"Óptimo: {inclinacionOptima:g}° → {maximo:,.1f} kWh/m²·año")
        for etiqueta, inclinacion in (inclinacionesMarcadas or {}).items():
            valor = float(np.interp(inclinacion, inclinaciones, radiacion))
            ax.plot(inclinacion, valor, marker="s", markersize=8, linestyle="none", label=f"{etiqueta}: {inclinacion:.2f}° → {valor:,.1f}")
        ax.set_title("Radiación anual en el plano frente a la inclinación (orientación sur)")
        ax.set_xlabel("Inclinación (°)")
        ax.set_ylabel("Radiación anual (kWh/m²·año)")
        ax.yaxis.set_major_formatter(Graficos.formatoMiles())
        ax.set_xlim(0, 90)
        ax.grid(True, alpha=0.3)
        ax.legend()
        return fig

    # ------------------------------------------------------------------
    # F-Chart
    # ------------------------------------------------------------------
    def crearFiguraFChartMensual(self, dfMensual: pl.DataFrame, titulo: str = None) -> Figure:
        """Energía solar y auxiliar de cada mes (barras apiladas) y fracción solar mensual (línea)."""
        fig = Figure(figsize=(10, 5.5))
        ax = fig.subplots()
        posiciones = np.arange(12)
        solar = dfMensual["Qu_kWhmes"].to_numpy()
        auxiliar = dfMensual["Qaux_kWhmes"].to_numpy()
        barraSolar = ax.bar(posiciones, solar, color="tab:orange", width=0.65, label="Energía solar")
        barraAuxiliar = ax.bar(posiciones, auxiliar, bottom=solar, color="tab:gray", width=0.65, label="Energía auxiliar")
        ax.set_ylabel("Energía (kWh/mes)")
        ax.yaxis.set_major_formatter(Graficos.formatoMiles())
        ax.set_xticks(posiciones)
        ax.set_xticklabels(self.mesesCortos)
        axFraccion = ax.twinx()
        axFraccion.plot(posiciones, dfMensual["FraccionSolar"].to_numpy(), color="tab:green", marker="o", linewidth=2, label="Fracción solar")
        axFraccion.set_ylim(0, 1.05)
        axFraccion.yaxis.set_major_formatter(Graficos.formatoPorcentaje())
        axFraccion.set_ylabel("Fracción solar mensual")
        lineas = [barraSolar, barraAuxiliar, axFraccion.lines[0]]
        ax.legend(lineas, [l.get_label() for l in lineas], loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=len(lineas), frameon=False)
        ax.set_title(titulo or "Energía solar, auxiliar y fracción solar por mes")
        ax.grid(True, axis="y", alpha=0.3)
        return fig

    def crearFiguraFraccionArea(self, dfCurva: pl.DataFrame, area: float, fraccion: float, fraccionMinima: float, fraccionMaxima: float) -> Figure:
        """Fracción solar anual frente al área de captación, con la banda objetivo y el diseño."""
        fig = Figure(figsize=(9, 5.5))
        ax = fig.subplots()
        ax.plot(dfCurva["Area_m2"].to_numpy(), dfCurva["FraccionAnual"].to_numpy(), color="tab:blue", linewidth=2)
        ax.axhspan(fraccionMinima, fraccionMaxima, color="tab:green", alpha=0.15, label=f"Objetivo: {fraccionMinima:.0%} a {fraccionMaxima:.0%}")
        ax.plot(area, fraccion, marker="o", markersize=10, color="tab:red", linestyle="none", label=f"Diseño: {area:.2f} m² → {fraccion:.1%}")
        ax.set_title("Fracción solar anual frente al área de captación")
        ax.set_xlabel("Área de captación (m²)")
        ax.set_ylabel("Fracción solar anual")
        ax.yaxis.set_major_formatter(Graficos.formatoPorcentaje())
        ax.set_ylim(0, 1.05)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="lower right")
        return fig

    # ------------------------------------------------------------------
    # Fotovoltaica
    # ------------------------------------------------------------------
    def crearFiguraEnergiaFotovoltaica(self, dfMensual: pl.DataFrame, unidadEnergia: str = "kWh") -> Figure:
        """Energía útil de cada mes (barras) y radiación diaria media (línea)."""
        columnaEnergia = f"Energia_{unidadEnergia}mes"
        fig = Figure(figsize=(10, 5.5))
        ax = fig.subplots()
        posiciones = np.arange(12)
        energia = dfMensual[columnaEnergia].to_numpy()
        barras = ax.bar(posiciones, energia, color="tab:blue", width=0.65, label="Energía útil")
        decimales = 0 if energia.max() >= 100 else 2
        for barra, valor in zip(barras, energia):
            ax.annotate(f"{valor:,.{decimales}f}", (barra.get_x() + barra.get_width() / 2, valor), xytext=(0, 3),
                        textcoords="offset points", ha="center", fontsize=8)
        ax.set_ylabel(f"Energía útil ({unidadEnergia}/mes)")
        ax.set_ylim(0, energia.max() * 1.2)
        ax.set_xticks(posiciones)
        ax.set_xticklabels(self.mesesCortos)
        axRadiacion = ax.twinx()
        axRadiacion.plot(posiciones, dfMensual["RadiacionDiaria_kWhm2dia"].to_numpy(), color="tab:orange", marker="o", label="Radiación diaria")
        axRadiacion.set_ylabel("Radiación diaria media (kWh/m²·día)")
        axRadiacion.set_ylim(0, dfMensual["RadiacionDiaria_kWhm2dia"].max() * 1.7)
        lineas = [barras, axRadiacion.lines[0]]
        ax.legend(lineas, [l.get_label() for l in lineas], loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=len(lineas), frameon=False)
        ax.set_title("Energía útil mensual del sistema fotovoltaico")
        ax.grid(True, axis="y", alpha=0.3)
        return fig

    # ------------------------------------------------------------------
    # Guardado
    # ------------------------------------------------------------------
    def guardarFigura(self, fig: Figure, nombreArchivo: str) -> list:
        """Guarda la figura en png y svg en la carpeta de salidas (la crea si no existe)."""
        if self.carpetaSalidas is None:
            raise ValueError("No se indicó la carpeta de salidas del graficador.")
        return Graficos.guardarFigura(fig, self.carpetaSalidas, nombreArchivo)

    @staticmethod
    def figuraABytes(fig: Figure, formato: str) -> bytes:
        return Graficos.figuraABytes(fig, formato)
