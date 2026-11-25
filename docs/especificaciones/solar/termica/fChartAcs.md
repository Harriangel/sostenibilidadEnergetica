# Solar térmica: dimensionamiento de un sistema de ACS por el método F-Chart

Especificación del dimensionamiento de un sistema solar térmico para agua caliente sanitaria (ACS) por el método F-Chart. Parte del script `F-Chart.py` (carpeta «Calentamiento solar a gran escala») y del informe «Dimensionamiento de un sistema solar térmico para un hotel» (Mendoza, Angel y Guardado, UNIR, 24 de noviembre de 2025). El clima mensual viene de `recursoSolar.md`.

**Decisión de diseño.** La plataforma usa por defecto la correlación de **Klein, Beckman y Duffie** con la corrección para ACS (sección 3.4). La correlación exponencial del informe (sección 3.5) queda como alternativa (`correlacion="informe"`) para reproducir sus resultados.

---

## 1. Caso de referencia

Hotel de 30 habitaciones en Ciudad de México, con colectores planos orientados al sur.

---

## 2. Datos de entrada

| Parámetro | Símbolo | Valor del caso | Unidad | Nota |
|---|---|---|---|---|
| `numeroHabitaciones` | — | 30 | hab | |
| `ocupacionPorHabitacion` | — | 2 | personas/hab | |
| `consumoPorPersona` | — | 50 | L/persona·día | |
| `temperaturaUso` | Tw | 45 | °C | Temperatura de suministro del ACS |
| `temperaturaRed` | Tred | 15 | °C | Constante todo el año |
| `densidadAgua` | ρ | 1,0 | kg/L | |
| `calorEspecifico` | ce | 4184 | J/kg·°C | El Anexo A del informe dice 4180, pero sus tablas usan 4184 |
| `areaColector` | Ab | 2 | m² por colector | Área bruta |
| `eficienciaOptica` | η0 | 0,75 | — | Se toma η0 = FR(τα) |
| `coeficientePerdidas` | a1 | 4,5 | W/m²·K | Se toma a1 = FRUL |
| `fraccionObjetivoMinima`, `fraccionObjetivoMaxima` | fmín, fmáx | 0,6 y 0,7 | — | |
| `eficienciaSistema` | ηsis | 0,45 | — | Solo para el área inicial |
| `correlacion` | — | `"klein"` | — | `"klein"` o `"informe"` |
| `temperaturaReferencia` | Tref | 100 | °C | Solo Klein |
| `correccionAcs` | — | Verdadero | — | Solo Klein |
| `pasoArea` | ΔA | 0,1 | m² | Paso de la iteración |
| `maxIteraciones` | — | 1000 | — | |

Clima mensual (de `recursoSolar.md`): radiación en el plano del colector `HTmes` (kWh/m²·mes) y temperatura ambiente `Tamb` (°C) de cada mes.

Validaciones (`ValueError`): cantidades y temperaturas físicas positivas; Tw > Tred; η0 en (0, 1]; a1 ≥ 0; 0 < fmín ≤ fmáx ≤ 1; ηsis en (0, 1]; 12 meses de clima con HTmes > 0; correlación válida.

Las variables `HTpromRef` (5,5 kWh/m²·día), `TambProm` (18 °C) y `beta` (20°) del script no intervienen en el cálculo y no se trasladan.

---

## 3. Cálculos

### 3.1 Demanda

```
V   = numeroHabitaciones · ocupacionPorHabitacion · consumoPorPersona      [L/día]       3000
Qd  = ρ · V · ce · (Tw − Tred) / 3,6·10⁶                                    [kWh/día]     104,6
Qm  = Qd · díasMes                                                          [kWh/mes]     3242,6 / 2928,8 / 3138,0
Qa  = Σ Qm                                                                  [kWh/año]     38.179
```

### 3.2 Área inicial

```
HTprom = promedio de HTmes            Qprom = promedio de Qm
fobj   = (fmín + fmáx) / 2 = 0,65
Ac0    = fobj · Qprom / (ηsis · HTprom)                                      [m²]
```

### 3.3 Parámetros adimensionales

Con Δt = 24 · díasMes (h):

```
D1 = η0 · HTmes · Ac / Qm
D2 = a1 · Δt · Ac · ΔT / (1000 · Qm)          (a1 en W/m²K; Δt en h; Qm en kWh)
```

ΔT depende de la correlación:

| Correlación | ΔT |
|---|---|
| Klein, con corrección para ACS | 11,6 + 1,18·Tw + 3,86·Tred − 2,32·Tamb |
| Klein, sin corrección | Tref − Tamb (100 − Tamb) |
| Informe | Tw − Tamb |

La corrección para ACS sustituye (100 − Tamb) por el numerador del factor de Klein, (11,6 + 1,18·Tw + 3,86·Tred − 2,32·Tamb)/(100 − Tamb) (Duffie y Beckman, 2013, cap. 20). No se aplica corrección por almacenamiento (se supone el volumen estándar de 75 L/m²).

### 3.4 Fracción solar mensual: Klein (por defecto)

```
f = 1,029·D1 − 0,065·D2 − 0,245·D1² + 0,0018·D2² + 0,0215·D1³        acotada a [0, 1]
```

Rango de validez de la correlación: 0 < D1 < 3 y 0 < D2 < 18. Fuera de él se calcula igual, pero se devuelve una advertencia.

### 3.5 Fracción solar mensual: informe (alternativa)

```
f = 1 − exp(−(a·D1 + b·D2 + c·D1² + d·D2² + e·D1·D2))
a = 0,525   b = 0,352   c = 1,2008   d = 0,0127   e = −0,3319
```

El informe dice que los coeficientes «se obtienen por ajuste empírico», pero no cita su origen. Observación: b > 0, así que, a igualdad de D1, más pérdidas (mayor D2) dan más fracción solar, lo que no es físico. Se conserva para reproducir el informe.

### 3.6 Energías y fracción anual

```
Qu   = f · Qm          energía solar útil del mes        [kWh/mes]
Qaux = Qm − Qu         energía auxiliar del mes          [kWh/mes]
F    = Σ Qu / Σ Qm     fracción solar anual
```

### 3.7 Casos de análisis (Tabla 3 del informe)

| Caso | Mes | Área |
|---|---|---|
| Representativo | El de HTmes más cercano a HTprom | Ac0 |
| Subdimensionado | El de mayor HTmes | fobj = 0,33 → Ac = fobj · Qm / (ηsis · HTmes) del mes |
| Sobredimensionado | El de menor HTmes | fobj = 1,0 → Ac = fobj · Qm / (ηsis · HTmes) del mes |

Para cada caso se reportan HTmes, Tamb, Qm, Ac, fobj, D1, D2 y f del mes.

### 3.8 Dimensionamiento iterativo

Se parte de Ac = Ac0 y se repite: se calcula F; si F < fmín, Ac += ΔA; si F > fmáx, Ac −= ΔA; si no, se detiene. Si se llega a `maxIteraciones` sin entrar en el rango, se devuelve el último resultado con una advertencia.

```
nColectores = ⌈Ac / Ab⌉          área instalada = nColectores · Ab
```

---

## 4. Salidas

- Demanda: V, Qd, tabla de Qm y Qa.
- Ac0, tabla de los tres casos, número de iteraciones, Ac final, F, número de colectores y área instalada.
- Tabla mensual: mes, días, HTmes, Tamb, Qm, D1, D2, f, Qu y Qaux; totales anuales de Qu y Qaux.
- Gráficas: f mensual, Qu y Qaux mensuales (barras apiladas) y F frente a Ac.

---

## 5. Valores de referencia

Clima de la Tabla 2 del informe (inclinación de 18°, acimut original a las hh:00):

| Mes | HTmes (kWh/m²·mes) | Tamb (°C) |
|---|---|---|
| Ene | 189,18 | 13,8 |
| Feb | 193,52 | 15,3 |
| Mar | 225,08 | 16,7 |
| Abr | 209,54 | 19,0 |
| May | 206,89 | 19,5 |
| Jun | 179,80 | 18,5 |
| Jul | 175,44 | 17,5 |
| Ago | 191,28 | 17,4 |
| Sep | 162,25 | 17,0 |
| Oct | 177,51 | 16,5 |
| Nov | 181,63 | 14,6 |
| Dic | 188,05 | 12,6 |

Comunes: Qd = 104,6 kWh/día; Qa = 38.179 kWh/año; HTprom = 190,014167 kWh/m²·mes; Qprom = 3181,583333 kWh/mes; **Ac0 = 24,185672315855594 m²**.

### 5.1 Correlación del informe (reproduce el script y el informe)

| Resultado | Valor |
|---|---|
| Iteraciones | 67 |
| Ac final | 17,5856723158555 m² |
| F | 0,6995920204795473 |
| Colectores | 9 |
| Qu anual | 26.709,72 kWh |
| Qaux anual | 11.469,28 kWh |
| Caso representativo (enero, Ac0) | D1 = 1,0583; D2 = 0,7791; f = 0,8517 |
| Caso subdimensionado (marzo) | Ac = 10,5647 m²; D1 = 0,5500; D2 = 0,3087; f = 0,5061 |
| Caso sobredimensionado (septiembre) | Ac = 42,9789 m²; D1 = 1,6667; D2 = 1,2425; f = 0,9813 |

El informe y `aplicacionF-Chart.xlsx` dan D2 = 0,7790, 0,3086 y 1,2445 y Ac = 10,5648 m², porque el script usaba HTmes y Tamb con todos los decimales; con el clima redondeado de la Tabla 2 se obtienen los valores de esta tabla.

Tabla mensual con el área final (coincide con `results/F-Chart (opt)/resultados.xlsx`):

| Mes | D1 | D2 | f | Qu (kWh) | Qaux (kWh) |
|---|---|---|---|---|---|
| Ene | 0,7695 | 0,5665 | 0,6908 | 2240,0 | 1002,6 |
| Feb | 0,8715 | 0,5393 | 0,7551 | 2211,6 | 717,2 |
| Mar | 0,9155 | 0,5139 | 0,7802 | 2530,0 | 712,6 |
| Abr | 0,8807 | 0,4721 | 0,7594 | 2383,1 | 754,9 |
| May | 0,8415 | 0,4630 | 0,7351 | 2383,8 | 858,8 |
| Jun | 0,7557 | 0,4812 | 0,6783 | 2128,5 | 1009,5 |
| Jul | 0,7136 | 0,4993 | 0,6489 | 2104,2 | 1138,4 |
| Ago | 0,7780 | 0,5011 | 0,6944 | 2251,7 | 990,9 |
| Sep | 0,6819 | 0,5084 | 0,6260 | 1964,5 | 1173,5 |
| Oct | 0,7220 | 0,5175 | 0,6558 | 2126,6 | 1116,0 |
| Nov | 0,7634 | 0,5520 | 0,6862 | 2153,2 | 984,8 |
| Dic | 0,7649 | 0,5883 | 0,6885 | 2232,4 | 1010,2 |

Los D2 del archivo xlsx difieren en el cuarto decimal (por ejemplo, 0,5664 frente a 0,5665) porque el script usaba Tamb con todos los decimales; la Tabla 2 los redondea a uno.

### 5.2 Correlación de Klein con corrección para ACS (por defecto)

| Resultado | Valor |
|---|---|
| F con Ac0 | 0,7242100831362482 |
| Iteraciones | 13 |
| Ac final | 22,985672315855577 m² |
| F | 0,6989916074842719 |
| Colectores | 12 |
| Qu anual | 26.686,80 kWh |
| Qaux anual | 11.492,20 kWh |
| Caso representativo (enero, Ac0) | D1 = 1,0583; D2 = 2,2620; f = 0,7022 |
| Caso subdimensionado (marzo, 10,5647 m²) | D1 = 0,5500; D2 = 0,9147; f = 0,4375 |
| Caso sobredimensionado (septiembre, 42,9789 m²) | D1 = 1,6667; D2 = 3,6903; f = 0,9186 |

| Mes | D1 | D2 | f | Qu (kWh) | Qaux (kWh) |
|---|---|---|---|---|---|
| Ene | 1,0058 | 2,1498 | 0,6776 | 2197,1 | 1045,5 |
| Feb | 1,1391 | 2,0672 | 0,7593 | 2223,9 | 704,9 |
| Mar | 1,1966 | 1,9901 | 0,7951 | 2578,3 | 664,3 |
| Abr | 1,1512 | 1,8635 | 0,7778 | 2440,7 | 697,3 |
| May | 1,0999 | 1,8360 | 0,7508 | 2434,4 | 808,2 |
| Jun | 0,9878 | 1,8910 | 0,6816 | 2138,9 | 999,1 |
| Jul | 0,9327 | 1,9461 | 0,6444 | 2089,5 | 1153,1 |
| Ago | 1,0169 | 1,9516 | 0,6957 | 2255,8 | 986,8 |
| Sep | 0,8914 | 1,9736 | 0,6165 | 1934,6 | 1203,4 |
| Oct | 0,9437 | 2,0012 | 0,6481 | 2101,5 | 1141,1 |
| Nov | 0,9978 | 2,1058 | 0,6753 | 2119,1 | 1018,9 |
| Dic | 0,9998 | 2,2159 | 0,6702 | 2173,1 | 1069,5 |

Con la misma área de 17,59 m², Klein con corrección para ACS da F = 0,573 y Klein con (Tw − Tamb) da F = 0,635.

---

## 6. Pruebas de aceptación

1. Demanda: Qd = 104,6 kWh/día y Qm de la sección 3.1.
2. Ac0 = 24,185672315855594 m² (tolerancia relativa 1 × 10⁻⁹).
3. Correlación del informe: iteraciones, Ac, F, colectores y totales de la sección 5.1 (1 × 10⁻⁹ en Ac y F); tabla mensual y casos a cuatro decimales.
4. Correlación de Klein: valores de la sección 5.2.
5. Casos borde: con Ac = 0, f = 0 en todos los meses; f siempre en [0, 1]; si fmín = fmáx, se llega a `maxIteraciones` y se avisa; Tw ≤ Tred lanza `ValueError`.
6. Con el clima recalculado por `recursoSolar.md` (19°) los resultados cambian; se fijan como referencia al implementar.

---

## 7. Observaciones sobre el informe

- **El informe mezcla dos corridas del script.**
  - Tablas 2 y 3, y la conclusión «17,59 m², 9 colectores»: corrida `opt` (18°).
  - Tabla 4, las energías de la conclusión (26.724 y 11.455 kWh/año), la sección «Análisis y discusión» y el Anexo C (26,00, 11,28, 49,72 y 19,00 m², 10 colectores): corrida `lat` (latitud + 23,5°), cuyo resultado final es 19,00 m².
  - Con la corrida `opt`, las energías correctas son 26.709,7 y 11.469,3 kWh/año.
- «Junio y marzo presentan la menor y menor radiación (162,25 y 225,08)»: el mes de 162,25 es septiembre, y marzo es el de mayor radiación.
- Anexo A: ce = 4180 J/kg·°C; las tablas usan 4184.
- La ecuación (10) usa FR(τα) y FRUL; se adoptan η0 y a1 sin factores de corrección del captador ni del intercambiador.
- Los coeficientes de la correlación exponencial no tienen fuente (sección 3.5).

---

## 8. Supuestos

- Demanda constante todos los días; temperatura de red constante.
- Volumen de almacenamiento estándar (75 L/m²); sin corrección por intercambiador.
- Colector caracterizado solo por η0 y a1 (se ignora a2).

---

## 9. Referencias

- Klein, S. A., Beckman, W. A., y Duffie, J. A. (1976). A design procedure for solar heating systems. *Solar Energy*, 18(2), 113–127.
- Duffie, J. A., y Beckman, W. A. (2013). *Solar engineering of thermal processes* (4.ª ed.), cap. 20. Wiley.
- Mendoza, D. L., Angel, H., y Guardado, M. S. (2025). *Dimensionamiento de un sistema solar térmico para un hotel*. Actividad grupal, Energía solar térmica, UNIR.
