"""
Núcleo estadístico: uso de tecnologías digitales y calidad del sueño (PSQI).

`validar(df)`  -> limpia y revisa la tabla de datos.
`analizar(df)` -> ejecuta todas las pruebas y devuelve (resultados, figuras).

Los resultados son un diccionario con tipos nativos de Python (serializable a
JSON). Las figuras son objetos de matplotlib; quien las llame debe guardarlas
y cerrarlas (ver `figuras_a_png`).
"""
from __future__ import annotations

import io
import platform
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import scipy
import statsmodels
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.outliers_influence import variance_inflation_factor

warnings.filterwarnings("ignore")


class AnalisisError(Exception):
    """Error que el usuario puede corregir (datos o parámetros)."""


# --------------------------------------------------------------------------- catálogo
ETIQUETAS = {
    "edad": "Edad (años)",
    "horas_pantalla_dia": "Horas de pantalla (h/día)",
    "horas_redes_dia": "Horas en redes sociales (h/día)",
    "horas_videojuegos_dia": "Horas en videojuegos (h/día)",
    "min_celular_antes_dormir": "Celular antes de dormir (min)",
    "tazas_cafeina_dia": "Cafeína (tazas/día)",
    "horas_estudio_trabajo_dia": "Estudio o trabajo (h/día)",
    "horas_sueno_noche": "Horas de sueño por noche",
    "psqi_total": "PSQI total",
}
CORTAS = {
    "psqi_total": "PSQI",
    "horas_pantalla_dia": "Pantalla",
    "horas_redes_dia": "Redes",
    "horas_videojuegos_dia": "Videojuegos",
    "min_celular_antes_dormir": "Celular\nnocturno",
    "tazas_cafeina_dia": "Cafeína",
    "horas_estudio_trabajo_dia": "Estudio/\ntrabajo",
    "horas_sueno_noche": "Horas\nsueño",
}
REQUERIDAS = [
    "psqi_total", "horas_pantalla_dia", "min_celular_antes_dormir",
    "tazas_cafeina_dia", "horas_estudio_trabajo_dia", "sexo", "edad",
]
OPCIONALES = ["horas_redes_dia", "horas_videojuegos_dia", "horas_sueno_noche", "carrera", "ciclo", "id"]
USO = ["min_celular_antes_dormir", "horas_pantalla_dia", "horas_redes_dia", "horas_videojuegos_dia"]
CONTROL = ["tazas_cafeina_dia", "horas_estudio_trabajo_dia"]
NO_NEGATIVAS = [c for c in ETIQUETAS if c != "psqi_total"]

ETIQ_MODELO = {
    "Intercept": "Intercepto",
    "pre_sueno_10min": "Celular antes de dormir (+10 min)",
    "horas_pantalla_dia": "Horas de pantalla (+1 h/día)",
    "horas_estudio_trabajo_dia": "Estudio o trabajo (+1 h/día)",
    "tazas_cafeina_dia": "Cafeína (+1 taza/día)",
    "masculino": "Masculino (frente a femenino)",
    "edad": "Edad (+1 año)",
}
MAPA_SEXO = {
    "m": "Masculino", "masculino": "Masculino", "hombre": "Masculino", "varon": "Masculino",
    "varón": "Masculino", "h": "Masculino",
    "f": "Femenino", "femenino": "Femenino", "mujer": "Femenino",
}

AZUL, NARANJA, GRIS = "#2F5D8C", "#D9822B", "#6B7280"
plt.rcParams.update({
    "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "figure.dpi": 120, "savefig.bbox": "tight",
})


# --------------------------------------------------------------------------- validación
def validar(df_raw: pd.DataFrame, minimo_n: int = 30):
    """Devuelve (df_limpio, errores, avisos). Con errores no se debe analizar."""
    errores: list[str] = []
    avisos: list[str] = []
    df = df_raw.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    faltan = [c for c in REQUERIDAS if c not in df.columns]
    if faltan:
        errores.append("Faltan columnas obligatorias: " + ", ".join(faltan) + ".")
        return df, errores, avisos

    for c in [c for c in ETIQUETAS if c in df.columns]:
        if not pd.api.types.is_numeric_dtype(df[c]):  # texto, p. ej. «7,5» con coma decimal
            df[c] = df[c].astype(str).str.strip().str.replace(",", ".", regex=False)
        df[c] = pd.to_numeric(df[c], errors="coerce")

    orig = df["sexo"]
    s = orig.astype(str).str.strip().str.lower()
    mapeado = s.map(MAPA_SEXO)
    desconocidos = sorted(set(s[mapeado.isna() & orig.notna() & ~s.isin(["", "nan", "none"])]))
    df["sexo"] = mapeado
    if desconocidos:
        avisos.append("Valores de «sexo» no reconocidos (se excluyen esas filas): " + ", ".join(desconocidos)
                      + ". Usa Femenino o Masculino.")

    n0 = len(df)
    df = df.dropna(subset=REQUERIDAS).reset_index(drop=True)
    if n0 - len(df) > 0:
        avisos.append(f"Se excluyeron {n0 - len(df)} filas con valores vacíos o no numéricos en columnas obligatorias.")

    if len(df) < minimo_n:
        errores.append(f"Se necesitan al menos {minimo_n} filas completas; hay {len(df)}.")
        return df, errores, avisos
    if len(df) < 100:
        avisos.append(f"Muestra pequeña (n = {len(df)}): los resultados tendrán poca potencia.")

    if ((df["psqi_total"] < 0) | (df["psqi_total"] > 21)).any():
        errores.append("El PSQI total debe estar entre 0 y 21.")
    for c in NO_NEGATIVAS:
        if c in df.columns and (df[c] < 0).any():
            errores.append(f"«{c}» tiene valores negativos.")
    if (df["horas_pantalla_dia"] > 24).any():
        errores.append("«horas_pantalla_dia» no puede superar 24.")
    if ((df["edad"] < 10) | (df["edad"] > 100)).any():
        avisos.append("Hay edades fuera del rango 10–100 años; revísalas.")
    if {"horas_redes_dia", "horas_videojuegos_dia"} <= set(df.columns):
        incoh = int(((df["horas_redes_dia"] + df["horas_videojuegos_dia"]) > df["horas_pantalla_dia"] + 0.05).sum())
        if incoh:
            avisos.append(f"En {incoh} filas redes + videojuegos supera las horas totales de pantalla.")
    return df, errores, avisos


# --------------------------------------------------------------------------- utilidades
def _py(x):
    """Convierte a tipos nativos (None para NaN/inf) para poder serializar."""
    if isinstance(x, dict):
        return {str(k): _py(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_py(v) for v in x]
    if isinstance(x, np.ndarray):
        return [_py(v) for v in x.tolist()]
    if isinstance(x, (np.floating, float)):
        return float(x) if np.isfinite(x) else None
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


def _fisher_ci(r: float, n: int, conf: float = 0.95):
    z = np.arctanh(r)
    se = 1 / np.sqrt(n - 3)
    zc = stats.norm.ppf(0.5 + conf / 2)
    return float(np.tanh(z - zc * se)), float(np.tanh(z + zc * se))


def figuras_a_png(figs: dict, dpi: int = 200) -> dict[str, bytes]:
    """Renderiza cada figura a PNG (bytes) y la cierra."""
    out = {}
    for nombre, fig in figs.items():
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
        plt.close(fig)
        out[nombre] = buf.getvalue()
    return out


# --------------------------------------------------------------------------- análisis
def analizar(df: pd.DataFrame, umbral_noct: int = 30, corte_psqi: int = 5):
    df = df.copy().reset_index(drop=True)
    n = len(df)
    if df["psqi_total"].nunique() < 2:
        raise AnalisisError("El PSQI es constante: no hay variación que analizar.")
    for v in ("horas_pantalla_dia", "min_celular_antes_dormir"):
        if df[v].nunique() < 2:
            raise AnalisisError(f"«{v}» es constante: no se puede estimar su relación con el PSQI.")

    df["mala_calidad_sueno"] = (df["psqi_total"] > corte_psqi).astype(int)
    df["pre_sueno_10min"] = df["min_celular_antes_dormir"] / 10
    df["masculino"] = (df["sexo"] == "Masculino").astype(int)
    alto = (df["min_celular_antes_dormir"] >= umbral_noct).to_numpy()
    df["uso_nocturno_alto"] = alto

    presentes = [c for c in ETIQUETAS if c in df.columns]
    variables = [c for c in presentes if df[c].nunique() > 1]
    R: dict = {"n": n, "umbral_noct": int(umbral_noct), "corte_psqi": int(corte_psqi), "avisos": []}

    # ---- descriptivo
    desc = []
    for c in presentes:
        s = df[c]
        desc.append({
            "variable": c, "etiqueta": ETIQUETAS[c], "media": s.mean(), "de": s.std(), "mediana": s.median(),
            "min": s.min(), "max": s.max(), "asimetria": s.skew() if s.nunique() > 2 else np.nan,
        })
    R["descriptivo"] = desc
    R["n_mala"] = int(df["mala_calidad_sueno"].sum())
    R["pct_mala"] = round(100 * R["n_mala"] / n, 1)
    R["sexo"] = {k: int(v) for k, v in df["sexo"].value_counts().items()}
    R["edad_rango"] = [int(df["edad"].min()), int(df["edad"].max())]
    R["carreras"] = int(df["carrera"].nunique()) if "carrera" in df.columns else None

    # ---- normalidad
    R["shapiro"] = {}
    for v in ["psqi_total", "horas_pantalla_dia", "min_celular_antes_dormir", "horas_redes_dia", "horas_videojuegos_dia"]:
        if v in variables:
            w, p = stats.shapiro(df[v])
            R["shapiro"][v] = {"W": w, "p": p}

    # ---- correlaciones con el PSQI
    R["correlaciones"] = {}
    for v in USO + CONTROL:
        if v in variables:
            r, p = stats.pearsonr(df[v], df["psqi_total"])
            rho, ps = stats.spearmanr(df[v], df["psqi_total"])
            lo, hi = _fisher_ci(r, n)
            R["correlaciones"][v] = {"r": r, "p": p, "lo": lo, "hi": hi, "rho": rho, "p_rho": ps}

    # ---- dos grupos por uso nocturno
    g1 = df.loc[alto, "psqi_total"]
    g0 = df.loc[~alto, "psqi_total"]
    if len(g1) < 5 or len(g0) < 5:
        raise AnalisisError(
            f"Con un umbral de {umbral_noct} min quedan {len(g1)} estudiantes con uso alto y {len(g0)} con uso bajo; "
            "cada grupo necesita al menos 5. Cambia el umbral.")
    t, p_t = stats.ttest_ind(g1, g0, equal_var=False)
    u, p_u = stats.mannwhitneyu(g1, g0, alternative="two-sided")
    _, lev_p = stats.levene(g1, g0)
    n1, n0_ = len(g1), len(g0)
    sp = np.sqrt(((n1 - 1) * g1.var() + (n0_ - 1) * g0.var()) / (n1 + n0_ - 2))
    diff = g1.mean() - g0.mean()
    d = diff / sp if sp > 0 else 0.0
    se_d = np.sqrt((n1 + n0_) / (n1 * n0_) + d ** 2 / (2 * (n1 + n0_)))
    se_diff = np.sqrt(g1.var() / n1 + g0.var() / n0_)
    dfw = se_diff ** 4 / ((g1.var() / n1) ** 2 / (n1 - 1) + (g0.var() / n0_) ** 2 / (n0_ - 1))
    tc = stats.t.ppf(0.975, dfw)
    R["dos_grupos"] = {
        "n_alto": n1, "n_bajo": n0_, "media_alto": g1.mean(), "media_bajo": g0.mean(),
        "sd_alto": g1.std(), "sd_bajo": g0.std(), "diff": diff, "diff_lo": diff - tc * se_diff,
        "diff_hi": diff + tc * se_diff, "t": t, "gl": dfw, "p_t": p_t, "U": u, "p_u": p_u,
        "levene_p": lev_p, "d": d, "d_lo": d - 1.96 * se_d, "d_hi": d + 1.96 * se_d,
    }

    # ---- ANOVA por terciles de pantalla
    try:
        df["nivel_pantalla"] = pd.qcut(df["horas_pantalla_dia"], 3, labels=["Bajo", "Medio", "Alto"], duplicates="raise")
        cortes = pd.qcut(df["horas_pantalla_dia"], 3, retbins=True, duplicates="raise")[1]
    except ValueError:
        raise AnalisisError("Las horas de pantalla tienen demasiados valores repetidos para formar terciles.")
    niveles = ["Bajo", "Medio", "Alto"]
    grupos = [df.loc[df["nivel_pantalla"] == k, "psqi_total"] for k in niveles]
    F, p_F = stats.f_oneway(*grupos)
    H, p_H = stats.kruskal(*grupos)
    _, lev3_p = stats.levene(*grupos)
    ss_b = sum(len(g) * (g.mean() - df["psqi_total"].mean()) ** 2 for g in grupos)
    ss_t = ((df["psqi_total"] - df["psqi_total"].mean()) ** 2).sum()
    tuk = pairwise_tukeyhsd(df["psqi_total"], df["nivel_pantalla"].astype(str))
    orden = {k: i for i, k in enumerate(niveles)}
    pares = []
    for fila in tuk._results_table.data[1:]:
        g_a, g_b, md, p_adj, lo, hi, rej = fila
        md, p_adj, lo, hi = float(md), float(p_adj), float(lo), float(hi)
        if orden[g_a] > orden[g_b]:
            g_a, g_b, md, lo, hi = g_b, g_a, -md, -hi, -lo
        pares.append({"a": g_a, "b": g_b, "diff": md, "lo": lo, "hi": hi, "p": p_adj, "rechaza": bool(rej)})
    pares.sort(key=lambda x: (orden[x["a"]], orden[x["b"]]))
    R["anova"] = {
        "cortes": [float(c) for c in cortes],
        "niveles": [{"nivel": k, "n": len(g), "media": g.mean(), "de": g.std()} for k, g in zip(niveles, grupos)],
        "F": F, "p": p_F, "gl1": 2, "gl2": n - 3, "eta2": ss_b / ss_t, "H": H, "p_H": p_H, "levene_p": lev3_p,
        "tukey": pares,
    }

    # ---- chi-cuadrado, OR y Fisher
    mala = df["mala_calidad_sueno"].to_numpy() == 1
    a = int((alto & mala).sum()); b = int((alto & ~mala).sum())
    c = int((~alto & mala).sum()); d_ = int((~alto & ~mala).sum())
    tabla = np.array([[d_, c], [b, a]])  # filas: uso bajo, alto; columnas: buena, mala calidad
    R["chi2"] = None
    if tabla.sum(axis=0).min() == 0 or tabla.sum(axis=1).min() == 0:
        R["avisos"].append("No hay estudiantes en una de las categorías de calidad de sueño; "
                           "se omiten el chi-cuadrado y la regresión logística.")
    else:
        chi2, p_chi, gl, esp = stats.chi2_contingency(tabla, correction=False)
        corregido = bool(min(a, b, c, d_) == 0)
        aa, bb, cc, dd = (x + 0.5 for x in (a, b, c, d_)) if corregido else (a, b, c, d_)
        or_ = (aa * dd) / (bb * cc)
        se_lor = np.sqrt(1 / aa + 1 / bb + 1 / cc + 1 / dd)
        _, p_fisher = stats.fisher_exact(tabla)
        R["chi2"] = {
            "tabla": {"bajo": {"buena": d_, "mala": c}, "alto": {"buena": b, "mala": a}},
            "chi2": chi2, "gl": int(gl), "p": p_chi, "v": float(np.sqrt(chi2 / (n * (min(tabla.shape) - 1)))),
            "min_esperado": float(esp.min()), "p_fisher": p_fisher, "OR": or_, "or_corregido": corregido,
            "or_lo": float(np.exp(np.log(or_) - 1.96 * se_lor)), "or_hi": float(np.exp(np.log(or_) + 1.96 * se_lor)),
            "pct_mala_alto": 100 * a / (a + b), "pct_mala_bajo": 100 * c / (c + d_),
        }

    # ---- regresión lineal múltiple
    candidatos = ["horas_pantalla_dia", "pre_sueno_10min", "tazas_cafeina_dia",
                  "horas_estudio_trabajo_dia", "masculino", "edad"]
    preds = [v for v in candidatos if df[v].nunique() > 1]
    omitidos = [v for v in candidatos if v not in preds]
    if omitidos:
        R["avisos"].append("Se omitieron del modelo por ser constantes: " + ", ".join(omitidos) + ".")
    formula = "psqi_total ~ " + " + ".join(preds)
    ols = smf.ols(formula, data=df).fit()
    ci = ols.conf_int()
    exog = ols.model.exog
    vif = {ols.model.exog_names[i]: float(variance_inflation_factor(exog, i)) for i in range(1, exog.shape[1])}
    _, bp_p, _, _ = het_breuschpagan(ols.resid, exog)
    sw_w, sw_p = stats.shapiro(ols.resid)
    z = df[["psqi_total"] + preds].apply(lambda s: (s - s.mean()) / s.std())
    beta_std = smf.ols(formula, data=z).fit().params.drop("Intercept")
    R["ols"] = {
        "formula": formula, "r2": ols.rsquared, "r2_adj": ols.rsquared_adj, "F": ols.fvalue, "p": ols.f_pvalue,
        "gl1": int(ols.df_model), "gl2": int(ols.df_resid), "n": int(ols.nobs),
        "coef": {k: {"b": ols.params[k], "se": ols.bse[k], "p": ols.pvalues[k], "lo": ci.loc[k, 0], "hi": ci.loc[k, 1],
                     "beta": (float(beta_std[k]) if k in beta_std.index else None)} for k in ols.params.index},
        "vif": vif, "vif_max": max(vif.values()) if vif else None, "bp_p": bp_p,
        "sw_w": sw_w, "sw_p": sw_p, "dw": float(sm.stats.durbin_watson(ols.resid)),
    }

    # ---- regresión logística
    R["logit"] = None
    logit = None
    if R["chi2"] is not None:
        try:
            logit = smf.logit("mala_calidad_sueno ~ " + " + ".join(preds), data=df).fit(disp=0, maxiter=200)
            if (not logit.mle_retvals.get("converged", True)) or (logit.params.abs() > 20).any() or (logit.bse > 1e3).any():
                raise ValueError("separación o no convergencia")
        except Exception:
            logit = None
            R["avisos"].append("La regresión logística no convergió (posible separación perfecta); se omite.")
    if logit is not None:
        lci = logit.conf_int()
        y = df["mala_calidad_sueno"].to_numpy()
        pred = logit.predict(df).to_numpy()
        ranks = stats.rankdata(pred)
        n_pos, n_neg = int(y.sum()), int((1 - y).sum())
        auc = (ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
        R["logit"] = {
            "pseudo_r2": logit.prsquared, "p": logit.llr_pvalue, "n": int(logit.nobs), "auc": float(auc),
            "gl": int(logit.df_model),
            "OR": {k: {"or": float(np.exp(logit.params[k])), "lo": float(np.exp(lci.loc[k, 0])),
                       "hi": float(np.exp(lci.loc[k, 1])), "p": logit.pvalues[k]}
                   for k in logit.params.index if k != "Intercept"},
        }

    # ---- potencia y versiones
    R["r_minimo_detectable"] = float(np.tanh((1.959964 + 0.841621) / np.sqrt(n - 3)))
    R["versiones"] = {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                      "scipy": scipy.__version__, "statsmodels": statsmodels.__version__}

    figs = _figuras(df, R, ols, cortes, niveles, grupos, variables)
    return _py(R), figs


# --------------------------------------------------------------------------- figuras
def _figuras(df, R, ols, cortes, niveles, grupos, variables):
    figs = {}
    corte = R["corte_psqi"]
    u = R["umbral_noct"]

    # F1: distribuciones
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    psqi = df["psqi_total"]
    ax[0].hist(psqi, bins=np.arange(-0.5, psqi.max() + 1.5, 1), color=AZUL, edgecolor="white")
    ax[0].axvline(corte + 0.5, color=NARANJA, ls="--", lw=2, label=f"Punto de corte (PSQI > {corte})")
    ax[0].legend(frameon=False, loc="upper right", fontsize=9)
    ax[0].set(title="Calidad del sueño (PSQI)", xlabel="Puntaje PSQI (más alto = peor)", ylabel="Estudiantes")
    ax[1].hist(df["horas_pantalla_dia"], bins=14, color=AZUL, edgecolor="white")
    ax[1].axvline(df["horas_pantalla_dia"].mean(), color=NARANJA, ls="--", lw=2, label="Promedio")
    ax[1].legend(frameon=False, loc="upper right", fontsize=9)
    ax[1].set(title="Uso diario de pantallas", xlabel="Horas por día", ylabel="Estudiantes")
    figs["f1_distribuciones"] = fig

    # F2 / F3: dispersión
    for nombre, var, titulo, xlabel in (
        ("f2_dispersion_pantalla", "horas_pantalla_dia", "Horas de pantalla y calidad del sueño", "Horas de pantalla por día"),
        ("f3_dispersion_nocturno", "min_celular_antes_dormir", "Uso del celular antes de dormir", "Minutos de uso en la última hora"),
    ):
        fig, ax = plt.subplots(figsize=(6.2, 4.4))
        ax.scatter(df[var], psqi, s=26, alpha=0.55, color=AZUL, edgecolor="none")
        sl = stats.linregress(df[var], psqi)
        xs = np.linspace(df[var].min(), df[var].max(), 100)
        ax.plot(xs, sl.intercept + sl.slope * xs, color=NARANJA, lw=2.4)
        ax.text(0.04, 0.95, f"r = {R['correlaciones'][var]['r']:.2f}".replace("-", "−"),
                transform=ax.transAxes, va="top", fontsize=10)
        ax.set(title=titulo, xlabel=xlabel, ylabel="PSQI (más alto = peor)")
        figs[nombre] = fig

    # F4: caja por tercil
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    etiquetas = [f"Bajo\n(≤{cortes[1]:.1f} h)", f"Medio\n({cortes[1]:.1f}–{cortes[2]:.1f} h)", f"Alto\n(>{cortes[2]:.1f} h)"]
    bp = ax.boxplot(grupos, tick_labels=etiquetas, patch_artist=True, medianprops=dict(color="white", lw=2), widths=0.55)
    for patch, col in zip(bp["boxes"], ["#8FB0D1", AZUL, "#1F3F5E"]):
        patch.set_facecolor(col)
    ax.set(title="PSQI según nivel de uso de pantallas", xlabel="Tercil de horas de pantalla", ylabel="PSQI (más alto = peor)")
    figs["f4_boxplot_terciles"] = fig

    # F5: barras chi-cuadrado
    if R["chi2"] is not None:
        fig, ax = plt.subplots(figsize=(5.2, 4.2))
        vals = [R["chi2"]["pct_mala_bajo"], R["chi2"]["pct_mala_alto"]]
        barras = ax.bar([f"<{u} min", f"≥{u} min"], vals, color=[AZUL, NARANJA], width=0.55)
        for b_, v_ in zip(barras, vals):
            ax.text(b_.get_x() + b_.get_width() / 2, v_ + 1.2, f"{v_:.1f}%", ha="center", fontweight="bold")
        ax.set(title="Mala calidad de sueño según uso nocturno", xlabel="Uso del celular antes de dormir",
               ylabel=f"% con PSQI > {corte}", ylim=(0, max(vals) + 15))
        figs["f5_barras_chi2"] = fig

    # F6: matriz de correlación (Spearman)
    cols = [c for c in CORTAS if c in variables]
    cm = df[cols].corr(method="spearman")
    fig, ax = plt.subplots(figsize=(6.6, 5.6))
    im = ax.imshow(cm, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(cols))); ax.set_xticklabels([CORTAS[c] for c in cols], rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(cols))); ax.set_yticklabels([CORTAS[c] for c in cols], fontsize=9)
    for i in range(len(cols)):
        for j in range(len(cols)):
            ax.text(j, i, f"{cm.iloc[i, j]:.2f}".replace("-", "−"), ha="center", va="center", fontsize=8,
                    color="white" if abs(cm.iloc[i, j]) > 0.55 else "black")
    ax.spines[:].set_visible(False)
    fig.colorbar(im, shrink=0.8, label="Spearman ρ")
    ax.set_title("Matriz de correlación (Spearman)")
    figs["f6_correlaciones"] = fig

    # F7: diagnóstico de residuos
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    sm.qqplot(ols.resid, line="s", ax=ax[0], markerfacecolor=AZUL, markeredgecolor="none", alpha=0.6)
    ax[0].get_lines()[1].set_color(NARANJA)
    ax[0].set_title("Q-Q de residuos")
    ax[1].scatter(ols.fittedvalues, ols.resid, s=22, alpha=0.55, color=AZUL, edgecolor="none")
    ax[1].axhline(0, color=NARANJA, lw=2)
    ax[1].set(title="Residuos vs. valores ajustados", xlabel="Valores ajustados", ylabel="Residuo")
    figs["f7_residuos"] = fig

    # F8: odds ratio ajustados
    if R["logit"] is not None:
        orr = R["logit"]["OR"]
        claves = list(orr.keys())
        fig, ax = plt.subplots(figsize=(7.2, 3.8))
        for i, k in enumerate(claves[::-1]):
            o = orr[k]
            col = NARANJA if (o["lo"] > 1 or o["hi"] < 1) else GRIS
            ax.plot([o["lo"], o["hi"]], [i, i], color=col, lw=2.2)
            ax.plot(o["or"], i, "o", color=col, ms=7)
        ax.axvline(1, color="black", lw=1, ls="--")
        ax.set_yticks(range(len(claves)))
        ax.set_yticklabels([ETIQ_MODELO.get(k, k) for k in claves[::-1]])
        ax.set_xscale("log")
        lo_x = min(o["lo"] for o in orr.values()) * 0.9
        hi_x = max(o["hi"] for o in orr.values()) * 1.1
        ticks = [t for t in (0.1, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 5, 10) if lo_x <= t <= hi_x]
        ax.xaxis.set_minor_locator(mticker.NullLocator())
        ax.set_xticks(ticks)
        ax.set_xticklabels([f"{t:g}" for t in ticks])
        ax.set_xlim(lo_x, hi_x)
        ax.set(title="Odds ratio ajustados (IC 95%) — mala calidad de sueño", xlabel="Odds ratio (escala logarítmica)")
        figs["f8_forest_or"] = fig
    return figs
