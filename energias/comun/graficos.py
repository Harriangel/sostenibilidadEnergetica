"""Utilidades de gráficas comunes a todas las tecnologías (API Figure de matplotlib, sin pyplot)."""
from io import BytesIO
from pathlib import Path

from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter


class Graficos:
    """Guardado de figuras en png y svg, conversión a bytes y formatos de eje comunes."""

    formatosSalida = ("png", "svg")
    resolucion = 200  # dpi

    @classmethod
    def guardarFigura(cls, fig: Figure, carpeta: Path, nombreArchivo: str) -> list:
        """Guarda la figura en la carpeta en cada formato de salida. Devuelve las rutas."""
        carpeta = Path(carpeta)
        carpeta.mkdir(parents=True, exist_ok=True)
        rutas = []
        for formato in cls.formatosSalida:
            ruta = carpeta / f"{nombreArchivo}.{formato}"
            fig.savefig(ruta, dpi=cls.resolucion, bbox_inches="tight")
            rutas.append(ruta)
        return rutas

    @classmethod
    def figuraABytes(cls, fig: Figure, formato: str) -> bytes:
        """Figura en memoria (png o svg), por ejemplo para botones de descarga."""
        if formato not in cls.formatosSalida:
            raise ValueError(f"Formato '{formato}' no válido. Opciones: {', '.join(cls.formatosSalida)}.")
        buffer = BytesIO()
        fig.savefig(buffer, format=formato, dpi=cls.resolucion, bbox_inches="tight")
        return buffer.getvalue()

    @classmethod
    def figuraABytesTodos(cls, fig: Figure) -> dict:
        """{formato: bytes} para cada formato de salida."""
        return {formato: cls.figuraABytes(fig, formato) for formato in cls.formatosSalida}

    # ------------------------------------------------------------------
    # Formatos de eje
    # ------------------------------------------------------------------
    @staticmethod
    def formatoMiles() -> FuncFormatter:
        """Números enteros con separador de miles: 1,234,567."""
        return FuncFormatter(lambda valor, _: f"{valor:,.0f}")

    @staticmethod
    def formatoGeneral() -> FuncFormatter:
        """Formato compacto ('g'): 0.5, 20, 1e-05."""
        return FuncFormatter(lambda valor, _: f"{valor:g}")

    @staticmethod
    def formatoComaDecimal() -> FuncFormatter:
        """Formato compacto con coma decimal: 0,02."""
        return FuncFormatter(lambda valor, _: f"{valor:g}".replace(".", ","))

    @staticmethod
    def formatoDecimales(decimales: int) -> FuncFormatter:
        """Número fijo de decimales con separador de miles: 1,234.56."""
        return FuncFormatter(lambda valor, _: f"{valor:,.{decimales}f}")

    @staticmethod
    def formatoMillones() -> FuncFormatter:
        """Valor en millones: 14500000 → 14.5."""
        return FuncFormatter(lambda valor, _: f"{valor / 1e6:g}")

    @staticmethod
    def formatoPorcentaje(decimales: int = 0) -> FuncFormatter:
        """Fracción como porcentaje: 0.07 → 7 %."""
        return FuncFormatter(lambda valor, _: f"{valor * 100:.{decimales}f} %")
