# Análisis de caudal de diseño para una central hidroeléctrica

Programa en Python que analiza la serie histórica de caudales medios diarios de una estación hidrológica (formato DHIME) para construir la curva de caudal clasificado promedio y determinar el caudal de equipamiento que maximiza la energía anual generada por una potencial central hidroeléctrica.

## Estructura del proyecto

```
analisisCaudal/
├── .venv/            Entorno virtual (polars, matplotlib, numpy)
├── data/             Archivos de entrada en .csv (descargaDhime.csv)
├── outputs/          Resultados en .csv, .svg y .png
├── scripts/
│   ├── analisisCaudalDiseno.py   Clase principal AnalisisCaudalDiseno (se ejecuta al final)
│   ├── lectorDatos.py            Clase LectorDatos
│   ├── procesadorCaudales.py     Clase ProcesadorCaudales
│   ├── calculadoraPotencia.py    Clase CalculadoraPotencia
│   └── graficador.py             Clase Graficador
└── requirements.txt
```

## Instalación y ejecución

Desde la carpeta raíz del proyecto (Windows):

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts\analisisCaudalDiseno.py
```

Los archivos de datos se colocan en `data/`. Se elige la fuente con el parámetro `fuente` (ver "Parámetros").

## Fuentes de datos

| | IDEAM (Colombia, DHIME) | CONAGUA (México) |
|---|---|---|
| Archivo por defecto | `descargaDhime.csv` | `SAACP.csv` |
| Metadatos antes del encabezado | No | Sí (estación, clave, estado, municipio) |
| Columna de caudal | `Valor` | `Gasto en Rio(m3/s)` |
| Formato de `Fecha` | `AAAA-MM-DD HH:MM` | `AAAA-MM-DD` |
| Otras columnas | Estación, variable, unidad, nivel de aprobación | Estación, `Nivel(m)` |
| Días sin caudal | No aparecen | Aparecen con nivel y gasto vacío (se descartan y se tratan como faltantes) |

El lector busca la línea del encabezado, por lo que acepta cualquier cantidad de líneas de metadatos, y lee el archivo en UTF-8 (con respaldo en latin-1). Para otro archivo de la misma fuente, indica su nombre en `nombreArchivo`.

## Flujo de trabajo (pipeline)

1. Lee el archivo de la carpeta `data` según la fuente elegida (IDEAM o CONAGUA).
2. Extrae `Fecha` (date) y `Valor` (float). `Valor` pasa a llamarse `Caudal`.
3. Agrega las columnas `Ano`, `Mes` y `Dia`.
4. Asigna cada fecha a un periodo anual de octubre a septiembre. El periodo se identifica con el año en que inicia (periodo 2000 = 1° de octubre de 2000 a 30 de septiembre de 2001). Se conservan solo los periodos con al menos `minDiasPorPeriodo` días con dato (300 por defecto).
5. Numera los días de 1 a 365 (`NumDia`; 1° de octubre = 1, 30 de septiembre = 365). Se incluyen las filas de las fechas faltantes, que quedan con `Caudal` nulo.
6. Gráfica de `NumDia` vs `Caudal` con una línea por periodo.
7. Crea `CaudalClasificado`: dentro de cada periodo ordena los caudales de mayor a menor sin modificar la numeración de los días (los días sin dato quedan al final).
8. Calcula `CaudalClasificadoPromedio`: promedio de `CaudalClasificado` de todos los periodos para cada `NumDia` (los nulos no se tienen en cuenta).
9. Gráfica de `NumDia` vs `CaudalClasificado` con todos los periodos y la línea promedio (punteada).
10. Exporta `NumDia` y `CaudalClasificadoPromedio`.
11. Calcula la energía anual para cada caudal de equipamiento (ver más abajo), la grafica contra `Qe` e identifica el `Qe` de energía máxima.

### Consideraciones sobre los datos

- El 29 de febrero se descarta para que todos los periodos tengan 365 días.
- Los periodos con menos de `minDiasPorPeriodo` días con dato se excluyen; en los demás, los días faltantes se completan con caudal nulo. Como esos días quedan al final de la clasificación, las posiciones altas de la curva promedio (caudales bajos) se calculan con menos periodos que las posiciones bajas, y en la última posición pueden aportar muy pocos. Al ejecutar, el programa imprime la cobertura de cada periodo.

## Potencia y energía generada

Para cada caudal de equipamiento `Qe` se aplica, fila por fila sobre `CaudalClasificadoPromedio`:

- Caudal mínimo técnico: `Qmt = Qe * K`
- Caudal utilizado `Qi`: el caudal clasificado limitado hacia arriba por `Qe`; si es inferior a `Qmt`, vale cero.
- Potencia (W): `Pc = η * ρ * g * Qi * H`, donde `η = ηg * ηG` o la eficiencia total indicada directamente (`eficienciaTotal`).
- Energía diaria (Wh-día): `Pc * 24`
- Energía anual (Wh-año): suma de la energía diaria de las 365 filas.

`Qe` varía desde el mínimo hasta el máximo del caudal clasificado promedio. El paso se define automáticamente según ese caudal máximo (parámetro `pasoQe` en `None`):

| Caudal máximo del clasificado promedio (m³/s) | Paso de Qe (m³/s) |
|---|---|
| menor a 25 | 0.1 |
| menor a 100 | 1 |
| menor a 1000 | 10 |
| menor a 2000 | 50 |
| 2000 o más | 50 |

Si se indica un valor en `pasoQe`, se usa ese paso sin importar el caudal.

### Parámetros (se editan al final de `scripts/analisisCaudalDiseno.py`)

| Parámetro | Descripción | Valor por defecto |
|---|---|---|
| `fuente` | Fuente del archivo: `IDEAM` o `CONAGUA` | IDEAM |
| `nombreArchivo` | Archivo en `data/`; con `None` se usa el de la fuente | None |
| `minDiasPorPeriodo` | Días con dato mínimos para incluir un periodo | 300 |
| `saltoNeto` | Salto neto H (m) | 10 |
| `tipoTurbina` | Pelton, Ossberger, Kaplan, Semikaplan, Francis o Hélice | Kaplan |
| `unidadEnergia` | `W`, `kW`, `MW` o `GW` (energía en Wh, kWh, MWh o GWh) | kW |
| `densidadAgua` | Densidad del agua ρ (kg/m³) | 1000 |
| `gravedad` | Aceleración de la gravedad g (m/s²) | 9.8 |
| `eficienciaTurbina` | ηg (se ignora si se indica `eficienciaTotal`) | 0.85 |
| `eficienciaGenerador` | ηG (se ignora si se indica `eficienciaTotal`) | 0.95 |
| `eficienciaTotal` | Eficiencia total ηg*ηG; con `None` se usa el producto de las dos | None |
| `pasoQe` | Incremento entre caudales de equipamiento (m³/s); `None` es automático | None |

Factor K por tipo de turbina:

| Turbina | K |
|---|---|
| Pelton | 0.10 |
| Ossberger | 0.15 |
| Kaplan | 0.22 |
| Semikaplan | 0.35 |
| Francis | 0.35 |
| Hélice | 0.65 |

## Resultados (carpeta `outputs`)

Los archivos de salida tienen siempre el mismo nombre, por lo que una nueva ejecución sobrescribe los resultados anteriores.

| Archivo | Contenido |
|---|---|
| `caudalesPorPeriodo.png` / `.svg` | Caudal diario por número de día, todos los periodos |
| `caudalesClasificados.png` / `.svg` | Caudales clasificados por periodo y promedio |
| `caudalClasificadoPromedio.csv` | `NumDia`, `CaudalClasificadoPromedio` |
| `energiaAnualVsCaudalEquipamiento.png` / `.svg` | Energía anual vs caudal de equipamiento, con el máximo resaltado |
| `energiaAnualPorCaudalEquipamiento.csv` | `CaudalEquipamiento`, `CaudalMinimoTecnico` y `EnergiaAnual_<unidad>h` |
