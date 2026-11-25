"""Dimensionamiento de un sistema solar térmico de ACS por el método F-Chart.

Implementa docs/especificaciones/solar/termica/fChartAcs.md. Por defecto usa la correlación de
Klein, Beckman y Duffie con la corrección para ACS; la correlación exponencial del informe del
curso queda como alternativa (correlacion="informe") para reproducirlo.
"""
import math

import numpy as np
import polars as pl


class SistemaFChart:
    """Demanda de ACS, fracción solar mensual y anual, casos de análisis y área de captación."""

    diasPorMes = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    nombresMeses = (
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    )
    joulesPorKWh = 3.6e6
    correlaciones = ("klein", "informe")

    # Klein, Beckman y Duffie (1976): f = a·D1 + b·D2 + c·D1² + d·D2² + e·D1³
    coeficientesKlein = (1.029, -0.065, -0.245, 0.0018, 0.0215)
    rangoD1Klein = (0.0, 3.0)
    rangoD2Klein = (0.0, 18.0)
    # Informe del curso: f = 1 − exp(−(a·D1 + b·D2 + c·D1² + d·D2² + e·D1·D2))
    coeficientesInforme = (0.525, 0.352, 1.2008, 0.0127, -0.3319)
    # Corrección para ACS de Klein: ΔT = 11,6 + 1,18·Tw + 3,86·Tred − 2,32·Tamb
    coeficientesCorreccionAcs = (11.6, 1.18, 3.86, -2.32)

    def __init__(
        self,
        climaMensual,
        numeroHabitaciones: int = 30,
        ocupacionPorHabitacion: float = 2,
        consumoPorPersona: float = 50,
        temperaturaUso: float = 45,
        temperaturaRed: float = 15,
        densidadAgua: float = 1.0,
        calorEspecifico: float = 4184,
        areaColector: float = 2,
        eficienciaOptica: float = 0.75,
        coeficientePerdidas: float = 4.5,
        fraccionObjetivoMinima: float = 0.6,
        fraccionObjetivoMaxima: float = 0.7,
        eficienciaSistema: float = 0.45,
        correlacion: str = "klein",
        temperaturaReferencia: float = 100,
        correccionAcs: bool = True,
        pasoArea: float = 0.1,
        maxIteraciones: int = 1000,
    ):
        """
        climaMensual: DataFrame con 12 filas y las columnas HTmes_kWhm2mes (radiación en el plano del
            colector, kWh/m²·mes) y Tamb_C (°C), como el de RecursoSolar.radiacionMensual, o un
            diccionario con esas dos listas.
        correlacion: "klein" (por defecto) o "informe".
        """
        self.htMes, self.tamb = self.validarClima(climaMensual)
        for nombre, valor in (
            ("número de habitaciones", numeroHabitaciones),
            ("ocupación por habitación", ocupacionPorHabitacion),
            ("consumo por persona", consumoPorPersona),
            ("densidad del agua", densidadAgua),
            ("calor específico", calorEspecifico),
            ("área del colector", areaColector),
            ("paso del área", pasoArea),
        ):
            if valor <= 0:
                raise ValueError(f"El valor de {nombre} debe ser positivo (se recibió {valor}).")
        if temperaturaUso <= temperaturaRed:
            raise ValueError("La temperatura de uso debe ser mayor que la temperatura de la red.")
        if not 0 < eficienciaOptica <= 1:
            raise ValueError(f"La eficiencia óptica debe estar en (0, 1] (se recibió {eficienciaOptica}).")
        if coeficientePerdidas < 0:
            raise ValueError("El coeficiente de pérdidas no puede ser negativo.")
        if not 0 < fraccionObjetivoMinima <= fraccionObjetivoMaxima <= 1:
            raise ValueError("Las fracciones objetivo deben cumplir 0 < mínima ≤ máxima ≤ 1.")
        if not 0 < eficienciaSistema <= 1:
            raise ValueError(f"La eficiencia del sistema debe estar en (0, 1] (se recibió {eficienciaSistema}).")
        if correlacion not in self.correlaciones:
            raise ValueError(f"Correlación '{correlacion}' no válida. Opciones: klein o informe.")
        if int(maxIteraciones) != maxIteraciones or maxIteraciones < 1:
            raise ValueError("El número máximo de iteraciones debe ser un entero positivo.")

        self.numeroHabitaciones = numeroHabitaciones
        self.ocupacionPorHabitacion = ocupacionPorHabitacion
        self.consumoPorPersona = consumoPorPersona
        self.temperaturaUso = temperaturaUso
        self.temperaturaRed = temperaturaRed
        self.densidadAgua = densidadAgua
        self.calorEspecifico = calorEspecifico
        self.areaColector = areaColector
        self.eficienciaOptica = eficienciaOptica
        self.coeficientePerdidas = coeficientePerdidas
        self.fraccionObjetivoMinima = fraccionObjetivoMinima
        self.fraccionObjetivoMaxima = fraccionObjetivoMaxima
        self.eficienciaSistema = eficienciaSistema
        self.correlacion = correlacion
        self.temperaturaReferencia = temperaturaReferencia
        self.correccionAcs = correccionAcs
        self.pasoArea = pasoArea
        self.maxIteraciones = int(maxIteraciones)

        self.dias = np.array(self.diasPorMes, dtype=float)
        self.horasMes = self.dias * 24
        self.demandaMensual = self.demandaDiaria() * self.dias

    @staticmethod
    def validarClima(climaMensual) -> tuple:
        """(HTmes, Tamb) como arreglos de 12 valores; lanza ValueError si el clima no es válido."""
        if isinstance(climaMensual, pl.DataFrame):
            faltantes = [c for c in ("HTmes_kWhm2mes", "Tamb_C") if c not in climaMensual.columns]
            if faltantes:
                raise ValueError(f"Al clima mensual le faltan las columnas: {', '.join(faltantes)}.")
            htMes, tamb = climaMensual["HTmes_kWhm2mes"].to_numpy(), climaMensual["Tamb_C"].to_numpy()
        else:
            htMes, tamb = climaMensual["HTmes_kWhm2mes"], climaMensual["Tamb_C"]
        htMes, tamb = np.asarray(htMes, dtype=float), np.asarray(tamb, dtype=float)
        if htMes.shape != (12,) or tamb.shape != (12,):
            raise ValueError("El clima mensual debe tener 12 meses de radiación y temperatura.")
        if (htMes <= 0).any():
            raise ValueError("La radiación mensual debe ser positiva en todos los meses.")
        return htMes, tamb

    # ------------------------------------------------------------------
    # Sección 3.1 y 3.2: demanda y área inicial
    # ------------------------------------------------------------------
    def volumenDiario(self) -> float:
        """Consumo diario de ACS (L/día)."""
        return self.numeroHabitaciones * self.ocupacionPorHabitacion * self.consumoPorPersona

    def demandaDiaria(self) -> float:
        """Energía para calentar el ACS de un día (kWh/día)."""
        masa = self.densidadAgua * self.volumenDiario()
        return masa * (self.calorEspecifico / self.joulesPorKWh) * (self.temperaturaUso - self.temperaturaRed)

    def tablaDemanda(self) -> pl.DataFrame:
        return pl.DataFrame(
            {"Mes": list(self.nombresMeses), "Dias": list(self.diasPorMes), "Qm_kWhmes": self.demandaMensual}
        )

    def fraccionObjetivo(self) -> float:
        return (self.fraccionObjetivoMinima + self.fraccionObjetivoMaxima) / 2

    def areaInicial(self) -> float:
        """Ac0 = fobj · Qprom / (ηsis · HTprom) (m²)."""
        return self.fraccionObjetivo() * np.mean(self.demandaMensual) / (self.eficienciaSistema * np.mean(self.htMes))

    # ------------------------------------------------------------------
    # Secciones 3.3 a 3.6: parámetros adimensionales y fracción solar
    # ------------------------------------------------------------------
    def diferenciaTemperatura(self, tamb):
        """ΔT de D2 según la correlación (°C)."""
        if self.correlacion == "informe":
            return self.temperaturaUso - tamb
        if self.correccionAcs:
            c0, cUso, cRed, cAmb = self.coeficientesCorreccionAcs
            return c0 + cUso * self.temperaturaUso + cRed * self.temperaturaRed + cAmb * tamb
        return self.temperaturaReferencia - tamb

    def fraccionSolar(self, d1, d2):
        """Fracción solar mensual según la correlación."""
        if self.correlacion == "informe":
            a, b, c, d, e = self.coeficientesInforme
            return 1 - np.exp(-(a * d1 + b * d2 + c * d1**2 + d * d2**2 + e * d1 * d2))
        a, b, c, d, e = self.coeficientesKlein
        return np.clip(a * d1 + b * d2 + c * d1**2 + d * d2**2 + e * d1**3, 0.0, 1.0)

    def parametrosAdimensionales(self, area, htMes=None, tamb=None, demanda=None, horas=None) -> tuple:
        """(D1, D2) para el área dada; por defecto, para los 12 meses."""
        htMes = self.htMes if htMes is None else htMes
        tamb = self.tamb if tamb is None else tamb
        demanda = self.demandaMensual if demanda is None else demanda
        horas = self.horasMes if horas is None else horas
        d1 = (self.eficienciaOptica * htMes * area) / demanda
        coeficienteMensual = self.coeficientePerdidas * horas / 1000  # kWh/m²·K por mes
        d2 = (coeficienteMensual * area * self.diferenciaTemperatura(tamb)) / demanda
        return d1, d2

    def calcularMensual(self, area: float) -> pl.DataFrame:
        """Tabla mensual: HTmes, Tamb, Qm, D1, D2, f, Qu y Qaux para el área de captación dada (m²)."""
        if area < 0:
            raise ValueError("El área de captación no puede ser negativa.")
        d1, d2 = self.parametrosAdimensionales(area)
        fraccion = self.fraccionSolar(d1, d2)
        energiaSolar = self.demandaMensual * fraccion
        return pl.DataFrame(
            {
                "Mes": list(self.nombresMeses),
                "Dias": list(self.diasPorMes),
                "HTmes_kWhm2mes": self.htMes,
                "Tamb_C": self.tamb,
                "Qm_kWhmes": self.demandaMensual,
                "D1": d1,
                "D2": d2,
                "FraccionSolar": fraccion,
                "Qu_kWhmes": energiaSolar,
                "Qaux_kWhmes": self.demandaMensual - energiaSolar,
            }
        )

    def fraccionAnual(self, area: float) -> float:
        """F = Σ Qu / Σ Qm para el área dada (m²)."""
        d1, d2 = self.parametrosAdimensionales(area)
        return float(np.sum(self.demandaMensual * self.fraccionSolar(d1, d2)) / np.sum(self.demandaMensual))

    def advertenciasRango(self, dfMensual: pl.DataFrame) -> list:
        """Meses fuera del rango de validez de la correlación de Klein."""
        if self.correlacion != "klein":
            return []
        advertencias = []
        for fila in dfMensual.iter_rows(named=True):
            if not (self.rangoD1Klein[0] < fila["D1"] < self.rangoD1Klein[1] and self.rangoD2Klein[0] < fila["D2"] < self.rangoD2Klein[1]):
                advertencias.append(
                    f"{fila['Mes']}: D1 = {fila['D1']:.3f}, D2 = {fila['D2']:.3f} fuera del rango de validez de Klein "
                    f"(0 < D1 < 3; 0 < D2 < 18)."
                )
        return advertencias

    # ------------------------------------------------------------------
    # Secciones 3.7 y 3.8: casos y dimensionamiento
    # ------------------------------------------------------------------
    def casosAnalisis(self) -> pl.DataFrame:
        """Casos representativo, subdimensionado (fobj = 0,33) y sobredimensionado (fobj = 1,0)."""
        areaInicial = self.areaInicial()
        indiceRepresentativo = int(np.argmin(np.abs(self.htMes - np.mean(self.htMes))))
        casos = [
            ("Representativo", indiceRepresentativo, self.fraccionObjetivo(), areaInicial),
            ("Subdimensionado", int(np.argmax(self.htMes)), 0.33, None),
            ("Sobredimensionado", int(np.argmin(self.htMes)), 1.0, None),
        ]
        filas = []
        for caso, indice, fraccionObjetivo, area in casos:
            demanda, ht = self.demandaMensual[indice], self.htMes[indice]
            if area is None:
                area = fraccionObjetivo * demanda / (self.eficienciaSistema * ht)
            d1, d2 = self.parametrosAdimensionales(
                area, htMes=ht, tamb=self.tamb[indice], demanda=demanda, horas=self.horasMes[indice]
            )
            filas.append(
                {
                    "Caso": caso,
                    "Mes": self.nombresMeses[indice],
                    "HTmes_kWhm2mes": float(ht),
                    "Tamb_C": float(self.tamb[indice]),
                    "Qm_kWhmes": float(demanda),
                    "Area_m2": float(area),
                    "FraccionObjetivo": fraccionObjetivo,
                    "D1": float(d1),
                    "D2": float(d2),
                    "FraccionSolar": float(self.fraccionSolar(d1, d2)),
                }
            )
        return pl.DataFrame(filas)

    def dimensionar(self) -> dict:
        """Ajusta el área desde Ac0 en pasos de pasoArea hasta que F quede en [fmín, fmáx]."""
        area = self.areaInicial()
        iteracion, fraccion, converge = 0, float("nan"), False
        while iteracion < self.maxIteraciones:
            iteracion += 1
            fraccion = self.fraccionAnual(area)
            if fraccion < self.fraccionObjetivoMinima:
                area += self.pasoArea
            elif fraccion > self.fraccionObjetivoMaxima:
                area -= self.pasoArea
            else:
                converge = True
                break
            if area < 0:
                area = 0.0
        dfMensual = self.calcularMensual(area)
        advertencias = self.advertenciasRango(dfMensual)
        if not converge:
            advertencias.insert(0, f"No se alcanzó la fracción objetivo en {self.maxIteraciones} iteraciones.")
        numeroColectores = math.ceil(area / self.areaColector - 1e-12)
        return {
            "iteraciones": iteracion,
            "converge": converge,
            "area_m2": area,
            "fraccionAnual": fraccion if converge else self.fraccionAnual(area),
            "numeroColectores": numeroColectores,
            "areaInstalada_m2": numeroColectores * self.areaColector,
            "energiaSolarAnual_kWh": float(dfMensual["Qu_kWhmes"].sum()),
            "energiaAuxiliarAnual_kWh": float(dfMensual["Qaux_kWhmes"].sum()),
            "dfMensual": dfMensual,
            "advertencias": advertencias,
        }

    def curvaFraccionArea(self, areas=None) -> pl.DataFrame:
        """Fracción solar anual frente al área de captación (por defecto de 0 a 3·Ac0)."""
        if areas is None:
            areas = np.linspace(0, 3 * self.areaInicial(), 61)
        return pl.DataFrame(
            {"Area_m2": [float(a) for a in areas], "FraccionAnual": [self.fraccionAnual(a) for a in areas]}
        )

    def calcular(self) -> dict:
        """Demanda, área inicial, casos de análisis y dimensionamiento."""
        return {
            "volumenDiario_L": self.volumenDiario(),
            "demandaDiaria_kWh": self.demandaDiaria(),
            "demandaAnual_kWh": float(np.sum(self.demandaMensual)),
            "dfDemanda": self.tablaDemanda(),
            "areaInicial_m2": self.areaInicial(),
            "fraccionAreaInicial": self.fraccionAnual(self.areaInicial()),
            "dfCasos": self.casosAnalisis(),
            "dimensionamiento": self.dimensionar(),
        }
