# Recurso solar: posición del sol e irradiancia en un plano inclinado

Especificación del cálculo del recurso solar que comparten la solar térmica, la fotovoltaica y la de concentración. Parte de los scripts `GTI_optimized.py`, `GTI_comparison.py` y `graphics.py` de la carpeta «Calentamiento solar a gran escala» del curso de Energía solar térmica (UNIR, 2025), y del Anexo B del informe «Dimensionamiento de un sistema solar térmico para un hotel» (Mendoza, Angel y Guardado, 2025).

No hay Excel de origen: los valores de referencia de la sección 6 se calcularon con las fórmulas de esta especificación y el TMY del caso (sección 2.1), y se contrastaron con SunEarthTools y con el cenit de NSRDB (sección 6.1).

---

## 1. Alcance

1. Leer un año meteorológico típico (TMY) horario de NSRDB.
2. Calcular la posición del sol (cenit y acimut) para cada registro, **a la misma hora del registro**.
3. Calcular la irradiancia en un plano inclinado (GTI o POA) con el modelo isotrópico y sus componentes directa, difusa y reflejada.
4. Agregar la irradiancia por hora del día, día y mes.
5. Barrer la inclinación para encontrar la que maximiza la radiación anual.

Fuera de alcance por ahora: modelos de difusa anisotrópicos (Hay-Davies, HDKR, Perez), seguidores y sombras.

---

## 2. Datos de entrada

### 2.1 TMY de NSRDB

Archivo del caso: `639946_19.45_-99.14_tmy-2024.csv` (NSRDB GOES TMY v4, punto 639946, Ciudad de México). Se descarga desde el visor de NSRDB o con su API; la clave de la API **no** se guarda en el repositorio.

| Línea | Contenido |
|---|---|
| 1 | Encabezados de metadatos (`Source`, `Location ID`, …, `Latitude`, `Longitude`, `Time Zone`, `Elevation`, …) |
| 2 | Valores de los metadatos: latitud 19,45; longitud −99,14; zona horaria −6; elevación 2240 m |
| 3 | Encabezados de los datos |
| 4 en adelante | 8760 registros horarios |

Columnas de datos usadas:

| Columna | Unidad | Uso |
|---|---|---|
| `Year`, `Month`, `Day`, `Hour`, `Minute` | — | Marca de tiempo en **hora estándar local** (sin horario de verano). Los registros están a las hh:30. `Year` varía por mes (es un TMY); no se usa en los cálculos |
| `Temperature` | °C | Temperatura ambiente |
| `DHI`, `DNI`, `GHI` | W/m² | Irradiancia difusa horizontal, directa normal y global horizontal |
| `Solar Zenith Angle` | ° | Cenit solar a la hora del registro |
| `Surface Albedo` | — | Albedo del suelo |

Los metadatos se leen por nombre de columna (no por posición). El lector valida que existan las columnas requeridas y que haya 8760 registros; si no, lanza `ValueError`.

### 2.2 Parámetros

| Parámetro | Símbolo | Valor por defecto | Unidad |
|---|---|---|---|
| `latitud`, `longitud`, `zonaHoraria` | φ, L, TZ | De los metadatos del TMY | °, °, h |
| `inclinacion` | β | — (sin valor por defecto) | ° (0 = horizontal, 90 = vertical) |
| `acimutPanel` | γp | 180 | ° desde el norte, en sentido horario (180 = sur) |
| `rangoInclinacion` | — | 0 a 90, paso 1 | ° |
| `usarCenitArchivo` | — | Verdadero | Usa `Solar Zenith Angle` del TMY; si es falso, el cenit calculado |

Validaciones: latitud en [−90, 90], longitud en [−180, 180], inclinación en [0, 90], acimut en [0, 360), irradiancias no negativas y albedo en [0, 1].

---

## 3. Posición del sol

Para cada registro, con el día del año *n* (1 a 365, año no bisiesto) y la hora estándar local *t* = `Hour` + `Minute`/60:

```
B   = (n − 1) · 360/365                                                        [°]
E   = 229,2 · (0,000075 + 0,001868 cos B − 0,032077 sen B
                − 0,014615 cos 2B − 0,04089 sen 2B)                            [min]   ecuación del tiempo
δ   = 0,006918 − 0,399912 cos B + 0,070257 sen B − 0,006758 cos 2B
      + 0,000907 sen 2B − 0,002697 cos 3B + 0,00148 sen 3B                     [rad]   declinación (Spencer)
ts  = t + [4 · (L − 15·TZ) + E] / 60                                           [h]     hora solar (L y TZ con el este positivo)
ω   = 15 · (ts − 12)                                                           [°]     ángulo horario
cos θz = sen φ sen δ + cos φ cos δ cos ω                                               cenit
cos γs' = (cos θz sen φ − sen δ) / (sen θz cos φ),  γs' con el signo de ω              acimut desde el sur (Duffie y Beckman)
γs  = (γs' + 180) mod 360                                                      [°]     acimut desde el norte, horario
```

Referencias: Spencer (1971) para δ y E; Duffie y Beckman (2013), cap. 1, para ω, θz y γs.

**Diferencia con el script original.** `GTI_optimized.py` tomaba el acimut de un archivo de SunEarthTools a las hh:00 y lo unía por `Hour` a registros de las hh:30: a las 12:30 usaba el acimut de las 12:00 (166° en lugar de unos 177°). La plataforma calcula el acimut a la hora del registro y no depende de SunEarthTools.

---

## 4. Irradiancia en el plano inclinado (modelo isotrópico)

```
cos θ = cos θz cos β + sen θz sen β cos(γs − γp)                ángulo de incidencia (AOI)
Gbi   = DNI · max(cos θ, 0)                                     directa inclinada            [W/m²]
Gdi   = DHI · (1 + cos β) / 2                                   difusa inclinada (isotrópica) [W/m²]
Gri   = GHI · ρ · (1 − cos β) / 2                               reflejada por el suelo        [W/m²]
GTI   = Gbi + Gdi + Gri                                                                     [W/m²]
```

ρ es `Surface Albedo`. θz es el cenit del archivo (o el calculado, según `usarCenitArchivo`); γs es siempre el calculado. Con β = 0, GTI = DNI·cos θz + DHI, que en el TMY coincide con la GHI.

El script original limitaba el AOI a 90° antes de calcular el coseno; es equivalente a `max(cos θ, 0)`.

**Erratas del informe (Anexo B).** La ecuación (7) dice `Gdi = DNI·rd`; debe ser `Gdi = DHI·rd`. En la ecuación (6) falta dividir entre 2 el factor `(1 − cos β)`. El código del script sí era correcto.

---

## 5. Salidas

| Salida | Descripción | Unidad |
|---|---|---|
| Tabla horaria | Mes, día, hora, minuto, temperatura, DNI, DHI, GHI, cenit, acimut, AOI, Gbi, Gdi, Gri, GTI | °C, W/m², ° |
| Perfil horario por mes | Promedio de cada componente por mes y hora del día | W/m² |
| Perfil horario anual | Promedio de cada componente por hora del día | W/m² |
| Radiación diaria | Suma de los 24 registros de cada día (un registro = 1 h) | Wh/m²·día |
| Radiación mensual | Promedio de la radiación diaria de cada mes (`HTdia`) y total del mes (`HTmes = HTdia · días`) | kWh/m²·día, kWh/m²·mes |
| Temperatura mensual | Promedio de `Temperature` por mes | °C |
| Radiación anual | Suma de los 8760 registros | kWh/m²·año |
| Barrido de inclinación | Radiación anual para cada inclinación del rango e inclinación óptima | °, kWh/m²·año |

Los nombres de columna llevan la unidad (`GTI_Wm2`, `HTdia_kWhm2dia`, `HTmes_kWhm2mes`, `Tamb_C`). Las tablas se devuelven como `polars.DataFrame`; las gráficas (perfiles horarios, radiación diaria y mensual, barrido de inclinación) se hacen con la API `Figure` de matplotlib, no con plotly.

---

## 6. Valores de referencia

TMY de la sección 2.1, acimut del panel 180°, cenit del archivo. Tolerancia relativa 1 × 10⁻⁹ (sumas de 8760 términos en el mismo orden).

### 6.1 Validación de la posición del sol

| Comparación | Puntos | Sesgo | RMS | Máximo |
|---|---|---|---|---|
| Elevación calculada frente a SunEarthTools 2025 (hh:00, elevación > 5°) | 4110 | +0,001° | 0,27° | 0,65° |
| Acimut calculado frente a SunEarthTools 2025 (hh:00, elevación > 5°) | 4110 | −0,02° | 0,85° | 5,6° (cerca del mediodía, cuando el acimut cambia rápido) |
| Cenit calculado frente a `Solar Zenith Angle` de NSRDB (hh:30, cenit < 85°) | — | +0,02° | 0,25° | — |

Prueba sugerida: el cenit calculado difiere del de NSRDB en menos de 1° (RMS < 0,5°) para cenit < 85°.

### 6.2 Radiación anual

| Caso | Radiación anual (Wh/m²·año) | Original con acimut a las hh:00 | Diferencia |
|---|---|---|---|
| GHI (β = 0°) | 2.193.006,5 | 2.193.006,5 | 0 |
| β = 18° | 2.287.430,5 | 2.280.167,3 (óptimo original) | +0,32 % |
| **β = 19° (óptimo)** | **2.287.663,8** | — | — |
| β = 20° | 2.287.358,1 | — | — |
| β = 30° | 2.255.036,1 | 2.244.027,2 | +0,49 % |
| β = latitud + 23,5° = 42,95° | 2.135.470,3 | — | — |
| β = 43° | 2.134.844,0 | 2.120.322,8 | +0,68 % |

La GHI anual es 2.192.997,0 Wh/m²; la diferencia con β = 0° (9,5 Wh/m²) se debe a redondeos del propio TMY entre GHI, DNI·cos θz y DHI.

### 6.3 Radiación mensual con la inclinación óptima (19°)

| Mes | HTdia (kWh/m²·día) | HTmes (kWh/m²·mes) | Tamb (°C) |
|---|---|---|---|
| Enero | 6,179 | 191,55 | 13,81 |
| Febrero | 7,002 | 196,06 | 15,32 |
| Marzo | 7,297 | 226,19 | 16,71 |
| Abril | 6,995 | 209,84 | 19,02 |
| Mayo | 6,656 | 206,35 | 19,54 |
| Junio | 5,959 | 178,78 | 18,45 |
| Julio | 5,628 | 174,48 | 17,50 |
| Agosto | 6,141 | 190,36 | 17,43 |
| Septiembre | 5,403 | 162,09 | 16,95 |
| Octubre | 5,744 | 178,06 | 16,45 |
| Noviembre | 6,093 | 182,79 | 14,61 |
| Diciembre | 6,166 | 191,13 | 12,60 |

Los valores con más decimales se fijan en las pruebas al implementar.

---

## 7. Pruebas de aceptación

1. El lector extrae latitud 19,45, longitud −99,14, zona horaria −6 y 8760 registros; un archivo sin `DNI` o con 8759 registros lanza `ValueError`.
2. Posición del sol: validación de la sección 6.1.
3. Con β = 0°, la GTI anual es 2.193.006,5 Wh/m² (tolerancia 1 × 10⁻⁹).
4. Radiación anual de la tabla 6.2 para 18°, 19°, 20°, 30°, 42,95° y 43°.
5. El barrido de 0° a 90° da el óptimo en 19°.
6. Radiación y temperatura mensuales de la tabla 6.3 (tres decimales en HTdia, dos en HTmes y Tamb).
7. Casos borde: β = 90° (vertical) da Gdi = DHI/2 y Gri = GHI·ρ/2; con DNI = 0, Gbi = 0; inclinación o latitud fuera de rango lanzan `ValueError`.

---

## 8. Supuestos y limitaciones

- Modelo isotrópico de la difusa: subestima la irradiancia frente a Hay-Davies o HDKR (Piccioli Artecona, 2022). Es suficiente para prefactibilidad.
- Albedo horario del TMY; suelo uniforme y reflexión difusa.
- Sin sombras, suciedad ni pérdidas por ángulo de incidencia (IAM).
- La radiación diaria suma registros horarios: cada registro representa la energía de 1 h (Wh/m²).
- La hora del TMY es estándar local; la conversión a hora solar usa la longitud y la ecuación del tiempo.

---

## 9. Referencias

- Duffie, J. A., y Beckman, W. A. (2013). *Solar engineering of thermal processes* (4.ª ed.). Wiley.
- Spencer, J. W. (1971). Fourier series representation of the position of the sun. *Search*, 2(5), 172.
- Sengupta, M., et al. (2018). The National Solar Radiation Data Base (NSRDB). *Renewable and Sustainable Energy Reviews*, 89, 51–60.
- Piccioli Artecona, I. (2022). *Modelado de la irradiancia solar sobre superficies inclinadas*. Tesis de maestría, Universidad de la República (Uruguay).
- Sandia National Laboratories (2026). PV Performance Modeling Collaborative: Angle of Incidence.
