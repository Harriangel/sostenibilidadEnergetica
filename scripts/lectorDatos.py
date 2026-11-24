import io
from pathlib import Path

import polars as pl


class LectorDatos:
    """Lee el archivo CSV de caudales de una estación hidrológica.

    Fuentes soportadas:
      - IDEAM (Colombia, DHIME): encabezado en la primera línea, caudal en 'Valor'
        y fecha como 'AAAA-MM-DD HH:MM'.
      - CONAGUA (México): varias líneas de metadatos antes del encabezado, caudal en
        'Gasto en Rio(m3/s)' (junto a 'Nivel(m)'), fecha como 'AAAA-MM-DD' y días
        con nivel pero sin gasto (celda vacía).
    """

    fuentes = {
        "IDEAM": {"columnaFecha": "Fecha", "columnaValor": "Valor"},
        "CONAGUA": {"columnaFecha": "Fecha", "columnaValor": "Gasto en Rio(m3/s)"},
    }

    def __init__(self, rutaArchivo: Path, fuente: str = "IDEAM"):
        self.rutaArchivo = Path(rutaArchivo)
        self.fuente = fuente.strip().upper()
        if self.fuente not in self.fuentes:
            raise ValueError(f"Fuente '{fuente}' no válida. Opciones: IDEAM o CONAGUA.")
        self.columnaFecha = self.fuentes[self.fuente]["columnaFecha"]
        self.columnaValor = self.fuentes[self.fuente]["columnaValor"]

    def leerLineas(self) -> list:
        """Lee el archivo como texto (UTF-8, con respaldo en latin-1)."""
        contenido = self.rutaArchivo.read_bytes()
        try:
            texto = contenido.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = contenido.decode("latin-1")
        return texto.splitlines()

    def encontrarEncabezado(self, lineas: list) -> int:
        """Índice de la línea del encabezado, saltando los metadatos previos."""
        for indice, linea in enumerate(lineas):
            if self.columnaFecha in linea and self.columnaValor in linea:
                return indice
        raise ValueError(
            f"No se encontró el encabezado con las columnas '{self.columnaFecha}' y "
            f"'{self.columnaValor}'. ¿El archivo corresponde a la fuente {self.fuente}?"
        )

    def leer(self) -> pl.DataFrame:
        """Pasos 1 y 2: lee el CSV y extrae 'Fecha' (date) y 'Valor' (float)."""
        if not self.rutaArchivo.exists():
            raise FileNotFoundError(f"No se encontró el archivo: {self.rutaArchivo}")

        lineas = self.leerLineas()
        indiceEncabezado = self.encontrarEncabezado(lineas)

        dfCrudo = pl.read_csv(
            io.StringIO("\n".join(lineas[indiceEncabezado:])),
            schema_overrides={self.columnaValor: pl.Float64},
            infer_schema_length=10000,
        )

        # La fecha empieza con AAAA-MM-DD en ambas fuentes; se toman solo los
        # 10 primeros caracteres para castearla a date
        dfDatos = dfCrudo.select(
            pl.col(self.columnaFecha).str.slice(0, 10).str.to_date("%Y-%m-%d").alias("Fecha"),
            pl.col(self.columnaValor).cast(pl.Float64).alias("Valor"),
        )

        # Se descartan los días sin caudal (en CONAGUA hay días con solo nivel); esos
        # días se completan después como faltantes. Una fecha repetida también
        # distorsionaría el conteo de días por periodo.
        return dfDatos.drop_nulls().unique(subset=["Fecha"], keep="first", maintain_order=True)
