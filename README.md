# Plataforma de diseño de centrales de energía renovable

Plataforma en Python para el **diseño de prefactibilidad** de centrales de energía renovable, con un módulo por tecnología. Cada módulo estima el recurso y la energía anual, dimensiona los componentes principales y calcula indicadores económicos comparables entre tecnologías.

El proyecto empezó como un aplicativo para el caudal de diseño de una pequeña central hidroeléctrica (versiones 1.0.0 a 3.0.0, ver `CHANGELOG.md`). Desde la versión 4.0.0 el cálculo vive en el paquete `energias/` y la interfaz es una aplicación Streamlit multipágina.

## Módulos disponibles

| Tecnología | Módulo | Qué calcula |
|---|---|---|
| Hidráulica (pequeña central) | `energias/hidraulica/` | Caudal de equipamiento (Qe) de energía máxima, canal de derivación y diámetro económico de la tubería forzada |
| Común | `energias/comun/` | Unidades de potencia y energía (W/kW/MW/GW, J↔Wh) y utilidades de gráficas (guardado en png y svg, bytes, formatos de eje) |

La hoja de ruta de las demás tecnologías está en `docs/contextoProyecto.md`.

## Estructura del proyecto

```
<repositorio>/
├── pyproject.toml          Paquete instalable (pip install -e .) y configuración de pytest
├── requirements.txt        polars, matplotlib, numpy, streamlit, pytest
├── energias/               Paquete de cálculo (no importa Streamlit)
│   ├── comun/
│   │   ├── unidades.py     Unidades: factores de potencia y energía, J↔Wh
│   │   └── graficos.py     Graficos: guardado de figuras, bytes y formatos de eje
│   └── hidraulica/
│       ├── analisisCaudalDiseno.py   AnalisisCaudalDiseno: clase principal del caudal de equipamiento
│       ├── lectorDatos.py            LectorDatos
│       ├── procesadorCaudales.py     ProcesadorCaudales
│       ├── calculadoraPotencia.py    CalculadoraPotencia
│       ├── disenoCanal.py            DisenoCanal (canal de derivación)
│       ├── disenoTuberiaForzada.py   DisenoTuberiaForzada (diámetro económico)
│       └── graficador.py             Graficador (figuras de la hidráulica)
├── interfaz/
│   ├── app.py              Página de inicio
│   └── pages/
│       └── 1_Hidraulica.py Hidráulica: caudal de equipamiento, canal y tubería
├── scripts/
│   └── ejecutarHidraulica.py   Ejecución por consola de la hidráulica
├── data/hidraulica/        descargaDhime.csv (IDEAM), SAACP.csv (CONAGUA)
├── outputs/hidraulica/     Resultados (se crea al ejecutar; no se versiona)
├── tests/                  Pruebas pytest (regresión, módulos comunes e interfaz)
└── docs/                   Contexto del proyecto y especificaciones con sus Excel
```

## Instalación

Desde la carpeta raíz del repositorio, en PowerShell (Windows, Python 3.13):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
```

`pip install -e .` instala el paquete `energias` en modo editable: los cambios en el código se usan sin reinstalar, y los scripts, la interfaz y las pruebas lo importan con `from energias.<tecnologia>.<modulo> import <Clase>`.

## Ejecución

### Consola

```powershell
python scripts\ejecutarHidraulica.py
```

Los parámetros se editan al inicio de `scripts/ejecutarHidraulica.py`. Con los valores por defecto (CONAGUA, H = 150 m, Francis, η total = 0,88) imprime `Energía anual máxima: 1,516,526,226.3 kWh/año con Qe = 238.79 m³/s` y guarda los resultados en `outputs/hidraulica/`.

### Interfaz web (Streamlit)

```powershell
python -m streamlit run interfaz\app.py
```

Se abre el navegador en `http://localhost:8501`. La página de inicio describe la plataforma y las tecnologías disponibles; cada tecnología tiene su página en la barra lateral. La primera vez Streamlit puede pedir un correo en la consola; se puede dejar vacío y pulsar Enter. Para cerrar la interfaz, `Ctrl + C` en la consola.

La página **Hidráulica** tiene tres pestañas: **1. Caudal de equipamiento**, **2. Canal de derivación** y **3. Tubería forzada**. Las dos últimas usan como caudal de diseño el caudal de equipamiento (Qe) de energía máxima del módulo 1, por lo que este debe calcularse primero.

En la barra lateral se elige la fuente (IDEAM o CONAGUA), el archivo (de la carpeta `data/hidraulica` o subiendo uno) y los parámetros del cálculo; el botón **Calcular** muestra las métricas principales, las gráficas y las tablas. Cada gráfica y tabla tiene su botón de descarga (PNG, SVG o CSV), y el botón **Guardar resultados en la carpeta outputs** exporta todo a `outputs/hidraulica/`, igual que la ejecución por consola.

### Pruebas

```powershell
python -m pytest
```

Las pruebas reproducen los resultados de referencia de la hidráulica (`docs/contextoAplicativo.md`, sección 7), prueban los módulos comunes y cargan cada página de la interfaz con `streamlit.testing.v1.AppTest`.

## Salidas

Cada tecnología guarda sus resultados en `outputs/<tecnologia>/`, que se crea al guardar. Los archivos tienen siempre el mismo nombre, así que una nueva ejecución sobrescribe los anteriores. El contenido de `outputs/` no se versiona.

## Módulo hidráulico

Analiza la serie histórica de caudales medios diarios de una estación hidrológica para construir la curva de caudal clasificado promedio y determinar el caudal de equipamiento que maximiza la energía anual de una potencial pequeña central hidroeléctrica. Con ese Qe como caudal de diseño, dimensiona el canal de derivación y el diámetro económico de la tubería forzada.

### Fuentes de datos

| | IDEAM (Colombia, DHIME) | CONAGUA (México) |
|---|---|---|
| Archivo por defecto | `descargaDhime.csv` | `SAACP.csv` |
| Metadatos antes del encabezado | No | Sí (estación, clave, estado, municipio) |
| Columna de caudal | `Valor` | `Gasto en Rio(m3/s)` |
| Formato de `Fecha` | `AAAA-MM-DD HH:MM` | `AAAA-MM-DD` |
| Otras columnas | Estación, variable, unidad, nivel de aprobación | Estación, `Nivel(m)` |
| Días sin caudal | No aparecen | Aparecen con nivel y gasto vacío (se descartan y se tratan como faltantes) |

El lector busca la línea del encabezado, por lo que acepta cualquier cantidad de líneas de metadatos, y lee el archivo en UTF-8 (con respaldo en latin-1). Para otro archivo de la misma fuente, indica su nombre en `nombreArchivo`.

### Flujo de trabajo (pipeline)

1. Lee el archivo de la carpeta `data/hidraulica` según la fuente elegida (IDEAM o CONAGUA).
2. Extrae `Fecha` (date) y `Valor` (float). `Valor` pasa a llamarse `Caudal`.
3. Agrega las columnas `Ano`, `Mes` y `Dia`.
4. Asigna cada fecha a un periodo anual de octubre a septiembre. El periodo se identifica con el año en que inicia (periodo 2000 = 1° de octubre de 2000 a 30 de septiembre de 2001). Se conservan solo los periodos con al menos `minDiasPorPeriodo` días con dato (300 por defecto).
5. Numera los días de 1 a 365 (`NumDia`; 1° de octubre = 1, 30 de septiembre = 365). Se incluyen las filas de las fechas faltantes, que quedan con `Caudal` nulo.
6. Gráfica de `NumDia` vs `Caudal` con una línea por periodo.
7. Crea `CaudalClasificado`: dentro de cada periodo ordena los caudales de mayor a menor sin modificar la numeración de los días (los días sin dato quedan al final).
8. Calcula `CaudalClasificadoPromedio`: promedio de `CaudalClasificado` de todos los periodos para cada `NumDia` (los nulos no se tienen en cuenta).
9. Gráfica de `NumDia` vs `CaudalClasificado` con todos los periodos y la línea promedio (punteada).
10. Exporta `NumDia` y `CaudalClasificadoPromedio`.
11. Calcula la energía anual para cada caudal de equipamiento (ver más abajo), la grafica contra `Qe`, identifica el `Qe` de energía máxima y grafica la energía generada cada día con ese `Qe` sobre la curva de caudal clasificado promedio.

#### Consideraciones sobre los datos

- El 29 de febrero se descarta para que todos los periodos tengan 365 días.
- Los periodos con menos de `minDiasPorPeriodo` días con dato se excluyen; en los demás, los días faltantes se completan con caudal nulo. Como esos días quedan al final de la clasificación, las posiciones altas de la curva promedio (caudales bajos) se calculan con menos periodos que las posiciones bajas, y en la última posición pueden aportar muy pocos. Al ejecutar, el programa imprime la cobertura de cada periodo.

### Potencia y energía generada

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

#### Parámetros (se editan en `scripts/ejecutarHidraulica.py`)

| Parámetro | Descripción | Valor por defecto |
|---|---|---|
| `fuente` | Fuente del archivo: `IDEAM` o `CONAGUA` | IDEAM |
| `nombreArchivo` | Archivo en `data/hidraulica/`; con `None` se usa el de la fuente | None |
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

### Canal de derivación

Canal de sección trapezoidal con la ecuación de Chezy-Manning (`energias/hidraulica/disenoCanal.py`). Los lados de la sección se llaman **x** (ancho superior), **y** (ancho de la base), **z** (profundidad del agua) y **w** (lado inclinado); la letra **A** se usa solo para el área.

Dos modos de cálculo:
- **Dimensionar para el caudal de diseño:** con el ancho de la base `y`, el talud (proyección horizontal / altura), la pendiente y el coeficiente de Manning, se calcula la profundidad normal `z` que conduce el caudal de diseño (resolviendo Manning por bisección).
- **Verificar una sección dada:** con `x`, `y` y `z` se calcula la capacidad `Q` (el cálculo de la Hoja 1 del Excel de origen) y se compara con el caudal de diseño.

La pendiente se define por las cotas aguas arriba y aguas abajo y la longitud, o directamente. El coeficiente de Manning se elige entre concreto sin pulir (0,014), canal excavado (0,025) u otro valor.

Fórmulas:

```
s  = (cota aguas arriba - cota aguas abajo) / L
w  = sqrt(z² + ((x - y)/2)²)        A = (x + y)/2 · z
Pm = 2w + y                          Rh = A / Pm
Q  = Rh^(2/3) · A · s^(1/2) / n      v = Q / A
Fr = v / sqrt(g · A / x)
```

**Número de Froude (Fr):** compara la velocidad del agua con la velocidad con que viaja una pequeña onda en su superficie. Con Fr < 1 el flujo es subcrítico (lento y profundo, estable; es el régimen habitual de un canal de derivación); con Fr > 1 es supercrítico (rápido y somero; puede erosionar y formar resaltos hidráulicos). Cerca de 1 el flujo es inestable, por lo que como regla práctica se evitan valores aproximadamente entre 0,8 y 1,2.

### Tubería forzada

Diámetro económico de la tubería forzada (`energias/hidraulica/disenoTuberiaForzada.py`). El caudal de diseño es el Qe del módulo 1.

**Iteración:** en cada paso se calculan, con el diámetro del paso anterior, la velocidad `v = 4Q/(πD²)`, el número de Reynolds, la rugosidad relativa, el factor de fricción `f` y el costo por metro `c`, y con ellos un nuevo diámetro. Se repite hasta que el error relativo entre dos diámetros consecutivos sea menor o igual que la tolerancia (5 % por defecto). El diámetro inicial es el que da la velocidad inicial supuesta (2,5 m/s por defecto).

Factor de fricción de Darcy (se elige el método y se comparan ambos al diámetro final):

```
Laminar (Re < 2000):  f = 64 / Re
Colebrook-White:      1/sqrt(f) = -2·log10( εr/3,7 + 2,51/(Re·sqrt(f)) )     (iterativo)
Swamee-Jain:          f = 0,25 / [ log10( εr/3,7 + 5,74/Re^0,9 ) ]²           (explícito)
```

El diagrama de Moody se genera con las curvas de Colebrook-White y marca el punto de operación (Re, f).

Otras fórmulas:

```
Re = ρ·v·D / μ            εr = ε / D
c  = k · (12,16 + 513,5 · D^1,5)       costo por metro (k = tasa de cambio desde USD)
D  = 1,106 · ( f·h·p / (η·a·c) )^0,143 · Q^0,43      diámetro económico
e  = (D + 508) / 400                   espesor, con D y e en mm
```

| Variable | Descripción | Valor por defecto |
|---|---|---|
| ε | Rugosidad absoluta, según el material elegido en la tabla | Hierro galvanizado (0,15 mm) |
| μ | Viscosidad dinámica (Pa·s) | 0,001 |
| ρ | Densidad del agua (la del módulo 1) | 1000 kg/m³ |
| h | Horas de funcionamiento al año | 6000 |
| p | Precio de la energía (moneda/kWh) | 0,27 |
| η | Eficiencia global (por defecto la del módulo 1) | Eficiencia total del módulo 1 |
| a | Factor de amortización | 0,064 |
| Tolerancia | Error relativo para detener la iteración | 5 % |
| Moneda | Código de la moneda; con una distinta de USD se pide la tasa de cambio (unidades de la moneda por 1 USD) | USD |

Tabla de rugosidad absoluta (ε usado en el cálculo, en mm): vidrio y plástico 0; PVC 0,0015; concreto 4,95 (valor medio del rango 0,9 a 9); goma lisa 0,01; tubería de cobre o bronce 0,0015; hierro fundido 0,26; hierro galvanizado 0,15; hierro forjado 0,046; acero inoxidable 0,002; acero comercial 0,045. También se puede ingresar un valor propio.

La correlación del costo de la tubería está en dólares: si se cambia la moneda, el precio de la energía debe ingresarse en esa moneda y la tasa de cambio convierte el costo de la tubería.

### Resultados (carpeta `outputs/hidraulica`)

Los archivos de salida tienen siempre el mismo nombre, por lo que una nueva ejecución sobrescribe los resultados anteriores.

| Archivo | Contenido |
|---|---|
| `caudalesPorPeriodo.png` / `.svg` | Caudal diario por número de día, todos los periodos |
| `caudalesClasificados.png` / `.svg` | Caudales clasificados por periodo y promedio |
| `caudalClasificadoPromedio.csv` | `NumDia`, `CaudalClasificadoPromedio` |
| `energiaDiariaClasificada.png` / `.svg` | Energía generada por día con el caudal de equipamiento óptimo |
| `energiaAnualVsCaudalEquipamiento.png` / `.svg` | Energía anual vs caudal de equipamiento, con el máximo resaltado |
| `energiaDiariaCaudalOptimo.csv` | `NumDia`, caudal clasificado promedio, caudal utilizado y `EnergiaDiaria_<unidad>h` con el `Qe` óptimo |
| `energiaAnualPorCaudalEquipamiento.csv` | `CaudalEquipamiento`, `CaudalMinimoTecnico` y `EnergiaAnual_<unidad>h` |

Con los botones de guardado de las pestañas 2 y 3 de la interfaz también se exportan `canalDerivacion.csv`, `seccionCanal` (png y svg), `tuberiaForzadaIteraciones.csv`, `tuberiaForzadaMetodosFriccion.csv`, `diagramaMoody` (png y svg) y `convergenciaDiametro` (png y svg).
