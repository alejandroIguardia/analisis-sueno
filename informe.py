"""
Generador del informe en LaTeX y PDF.

`generar(R, meta, pngs)` arma `informe.tex` con las cifras, tablas y textos
calculados, lo compila con pdflatex (si está instalado) y devuelve el PDF y un
.zip autocontenido (.tex + figuras) para compilar en otro equipo u Overleaf.
Solo usa paquetes estándar de LaTeX (sin babel/spanish), para que compile en
instalaciones mínimas.
"""
from __future__ import annotations

import io
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import pandas as pd

import textos as tx
from analisis import ETIQUETAS

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

_ESC = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
        "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
_SIMBOLOS = [
    ("χ²", r"$\chi^2$"), ("η²", r"$\eta^2$"), ("R²", r"$R^2$"), ("H₀", r"$H_0$"), ("H₁", r"$H_1$"),
    ("α", r"$\alpha$"), ("β", r"$\beta$"), ("ρ", r"$\rho$"), ("≥", r"$\geq$"), ("≤", r"$\leq$"),
    ("≈", r"$\approx$"), ("±", r"$\pm$"), ("×", r"$\times$"), ("→", r"$\rightarrow$"), ("−", r"$-$"),
    ("’", "'"), ("‘", "`"), ("“", "``"), ("”", "''"), ("—", "---"), ("–", "--"), ("·", r"\textperiodcentered{}"),
    ("«", r"\guillemotleft{}"), ("»", r"\guillemotright{}"),
]


def tex(s) -> str:
    """Texto con marcado ligero (**negrita**, *cursiva*, símbolos Unicode) -> LaTeX."""
    s = "" if s is None else str(s)
    s = "".join(_ESC.get(ch, ch) for ch in s)
    s = s.replace(" \\%", r"\,\%")
    for a, b in _SIMBOLOS:
        s = s.replace(a, b)
    s = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", s)
    s = re.sub(r"\*(.+?)\*", r"\\emph{\1}", s)
    return s


def fecha_es(d) -> str:
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def tabla_tex(df: pd.DataFrame, spec: str, pie: str, etiqueta: str) -> str:
    cab = " & ".join(rf"\textbf{{{tex(c)}}}" for c in df.columns)
    filas = "\n".join(" & ".join(tex(c) for c in fila) + r" \\" for fila in df.itertuples(index=False))
    return (
        "\\begin{table}[H]\n\\centering\\small\n"
        f"\\caption{{{tex(pie)}}}\\label{{{etiqueta}}}\n"
        f"\\begin{{tabular}}{{{spec}}}\n\\toprule\n{cab} \\\\\n\\midrule\n{filas}\n\\bottomrule\n\\end{{tabular}}\n\\end{{table}}\n"
    )


def figura_tex(nombres: list[str], ancho: float, pie: str, etiqueta: str) -> str:
    if len(nombres) == 1:
        cuerpo = f"\\includegraphics[width={ancho}\\linewidth]{{figuras/{nombres[0]}.png}}"
    else:
        cuerpo = "\\hfill".join(
            f"\\begin{{minipage}}{{0.48\\linewidth}}\\centering\\includegraphics[width=\\linewidth]{{figuras/{n}.png}}\\end{{minipage}}"
            for n in nombres)
    return f"\\begin{{figure}}[htbp]\n\\centering\n{cuerpo}\n\\caption{{{tex(pie)}}}\\label{{{etiqueta}}}\n\\end{{figure}}\n"


def parrafos(items: list[str]) -> str:
    return "\n\n".join(tex(p) for p in items)


def itemize(items: list[str], env: str = "itemize") -> str:
    cuerpo = "\n".join(f"\\item {tex(i)}" for i in items)
    return f"\\begin{{{env}}}[leftmargin=*,itemsep=2pt]\n{cuerpo}\n\\end{{{env}}}"


# --------------------------------------------------------------------------- documento
PREAMBULO = r"""\documentclass[11pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{charter}
\usepackage[scaled=.92]{helvet}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{array}
\usepackage{caption}
\usepackage{float}
\usepackage{xcolor}
\usepackage{enumitem}
\usepackage{setspace}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{microtype}
\usepackage[margin=2.5cm]{geometry}
\usepackage[hidelinks]{hyperref}
\renewcommand{\figurename}{Figura}
\renewcommand{\tablename}{Tabla}
\renewcommand{\contentsname}{Contenido}
\renewcommand{\refname}{Referencias}
\setstretch{1.12}
\captionsetup{font=small,labelfont=bf,skip=6pt}
\titleformat{\section}{\sffamily\Large\bfseries\color[HTML]{14243A}}{\thesection}{0.7em}{}
\titleformat{\subsection}{\sffamily\large\bfseries\color[HTML]{2F5D8C}}{\thesubsection}{0.7em}{}
\setlength{\parskip}{4pt}
\setlength{\parindent}{0pt}
\pagestyle{fancy}\fancyhf{}
\renewcommand{\headrulewidth}{0.3pt}
\fancyhead[L]{\small\sffamily TITULO_CORTO}
\fancyhead[R]{\small\sffamily DATOS_NOTA}
\fancyfoot[C]{\small\thepage}
"""


def construir_tex(R: dict, meta: dict, nombres_figuras: set[str]) -> str:
    T = tx.construir(R, meta)
    D = tx.tablas(R)
    u, corte, n = R["umbral_noct"], R["corte_psqi"], R["n"]
    simulados = bool(meta.get("simulados"))
    hoy = meta["fecha"]

    pre = (PREAMBULO.replace("TITULO_CORTO", tex(meta["titulo_corto"]))
           .replace("DATOS_NOTA", "Datos simulados" if simulados else tex(meta["curso"])))
    limpio = lambda t: re.sub(r"[{}\\&#$%^_~]", "", str(t))
    autores = [a for a in (meta.get("autores") or [meta.get("autor", "")]) if str(a).strip()]
    pdfinfo = f"\\hypersetup{{pdftitle={{{limpio(meta['titulo'])}}},pdfauthor={{{limpio(', '.join(autores))}}}}}\n"

    portada = [
        r"\begin{titlepage}", r"\centering", r"\sffamily",
        rf"{{\large\textbf{{{tex(meta['institucion'])}}}\par}}", r"\vspace{0.4cm}",
        rf"{{\large {tex(meta['curso'])}\par}}", r"\vfill",
        rf"{{\fontsize{{26}}{{32}}\selectfont\bfseries\color[HTML]{{14243A}} {tex(meta['titulo'])}\par}}",
        r"\vspace{0.8cm}", r"{\color[HTML]{D9822B}\rule{4cm}{1.2pt}\par}", r"\vspace{0.8cm}",
        rf"{{\large {r' \\ '.join(tex(a) for a in autores)}\par}}", r"\vspace{0.3cm}", rf"{{\normalsize {tex(hoy)}\par}}", r"\vfill",
    ]
    if simulados:
        portada.append(r"\fbox{\parbox{0.8\linewidth}{\centering\small\textbf{Datos simulados.} "
                       r"El análisis ilustra el método estadístico; los resultados no describen a estudiantes reales.}}")
    portada += [r"\end{titlepage}", r"\tableofcontents", r"\newpage"]

    # ---- resumen e introducción
    cuerpo = [
        r"\section*{Resumen}", tex(T["resumen"]),
        r"\section{Introducción y objetivos}",
        tex("Los estudiantes universitarios pasan buena parte del día frente a pantallas, incluida la hora previa a dormir. "
            "Estudios previos asocian el uso nocturno de dispositivos con menor calidad y duración del sueño (Chang et al., 2015; "
            "Hale y Guan, 2015). Este informe evalúa esa relación con las técnicas estadísticas del curso."),
        tex("**Pregunta de investigación:** ¿existe relación entre el uso de tecnologías digitales y la calidad del sueño en estudiantes universitarios?"),
        tex("**Objetivo general:** analizar estadísticamente la asociación entre el uso de tecnologías digitales y la calidad del sueño."),
        tex("**Objetivos específicos:**"),
        itemize([
            "Describir el uso de pantallas y la calidad del sueño (PSQI) de la muestra.",
            "Medir la correlación entre horas de pantalla, uso nocturno del celular y PSQI.",
            f"Comparar el PSQI entre niveles de uso de pantallas y entre uso nocturno alto y bajo (umbral de {u} minutos).",
            "Estimar el efecto de cada variable de uso controlando por cafeína, carga de estudio o trabajo, sexo y edad.",
        ], "enumerate"),
        tex("**Hipótesis** (α = 0.05): H₀, no existe asociación entre el uso de tecnologías digitales y el PSQI; "
            "H₁, a mayor uso, mayor PSQI (peor calidad de sueño)."),
    ]

    # ---- metodología
    sx = R["sexo"]
    desc_muestra = (f"{n} estudiantes ({sx.get('Femenino', 0)} mujeres y {sx.get('Masculino', 0)} hombres, de "
                    f"{R['edad_rango'][0]} a {R['edad_rango'][1]} años"
                    + (f", de {R['carreras']} carreras" if R.get("carreras") else "") + ")")
    if simulados:
        origen = ("**Naturaleza de los datos.** Los datos son simulados con fines ilustrativos: no provienen de una encuesta real, "
                  "por lo que los resultados no son evidencia sobre estudiantes reales. "
                  f"El diseño es transversal, con {desc_muestra}.")
    else:
        muestreo = meta.get("muestreo", "No especificado")
        frase_muestreo = "No se especificó el diseño muestral." if muestreo == "No especificado" else f"{muestreo}."
        origen = (f"**Origen de los datos.** {meta['fuente'].strip().rstrip('.')}. "
                  f"{frase_muestreo} El diseño es transversal, con {desc_muestra}.")
    filas_var = []
    for v in ["psqi_total", "horas_pantalla_dia", "horas_redes_dia", "horas_videojuegos_dia", "min_celular_antes_dormir",
              "tazas_cafeina_dia", "horas_estudio_trabajo_dia", "horas_sueno_noche", "sexo", "edad"]:
        if v in {d["variable"] for d in R["descriptivo"]} or v == "sexo":
            tipo, d_ = tx.DESC_VARIABLES[v]
            etiqueta = "Sexo" if v == "sexo" else ETIQUETAS[v]
            filas_var.append([etiqueta, tipo, d_.format(corte=corte)])
    t_var = pd.DataFrame(filas_var, columns=["Variable", "Tipo", "Descripción"])
    cuerpo += [
        r"\section{Metodología}", tex(origen),
        tabla_tex(t_var, r">{\raggedright\arraybackslash}p{3.8cm}>{\raggedright\arraybackslash}p{3.0cm}>{\raggedright\arraybackslash}p{7.4cm}", "Variables del estudio.", "tab:variables"),
        tex(f"**Análisis estadístico** (α = 0.05; Python {R['versiones']['python']} con pandas, SciPy y statsmodels):"),
        itemize([
            "Estadística descriptiva: media, desviación estándar, mediana y asimetría.",
            "Normalidad con Shapiro-Wilk.",
            "Correlación de Pearson y Spearman con IC 95 % (transformación de Fisher).",
            f"Uso nocturno del celular de {u} minutos o más frente a menos de {u}: t de Welch, U de Mann-Whitney y d de Cohen.",
            "Terciles de horas de pantalla: ANOVA de un factor, Kruskal-Wallis, Tukey y η².",
            "Chi-cuadrado de independencia entre uso nocturno y mala calidad de sueño, con V de Cramér, odds ratio y, si corresponde, prueba exacta de Fisher.",
            "Regresión lineal múltiple sobre el PSQI y regresión logística sobre PSQI > " + str(corte) + ", con VIF, Breusch-Pagan, Durbin-Watson, Shapiro-Wilk de residuos y AUC.",
        ], "enumerate"),
    ]

    # ---- resultados
    cuerpo += [
        r"\section{Resultados}", r"\subsection{Descriptivo}", tex(T["descriptivo"]),
        tabla_tex(D["descriptivo"], "lrrrrr", "Estadísticos descriptivos de la muestra.", "tab:desc"),
        tex(T["normalidad"]),
        figura_tex(["f1_distribuciones"], 1.0, tx.PIES["f1_distribuciones"], "fig:f1"),
        r"\subsection{Correlaciones}", tex(T["correlaciones"]),
        tabla_tex(D["correlaciones"], "lrrrr", "Correlación de cada variable con el PSQI.", "tab:corr"),
        figura_tex(["f6_correlaciones"], 0.72, tx.PIES["f6_correlaciones"], "fig:f6"),
        figura_tex(["f2_dispersion_pantalla", "f3_dispersion_nocturno"], 1.0,
                   "Dispersión del PSQI frente a las horas de pantalla (izquierda) y al uso del celular antes de dormir (derecha), con la recta de regresión simple.", "fig:disp"),
        rf"\subsection{{Uso nocturno alto frente a bajo}}", tex(T["dos_grupos"]),
        r"\subsection{Niveles de uso de pantallas (ANOVA)}", tex(T["anova"]),
        tabla_tex(D["terciles"], "lrrr", "PSQI por tercil de horas de pantalla.", "tab:terciles"),
        tabla_tex(D["tukey"], "lrrr", "Comparaciones por pares de Tukey.", "tab:tukey"),
        figura_tex(["f4_boxplot_terciles"], 0.62, tx.PIES["f4_boxplot_terciles"], "fig:f4"),
    ]
    if "chi2" in D:
        cuerpo += [r"\subsection{Uso nocturno y mala calidad de sueño (chi-cuadrado)}", tex(T["chi2"]),
                   tabla_tex(D["chi2"], "lrrr", "Calidad de sueño según uso nocturno del celular.", "tab:chi2")]
        if "f5_barras_chi2" in nombres_figuras:
            cuerpo.append(figura_tex(["f5_barras_chi2"], 0.55, tx.PIES["f5_barras_chi2"], "fig:f5"))
    else:
        cuerpo += [r"\subsection{Uso nocturno y mala calidad de sueño (chi-cuadrado)}", tex(T["chi2"])]

    cuerpo += [
        r"\subsection{Regresión lineal múltiple}", tex(T["ols_resumen"]),
        tabla_tex(D["ols"], "lrrrrr", "Regresión lineal múltiple sobre el PSQI.", "tab:ols"),
        tex(T["ols_efectos"]),
        r"\subsubsection*{Verificación de supuestos}", tex(T["supuestos"]),
        tabla_tex(D["supuestos"], r">{\raggedright\arraybackslash}p{3.8cm}>{\raggedright\arraybackslash}p{2.8cm}>{\raggedright\arraybackslash}p{3.7cm}>{\raggedright\arraybackslash}p{4.2cm}", "Supuestos del modelo lineal.", "tab:supuestos"),
        figura_tex(["f7_residuos"], 1.0, tx.PIES["f7_residuos"], "fig:f7"),
        r"\subsection{Regresión logística}", tex(T["logit"]),
    ]
    if "logit" in D:
        cuerpo.append(tabla_tex(D["logit"], "lrrr", f"Regresión logística sobre mala calidad de sueño (PSQI > {corte}).", "tab:logit"))
        if "f8_forest_or" in nombres_figuras:
            cuerpo.append(figura_tex(["f8_forest_or"], 0.9, tx.PIES["f8_forest_or"], "fig:f8"))
    if R["avisos"]:
        cuerpo += [r"\subsubsection*{Notas del análisis}", itemize(R["avisos"])]

    # ---- cierre
    cuerpo += [
        r"\section{Discusión}", parrafos(T["discusion"]),
        r"\section{Limitaciones}", itemize(T["limitaciones"]),
        r"\section{Conclusiones y recomendaciones}", itemize(T["conclusiones"], "enumerate"),
        tex("**Recomendaciones.** " + T["recomendacion"]),
        r"\begin{thebibliography}{9}",
        r"\bibitem{buysse} Buysse, D. J., Reynolds, C. F., Monk, T. H., Berman, S. R., \& Kupfer, D. J. (1989). The Pittsburgh Sleep Quality Index: A new instrument for psychiatric practice and research. \emph{Psychiatry Research, 28}(2), 193--213.",
        r"\bibitem{chang} Chang, A.-M., Aeschbach, D., Duffy, J. F., \& Czeisler, C. A. (2015). Evening use of light-emitting eReaders negatively affects sleep, circadian timing, and next-morning alertness. \emph{Proceedings of the National Academy of Sciences, 112}(4), 1232--1237.",
        r"\bibitem{cohen} Cohen, J. (1988). \emph{Statistical power analysis for the behavioral sciences} (2.\textordfeminine{} ed.). Lawrence Erlbaum Associates.",
        r"\bibitem{hale} Hale, L., \& Guan, S. (2015). Screen time and sleep among school-aged children and adolescents: A systematic review. \emph{Sleep Medicine Reviews, 21}, 50--58.",
        r"\bibitem{seabold} Seabold, S., \& Perktold, J. (2010). Statsmodels: Econometric and statistical modeling with Python. \emph{Proceedings of the 9th Python in Science Conference}, 92--96.",
        r"\bibitem{scipy} Virtanen, P., et al. (2020). SciPy 1.0: Fundamental algorithms for scientific computing in Python. \emph{Nature Methods, 17}, 261--272.",
        r"\end{thebibliography}",
    ]

    v = R["versiones"]
    anexo = [
        r"\appendix", r"\section{Anexo: reproducibilidad}",
        tex("Este informe se generó automáticamente con la aplicación de análisis a partir de los datos cargados; "
            "si los datos cambian, todas las cifras, tablas, figuras e interpretaciones se recalculan."),
        tex(f"**Modelo lineal:** {R['ols']['formula'].replace('~', '=')}."),
        tex(f"**Parámetros:** punto de corte del PSQI = {corte}; umbral de uso nocturno = {u} minutos; α = 0.05."),
        tex(f"**Software:** Python {v['python']}, NumPy {v['numpy']}, pandas {v['pandas']}, SciPy {v['scipy']}, statsmodels {v['statsmodels']}."),
    ]
    if meta.get("ejemplo_intacto"):
        anexo.append(tex("**Datos de ejemplo:** se generaron con el script 01_generar_datos.py (semilla 2026)."))
    return pre + pdfinfo + "\\begin{document}\n" + "\n".join(portada) + "\n\n" + "\n\n".join(cuerpo) + "\n\n" + "\n\n".join(anexo) + "\n\\end{document}\n"


# --------------------------------------------------------------------------- compilación
def _error_latex(log: str) -> str:
    lineas = log.splitlines()
    for i, ln in enumerate(lineas):
        if ln.startswith("!"):
            return "\n".join(lineas[i:i + 8])
    return "\n".join(lineas[-15:])


def generar(R: dict, meta: dict, pngs: dict[str, bytes], compilar: bool = True) -> dict:
    """Devuelve {'ok', 'pdf', 'zip', 'tex', 'log', 'motivo'}."""
    meta = dict(meta)
    meta.setdefault("fecha", fecha_es(pd.Timestamp.today()))
    meta.setdefault("titulo_corto", "Tecnología digital y sueño")
    contenido = construir_tex(R, meta, set(pngs))
    res = {"ok": False, "pdf": None, "zip": None, "tex": contenido, "log": "", "motivo": ""}

    with tempfile.TemporaryDirectory() as tmp:
        carpeta = Path(tmp)
        (carpeta / "figuras").mkdir()
        for nombre, datos in pngs.items():
            (carpeta / "figuras" / f"{nombre}.png").write_bytes(datos)
        (carpeta / "informe.tex").write_text(contenido, encoding="utf-8")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(carpeta / "informe.tex", "informe.tex")
            for p in sorted((carpeta / "figuras").glob("*.png")):
                z.write(p, f"figuras/{p.name}")
        res["zip"] = buf.getvalue()

        if not compilar:
            return res
        exe = shutil.which("pdflatex")
        if exe is None:
            res["motivo"] = "No se encontró pdflatex en este equipo; descarga el paquete .zip y compílalo en Overleaf o con TeX Live/MiKTeX."
            return res
        log = ""
        for _ in range(2):  # dos pasadas: índice y referencias
            try:
                proc = subprocess.run([exe, "-interaction=nonstopmode", "-halt-on-error", "informe.tex"],
                                      cwd=carpeta, capture_output=True, timeout=180)
            except subprocess.TimeoutExpired:
                res["motivo"] = "pdflatex tardó más de 3 minutos y se canceló."
                return res
            log = (proc.stdout + proc.stderr).decode("utf-8", errors="replace")
            if proc.returncode != 0:
                res["log"] = log
                res["motivo"] = "LaTeX falló al compilar:\n" + _error_latex(log)
                return res
        pdf = carpeta / "informe.pdf"
        if not pdf.exists():
            res["motivo"] = "pdflatex terminó sin generar el PDF."
            return res
        res.update(ok=True, pdf=pdf.read_bytes(), log=log)
    return res
