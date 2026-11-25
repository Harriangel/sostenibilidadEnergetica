# Solar fotovoltaica: energía útil por horas solares pico y comparación con PVWatts

Especificación del libro `Análisis de radiación diaria.xlsx` (curso de Energía solar fotovoltaica, UNIR, 2026). El libro está en la carpeta del curso del autor y no se versiona aquí, porque incluye la dirección del sitio de Bogotá. Esta especificación transcribe todos los datos y fórmulas que se necesitan.

---

## 1. Estructura del libro

| Hoja | Contenido | Fórmulas |
|---|---|---|
| `data GHI` | Climatología mensual de NASA POWER (2001–2020) para Bogotá (lat 4,6493; lon −74,1671; 1790 m): difusa, DNI y global horizontal (kWh/m²·día), albedo, temperatura a 2 m (°C) y viento a 10 m (m/s) | No |
| `data anual THI` | PVWatts mensual, Bogotá (NSRDB 4,65, −74,18; 2219 m): 37,9 kWp, inclinación 20°, acimut 180°, pérdidas 14,08 %, CC/CA 1,2, inversor 96 % | No |
| `data diaria THI` | PVWatts horario (8760 h) del mismo sistema | No |
| `Energía útil` | Energía útil mensual y anual por horas solares pico | Sí |
| `PVWatts YUC` | PVWatts mensual, Mérida (NSRDB 20,97, −89,62): 4 kWp, ocho inclinaciones (5° a 40°) | Una columna |
| `Merida (2)` | Producción AC mensual por inclinación, con máximo, promedio y mínimo | Sí |

---

## 2. Método de horas solares pico (hoja `Energía útil`)

### 2.1 Entradas

| Celda | Variable | Valor | Unidad |
|---|---|---|---|
| D3:D14 | `radiacionDiaria` (H) | GHI mensual de NASA POWER (`data GHI`, fila 20), transpuesta | kWh/m²·día |
| B3:B14 | `diasMes` | 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 | días |
| J9 | `potenciaNominal` (Pnom) | 5 | kWp |
| J10 | `perdidasSistema` (L) | 0,14 | — |

Radiación diaria (GHI horizontal de NASA POWER):

| Mes | H (kWh/m²·día) |
|---|---|
| Ene | 4,9236 |
| Feb | 4,8634 |
| Mar | 4,5098 |
| Abr | 4,4542 |
| May | 4,4765 |
| Jun | 4,5036 |
| Jul | 4,5866 |
| Ago | 4,6322 |
| Sep | 4,8660 |
| Oct | 4,7105 |
| Nov | 4,5070 |
| Dic | 4,6457 |
| Anual (dato de NASA, `ANN`) | 4,639 |

### 2.2 Fórmulas

| Celda | Variable | Fórmula Excel | Expresión | Unidad |
|---|---|---|---|---|
| E3:E14 | `radiacionMensual` | `=+D3*B3` | Hm = H · días | kWh/m²·mes |
| F3:F14 | `energiaUtilMensual` | `=+E3*$J$9*(1-$J$10)` | Em = Hm · Pnom · (1 − L) | kWh/mes |
| G3:G14 | `rendimientoMensual` | `=+F3/$J$9` | Ym = Em / Pnom | kWh/kWp·mes |
| J4, J5 | máximo y mínimo de H | `=MAX(D3:D14)`, `=MIN(D3:D14)` | | kWh/m²·día |
| J6 | `radiacionAnual` | `=SUM(E3:E14)` | Ha = Σ Hm | kWh/m²·año |
| J12 | `energiaUtilAnual` | `=SUM(F3:F14)` | Ea = Σ Em | kWh/año |
| J13 | `promedioDiario` | `=J12/365` | Ea / 365 | kWh/día |
| J14 | `rendimientoAnual` | `=J12/J9` | Ya = Ea / Pnom | kWh/kWp·año |
| J15 | `factorPlanta` | `=J12/(J9*8760)` | FP = Ea / (Pnom · 8760) | — |

La expresión Hm · Pnom equivale a horas solares pico (H / 1 kW/m²) por potencia nominal; (1 − L) es el rendimiento global del sistema (performance ratio).

### 2.3 Valores de referencia

| Mes | Hm (kWh/m²·mes) | Em (kWh/mes) | Ym (kWh/kWp·mes) |
|---|---|---|---|
| Ene | 152,6316 | 656,31588 | 131,263176 |
| Feb | 136,1752 | 585,55336 | 117,110672 |
| Mar | 139,8038 | 601,15634 | 120,231268 |
| Abr | 133,6260 | 574,59180 | 114,918360 |
| May | 138,7715 | 596,71745 | 119,343490 |
| Jun | 135,1080 | 580,96440 | 116,192880 |
| Jul | 142,1846 | 611,39378 | 122,278756 |
| Ago | 143,5982 | 617,47226 | 123,494452 |
| Sep | 145,9800 | 627,71400 | 125,542800 |
| Oct | 146,0255 | 627,90965 | 125,581930 |
| Nov | 135,2100 | 581,40300 | 116,280600 |
| Dic | 144,0167 | 619,27181 | 123,854362 |

| Resultado | Valor |
|---|---|
| H máxima / mínima | 4,9236 / 4,4542 kWh/m²·día |
| Radiación anual Ha | 1693,1311 kWh/m²·año |
| Energía útil anual Ea | 7280,46373 kWh/año |
| Promedio diario | 19,946475972602737 kWh/día |
| Rendimiento anual Ya | 1456,092746 kWh/kWp·año |
| Factor de planta | 0,16622063310502283 |

Tolerancia relativa 1 × 10⁻⁹.

---

## 3. Ampliaciones para la plataforma

1. **Radiación en el plano del panel.** La hoja usa la GHI horizontal. La plataforma permite tomar H de `recursoSolar.md` (GTI mensual con la inclinación y el acimut elegidos). Con la radiación horizontal (inclinación 0°) los resultados deben ser los de la sección 2.3.
2. **Inversor.** Parámetro `eficienciaInversor` (por defecto 1,0, sin efecto): Em = Hm · Pnom · (1 − L) · ηinv.
3. **Unidades.** Energía en kWh, MWh o GWh con `energias.comun.unidades`.
4. **LCOE.** Con CAPEX, OPEX, vida útil y tasa, mediante `energias.comun.economia` (pendiente de datos de costos del curso).

---

## 4. Comparación con PVWatts

### 4.1 Lectura de los archivos de PVWatts

Los archivos mensual y horario de PVWatts tienen 31 o 32 líneas de metadatos (ubicación, tamaño del sistema, tipo de módulo y de campo, inclinación, acimut, pérdidas, relación CC/CA, eficiencia del inversor, albedo y pérdidas mensuales), seguidas de los encabezados y los datos:

- **Mensual:** mes, irradiación diaria promedio en el plano (kWh/m²·día), producción CC (kWh) y producción CA (kWh).
- **Horario:** mes, día, hora, irradiación directa y difusa (W/m²), temperatura ambiente (°C), viento (m/s), albedo, irradiación en el plano (W/m²), temperatura de celdas (°C), producción CC (W) y CA (W).

El lector busca la línea de encabezados por su contenido y devuelve los metadatos (diccionario) y los datos (`polars.DataFrame`).

### 4.2 Valores de referencia, Bogotá (37,9 kWp, 20°)

| Resultado | Valor |
|---|---|
| Irradiación anual en el plano (suma horaria) | 1708,4 kWh/m²·año |
| Producción CC anual | 51.365,3 kWh |
| Producción CA anual | 48.889,3 kWh |
| Rendimiento CA | 1290 kWh/kWp·año |

El método de la sección 2 da 1456 kWh/kWp·año para Bogotá, unos 13 % más que PVWatts, porque no considera el inversor (96 %) ni la temperatura de las celdas y usa otra fuente de radiación (NASA POWER frente a NSRDB).

### 4.3 Valores de referencia, Mérida (4 kWp): producción CA anual por inclinación

Suma de los doce meses de la hoja `Merida (2)`:

| Inclinación | 5° | 10° | 15° | **20°** | 25° | 30° | 35° | 40° |
|---|---|---|---|---|---|---|---|---|
| kWh/año | 5971,7 | 6067,9 | 6120,9 | **6131,8** | 6102,1 | 6033,2 | 5926,3 | 5783,7 |

La inclinación con mayor producción anual es 20° (latitud 20,97°). La hoja reporta además el máximo, el promedio y el mínimo mensual entre inclinaciones (columnas K a M); por ejemplo, en enero el máximo es 527,02 kWh (40°) y en mayo 588,31 kWh (5°).

Nota: en `PVWatts YUC` el bloque de 20° tiene otro formato (Mes, Días, kWh/m²·día, kWh/m², kWh CC, kWh CA), por eso `Merida (2)` toma la columna F para esa inclinación y la D para las demás. Es correcto.

---

## 5. Pruebas de aceptación

1. Sección 2.3 completa (tolerancia relativa 1 × 10⁻⁹).
2. Con `eficienciaInversor` = 1,0 y radiación horizontal, mismos resultados; con 0,96, la energía se multiplica por 0,96.
3. Lector de PVWatts: los totales de las secciones 4.2 y 4.3 (con los archivos exportados de PVWatts guardados en `data/solar/`).
4. Validaciones (`ValueError`): Pnom ≤ 0; pérdidas fuera de [0, 1); eficiencia del inversor fuera de (0, 1]; radiación negativa; distinto de 12 meses.

---

## 6. Pendiente

- Los demás Excel del curso de fotovoltaica (dimensionamiento de módulos e inversor, cableado, costos) para ampliar el módulo.
- Exportar los CSV de PVWatts de Bogotá y Mérida a `data/solar/` para las pruebas del lector.
