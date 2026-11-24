# Contexto del aplicativo de caudal de diseño (hidráulica)

Este documento resume qué hace el aplicativo, cómo está construido, qué decisiones de diseño se tomaron y qué quedó pendiente. Describe el estado de la **versión 3.0.0**, la última antes de la reestructuración del proyecto. El historial de cambios por versión está en `CHANGELOG.md`.

El aplicativo se desarrolló en conversaciones con Claude entre octubre y noviembre de 2026. Cada versión se entregaba como un zip, sin control de versiones; este repositorio empieza a llevar ese historial.

---

## 1. Propósito

Determinar, a partir de la serie histórica de caudales medios diarios de una estación hidrológica, el **caudal de equipamiento (Qe)** que maximiza la energía anual de una potencial pequeña central hidroeléctrica. Con ese Qe como caudal de diseño, dimensionar el **canal de derivación** y el **diámetro económico de la tubería forzada**.

Tiene tres módulos:

| Módulo | Qué calcula | Entrada principal | Salida principal |
|---|---|---|---|
| 1. Caudal de equipamiento | Curva de caudal clasificado promedio, energía anual por Qe y Qe óptimo | CSV de caudales diarios (IDEAM o CONAGUA) | Qe de energía máxima y energía anual |
| 2. Canal de derivación | Sección trapezoidal por Manning | Qe del módulo 1 | Profundidad, velocidad y número de Froude |
| 3. Tubería forzada | Diámetro económico iterando con Colebrook | Qe del módulo 1 | Diámetro, velocidad, f, costo y espesor |

Se usa de dos maneras:
- **Consola:** `python scripts\analisisCaudalDiseno.py`, con los parámetros editables al final del archivo. Solo ejecuta el módulo 1.
- **Interfaz web:** `python -m streamlit run scripts\interfazStreamlit.py`, con los tres módulos en pestañas.

---

## 2. Estructura (versión 3.0.0)

```
analisisCaudal/
├── data/                  descargaDhime.csv (IDEAM), SAACP.csv (CONAGUA)
├── outputs/               resultados csv, png y svg (no se versionan)
├── scripts/
│   ├── analisisCaudalDiseno.py   AnalisisCaudalDiseno: clase principal del módulo 1
│   ├── lectorDatos.py            LectorDatos: lectura según la fuente
│   ├── procesadorCaudales.py     ProcesadorCaudales: periodos, numeración, clasificación
│   ├── calculadoraPotencia.py    CalculadoraPotencia: potencia y energía por Qe
│   ├── disenoCanal.py            DisenoCanal: módulo 2
│   ├── disenoTuberiaForzada.py   DisenoTuberiaForzada: módulo 3
│   ├── graficador.py             Graficador: todas las figuras (API Figure de matplotlib)
│   └── interfazStreamlit.py      InterfazStreamlit: interfaz web
├── README.md
└── requirements.txt       polars, matplotlib, numpy, streamlit
```

Convenciones: variables y métodos en camelCase, programación orientada a objetos con una clase por responsabilidad, textos y documentación en español, `polars` para datos y `matplotlib` para gráficas.

---

## 3. Módulo 1: caudal de equipamiento

### 3.1 Lectura de datos (`LectorDatos`)

| | IDEAM (Colombia, DHIME) | CONAGUA (México) |
|---|---|---|
| Archivo de ejemplo | `descargaDhime.csv` | `SAACP.csv` (estación Salto de Agua, Chiapas) |
| Encabezado | Primera línea | Después de varias líneas de metadatos |
| Columna de caudal | `Valor` | `Gasto en Rio(m3/s)` |
| Formato de `Fecha` | `AAAA-MM-DD HH:MM` | `AAAA-MM-DD` |
| Días sin caudal | No aparecen | Aparecen con nivel y gasto vacío |

- El lector busca la línea del encabezado, así que acepta cualquier número de líneas de metadatos.
- Lee el archivo en UTF-8, con respaldo en latin-1.
- Toma los 10 primeros caracteres de la fecha.
- Descarta los días sin caudal y las fechas repetidas.

### 3.2 Pipeline

1. Leer el archivo y extraer `Fecha` (date) y `Valor` (float). `Valor` pasa a llamarse `Caudal`.
2. Agregar `Ano`, `Mes` y `Dia`.
3. Asignar cada fecha a un **periodo hidrológico de octubre a septiembre**. El periodo se nombra por el año en que inicia: el periodo 2000 va del 1/10/2000 al 30/09/2001.
4. **Excluir el 29 de febrero**, para que todos los periodos tengan 365 días.
5. Conservar solo los periodos con al menos **300 días con dato** (`minDiasPorPeriodo`).
6. Numerar los días de 1 a 365 (`NumDia`; 1° de octubre = 1). Los días faltantes de los periodos conservados se completan como filas con caudal nulo.
7. `CaudalClasificado`: dentro de cada periodo, ordenar los caudales de mayor a menor sin cambiar la numeración. Los nulos quedan al final.
8. `CaudalClasificadoPromedio`: promedio por `NumDia` de todos los periodos, ignorando nulos.
9. Calcular la energía anual para cada caudal de equipamiento (sección 3.3) e identificar el máximo.
10. Calcular la energía diaria con el Qe óptimo.

### 3.3 Potencia y energía (`CalculadoraPotencia`)

Para cada Qe, fila por fila sobre `CaudalClasificadoPromedio`:

```
Qmt = Qe · K                                  caudal mínimo técnico
Qi  = min(Qclasificado, Qe)  si Qclasificado ≥ Qmt;  0 si es menor
P   = η · ρ · g · Qi · H                      [W]
Ediaria = P · 24                              [Wh/día]
Eanual  = Σ Ediaria de las 365 filas          [Wh/año]
```

- **η:** `eficienciaTotal` si se indica; si no, ηg · ηG (0,85 · 0,95).
- **ρ y g:** 1000 kg/m³ y 9,8 m/s², editables.
- **Factor K por turbina:**

| Turbina | K |
|---|---|
| Pelton | 0,10 |
| Ossberger | 0,15 |
| Kaplan | 0,22 |
| Semikaplan | 0,35 |
| Francis | 0,35 |
| Hélice | 0,65 |

- **Rango de Qe:** del mínimo al máximo del caudal clasificado promedio.
- **Paso automático de Qe**, según el caudal máximo:

| Caudal máximo (m³/s) | Paso (m³/s) |
|---|---|
| < 25 | 0,1 |
| < 100 | 1 |
| < 1000 | 10 |
| < 2000 | 50 |
| ≥ 2000 | 50 (la regla original no lo define) |

  Un valor en `pasoQe` reemplaza el paso automático.
- **Unidades de salida:** W/Wh, kW/kWh (por defecto), MW/MWh o GW/GWh.

### 3.4 Gráficas y salidas

- **Gráficas:**
  - Caudal por día de todos los periodos.
  - Caudales clasificados por periodo, con el promedio en línea punteada.
  - Energía diaria con el Qe óptimo.
  - Energía anual contra Qe, con el máximo resaltado.
- **CSV:** `caudalClasificadoPromedio.csv`, `energiaAnualPorCaudalEquipamiento.csv` y `energiaDiariaCaudalOptimo.csv`.
- Todo se exporta a `outputs/` en png y svg, y cada ejecución sobrescribe los archivos anteriores.

---

## 4. Módulo 2: canal de derivación (`DisenoCanal`)

Sección trapezoidal con la ecuación de Chezy-Manning. Los lados se llaman **x** (ancho superior), **y** (base), **z** (profundidad del agua) y **w** (lado inclinado). **A** se usa solo para el área.

```
s  = (cota aguas arriba − cota aguas abajo) / L
w  = √(z² + ((x − y)/2)²)        A  = (x + y)/2 · z
Pm = 2w + y                      Rh = A / Pm
Q  = Rh^(2/3) · A · s^(1/2) / n   v = Q / A
Fr = v / √(g · A / x)
```

- **Dimensionar:** dados la base, el talud y la pendiente, encuentra por bisección la profundidad z que conduce Qe.
- **Verificar:** dada una sección (x, y, z), calcula su capacidad y la compara con Qe.
- **Coeficiente de Manning n:** concreto sin pulir 0,014, canal excavado 0,025, u otro valor.
- **Número de Froude:**
  - Fr < 1: flujo subcrítico, el régimen habitual de un canal.
  - Fr > 1: flujo supercrítico.
  - Entre 0,8 y 1,2: flujo inestable, se recomienda evitarlo.

Origen: Hoja 1 de `docs/especificaciones/hidraulica/Canal_de_derivación_y_tubería_forzada.xlsx`. En esa hoja, "A" era a la vez el ancho superior y el área; aquí se renombró.

---

## 5. Módulo 3: tubería forzada (`DisenoTuberiaForzada`)

El caudal de diseño es el Qe del módulo 1. El diámetro se itera: en cada paso se recalculan v, Re, εr, f y c con el diámetro anterior, hasta que el error relativo |Dn+1 − Dn| / Dn+1 sea ≤ tolerancia (5 % por defecto). El diámetro inicial es el que da una velocidad supuesta de 2,5 m/s.

```
v = 4Q / (πD²)        Re = ρvD / μ        εr = ε / D
f: laminar (Re < 2000) 64/Re; turbulento por Colebrook-White (iterativa) o Swamee-Jain (explícita)
c = k · (12,16 + 513,5 · D^1,5)          costo por metro; k = tasa de cambio desde USD
D = 1,106 · (f·h·p / (η·a·c))^0,143 · Q^0,43     diámetro económico
e = (D + 508) / 400                      espesor, con D y e en mm
```

Valores por defecto:

| Parámetro | Valor |
|---|---|
| Material | Hierro galvanizado (ε = 0,15 mm), de una tabla de 10 materiales; el concreto usa el valor medio, 4,95 mm |
| μ | 0,001 Pa·s |
| h | 6000 h/año |
| p | 0,27 por kWh |
| a | 0,064 |
| η | La eficiencia total del módulo 1 |
| Moneda | USD; con otra moneda se pide la tasa de cambio, y p se ingresa en esa moneda |

La interfaz muestra:
- un diagrama de Moody generado con Colebrook, con el punto de operación;
- el gráfico de convergencia;
- la tabla de iteraciones;
- la comparación de f entre los dos métodos;
- las fórmulas.

Origen: Hoja 2 del mismo Excel. Se corrigieron tres cosas:
- las unidades intercambiadas de ν y μ;
- f calculado con un caudal distinto al del diámetro económico;
- el diámetro económico sin iterar (el Excel daba 0,981 m; convergido da 0,830 m).

---

## 6. Interfaz Streamlit (`InterfazStreamlit`)

- **Barra lateral (módulo 1):** fuente, archivo de `data/` o subido, días mínimos, salto, turbina (muestra K), eficiencia (total o por separado), ρ, g, unidad y paso de Qe.
- **Pestaña 1:** métricas (energía máxima, Qe, periodos incluidos, paso), una pestaña por gráfica con descarga en PNG y SVG, tablas con descarga en CSV y un botón para guardar en `outputs/`.
- **Pestañas 2 y 3:** canal y tubería con sus entradas, métricas, gráficos, fórmulas en LaTeX y descargas.
- **Errores:** si la fuente no corresponde al archivo, muestra un mensaje en vez de fallar.

---

## 7. Resultados de referencia (versión 3.0.0)

Estos valores sirven como pruebas de regresión: la reestructuración debe reproducirlos exactamente.

| Caso | Resultado |
|---|---|
| CONAGUA (`SAACP.csv`), H = 150 m, Francis, η total = 0,88, paso automático, 300 días | Qe = 238,79333333333335 m³/s; Eanual = 1.516.526.226,2599678 kWh/año; paso 50; 25 de 33 periodos; 39 valores de Qe |
| IDEAM (`descargaDhime.csv`), H = 10 m, Kaplan, ηg = 0,85 y ηG = 0,95, paso automático, 300 días | Qe = 3,4717000000000002 m³/s; Eanual = 1.032.428,0985059995 kWh/año; paso 0,1; 20 de 27 periodos; 227 valores de Qe |
| Canal: x = 5,2, y = 1,2, z = 1,0 m; cotas 1,1 y 1,0 m; L = 100 m; n = 0,014 | Q = 4,9350418541031935 m³/s; v = 1,542200579407248 m/s; Pm = 5,67213595499958 m; Rh = 0,5641613715516516 m; Fr = 0,6279925718620699 |
| Canal, dimensionar con y = 1,2 m y talud 2 para el Q anterior | z = 1,0 m (bisección) |
| Tubería: Q = 0,5 m³/s, ε = 0,2 mm, η = 0,9, demás por defecto, tolerancia 5 % | D = 0,8342021876785625 m en 3 iteraciones |
| Tubería: el mismo caso con tolerancia 1e-9 | D = 0,829721252601844 m; f = 0,015330366062117984 |
| Colebrook: Re = 250.000, εr = 0,002 | f = 0,024139763482553166 |

Las tres versiones (1, 2 y 3) dan resultados idénticos en el módulo 1; los CSV coinciden byte a byte.

---

## 8. Pendientes y limitaciones conocidas

| # | Tema | Estado |
|---|---|---|
| 1 | **Cola de la curva promedio.** Los días faltantes quedan al final de la clasificación, así que las últimas posiciones se promedian con pocos periodos y la curva deja de ser decreciente (en CONAGUA sube en 14 posiciones; la posición 365 depende de un solo periodo). Afecta el caudal mínimo, desde donde arranca Qe. | Propuesta sin decidir: asignar a cada periodo todas las posiciones por porcentaje de excedencia |
| 2 | **El módulo 3 no calcula pérdidas.** Sin longitud ni salto bruto no hay hf ni altura neta. | Propuesta sin decidir: agregar L y salto bruto, hf = f·(L/D)·v²/(2g), Hn = Hb − hf, y una tabla de barrido D–V |
| 3 | El costo c y el espesor e no dependen de la presión; en saltos altos probablemente se subestiman. | Abierto |
| 4 | Constantes del costo, el espesor y el diámetro económico tomadas del Excel original. | Confirmar la fuente bibliográfica |
| 5 | Paso de Qe para caudales ≥ 2000 m³/s no definido por la regla (se usa 50). | Abierto |
| 6 | `outputs/` se sobrescribe en cada ejecución, aunque cambie la fuente. | Propuesta: subcarpeta por archivo o tecnología |
| 7 | La interfaz no tiene control de acceso. | Solo si se publica en red |
| 8 | En `Clase_3_Ecuación_de_Colebrook.xlsx` se detectaron errores que no se incorporaron al aplicativo: f de la fila 47 (D = 0,7 m, V = 5 m/s) es la rugosidad relativa copiada; hf multiplica por g·0,01 en vez de dividir entre 2g (−3,96 %); el bloque Pelton tiene errores de fórmula (√, grados/radianes, diámetro del chorro). | Corregir solo si se incorpora el bloque |
