"""Recurso solar: lectura del TMY de NSRDB, posición del sol e irradiancia en un plano inclinado.

Implementa docs/especificaciones/solar/recursoSolar.md. La posición del sol se calcula a la hora de
cada registro del TMY (hh:30), con las ecuaciones de Spencer (1971) y Duffie y Beckman (2013).
"""
import csv
import io
from pathlib import Path

import numpy as np
import polars as pl


class LectorTmy:
    """Lee un TMY horario de NSRDB (formato CSV con dos líneas de metadatos antes de los datos).

    Devuelve los metadatos (latitud, longitud, zona horaria, elevación) y un DataFrame con las
    columnas renombradas: Mes, Dia, Hora, Minuto, Temperatura_C, DHI_Wm2, DNI_Wm2, GHI_Wm2,
    Cenit_grados y Albedo.
    """

    registrosPorAnio = 8760
    columnasDatos = {
        "Month": "Mes",
        "Day": "Dia",
        "Hour": "Hora",
        "Minute": "Minuto",
        "Temperature": "Temperatura_C",
        "DHI": "DHI_Wm2",
        "DNI": "DNI_Wm2",
        "GHI": "GHI_Wm2",
        "Solar Zenith Angle": "Cenit_grados",
        "Surface Albedo": "Albedo",
    }
    columnasMetadatos = {"Latitude": "latitud", "Longitude": "longitud", "Time Zone": "zonaHoraria", "Elevation": "elevacion"}

    def __init__(self, rutaArchivo: Path):
        self.rutaArchivo = Path(rutaArchivo)

    def leer(self) -> tuple:
        """(metadatos, DataFrame horario). Lanza ValueError si faltan columnas o registros."""
        if not self.rutaArchivo.exists():
            raise FileNotFoundError(f"No se encontró el archivo TMY: {self.rutaArchivo}")
        lineas = self.rutaArchivo.read_text(encoding="utf-8-sig").splitlines()
        if len(lineas) < 4:
            raise ValueError("El archivo TMY no tiene las dos líneas de metadatos y los datos.")

        encabezadoMetadatos, valoresMetadatos = list(csv.reader(lineas[:2]))
        metadatosCrudos = dict(zip(encabezadoMetadatos, valoresMetadatos))
        faltantes = [c for c in self.columnasMetadatos if c not in metadatosCrudos]
        if faltantes:
            raise ValueError(f"Faltan metadatos en el TMY: {', '.join(faltantes)}.")
        metadatos = {nombre: float(metadatosCrudos[c]) for c, nombre in self.columnasMetadatos.items()}

        dfCrudo = pl.read_csv(io.StringIO("\n".join(lineas[2:])), infer_schema_length=0)
        faltantes = [c for c in self.columnasDatos if c not in dfCrudo.columns]
        if faltantes:
            raise ValueError(f"Faltan columnas en el TMY: {', '.join(faltantes)}.")
        df = dfCrudo.select(
            [pl.col(c).cast(pl.Float64).alias(nombre) for c, nombre in self.columnasDatos.items()]
        ).with_columns(pl.col("Mes", "Dia", "Hora", "Minuto").cast(pl.Int64))
        if df.height != self.registrosPorAnio:
            raise ValueError(f"El TMY debe tener {self.registrosPorAnio} registros horarios (tiene {df.height}).")
        return metadatos, df


class PosicionSolar:
    """Cenit y acimut del sol para una ubicación, a partir del día del año y la hora estándar local."""

    diasPorMes = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

    def __init__(self, latitud: float, longitud: float, zonaHoraria: float):
        if not -90 <= latitud <= 90:
            raise ValueError(f"La latitud debe estar entre −90° y 90° (se recibió {latitud}).")
        if not -180 <= longitud <= 180:
            raise ValueError(f"La longitud debe estar entre −180° y 180° (se recibió {longitud}).")
        if not -12 <= zonaHoraria <= 14:
            raise ValueError(f"La zona horaria debe estar entre −12 y 14 h (se recibió {zonaHoraria}).")
        self.latitud = latitud
        self.longitud = longitud
        self.zonaHoraria = zonaHoraria

    @classmethod
    def diaDelAnio(cls, mes, dia) -> np.ndarray:
        """Día del año (1 a 365) en un año no bisiesto."""
        acumulado = np.concatenate(([0], np.cumsum(cls.diasPorMes)[:-1]))
        return acumulado[np.asarray(mes) - 1] + np.asarray(dia)

    def calcular(self, diaAnio, horaEstandar) -> dict:
        """{'cenit', 'acimut'} en grados; acimut desde el norte en sentido horario.

        diaAnio: 1 a 365; horaEstandar: hora estándar local en horas decimales (sin horario de verano).
        """
        diaAnio = np.asarray(diaAnio, dtype=float)
        horaEstandar = np.asarray(horaEstandar, dtype=float)
        B = np.radians((diaAnio - 1) * 360 / 365)
        ecuacionTiempo = 229.2 * (
            0.000075 + 0.001868 * np.cos(B) - 0.032077 * np.sin(B) - 0.014615 * np.cos(2 * B) - 0.04089 * np.sin(2 * B)
        )
        declinacion = (
            0.006918 - 0.399912 * np.cos(B) + 0.070257 * np.sin(B) - 0.006758 * np.cos(2 * B)
            + 0.000907 * np.sin(2 * B) - 0.002697 * np.cos(3 * B) + 0.00148 * np.sin(3 * B)
        )
        horaSolar = horaEstandar + (4 * (self.longitud - 15 * self.zonaHoraria) + ecuacionTiempo) / 60
        anguloHorario = np.radians(15 * (horaSolar - 12))
        phi = np.radians(self.latitud)

        cosCenit = np.clip(
            np.sin(phi) * np.sin(declinacion) + np.cos(phi) * np.cos(declinacion) * np.cos(anguloHorario), -1, 1
        )
        cenit = np.arccos(cosCenit)
        senCenit = np.sin(cenit)
        with np.errstate(divide="ignore", invalid="ignore"):
            cosAcimut = np.clip((cosCenit * np.sin(phi) - np.sin(declinacion)) / (senCenit * np.cos(phi)), -1, 1)
        acimutDesdeSur = np.where(senCenit < 1e-9, 0.0, np.copysign(np.abs(np.arccos(cosAcimut)), anguloHorario))
        return {
            "cenit": np.degrees(cenit),
            "acimut": np.mod(np.degrees(acimutDesdeSur) + 180, 360),
        }


class RecursoSolar:
    """Irradiancia en un plano inclinado (modelo isotrópico) a partir de un TMY de NSRDB.

    Todas las salidas son polars.DataFrame con la unidad en el nombre de las columnas.
    """

    nombreTecnologia = "solar"
    archivoPorDefecto = "tmyCiudadMexico.csv"
    componentesHorizontales = ("DNI_Wm2", "DHI_Wm2", "GHI_Wm2")
    componentesInclinadas = ("Gbi_Wm2", "Gdi_Wm2", "Gri_Wm2", "GTI_Wm2")
    nombresMeses = (
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    )

    def __init__(self, rutaTmy: Path = None, acimutPanel: float = 180.0, usarCenitArchivo: bool = True):
        """
        rutaTmy: TMY de NSRDB; por defecto data/solar/tmyCiudadMexico.csv.
        acimutPanel: acimut del plano en grados desde el norte, sentido horario (180 = sur).
        usarCenitArchivo: usa el cenit del TMY (True) o el calculado (False).
        """
        if not 0 <= acimutPanel < 360:
            raise ValueError(f"El acimut del panel debe estar en [0°, 360°) (se recibió {acimutPanel}).")
        carpetaRaiz = Path(__file__).resolve().parents[2]
        self.rutaTmy = Path(rutaTmy) if rutaTmy is not None else carpetaRaiz / "data" / self.nombreTecnologia / self.archivoPorDefecto
        self.acimutPanel = acimutPanel
        self.usarCenitArchivo = usarCenitArchivo

        self.metadatos, dfTmy = LectorTmy(self.rutaTmy).leer()
        if (dfTmy.select(pl.col(*self.componentesHorizontales)) < 0).to_numpy().any():
            raise ValueError("El TMY tiene irradiancias negativas.")
        if not dfTmy["Albedo"].is_between(0, 1).all():
            raise ValueError("El TMY tiene valores de albedo fuera de [0, 1].")
        self.posicionSolar = PosicionSolar(self.metadatos["latitud"], self.metadatos["longitud"], self.metadatos["zonaHoraria"])
        posicion = self.posicionSolar.calcular(
            PosicionSolar.diaDelAnio(dfTmy["Mes"].to_numpy(), dfTmy["Dia"].to_numpy()),
            (dfTmy["Hora"] + dfTmy["Minuto"] / 60).to_numpy(),
        )
        self.dfTmy = dfTmy.with_columns(
            pl.Series("CenitCalculado_grados", posicion["cenit"]),
            pl.Series("Acimut_grados", posicion["acimut"]),
        )

    @property
    def latitud(self) -> float:
        return self.metadatos["latitud"]

    # ------------------------------------------------------------------
    # Irradiancia inclinada
    # ------------------------------------------------------------------
    @staticmethod
    def validarInclinacion(inclinacion: float) -> None:
        if not 0 <= inclinacion <= 90:
            raise ValueError(f"La inclinación debe estar entre 0° y 90° (se recibió {inclinacion}).")

    def calcularPlano(self, inclinacion: float) -> pl.DataFrame:
        """Tabla horaria con AOI, Gbi, Gdi, Gri y GTI (W/m²) para la inclinación dada (grados)."""
        self.validarInclinacion(inclinacion)
        beta = np.radians(inclinacion)
        columnaCenit = "Cenit_grados" if self.usarCenitArchivo else "CenitCalculado_grados"
        cenit = np.radians(self.dfTmy[columnaCenit].to_numpy())
        acimut = np.radians(self.dfTmy["Acimut_grados"].to_numpy())
        cosAoi = np.cos(cenit) * np.cos(beta) + np.sin(cenit) * np.sin(beta) * np.cos(acimut - np.radians(self.acimutPanel))
        gbi = self.dfTmy["DNI_Wm2"].to_numpy() * np.maximum(cosAoi, 0.0)
        gdi = self.dfTmy["DHI_Wm2"].to_numpy() * (1 + np.cos(beta)) / 2
        gri = self.dfTmy["GHI_Wm2"].to_numpy() * self.dfTmy["Albedo"].to_numpy() * (1 - np.cos(beta)) / 2
        return self.dfTmy.with_columns(
            pl.Series("AOI_grados", np.degrees(np.arccos(np.clip(cosAoi, -1, 1)))),
            pl.Series("Gbi_Wm2", gbi),
            pl.Series("Gdi_Wm2", gdi),
            pl.Series("Gri_Wm2", gri),
            pl.Series("GTI_Wm2", gbi + gdi + gri),
        )

    def radiacionAnual(self, inclinacion: float) -> float:
        """Radiación anual en el plano (Wh/m²·año): suma de los 8760 registros horarios."""
        return float(self.calcularPlano(inclinacion)["GTI_Wm2"].sum())

    def barridoInclinacion(self, inclinaciones=None) -> pl.DataFrame:
        """Radiación anual (kWh/m²·año) para cada inclinación; por defecto de 0° a 90° cada 1°."""
        if inclinaciones is None:
            inclinaciones = range(0, 91)
        filas = [
            {"Inclinacion_grados": float(beta), "RadiacionAnual_kWhm2": self.radiacionAnual(beta) / 1000}
            for beta in inclinaciones
        ]
        return pl.DataFrame(filas)

    def inclinacionOptima(self, inclinaciones=None) -> dict:
        """{'inclinacion', 'radiacionAnual_kWhm2'} de la inclinación con mayor radiación anual."""
        dfBarrido = self.barridoInclinacion(inclinaciones)
        fila = dfBarrido.sort("RadiacionAnual_kWhm2", descending=True).row(0, named=True)
        return {"inclinacion": fila["Inclinacion_grados"], "radiacionAnual_kWhm2": fila["RadiacionAnual_kWhm2"]}

    # ------------------------------------------------------------------
    # Agregados
    # ------------------------------------------------------------------
    def tablaMeses(self) -> pl.DataFrame:
        return pl.DataFrame(
            {"Mes": list(range(1, 13)), "NombreMes": list(self.nombresMeses), "Dias": list(PosicionSolar.diasPorMes)}
        )

    def radiacionMensual(self, inclinacion: float) -> pl.DataFrame:
        """HTdia (kWh/m²·día), HTmes (kWh/m²·mes) y Tamb (°C) de cada mes en el plano inclinado.

        Con inclinación 0° la radiación es la horizontal (GHI efectiva del modelo).
        """
        dfPlano = self.calcularPlano(inclinacion)
        dfMes = dfPlano.group_by("Mes").agg(
            pl.col("GTI_Wm2").sum().alias("suma_Wh"),
            pl.col("Temperatura_C").mean().alias("Tamb_C"),
        )
        return (
            self.tablaMeses()
            .join(dfMes, on="Mes")
            .sort("Mes")
            .select(
                "Mes",
                "NombreMes",
                "Dias",
                (pl.col("suma_Wh") / pl.col("Dias") / 1000).alias("HTdia_kWhm2dia"),
                (pl.col("suma_Wh") / 1000).alias("HTmes_kWhm2mes"),
                "Tamb_C",
            )
        )

    def radiacionDiaria(self, dfPlano: pl.DataFrame, componentes=None) -> pl.DataFrame:
        """Radiación de cada día (kWh/m²·día) por componente: suma de los registros horarios / 1000."""
        componentes = list(componentes or self.componentesInclinadas)
        return (
            dfPlano.group_by("Mes", "Dia")
            .agg([(pl.col(c).sum() / 1000).alias(c.replace("_Wm2", "_kWhm2dia")) for c in componentes])
            .sort("Mes", "Dia")
            .with_row_index("DiaAnio", offset=1)
        )

    def perfilHorario(self, dfPlano: pl.DataFrame, componentes=None, porMes: bool = False) -> pl.DataFrame:
        """Irradiancia promedio (W/m²) por hora del día; por mes y hora si porMes es True."""
        componentes = list(componentes or self.componentesInclinadas)
        claves = ["Mes", "Hora"] if porMes else ["Hora"]
        return dfPlano.group_by(claves).agg([pl.col(c).mean() for c in componentes]).sort(claves)
