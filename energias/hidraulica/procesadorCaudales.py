from datetime import date, timedelta

import polars as pl


class ProcesadorCaudales:
    """Transforma la serie diaria de caudales en curvas de caudal clasificado.

    Un periodo anual va del 1° de octubre al 30 de septiembre y se identifica
    con el año en que inicia (periodo 2000 = 01/10/2000 a 30/09/2001).
    El 29 de febrero se descarta para que todos los periodos tengan 365 días.
    """

    diasPorPeriodo = 365

    def __init__(self, mesInicio: int = 10, minDiasPorPeriodo: int = 300):
        self.mesInicio = mesInicio
        self.minDiasPorPeriodo = minDiasPorPeriodo
        self.dfCalendario = self.crearCalendarioReferencia()
        self.dfResumenPeriodos = None

    def crearCalendarioReferencia(self) -> pl.DataFrame:
        """Calendario de 365 días (sin 29 de febrero) con su NumDia de 1 a 365."""
        fechaInicio = date(2001, self.mesInicio, 1)
        fechaFin = fechaInicio + timedelta(days=self.diasPorPeriodo - 1)
        return pl.DataFrame(
            {"FechaRef": pl.date_range(fechaInicio, fechaFin, interval="1d", eager=True)}
        ).select(
            pl.col("FechaRef").dt.month().alias("Mes"),
            pl.col("FechaRef").dt.day().alias("Dia"),
            pl.int_range(1, self.diasPorPeriodo + 1).alias("NumDia"),
        )

    def renombrarCaudal(self, df: pl.DataFrame) -> pl.DataFrame:
        """La columna 'Valor' del archivo pasa a llamarse 'Caudal'."""
        return df.rename({"Valor": "Caudal"})

    def agregarColumnasFecha(self, df: pl.DataFrame) -> pl.DataFrame:
        """Paso 3: agrega 'Ano', 'Mes' y 'Dia' a partir de 'Fecha'."""
        return df.with_columns(
            pl.col("Fecha").dt.year().alias("Ano"),
            pl.col("Fecha").dt.month().alias("Mes"),
            pl.col("Fecha").dt.day().alias("Dia"),
        )

    def asignarPeriodosAnuales(self, df: pl.DataFrame) -> pl.DataFrame:
        """Paso 4: asigna cada fecha a su periodo anual (octubre a septiembre) y
        conserva solo los periodos con al menos 'minDiasPorPeriodo' días con dato.

        Los días que falten en los periodos conservados se completan en el paso
        siguiente. Se guarda en 'dfResumenPeriodos' la cobertura de cada periodo.
        """
        dfPeriodos = df.with_columns(
            pl.when(pl.col("Mes") >= self.mesInicio)
            .then(pl.col("Ano"))
            .otherwise(pl.col("Ano") - 1)
            .alias("Periodo")
        ).filter(~((pl.col("Mes") == 2) & (pl.col("Dia") == 29)))

        self.dfResumenPeriodos = (
            dfPeriodos.group_by("Periodo")
            .agg(pl.len().alias("DiasConDato"))
            .with_columns(
                (self.diasPorPeriodo - pl.col("DiasConDato")).alias("DiasFaltantes"),
                (pl.col("DiasConDato") >= self.minDiasPorPeriodo).alias("Incluido"),
            )
            .sort("Periodo")
        )

        periodosValidos = self.dfResumenPeriodos.filter(pl.col("Incluido"))["Periodo"]
        if periodosValidos.len() == 0:
            raise ValueError(
                f"Ningún periodo tiene al menos {self.minDiasPorPeriodo} días con dato."
            )
        # implode(): la serie se pasa como una sola colección de valores (is_in con una serie
        # del mismo tipo es ambiguo y está obsoleto en polars)
        return dfPeriodos.filter(pl.col("Periodo").is_in(periodosValidos.implode()))

    def numerarDias(self, df: pl.DataFrame) -> pl.DataFrame:
        """Paso 5: numera los días de 1 a 365 dentro de cada periodo
        (1° de octubre = 1, 30 de septiembre = 365).

        Se arma una grilla completa de 365 días por periodo e incluye las filas
        de las fechas faltantes, que quedan con Caudal nulo.
        """
        dfGrilla = (
            df.select("Periodo")
            .unique()
            .join(self.dfCalendario, how="cross")
            .with_columns(
                pl.when(pl.col("Mes") >= self.mesInicio)
                .then(pl.col("Periodo"))
                .otherwise(pl.col("Periodo") + 1)
                .alias("Ano")
            )
            .with_columns(pl.date(pl.col("Ano"), pl.col("Mes"), pl.col("Dia")).alias("Fecha"))
        )

        return (
            dfGrilla.join(
                df.select("Periodo", "Mes", "Dia", "Caudal"),
                on=["Periodo", "Mes", "Dia"],
                how="left",
            )
            .select("Fecha", "Ano", "Mes", "Dia", "Periodo", "NumDia", "Caudal")
            .sort("Periodo", "NumDia")
        )

    def clasificarCaudales(self, df: pl.DataFrame) -> pl.DataFrame:
        """Paso 7: dentro de cada periodo ordena los caudales de mayor a menor
        y los asigna a los días 1..365 sin modificar la numeración de los días."""
        return df.sort("Periodo", "NumDia").with_columns(
            pl.col("Caudal")
            .sort(descending=True, nulls_last=True)
            .over("Periodo")
            .alias("CaudalClasificado")
        )

    def calcularPromedioClasificado(self, df: pl.DataFrame) -> pl.DataFrame:
        """Paso 8: promedio de 'CaudalClasificado' de todos los periodos para
        cada NumDia."""
        return df.with_columns(
            pl.col("CaudalClasificado").mean().over("NumDia").alias("CaudalClasificadoPromedio")
        )

    def construirResultado(self, df: pl.DataFrame) -> pl.DataFrame:
        """Paso 10: dataframe final con 'NumDia' y 'CaudalClasificadoPromedio'."""
        return (
            df.select("NumDia", "CaudalClasificadoPromedio")
            .unique(subset=["NumDia"])
            .sort("NumDia")
        )
