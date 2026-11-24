import unicodedata

import polars as pl


class CalculadoraPotencia:
    """Calcula la energía anual generada para cada caudal de equipamiento (Qe).

    Para cada Qe se aplica, fila por fila sobre la curva de caudal clasificado
    promedio, Pc = ηg * ηG * ρ * g * Qi * H (en W), donde Qi es el caudal
    clasificado limitado hacia arriba por Qe y llevado a cero si es inferior
    al caudal mínimo técnico Qmt = Qe * K.
    """

    horasPorDia = 24

    # Factor K (caudal mínimo técnico = Qe * K) según el tipo de turbina
    factoresK = {
        "pelton": 0.10,
        "ossberger": 0.15,
        "kaplan": 0.22,
        "semikaplan": 0.35,
        "francis": 0.35,
        "helice": 0.65,
    }

    # Paso de Qe (m³/s) según el caudal máximo del clasificado promedio:
    # (límite superior exclusivo, paso). Por encima del último límite se usa el último paso.
    escalonesPasoQe = ((25, 0.1), (100, 1.0), (1000, 10.0), (2000, 50.0))

    # Factor de conversión desde W / Wh a cada unidad
    factoresUnidad = {"W": 1.0, "kW": 1e-3, "MW": 1e-6, "GW": 1e-9}

    def __init__(
        self,
        saltoNeto: float,
        tipoTurbina: str,
        unidadEnergia: str = "kW",
        densidadAgua: float = 1000.0,
        gravedad: float = 9.8,
        eficienciaTurbina: float = 0.85,
        eficienciaGenerador: float = 0.95,
        eficienciaTotal: float = None,
        pasoQe: float = None,
    ):
        self.saltoNeto = saltoNeto
        self.densidadAgua = densidadAgua
        self.gravedad = gravedad
        self.eficienciaTurbina = eficienciaTurbina
        self.eficienciaGenerador = eficienciaGenerador
        # Si se indica la eficiencia total (ηg*ηG), reemplaza el producto de las dos
        self.eficienciaTotal = (
            eficienciaTotal if eficienciaTotal is not None else eficienciaTurbina * eficienciaGenerador
        )
        if not 0 < self.eficienciaTotal <= 1:
            raise ValueError("La eficiencia total debe estar entre 0 y 1.")
        # Si pasoQe es None, se define automáticamente según el caudal máximo
        self.pasoQe = pasoQe

        self.tipoTurbina = self.normalizarTexto(tipoTurbina)
        if self.tipoTurbina not in self.factoresK:
            raise ValueError(
                f"Tipo de turbina '{tipoTurbina}' no válido. "
                "Opciones: Pelton, Ossberger, Kaplan, Semikaplan, Francis o Hélice."
            )
        self.factorK = self.factoresK[self.tipoTurbina]

        if unidadEnergia not in self.factoresUnidad:
            raise ValueError(
                f"Unidad '{unidadEnergia}' no válida. Opciones: W, kW, MW o GW."
            )
        self.unidadEnergia = unidadEnergia
        self.factorUnidad = self.factoresUnidad[unidadEnergia]
        self.nombreColumnaEnergia = f"EnergiaAnual_{unidadEnergia}h"
        self.nombreColumnaEnergiaDiaria = f"EnergiaDiaria_{unidadEnergia}h"

    @staticmethod
    def normalizarTexto(texto: str) -> str:
        """Minúsculas y sin tildes, para aceptar 'Hélice', 'helice', etc."""
        textoSinTildes = unicodedata.normalize("NFD", texto.strip().lower())
        return "".join(c for c in textoSinTildes if unicodedata.category(c) != "Mn")

    def definirPasoQe(self, qeMaximo: float) -> float:
        """Paso entre caudales de equipamiento: el indicado por el usuario o,
        si no se indicó, el que corresponde al caudal máximo (ver escalonesPasoQe)."""
        if self.pasoQe is not None:
            return self.pasoQe
        for limite, paso in self.escalonesPasoQe:
            if qeMaximo < limite:
                return paso
        return self.escalonesPasoQe[-1][1]

    def crearCaudalesEquipamiento(self, dfCaudales: pl.DataFrame) -> list:
        """Qe va del mínimo al máximo del caudal clasificado promedio,
        avanzando de 'paso' en 'paso' (m³/s)."""
        qeMinimo = dfCaudales["CaudalClasificadoPromedio"].min()
        qeMaximo = dfCaudales["CaudalClasificadoPromedio"].max()
        self.pasoQeUtilizado = self.definirPasoQe(qeMaximo)
        nPasos = int((qeMaximo - qeMinimo) / self.pasoQeUtilizado + 1e-9)
        return [qeMinimo + i * self.pasoQeUtilizado for i in range(nPasos + 1)]

    def calcularPotenciaDiaria(self, dfCaudales: pl.DataFrame, caudalEquipamiento: float) -> pl.DataFrame:
        """Potencia (W) y energía diaria (Wh-día) fila por fila para un Qe."""
        caudalMinimoTecnico = caudalEquipamiento * self.factorK
        return (
            dfCaudales.select("NumDia", "CaudalClasificadoPromedio")
            .with_columns(
                pl.when(pl.col("CaudalClasificadoPromedio") < caudalMinimoTecnico)
                .then(0.0)
                .otherwise(pl.min_horizontal(pl.col("CaudalClasificadoPromedio"), pl.lit(caudalEquipamiento)))
                .alias("CaudalUtilizado")
            )
            .with_columns(
                (
                    self.eficienciaTotal
                    * self.densidadAgua
                    * self.gravedad
                    * pl.col("CaudalUtilizado")
                    * self.saltoNeto
                ).alias("Potencia")
            )
            .with_columns((pl.col("Potencia") * self.horasPorDia).alias("EnergiaDiaria"))
        )

    def calcularEnergiaDiariaEnUnidad(self, dfCaudales: pl.DataFrame, caudalEquipamiento: float) -> pl.DataFrame:
        """Energía generada cada día (unidad elegida, h/día) para un Qe dado."""
        return self.calcularPotenciaDiaria(dfCaudales, caudalEquipamiento).select(
            "NumDia",
            "CaudalClasificadoPromedio",
            "CaudalUtilizado",
            (pl.col("EnergiaDiaria") * self.factorUnidad).alias(self.nombreColumnaEnergiaDiaria),
        )

    def calcularEnergiaAnual(self, dfCaudales: pl.DataFrame, caudalEquipamiento: float) -> float:
        """Energía generada al año (Wh-año): suma de la energía de todas las filas."""
        return self.calcularPotenciaDiaria(dfCaudales, caudalEquipamiento)["EnergiaDiaria"].sum()

    def calcularEnergiaPorCaudalEquipamiento(self, dfCaudales: pl.DataFrame) -> pl.DataFrame:
        """Guarda cada pareja Qe - energía anual, con la energía en la unidad elegida."""
        if dfCaudales["CaudalClasificadoPromedio"].null_count() > 0:
            raise ValueError("La curva de caudal clasificado promedio tiene valores nulos.")

        filas = []
        for caudalEquipamiento in self.crearCaudalesEquipamiento(dfCaudales):
            energiaAnualWh = self.calcularEnergiaAnual(dfCaudales, caudalEquipamiento)
            filas.append(
                {
                    "CaudalEquipamiento": caudalEquipamiento,
                    "CaudalMinimoTecnico": caudalEquipamiento * self.factorK,
                    self.nombreColumnaEnergia: energiaAnualWh * self.factorUnidad,
                }
            )
        return pl.DataFrame(filas)

    def identificarMaximo(self, dfEnergia: pl.DataFrame) -> dict:
        """Fila con la energía anual máxima (caudal de equipamiento óptimo)."""
        return dfEnergia.sort(self.nombreColumnaEnergia, descending=True).row(0, named=True)
