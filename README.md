# Tecnología digital y calidad del sueño — app de análisis

Aplicación en Streamlit que **carga o edita los datos, recalcula todas las pruebas estadísticas y genera el informe en PDF con LaTeX**. Incluye datos simulados de ejemplo (n = 200).

## Ejecutar

```bash
pip install -r requirements.txt
streamlit run app.py
```

Para generar el PDF directamente desde la app necesitas un compilador LaTeX con `pdflatex` (paquetes estándar):

- Windows: MiKTeX · macOS: MacTeX o BasicTeX · Linux: `sudo apt install texlive-latex-extra texlive-fonts-recommended`

Sin LaTeX la app funciona igual y ofrece el **paquete .zip** (`informe.tex` + `figuras/`) para compilarlo en Overleaf.

## Uso

1. **Datos**: usa el ejemplo o carga un CSV/Excel (acepta `;` y coma decimal). La tabla es editable: cambia celdas, agrega o borra filas y todo se recalcula.
2. **Parámetros**: umbral de uso nocturno (por defecto 30 min). Mala calidad de sueño = PSQI > 5.
3. **Pestañas**: descriptivo, correlaciones, comparaciones (t/Mann-Whitney, ANOVA/Kruskal/Tukey, chi-cuadrado) y regresión (lineal y logística, con supuestos).
4. **Informe PDF**: completa título, autor y, si los datos no son simulados, su origen y el diseño muestral; luego «Generar informe PDF».

## Columnas

Obligatorias: `psqi_total` (0–21), `horas_pantalla_dia`, `min_celular_antes_dormir`, `tazas_cafeina_dia`, `horas_estudio_trabajo_dia`, `sexo` (Femenino/Masculino, también F/M), `edad`.
Opcionales: `horas_redes_dia`, `horas_videojuegos_dia`, `horas_sueno_noche`, `carrera`, `ciclo`, `id`. En la barra lateral puedes descargar una plantilla.

## Cómo se construye el informe

Las cifras, tablas y figuras salen del análisis, y **cada afirmación del texto depende de los resultados** (`textos.py`): solo dice «se rechaza H₀» si la prueba es significativa, elige «peor» o «mejor» según el signo, advierte si un supuesto no se cumple, etc. Si marcas los datos como simulados, el informe lo declara en portada, metodología y limitaciones; si no, usa el origen y el diseño muestral que indiques.

## Archivos

| Archivo | Función |
| --- | --- |
| `app.py` | Interfaz Streamlit |
| `analisis.py` | Validación, pruebas estadísticas y figuras |
| `textos.py` | Tablas y texto de interpretación condicional |
| `informe.py` | Plantilla LaTeX y compilación a PDF |
| `01_generar_datos.py` | Genera `datos_simulados.csv` (semilla 2026) |
| `tests/` | Pruebas automáticas |

## Pruebas

```bash
pip install pytest pypdf
python -m pytest
```

## Despliegue en Streamlit Community Cloud

`packages.txt` instala LaTeX en el servidor, de modo que el botón de PDF también funciona en línea.

> Los datos de ejemplo son simulados: sirven para ilustrar el método, no para describir estudiantes reales.

## Publicar en Streamlit Community Cloud

1. Crea un repositorio en GitHub y sube **el contenido** de esta carpeta (`app.py` debe quedar en la raíz del repositorio). El `.gitignore` ya excluye `.venv`.
2. Entra a https://share.streamlit.io con tu cuenta de GitHub, elige **Create app → Deploy a public app from GitHub**.
3. Repositorio: el que creaste · Rama: `main` · Archivo principal: `app.py`.
4. En **Advanced settings** elige Python 3.12.
5. **Deploy**. La primera vez tarda varios minutos porque instala LaTeX desde `packages.txt`.
6. La URL `https://<nombre>.streamlit.app` funciona desde cualquier red. Con datos reales, en *Settings → Sharing* ponla privada e invita por correo.
