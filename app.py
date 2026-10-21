"""
Aplicación web (Streamlit): uso de tecnologías digitales y calidad del sueño.

Carga o edita los datos, recalcula todas las pruebas estadísticas y genera el
informe en PDF (LaTeX). Ejecutar:  streamlit run app.py
"""
from __future__ import annotations

import hashlib
import io
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import analisis as an
import informe
import textos as tx

BASE = Path(__file__).parent
TITULO = "Uso de tecnologías digitales y calidad del sueño en estudiantes universitarios"
MUESTREOS = ["Muestreo por conveniencia", "Muestreo aleatorio simple", "Muestreo estratificado",
             "Censo / población completa", "No especificado"]
ORIGEN_EJ, ORIGEN_ARCH = "Datos simulados de ejemplo", "Cargar archivo (CSV o Excel)"

st.set_page_config(page_title="Tecnología digital y sueño", page_icon="🌙", layout="wide")

TEMAS = {  # oscuro, medio, claro, acento, fondo, suave, borde
    "Océano": ("#14243A", "#2F5D8C", "#3F78B0", "#D9822B", "#F7F9FC", "#E8EEF6", "#DCE5F0"),
    "Esmeralda": ("#0B3D2E", "#1F7A5C", "#34A583", "#E0A100", "#F5FAF7", "#E3F1EA", "#D3E6DB"),
    "Atardecer": ("#2D1B4E", "#6D3FA0", "#C2507A", "#F29E4C", "#FBF7FB", "#F1E8F4", "#E6D8EC"),
    "Grafito": ("#1F2933", "#3E4C59", "#616E7C", "#0E9F9A", "#F8F9FA", "#ECEFF2", "#DDE1E6"),
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@600;700&display=swap');
:root {--dark:%D%; --mid:%M%; --light:%L%; --acc:%A%; --bg:%B%; --soft:%S%; --bord:%R%;}
html, body, .stApp, [class*="css"] {font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;}
.stApp {background: var(--bg); color: var(--dark);}
.block-container {padding-top: 3.6rem; max-width: 1280px;}
h1, h2, h3 {font-family: 'Poppins', 'Inter', sans-serif; color: var(--dark); letter-spacing: -.01em;}
h2, h3 {padding-bottom: .25rem; border-bottom: 2px solid var(--soft);}
h2::after, h3::after {content: ""; display: block; width: 46px; height: 3px; background: var(--acc);
                      border-radius: 3px; margin-top: .25rem; position: relative; top: .3rem;}
@keyframes subir {from {opacity: 0; transform: translateY(10px);} to {opacity: 1; transform: none;}}
.hero, div[data-testid="stTabsContent"], div[data-testid="stMetric"] {animation: subir .45s ease both;}
.hero {position: relative; overflow: hidden; background: linear-gradient(120deg, var(--dark) 0%, var(--mid) 62%, var(--light) 100%);
       color: #fff; padding: 1.8rem 2rem; border-radius: 20px; margin-bottom: 1.2rem;
       box-shadow: 0 10px 28px color-mix(in srgb, var(--dark) 28%, transparent);}
.hero::before {content: ""; position: absolute; right: -60px; top: -70px; width: 260px; height: 260px;
               border-radius: 50%; background: radial-gradient(circle, rgba(255,255,255,.22), transparent 68%);}
.hero::after {content: ""; position: absolute; right: 90px; bottom: -90px; width: 190px; height: 190px;
              border-radius: 50%; background: radial-gradient(circle, color-mix(in srgb, var(--acc) 55%, transparent), transparent 70%);}
.hero h1 {color: #fff; font-size: 1.85rem; line-height: 1.2; margin: 0 0 .4rem 0; padding: 0; border: 0; position: relative; z-index: 1;}
.hero h1::after {display: none;}
.hero p {color: rgba(255,255,255,.82); margin: 0; font-size: 1rem; position: relative; z-index: 1;}
.hero .chips {margin-top: .9rem; display: flex; flex-wrap: wrap; gap: .45rem; position: relative; z-index: 1;}
.hero .chip {background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.28); backdrop-filter: blur(4px);
             padding: .18rem .75rem; border-radius: 999px; font-size: .8rem; color: #fff;}
.hero .chip.sim {background: var(--acc); border-color: var(--acc); font-weight: 600;}
div[data-testid="stMetric"] {background: #fff; border: 1px solid var(--bord); border-left: 5px solid var(--acc);
       border-radius: 14px; padding: .85rem 1.05rem; box-shadow: 0 2px 10px color-mix(in srgb, var(--dark) 8%, transparent);
       transition: transform .18s ease, box-shadow .18s ease;}
div[data-testid="stMetric"]:hover {transform: translateY(-3px); box-shadow: 0 10px 22px color-mix(in srgb, var(--dark) 14%, transparent);}
div[data-testid="stMetricValue"] {color: var(--dark); font-weight: 700; font-family: 'Poppins', 'Inter', sans-serif;}
[role="tablist"] {gap: .4rem !important; background: var(--soft) !important; padding: .35rem !important; border-radius: 14px !important; border-bottom: 0 !important;}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {display: none !important;}
button[role="tab"] {font-weight: 600 !important; border-radius: 10px !important; padding: .5rem 1.15rem !important; height: auto !important; color: var(--mid) !important; background: transparent !important;}
button[role="tab"] p {font-size: .95rem; font-weight: 600; color: inherit;}
button[role="tab"]:hover {background: color-mix(in srgb, var(--mid) 10%, transparent) !important;}
button[role="tab"][aria-selected="true"] {background: #fff !important; color: var(--dark) !important; box-shadow: 0 2px 8px color-mix(in srgb, var(--dark) 14%, transparent);}
section[data-testid="stSidebar"] {background: linear-gradient(180deg, var(--soft), var(--bg)); border-right: 1px solid var(--bord);}
section[data-testid="stSidebar"] h2 {font-size: .95rem; text-transform: uppercase; letter-spacing: .08em; color: var(--mid);
       border: 0; font-family: 'Inter', sans-serif; margin-top: .6rem;}
section[data-testid="stSidebar"] h2::after {display: none;}
button[data-testid="stBaseButton-primary"], button[kind="primary"] {background: linear-gradient(120deg, var(--mid), var(--light)); border: 0; color: #fff;
       border-radius: 12px; font-weight: 600; box-shadow: 0 4px 12px color-mix(in srgb, var(--mid) 35%, transparent); transition: transform .15s ease, filter .15s;}
button[data-testid="stBaseButton-primary"]:hover, button[kind="primary"]:hover {transform: translateY(-2px); filter: brightness(1.08); color: #fff;}
button[data-testid="stBaseButton-secondary"], button[kind="secondary"] {border-radius: 12px; border: 1px solid var(--bord); background: #fff; color: var(--dark); transition: all .15s;}
button[data-testid="stBaseButton-secondary"]:hover, button[kind="secondary"]:hover {border-color: var(--mid); color: var(--mid); transform: translateY(-1px);}
div[data-testid="stImage"] img {border-radius: 14px; border: 1px solid var(--bord); background: #fff; padding: .4rem; box-shadow: 0 2px 10px color-mix(in srgb, var(--dark) 7%, transparent);}
div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {border-radius: 14px; overflow: hidden; border: 1px solid var(--bord); box-shadow: 0 2px 10px color-mix(in srgb, var(--dark) 6%, transparent);}
div[data-testid="stAlert"] {border-radius: 14px; border: 1px solid var(--bord);}
div[data-testid="stExpander"] {border-radius: 14px; border: 1px solid var(--bord); background: #fff;}
div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] > div {border-radius: 10px !important;}
div[data-testid="stSlider"] [role="slider"] {background-color: var(--mid); box-shadow: 0 0 0 4px color-mix(in srgb, var(--mid) 22%, transparent);}
input[type="checkbox"], input[type="radio"] {accent-color: var(--mid);}
::-webkit-scrollbar {width: 10px; height: 10px;} ::-webkit-scrollbar-thumb {background: var(--bord); border-radius: 8px;}
::-webkit-scrollbar-thumb:hover {background: var(--mid);}
.pie {text-align: center; color: var(--mid); opacity: .8; font-size: .82rem; padding: 1.6rem 0 .5rem 0;}
@media (max-width: 700px) {.hero {padding: 1.2rem;} .hero h1 {font-size: 1.35rem;}}
</style>
"""


def aplicar_tema(nombre: str):
    d, m, l, a, b, s, r = TEMAS[nombre]
    css = CSS
    for k, v in {"%D%": d, "%M%": m, "%L%": l, "%A%": a, "%B%": b, "%S%": s, "%R%": r}.items():
        css = css.replace(k, v)
    st.markdown(css, unsafe_allow_html=True)



# --------------------------------------------------------------------------- datos
@st.cache_data
def cargar_ejemplo() -> pd.DataFrame:
    return pd.read_csv(BASE / "datos_simulados.csv")


def normalizar_carga(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    if "sexo" in df.columns:
        df["sexo"] = df["sexo"].map(lambda x: an.MAPA_SEXO.get(str(x).strip().lower(), x) if pd.notna(x) else x)
    return df


def leer_archivo(archivo) -> pd.DataFrame:
    if archivo.name.lower().endswith(".xlsx"):
        return pd.read_excel(archivo)
    bruto = archivo.getvalue()
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(io.StringIO(bruto.decode(enc)), sep=None, engine="python")
        except UnicodeDecodeError:
            continue
    raise ValueError("No se pudo leer el archivo como texto.")


def es_ejemplo_intacto(df_ok: pd.DataFrame) -> bool:
    try:
        ej, _, _ = an.validar(cargar_ejemplo())
        cols = [c for c in an.ETIQUETAS if c in ej.columns]
        return (df_ok.shape[0] == ej.shape[0] and np.allclose(df_ok[cols].to_numpy(float), ej[cols].to_numpy(float))
                and bool((df_ok["sexo"].to_numpy() == ej["sexo"].to_numpy()).all()))
    except Exception:
        return False


def restablecer():
    st.session_state.pop("editor", None)
    st.session_state["df_base"] = st.session_state.get("df_original")


def config_columnas(df: pd.DataFrame) -> dict:
    cfg = {}
    if "psqi_total" in df.columns:
        cfg["psqi_total"] = st.column_config.NumberColumn("psqi_total", min_value=0, max_value=21, step=1,
                                                          help="0 a 21; más alto es peor calidad de sueño")
    if "sexo" in df.columns and df["sexo"].dropna().isin(["Femenino", "Masculino"]).all():
        cfg["sexo"] = st.column_config.SelectboxColumn("sexo", options=["Femenino", "Masculino"])
    return cfg


# --------------------------------------------------------------------------- barra lateral
with st.sidebar:
    st.header("Datos")
    origen = st.radio("Origen", [ORIGEN_EJ, ORIGEN_ARCH], label_visibility="collapsed")
    archivo = st.file_uploader("CSV o Excel", type=["csv", "xlsx"]) if origen == ORIGEN_ARCH else None
    plantilla = cargar_ejemplo().head(3).to_csv(index=False)
    st.download_button("Descargar plantilla CSV", plantilla, "plantilla_datos.csv", "text/csv",
                       help="Muestra las columnas que espera la app (las 7 primeras de la lista son obligatorias).")
    with st.expander("Columnas esperadas"):
        st.markdown("**Obligatorias:** " + ", ".join(f"`{c}`" for c in an.REQUERIDAS)
                    + "\n\n**Opcionales:** " + ", ".join(f"`{c}`" for c in an.OPCIONALES)
                    + "\n\n`sexo` acepta Femenino/Masculino (también F/M). El PSQI va de 0 a 21.")

    st.header("Parámetros")
    umbral = st.slider("Uso nocturno alto desde (min)", 10, 60, 30, 5,
                       help="Define los dos grupos de la comparación y del chi-cuadrado. Elígelo antes de ver los resultados.")
    st.caption("Mala calidad de sueño: PSQI > 5 (Buysse et al., 1989). α = 0.05.")

    st.header("Informe")
    es_simulado_def = origen == ORIGEN_EJ
    simulados = st.checkbox("Los datos son simulados", value=es_simulado_def, key=f"simulados_{origen}")
    titulo = st.text_input("Título", TITULO)
    autores_txt = st.text_area("Autores (uno por línea)", "Roberto Alejandro Iguardia Rosales", height=110,
                               help="Cada línea aparece como un autor en la portada. Puedes agregar el carné: «Nombre – carné».")
    autores = [a.strip() for a in autores_txt.splitlines() if a.strip()]
    institucion = st.text_input("Institución", "Universidad Mariano Gálvez de Guatemala")
    curso = st.text_input("Curso", "Estadística")
    fuente, muestreo = "", "No especificado"
    if not simulados:
        fuente = st.text_area("Origen de los datos", placeholder="Ej.: Encuesta aplicada a estudiantes de la UMG en octubre de 2026.")
        muestreo = st.selectbox("Diseño muestral", MUESTREOS)

    st.header("Apariencia")
    tema = st.selectbox("Tema de color", list(TEMAS), label_visibility="collapsed")

aplicar_tema(tema)

# --------------------------------------------------------------------------- estado de los datos
firma = (origen, getattr(archivo, "name", None), getattr(archivo, "size", None))
if st.session_state.get("firma") != firma:
    st.session_state["firma"] = firma
    st.session_state.pop("editor", None)
    st.session_state.pop("informe", None)
    df0, error_carga = None, None
    if origen == ORIGEN_EJ:
        df0 = cargar_ejemplo()
    elif archivo is not None:
        try:
            df0 = normalizar_carga(leer_archivo(archivo))
        except Exception as e:  # archivo ilegible
            error_carga = f"No se pudo leer el archivo: {e}"
    st.session_state["df_original"] = df0
    st.session_state["df_base"] = df0
    st.session_state["error_carga"] = error_carga

import html as _html
_chips = "".join(f'<span class="chip">{_html.escape(c)}</span>' for c in
                 [curso.strip() or "Estadística", institucion.strip() or "Institución", " · ".join(autores) or "Sin autor"])
if simulados:
    _chips = '<span class="chip sim">Datos simulados</span>' + _chips
st.markdown(f'''<div class="hero"><h1>{_html.escape(titulo.strip() or TITULO)}</h1>
<p>Análisis estadístico con recálculo en vivo e informe en PDF generado con LaTeX.</p>
<div class="chips">{_chips}</div></div>''', unsafe_allow_html=True)

tabs = st.tabs(["Datos", "Descriptivo", "Correlaciones", "Comparaciones", "Regresión", "Informe PDF"])
t_datos, t_desc, t_corr, t_comp, t_reg, t_inf = tabs

df_ok, errores, avisos = None, [], []
with t_datos:
    if st.session_state.get("error_carga"):
        st.error(st.session_state["error_carga"])
    if st.session_state.get("df_base") is None:
        st.info("Carga un archivo CSV o Excel en la barra lateral, o usa los datos simulados de ejemplo.")
    else:
        st.markdown("Edita las celdas, agrega o elimina filas: **todo se recalcula** al instante.")
        base = st.session_state["df_base"]
        editado = st.data_editor(base, num_rows="dynamic", key="editor", height=380, width="stretch",
                                 column_config=config_columnas(base))
        df_ok, errores, avisos = an.validar(editado)
        c1, c2, c3 = st.columns([1, 1, 2])
        c1.metric("Filas válidas", 0 if df_ok is None else len(df_ok))
        c2.button("Restablecer datos originales", on_click=restablecer)
        if not errores:
            c3.download_button("Descargar datos (CSV)", df_ok.to_csv(index=False), "datos_analizados.csv", "text/csv")
        for a in avisos:
            st.warning(a)
        for e in errores:
            st.error(e)


def detener(mensaje: str):
    for t in tabs[1:]:
        with t:
            st.info(mensaje)
    st.stop()


if df_ok is None:
    detener("Primero carga los datos en la pestaña «Datos».")
if errores:
    detener("Corrige los errores de la pestaña «Datos» para ver los resultados.")

# --------------------------------------------------------------------------- cálculo (con memoria)
clave = hashlib.sha256((df_ok.to_csv(index=False) + f"|{umbral}").encode()).hexdigest()
if st.session_state.get("clave_res") != clave:
    try:
        R_, figs_ = an.analizar(df_ok, umbral)
        st.session_state.update(clave_res=clave, R=R_, pngs=an.figuras_a_png(figs_), error_res=None)
    except an.AnalisisError as e:
        st.session_state.update(clave_res=clave, R=None, pngs=None, error_res=str(e))
if st.session_state.get("error_res"):
    detener(st.session_state["error_res"])

R, PNGS = st.session_state["R"], st.session_state["pngs"]
meta = {
    "titulo": titulo.strip() or TITULO, "autor": ", ".join(autores), "autores": autores, "institucion": institucion.strip(), "curso": curso.strip(),
    "titulo_corto": "Tecnología digital y sueño" if (titulo.strip() or TITULO) == TITULO else (titulo.strip()[:42] + "…"),
    "simulados": simulados, "fuente": fuente, "muestreo": muestreo,
    "ejemplo_intacto": origen == ORIGEN_EJ and es_ejemplo_intacto(df_ok),
}
T = tx.construir(R, meta)
D = tx.tablas(R)


def figura(nombre: str, ancho: int | None = None):
    if nombre in PNGS:
        st.image(PNGS[nombre], caption=tx.PIES[nombre], width=ancho if ancho else "stretch")


def tabla(nombre: str):
    if nombre in D:
        st.dataframe(D[nombre], hide_index=True, width="stretch")


# --------------------------------------------------------------------------- pestañas de resultados
with t_desc:
    m = st.columns(4)
    m[0].metric("Mala calidad de sueño", f"{R['pct_mala']:.1f} %", help=f"PSQI > {R['corte_psqi']}")
    m[1].metric("PSQI promedio", tx.f(next(d for d in R["descriptivo"] if d["variable"] == "psqi_total")["media"]))
    m[2].metric("Pantalla (h/día)", tx.f(next(d for d in R["descriptivo"] if d["variable"] == "horas_pantalla_dia")["media"]))
    m[3].metric("Celular antes de dormir (min)", tx.f(next(d for d in R["descriptivo"] if d["variable"] == "min_celular_antes_dormir")["media"], 1))
    st.markdown(T["resumen"])
    tabla("descriptivo")
    st.markdown(T["normalidad"])
    figura("f1_distribuciones")

with t_corr:
    st.markdown(T["correlaciones"])
    tabla("correlaciones")
    a, b = st.columns(2)
    with a:
        figura("f2_dispersion_pantalla")
    with b:
        figura("f3_dispersion_nocturno")
    figura("f6_correlaciones", 640)

with t_comp:
    st.subheader(f"Uso nocturno de {R['umbral_noct']} min o más frente a menos")
    st.markdown(T["dos_grupos"])
    st.subheader("Niveles de uso de pantallas (ANOVA)")
    st.markdown(T["anova"])
    a, b = st.columns(2)
    with a:
        tabla("terciles")
        tabla("tukey")
    with b:
        figura("f4_boxplot_terciles")
    st.subheader("Uso nocturno y mala calidad de sueño (chi-cuadrado)")
    st.markdown(T["chi2"])
    a, b = st.columns(2)
    with a:
        tabla("chi2")
    with b:
        figura("f5_barras_chi2")

with t_reg:
    st.subheader("Regresión lineal múltiple")
    st.markdown(T["ols_resumen"])
    tabla("ols")
    st.markdown(T["ols_efectos"])
    st.markdown("**Verificación de supuestos.** " + T["supuestos"])
    tabla("supuestos")
    figura("f7_residuos")
    st.subheader("Regresión logística")
    st.markdown(T["logit"])
    tabla("logit")
    figura("f8_forest_or", 760)
    for a_ in R["avisos"]:
        st.warning(a_)

with t_inf:
    st.markdown("El informe se arma con **los datos que ves ahora**: cifras, tablas, figuras e interpretación se recalculan. "
                "Cada afirmación del texto depende de los resultados (por ejemplo, solo dice «se rechaza H₀» si la prueba es significativa).")
    hay_latex = shutil.which("pdflatex") is not None
    st.caption("pdflatex: " + ("disponible en este equipo." if hay_latex else
                               "no encontrado; podrás descargar el paquete .zip y compilarlo en Overleaf o con TeX Live/MiKTeX."))
    bloqueo = None
    if not simulados and not fuente.strip():
        bloqueo = "Describe el origen de los datos en la barra lateral para generar el informe."
    if not autores:
        bloqueo = "Escribe al menos un autor en la barra lateral."
    if bloqueo:
        st.warning(bloqueo)
    huella = hashlib.sha256((clave + json.dumps(meta, sort_keys=True, default=str)).encode()).hexdigest()
    if st.button("Generar informe PDF", type="primary", disabled=bloqueo is not None):
        with st.spinner("Compilando el informe en LaTeX…"):
            res = informe.generar(R, meta, PNGS)
        res["huella"] = huella
        st.session_state["informe"] = res
    res = st.session_state.get("informe")
    if res:
        if res.get("huella") != huella:
            st.warning("Este informe corresponde a datos o textos anteriores; vuelve a generarlo para actualizarlo.")
        if res["ok"]:
            st.success("Informe generado.")
            st.download_button("Descargar PDF", res["pdf"], "informe_estadistico.pdf", "application/pdf", type="primary")
        else:
            st.error(res["motivo"])
        st.download_button("Descargar paquete LaTeX (.zip)", res["zip"], "informe_latex.zip", "application/zip",
                           help="Contiene informe.tex y la carpeta figuras/; compila con pdflatex u Overleaf.")

st.markdown('<div class="pie">α = 0.05 · PSQI &gt; 5 = mala calidad de sueño · Python, SciPy, statsmodels y LaTeX</div>', unsafe_allow_html=True)
