# Central mareomotriz: energía anual y LCOE

Especificación del libro `Calculo_de_la_energia_potencial_y_LCOE.xlsx` (hoja única `Act1`) para implementarlo en una aplicación de Python. Describe las entradas, las fórmulas celda por celda, las salidas y los valores de prueba.

El modelo estima, para **una turbina** mareomotriz:

1. el número de pasos de agua por año según el tipo de marea y de turbina;
2. la energía potencial y la energía eléctrica (útil) anual;
3. el costo nivelado de la energía (LCOE) por valor presente, con dos escenarios de sensibilidad.

---

## 1. Estructura de la hoja `Act1`

| Bloque | Rango | Contenido |
|---|---|---|
| Título | B2:M3 | «Cálculo de la energía eléctrica anual de una central mareomotriz» |
| Leyenda de energía | B10:C14 | Significado de E, n, m, g y h (solo texto) |
| Entradas de energía | F7:H19 | Turbina, marea y constantes físicas |
| Cálculos de energía | J7:L24 | Pasos por turbina y energía anual |
| Leyenda del LCOE | B34:C40 | Significado de LCOE, i, VU, CAPEX, OPEX, r y Eg (solo texto) |
| Entradas del LCOE | F30:H34 | Vida útil, tasa, CAPEX y OPEX |
| Cálculos del LCOE | J30:L41 | LCOE base y escenarios de sensibilidad |

La hoja no tiene nombres definidos; todas las referencias son a celdas.

---

## 2. Datos de entrada

### 2.1 Entradas categóricas (texto)

| Celda | Variable Python | Valor actual | Valores aceptados | Uso |
|---|---|---|---|---|
| G8 | `tipo_turbina` | `"Eje horizontal"` | Texto libre | Solo descriptivo; no interviene en los cálculos |
| G9 | `direccion` | `"Bidireccional"` | `"Unidireccional"`, `"Bidireccional"` | Define los pasos por ciclo (K15) |
| G12 | `tipo_marea` | `"Semidiurna"` | `"Diurna"`, `"Semidiurna"` | Define la duración del ciclo (K12) |

### 2.2 Entradas numéricas

| Celda | Variable Python | Símbolo | Valor actual | Unidad | Nota |
|---|---|---|---|---|---|
| K9 | `dia_lunar_h` | — | 24,8 | h | Duración del día lunar |
| K10 | `dia_solar_h` | — | 24 | h | Duración del día solar |
| G16 | `masa_kg` | m | 8,7 × 10⁹ | kg | Masa de agua por ciclo y turbina (8,7 × 10⁶ t) |
| G17 | `g` | g | 9,81 | m/s² | Aceleración de la gravedad |
| G18 | `desnivel_m` | h | 3,6 | m | Desnivel efectivo medio |
| G19 | `eta` | η | 0,38 | — | Rendimiento global (hidráulico + eléctrico) |
| G30 | `vida_util` | VU | 25 | años | Vida útil |
| G31 | `tasa` | r | 0,07 | — | Tasa de descuento (formato 7 %) |
| G33 | `capex` | CAPEX | 14.500.000 | €/turbina | Inversión inicial (año 0) |
| G34 | `opex` | OPEX | 450.000 | €/año | Costo anual de operación y mantenimiento (años 1 a VU) |

### 2.3 Constantes fijas dentro de las fórmulas

No están en celdas propias. En la aplicación conviene volverlas parámetros con estos valores por defecto:

| Constante | Valor | Dónde aparece | Variable sugerida |
|---|---|---|---|
| Días por año | 365 | K14 | `dias_anio = 365` |
| Factor de energía potencial | 1/2 | K19 | Ver §3.2 (fijo, no parametrizar) |
| J por kWh | 3.600.000 | K20 | `J_POR_KWH = 3.6e6` |
| Incremento de CAPEX (escenario A) | 115 % | K35 | `factor_capex_A = 1.15` |
| Factor de energía (escenario B) | 90 % | K40 | `factor_energia_B = 0.90` |

---

## 3. Cálculos

### 3.1 Pasos de agua por turbina y año

| Celda | Variable | Fórmula Excel | Expresión | Unidad | Valor |
|---|---|---|---|---|---|
| K12 | `ciclo_h` | `=+IF(G12="Diurna",K9,IF(G12="Semidiurna",K9/2,))` | Diurna: día lunar; semidiurna: día lunar / 2 | h/ciclo | 12,4 |
| K13 | `ciclos_dia` | `=+K10/K12` | día solar / ciclo | ciclos/día | 1,935484 |
| K14 | `ciclos_anio` | `=+K13*365` | ciclos/día × 365 | ciclos/año | 706,451613 |
| K15 | `n` | `=+IF(G9="Unidireccional",K14,IF(G9="Bidireccional",K14*2,))` | Unidireccional: × 1; bidireccional: × 2 | pasos/año | 1.412,903226 |

Si G12 o G9 tienen un valor distinto de los admitidos, el `IF` anidado devuelve 0 y la energía resulta 0. La aplicación debe **validar la entrada y lanzar un error** en ese caso, no devolver 0.

### 3.2 Energía anual

| Celda | Variable | Fórmula Excel | Expresión | Unidad | Valor |
|---|---|---|---|---|---|
| K19 | `ep_J` | `=+(K15*G16*G17*G18)/2` | n · ½ · m · g · h | J/año | 2,170567 × 10¹⁴ |
| K20 | `ep_kWh` | `=K19*(1/3600000)` | Ep / 3,6 × 10⁶ | kWh/año | 60.293.525,81 |
| K21 | `eu_kWh` | `=+K20*G19` | Ep · η | kWh/año | 22.911.539,81 |
| K23 | `eu_MWh` | `=+K21/1000` | Eu / 1000 | MWh/año | 22.911,54 |
| K24 | `eu_GWh` | `=+K21/1000000` | Eu / 10⁶ | GWh/año | 22,91 |

Ecuaciones:

```
E_paso = ½ · m · g · h                 [J/paso]   (no tiene celda propia; está dentro de K19)
Ep     = n · E_paso                    [J/año]    (K19)
Eu     = η · Ep                        [J/año → K21 en kWh/año]
```

El factor ½ indica que el centro de masas del agua desciende, en promedio, la mitad del desnivel. **K21 (`eu_kWh`) es la energía que usa el LCOE.**

### 3.3 LCOE por valor presente

El LCOE es el precio constante de venta de la energía con el que el valor presente de los ingresos iguala al de los costos, descontados a la tasa r:

```
LCOE = VP_costos / VP_energía

VP_costos  = CAPEX + Σ_{t=1..VU} OPEX / (1+r)^t = CAPEX + OPEX · FVP
VP_energía =         Σ_{t=1..VU} Eu   / (1+r)^t =         Eu   · FVP

FVP = [1 − (1+r)^(−VU)] / r            (factor de valor presente de una anualidad vencida)
```

| Celda | Variable | Fórmula Excel | Unidad | Valor |
|---|---|---|---|---|
| K30 | `lcoe_base` | `=(-G33+PV(G31,G30,G34))/PV(G31,G30,K21)` | €/kWh | 0,0739476 |
| K35 | `lcoe_A` | `=(-(G33*115%)+PV(G31,G30,G34))/PV(G31,G30,K21)` | €/kWh | 0,0820936 |
| K40 | `lcoe_B` | `=(-G33+PV(G31,G30,G34))/PV(G31,G30,K21*90%)` | €/kWh | 0,0821640 |

**Signo de la función `PV` de Excel.** `PV(rate, nper, pmt)` devuelve el valor presente con signo contrario al pago: `PV(r, VU, P) = −P · FVP` (con `fv = 0` y `type = 0`, es decir, pagos al final de cada año). Por eso K30 se simplifica así:

```
K30 = (−CAPEX − OPEX·FVP) / (−Eu·FVP) = (CAPEX + OPEX·FVP) / (Eu·FVP)
```

En Python no hace falta `numpy_financial`: basta con calcular FVP directamente (ver §5). Si se usa `numpy_financial.pv`, el signo es el mismo que en Excel.

Valores intermedios del caso base, sin celda propia en el Excel pero útiles para reportar:

| Variable | Expresión | Valor |
|---|---|---|
| `fvp` | [1 − 1,07⁻²⁵] / 0,07 | 11,653583 años |
| `vp_opex` | OPEX · FVP | 5.244.112,43 € |
| `vp_costos` | CAPEX + OPEX · FVP | 19.744.112,43 € |
| `vp_energia` | Eu · FVP | 267.001.534,88 kWh |

### 3.4 Escenarios de sensibilidad

| Escenario | Celda | Cambio | VP costos (€) | VP energía (kWh) | LCOE (€/kWh) | Variación frente a base |
|---|---|---|---|---|---|---|
| Base | K30 | — | 19.744.112,43 | 267.001.534,88 | 0,0739476 | — |
| A: CAPEX +15 % | K35 | CAPEX × 1,15 | 21.919.112,43 | 267.001.534,88 | 0,0820936 | +11,02 % |
| B: energía −10 % | K40 | Eu × 0,90 | 19.744.112,43 | 240.301.381,39 | 0,0821640 | +11,11 % |

Las variaciones no están en el Excel; se calculan como `lcoe_X / lcoe_base − 1`.

### 3.5 Celdas que no se deben replicar (K31, K36 y K41)

Bajo cada LCOE hay una fórmula alternativa sin etiqueta ni unidad:

| Celda | Fórmula Excel | Valor |
|---|---|---|
| K31 | `=+($G$33*$G$31+$G$34)/$K$21` | 0,0639416 |
| K36 | `=+(($G$33*115%)*$G$31+$G$34)/$K$21` | 0,0705867 |
| K41 | `=+($G$33*$G$31+$G$34)/($K$21*90%)` | 0,0710462 |

Estas fórmulas anualizan el CAPEX multiplicándolo solo por r, como si la inversión nunca se amortizara (perpetuidad). Por eso subestiman el LCOE en unos 13,5 %. **No forman parte del modelo**: el LCOE válido es el de K30, K35 y K40. Si la aplicación necesita una anualidad equivalente, el factor correcto es el de recuperación de capital, `CRF = 1 / FVP = 0,0858105`, y da el mismo LCOE que el método de valor presente.

---

## 4. Salidas

| Celda | Variable | Descripción | Unidad | Valor esperado |
|---|---|---|---|---|
| K12 | `ciclo_h` | Duración del ciclo de marea | h/ciclo | 12,4 |
| K13 | `ciclos_dia` | Ciclos por día solar | ciclos/día | 1,935483870967742 |
| K14 | `ciclos_anio` | Ciclos por año | ciclos/año | 706,4516129032257 |
| K15 | `n` | Pasos por turbina y año | pasos/año | 1412,9032258064515 |
| K19 | `ep_J` | Energía potencial anual | J/año | 217056692903225,8 |
| K20 | `ep_kWh` | Energía potencial anual | kWh/año | 60293525,80645161 |
| K21 | `eu_kWh` | Energía eléctrica anual | kWh/año | 22911539,80645161 |
| K23 | `eu_MWh` | Energía eléctrica anual | MWh/año | 22911,539806451612 |
| K24 | `eu_GWh` | Energía eléctrica anual | GWh/año | 22,91153980645161 |
| K30 | `lcoe_base` | LCOE del caso base | €/kWh | 0,07394756153502048 |
| K35 | `lcoe_A` | LCOE con CAPEX +15 % | €/kWh | 0,08209358212253212 |
| K40 | `lcoe_B` | LCOE con energía −10 % | €/kWh | 0,08216395726113387 |

Formatos de presentación en el Excel: K13 a K15 con 3 decimales; K20 a K24 con separador de miles y 2 decimales; LCOE como `€ 0,000`.

---

## 5. Implementación de referencia en Python

```python
from dataclasses import dataclass, asdict

J_POR_KWH = 3.6e6


@dataclass
class Entradas:
    # Turbina y marea
    direccion: str = "Bidireccional"   # "Unidireccional" | "Bidireccional"
    tipo_marea: str = "Semidiurna"     # "Diurna" | "Semidiurna"
    dia_lunar_h: float = 24.8
    dia_solar_h: float = 24.0
    dias_anio: int = 365
    # Constantes físicas
    masa_kg: float = 8.7e9
    g: float = 9.81
    desnivel_m: float = 3.6
    eta: float = 0.38
    # Económicas
    vida_util: int = 25
    tasa: float = 0.07
    capex: float = 14_500_000.0
    opex: float = 450_000.0
    # Sensibilidad
    factor_capex_A: float = 1.15
    factor_energia_B: float = 0.90


def fvp(r: float, n: int) -> float:
    """Factor de valor presente de una anualidad vencida: Σ_{t=1..n} 1/(1+r)^t."""
    if r == 0:
        return float(n)
    return (1 - (1 + r) ** -n) / r


def lcoe(capex: float, opex: float, energia_kwh: float, r: float, n: int) -> float:
    """LCOE por valor presente [€/kWh]. Equivale a K30/K35/K40 del Excel."""
    f = fvp(r, n)
    return (capex + opex * f) / (energia_kwh * f)


def calcular(e: Entradas) -> dict:
    # --- Validaciones (el Excel devolvería 0 en silencio) ---
    ciclos_por_dia_lunar = {"Diurna": 1, "Semidiurna": 2}
    pasos_por_ciclo = {"Unidireccional": 1, "Bidireccional": 2}
    if e.tipo_marea not in ciclos_por_dia_lunar:
        raise ValueError(f"tipo_marea inválido: {e.tipo_marea!r}")
    if e.direccion not in pasos_por_ciclo:
        raise ValueError(f"direccion inválida: {e.direccion!r}")
    if e.vida_util <= 0 or e.tasa < 0:
        raise ValueError("vida_util debe ser > 0 y tasa >= 0")

    # --- Pasos por turbina (K12–K15) ---
    ciclo_h = e.dia_lunar_h / ciclos_por_dia_lunar[e.tipo_marea]
    ciclos_dia = e.dia_solar_h / ciclo_h
    ciclos_anio = ciclos_dia * e.dias_anio
    n = ciclos_anio * pasos_por_ciclo[e.direccion]

    # --- Energía (K19–K24) ---
    e_paso_J = 0.5 * e.masa_kg * e.g * e.desnivel_m
    ep_J = n * e_paso_J
    ep_kWh = ep_J / J_POR_KWH
    eu_kWh = ep_kWh * e.eta

    # --- LCOE (K30, K35, K40) ---
    f = fvp(e.tasa, e.vida_util)
    vp_costos = e.capex + e.opex * f
    vp_energia = eu_kWh * f
    lcoe_base = lcoe(e.capex, e.opex, eu_kWh, e.tasa, e.vida_util)
    lcoe_A = lcoe(e.capex * e.factor_capex_A, e.opex, eu_kWh, e.tasa, e.vida_util)
    lcoe_B = lcoe(e.capex, e.opex, eu_kWh * e.factor_energia_B, e.tasa, e.vida_util)

    return {
        "ciclo_h": ciclo_h,                 # K12
        "ciclos_dia": ciclos_dia,           # K13
        "ciclos_anio": ciclos_anio,         # K14
        "n": n,                             # K15
        "e_paso_J": e_paso_J,
        "ep_J": ep_J,                       # K19
        "ep_kWh": ep_kWh,                   # K20
        "eu_kWh": eu_kWh,                   # K21
        "eu_MWh": eu_kWh / 1e3,             # K23
        "eu_GWh": eu_kWh / 1e6,             # K24
        "potencia_media_MW": eu_kWh / 1e3 / 8760,
        "fvp": f,
        "crf": 1 / f,
        "vp_costos": vp_costos,
        "vp_energia": vp_energia,
        "lcoe_base": lcoe_base,             # K30
        "lcoe_A": lcoe_A,                   # K35
        "lcoe_B": lcoe_B,                   # K40
        "var_A_pct": (lcoe_A / lcoe_base - 1) * 100,
        "var_B_pct": (lcoe_B / lcoe_base - 1) * 100,
    }


if __name__ == "__main__":
    for k, v in calcular(Entradas()).items():
        print(f"{k:>18}: {v:,.6f}")
```

### Equivalencia con `numpy_financial` (opcional)

```python
import numpy_financial as npf
lcoe_base = (-capex + npf.pv(r, VU, opex)) / npf.pv(r, VU, eu_kWh)   # igual que K30
```

---

## 6. Pruebas de aceptación

Con las entradas por defecto, la implementación debe reproducir el Excel con una tolerancia relativa de 1 × 10⁻⁹:

```python
import math

ESPERADO = {
    "ciclo_h": 12.4,
    "ciclos_dia": 1.9354838709677418,
    "ciclos_anio": 706.4516129032257,
    "n": 1412.9032258064515,
    "ep_J": 217056692903225.8,
    "ep_kWh": 60293525.80645161,
    "eu_kWh": 22911539.80645161,
    "eu_MWh": 22911.539806451612,
    "eu_GWh": 22.91153980645161,
    "lcoe_base": 0.07394756153502048,
    "lcoe_A": 0.08209358212253212,
    "lcoe_B": 0.08216395726113387,
}


def test_reproduce_excel():
    r = calcular(Entradas())
    for k, v in ESPERADO.items():
        assert math.isclose(r[k], v, rel_tol=1e-9), (k, r[k], v)


def test_casos_borde():
    # Unidireccional: la mitad de pasos y de energía
    r = calcular(Entradas(direccion="Unidireccional"))
    assert math.isclose(r["n"], ESPERADO["n"] / 2)
    # Marea diurna: ciclo de 24,8 h
    assert math.isclose(calcular(Entradas(tipo_marea="Diurna"))["ciclo_h"], 24.8)
    # r = 0: FVP = VU (sin división por cero)
    assert calcular(Entradas(tasa=0.0))["fvp"] == 25.0
```

---

## 7. Observaciones del libro original

- **Leyendas inconsistentes con los cálculos.** La leyenda B34:C34 dice «LCOE en €/MWh», pero K30, K35 y K40 están en **€/kWh**. B37:C37 dice «CAPEX en €/año», pero G33 es una inversión única en **€/turbina** (H33). B10:C10 da E en GWh/año, aunque se calcula en J, kWh, MWh y GWh. B40:C40 menciona `Eg` en MWh/año, que corresponde a K21 (en kWh/año) y no a una celda propia. B35 define `i` (año), que no se usa: el índice de año es implícito en `PV`.
- **Erratas de texto.** La etiqueta de C13 dice `m/s"` (debería ser `m/s²`) y la de B26 «nievelado» (debería ser «nivelado»).
- **Supuestos del modelo.** Masa, desnivel y rendimiento constantes en todos los ciclos; operación todo el año (365 días, sin paradas por mantenimiento); OPEX y energía constantes, sin inflación, impuestos, degradación ni reposición de equipos; CAPEX íntegro en el año 0 y flujos al final de cada año.
- **Ampliaciones sugeridas para la aplicación.** Número de turbinas (multiplica energía, CAPEX y OPEX), disponibilidad anual (factor sobre `eu_kWh`), sensibilidades parametrizables y barridos de r, η, h y CAPEX.
