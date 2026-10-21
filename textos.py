"""
Textos de interpretación y tablas, generados a partir de los resultados.

Cada afirmación depende de los valores calculados (significancia, signo,
magnitud), de modo que el informe sigue siendo correcto si cambian los datos.
Los textos usan Unicode y marcado ligero (**negrita**, *cursiva*): se muestran
tal cual en Streamlit y `informe.py` los convierte a LaTeX.
"""
from __future__ import annotations

import pandas as pd

from analisis import CONTROL, ETIQ_MODELO, ETIQUETAS, USO

ALFA = 0.05

NOMBRE = {
    "min_celular_antes_dormir": "el uso del celular antes de dormir",
    "horas_pantalla_dia": "las horas diarias de pantalla",
    "horas_redes_dia": "las horas en redes sociales",
    "horas_videojuegos_dia": "las horas en videojuegos",
    "tazas_cafeina_dia": "el consumo de cafeína",
    "horas_estudio_trabajo_dia": "las horas de estudio o trabajo",
}
NOMBRE_CTRL = {
    "tazas_cafeina_dia": "la cafeína",
    "horas_estudio_trabajo_dia": "el tiempo de estudio o trabajo",
    "masculino": "el sexo",
    "edad": "la edad",
}
# variable de la correlación -> nombre del término en el modelo
A_MODELO = {"min_celular_antes_dormir": "pre_sueno_10min", "horas_pantalla_dia": "horas_pantalla_dia"}

DESC_VARIABLES = {
    "psqi_total": ("Discreta (0 a 21)", "Calidad de sueño; más alto es peor. Un puntaje mayor que {corte} se clasifica como mala calidad (Buysse et al., 1989)."),
    "horas_pantalla_dia": ("Continua (h/día)", "Uso total diario de dispositivos con pantalla."),
    "horas_redes_dia": ("Continua (h/día)", "Tiempo diario en redes sociales."),
    "horas_videojuegos_dia": ("Continua (h/día)", "Tiempo diario en videojuegos."),
    "min_celular_antes_dormir": ("Continua (min)", "Minutos de uso del celular en la última hora antes de dormir."),
    "tazas_cafeina_dia": ("Discreta (tazas/día)", "Consumo de cafeína (variable de control)."),
    "horas_estudio_trabajo_dia": ("Continua (h/día)", "Horas de estudio o trabajo (variable de control)."),
    "horas_sueno_noche": ("Continua (h)", "Horas de sueño por noche."),
    "sexo": ("Categórica", "Femenino o masculino (variable de control)."),
    "edad": ("Discreta (años)", "Edad en años cumplidos (variable de control)."),
}

PIES = {
    "f1_distribuciones": "Distribución del PSQI (izquierda) y de las horas diarias de pantalla (derecha).",
    "f2_dispersion_pantalla": "Horas de pantalla y PSQI, con la recta de regresión simple.",
    "f3_dispersion_nocturno": "Uso del celular antes de dormir y PSQI, con la recta de regresión simple.",
    "f4_boxplot_terciles": "PSQI según tercil de horas diarias de pantalla.",
    "f5_barras_chi2": "Porcentaje de estudiantes con mala calidad de sueño según el uso nocturno del celular.",
    "f6_correlaciones": "Matriz de correlación de Spearman entre las variables del estudio.",
    "f7_residuos": "Gráfico Q-Q de los residuos (izquierda) y residuos frente a valores ajustados (derecha).",
    "f8_forest_or": "Odds ratio ajustados de mala calidad de sueño. Los intervalos que no cruzan 1 aparecen en naranja.",
}


# --------------------------------------------------------------------------- formato
def f(x, d: int = 2) -> str:
    """Número con d decimales y signo menos tipográfico; None -> raya."""
    if x is None:
        return "—"
    return f"{x:.{d}f}".replace("-", "−")


def p_tabla(p) -> str:
    if p is None:
        return "—"
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def P(p) -> str:
    """Valor p para texto corrido, con p en cursiva."""
    if p is None:
        return "*p* = —"
    return "*p* < 0.001" if p < 0.001 else f"*p* = {p:.3f}"


def sig(p) -> bool:
    return p is not None and p < ALFA


def lista(items: list[str]) -> str:
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " y " + items[-1]


def cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def mag_r(r: float) -> str:
    a = abs(r)
    return "despreciable" if a < 0.10 else "baja" if a < 0.30 else "moderada" if a < 0.50 else "alta"


def mag_d(d: float) -> str:
    a = abs(d)
    return "muy pequeño" if a < 0.2 else "pequeño" if a < 0.5 else "mediano" if a < 0.8 else "grande"


def mag_eta(e: float) -> str:
    return "despreciable" if e < 0.01 else "pequeño" if e < 0.06 else "mediano" if e < 0.14 else "grande"


def mag_v(v: float) -> str:
    return "muy pequeño" if v < 0.1 else "pequeño" if v < 0.3 else "mediano" if v < 0.5 else "grande"


def mag_auc(a: float) -> str:
    return "pobre" if a < 0.6 else "limitada" if a < 0.7 else "aceptable" if a < 0.8 else "buena" if a < 0.9 else "excelente"


def _concuerdan(nom_a, txt_a, sig_a, nom_b, txt_b, sig_b) -> str:
    if sig_a and sig_b:
        return f"es significativa según {nom_a}, {txt_a}, y según {nom_b}, {txt_b}"
    if not sig_a and not sig_b:
        return f"no es significativa ni según {nom_a}, {txt_a}, ni según {nom_b}, {txt_b}"
    s, ns = (nom_a, nom_b) if sig_a else (nom_b, nom_a)
    ts, tn = (txt_a, txt_b) if sig_a else (txt_b, txt_a)
    return f"es significativa según {s}, {ts}, pero no según {ns}, {tn}"


# --------------------------------------------------------------------------- tablas
def tablas(R: dict) -> dict[str, pd.DataFrame]:
    T: dict[str, pd.DataFrame] = {}
    T["descriptivo"] = pd.DataFrame(
        [[d["etiqueta"], f(d["media"]), f(d["de"]), f(d["mediana"]), f(d["min"], 1), f(d["max"], 1)]
         for d in R["descriptivo"]],
        columns=["Variable", "Media", "DE", "Mediana", "Mín.", "Máx."])

    filas = []
    for v, c in sorted(R["correlaciones"].items(), key=lambda kv: -abs(kv[1]["r"])):
        filas.append([ETIQUETAS[v], f"{f(c['r'], 3)} ({f(c['lo'], 3)} a {f(c['hi'], 3)})", p_tabla(c["p"]),
                      f(c["rho"], 3), p_tabla(c["p_rho"])])
    T["correlaciones"] = pd.DataFrame(
        filas, columns=["Variable", "r de Pearson (IC 95 %)", "p", "ρ de Spearman", "p (ρ)"])

    an = R["anova"]
    T["terciles"] = pd.DataFrame(
        [[x["nivel"], x["n"], f(x["media"]), f(x["de"])] for x in an["niveles"]],
        columns=["Nivel de pantalla", "n", "PSQI medio", "DE"])
    T["tukey"] = pd.DataFrame(
        [[f"{x['a']} frente a {x['b'].lower()}", f(x["diff"]), f"{f(x['lo'])} a {f(x['hi'])}", p_tabla(x["p"])]
         for x in an["tukey"]],
        columns=["Comparación", "Diferencia de medias", "IC 95 %", "p ajustado"])

    ch = R["chi2"]
    if ch:
        u, c = R["umbral_noct"], R["corte_psqi"]
        T["chi2"] = pd.DataFrame(
            [[f"Menos de {u} min", ch["tabla"]["bajo"]["buena"], ch["tabla"]["bajo"]["mala"], f"{ch['pct_mala_bajo']:.1f} %"],
             [f"{u} min o más", ch["tabla"]["alto"]["buena"], ch["tabla"]["alto"]["mala"], f"{ch['pct_mala_alto']:.1f} %"]],
            columns=["Celular antes de dormir", f"Buena (PSQI ≤ {c})", f"Mala (PSQI > {c})", "% con mala calidad"])

    ols = R["ols"]
    orden = sorted(ols["coef"], key=lambda k: (k == "Intercept", -abs(ols["coef"][k]["beta"] or 0)))
    T["ols"] = pd.DataFrame(
        [[ETIQ_MODELO.get(k, k), f(ols["coef"][k]["b"], 3), f(ols["coef"][k]["se"], 3),
          f"{f(ols['coef'][k]['lo'], 3)} a {f(ols['coef'][k]['hi'], 3)}", p_tabla(ols["coef"][k]["p"]),
          f(ols["coef"][k]["beta"], 3)] for k in orden],
        columns=["Variable", "b", "Error estándar", "IC 95 %", "p", "β estandarizado"])

    if R["logit"]:
        T["logit"] = pd.DataFrame(
            [[ETIQ_MODELO.get(k, k), f(o["or"]), f"{f(o['lo'])} a {f(o['hi'])}", p_tabla(o["p"])]
             for k, o in R["logit"]["OR"].items()],
            columns=["Variable", "Odds ratio", "IC 95 %", "p"])

    T["supuestos"] = pd.DataFrame(supuestos(R), columns=["Supuesto", "Prueba", "Resultado", "Conclusión"])
    return T


def supuestos(R: dict) -> list[list[str]]:
    o = R["ols"]
    filas = []
    if o["vif_max"] is not None:
        filas.append(["Sin multicolinealidad", "VIF máximo", f(o["vif_max"]),
                      "Se cumple" if o["vif_max"] < 5 else "Posible multicolinealidad"])
    filas.append(["Varianza constante", "Breusch-Pagan", f"p = {p_tabla(o['bp_p'])}",
                  "Se cumple" if o["bp_p"] >= ALFA else "No se cumple (heterocedasticidad)"])
    filas.append(["Errores independientes", "Durbin-Watson", f(o["dw"]),
                  "Se cumple" if 1.5 <= o["dw"] <= 2.5 else "Posible autocorrelación"])
    ok = o["sw_p"] >= ALFA
    filas.append(["Normalidad de residuos", "Shapiro-Wilk", f"W = {f(o['sw_w'], 3)}; p = {p_tabla(o['sw_p'])}",
                  "Se cumple" if ok else ("Desviación leve, tolerable con n ≥ 100" if o["n"] >= 100 else "Desviación; interpretar con cautela")])
    return filas


# --------------------------------------------------------------------------- textos
def construir(R: dict, meta: dict) -> dict:
    """Devuelve los párrafos de interpretación (listas de str con marcado ligero)."""
    n = R["n"]
    corr = R["correlaciones"]
    ols, lg, ch, dg, an = R["ols"], R["logit"], R["chi2"], R["dos_grupos"], R["anova"]
    u, corte = R["umbral_noct"], R["corte_psqi"]
    simulados = bool(meta.get("simulados"))
    T: dict = {}

    # variables de uso significativas (asociación simple)
    sig_pos = sorted([v for v in USO if v in corr and sig(corr[v]["p"]) and corr[v]["r"] > 0], key=lambda v: -abs(corr[v]["r"]))
    sig_neg = sorted([v for v in USO if v in corr and sig(corr[v]["p"]) and corr[v]["r"] < 0], key=lambda v: -abs(corr[v]["r"]))
    controles = [NOMBRE_CTRL[k] for k in ("tazas_cafeina_dia", "horas_estudio_trabajo_dia", "masculino", "edad") if k in ols["coef"]]
    ctrl_txt = lista(controles)
    # términos del modelo significativos entre los dos de uso principal
    mod_sig = {v: sig(ols["coef"][A_MODELO[v]]["p"]) for v in A_MODELO if A_MODELO[v] in ols["coef"]}

    # ---- resumen
    muestra = f"En una muestra {'simulada ' if simulados else ''}de {n} estudiantes, "
    if sig_pos or sig_neg:
        partes = []
        if sig_pos:
            partes.append(lista([f"{NOMBRE[v]} (*r* = {f(corr[v]['r'])})" for v in sig_pos])
                          + (" se asocia" if len(sig_pos) == 1 else " se asocian") + " con peor calidad de sueño")
        if sig_neg:
            partes.append(lista([f"{NOMBRE[v]} (*r* = {f(corr[v]['r'])})" for v in sig_neg])
                          + (" se asocia" if len(sig_neg) == 1 else " se asocian") + " con mejor calidad de sueño")
        txt = muestra + "; ".join(partes)
        base = [v for v in sig_pos + sig_neg if v in mod_sig]
        if base and ctrl_txt:
            nb = lista([NOMBRE[v] for v in base])
            if all(mod_sig[v] for v in base):
                txt += f", y la asociación de {nb} se mantiene al controlar por {ctrl_txt}."
            elif any(mod_sig[v] for v in base):
                conserva = [NOMBRE[v] for v in base if mod_sig[v]]
                txt += f". Al controlar por {ctrl_txt}, solo {lista(conserva)} conserva una asociación significativa."
            else:
                txt += f". Al controlar por {ctrl_txt}, la asociación de {nb} deja de ser significativa."
        else:
            txt += "."
    else:
        txt = (muestra + "no se encontró una asociación estadísticamente significativa entre el uso de tecnologías "
               "digitales y la calidad del sueño (α = 0.05).")
    T["resumen"] = txt

    # ---- descriptivo y normalidad
    ps = next(d for d in R["descriptivo"] if d["variable"] == "psqi_total")
    pan = next(d for d in R["descriptivo"] if d["variable"] == "horas_pantalla_dia")
    T["descriptivo"] = (f"El {R['pct_mala']:.1f} % de la muestra ({R['n_mala']} de {n} estudiantes) tiene mala calidad de sueño "
                        f"(PSQI > {corte}); el PSQI promedio es {f(ps['media'])} (DE = {f(ps['de'])}) y el uso promedio de "
                        f"pantallas es {f(pan['media'])} horas al día.")
    sw = R["shapiro"]
    rech = [v for v in sw if sig(sw[v]["p"])]
    nom = lambda v: f"{NOMBRE.get(v, 'el PSQI')} (*W* = {f(sw[v]['W'], 3)}, {P(sw[v]['p'])})" if v != "psqi_total" else f"el PSQI (*W* = {f(sw[v]['W'], 3)}, {P(sw[v]['p'])})"
    if rech:
        norm = f"La prueba de Shapiro-Wilk rechaza la normalidad de {lista([nom(v) for v in rech])}."
        if len(rech) < len(sw):
            norm += f" No la rechaza para {lista([nom(v) for v in sw if v not in rech])}."
        norm += " Por eso cada prueba paramétrica se acompaña de su alternativa no paramétrica."
    else:
        norm = ("La prueba de Shapiro-Wilk no rechaza la normalidad de las variables evaluadas; aun así, cada prueba "
                "paramétrica se acompaña de su alternativa no paramétrica.")
    asim = [d for d in R["descriptivo"] if d["variable"] in NOMBRE and d["asimetria"] is not None and abs(d["asimetria"]) > 1]
    if asim:
        norm += " Presentan asimetría marcada: " + lista([f"{NOMBRE[d['variable']]} (asimetría = {f(d['asimetria'])})" for d in asim]) + "."
    T["normalidad"] = norm

    # ---- correlaciones
    sig_c = [v for v in corr if sig(corr[v]["p"])]
    if not sig_c:
        c1 = "Ninguna correlación con el PSQI alcanza significancia estadística."
    else:
        signos = {corr[v]["r"] > 0 for v in sig_c}
        mags = sorted({mag_r(corr[v]["r"]) for v in sig_c})
        sentido = ("positivas (a mayor valor, peor calidad de sueño)" if signos == {True}
                   else "negativas (a mayor valor, mejor calidad de sueño)" if signos == {False}
                   else "de signo mixto")
        c1 = f"Las correlaciones significativas son {sentido} y de magnitud {lista(mags)}."
    disc = [v for v in corr if sig(corr[v]["p"]) != sig(corr[v]["p_rho"])]
    c2 = ("Pearson y Spearman coinciden en qué variables son significativas, así que las desviaciones de la normalidad "
          "no cambian la conclusión." if not disc else
          f"Pearson y Spearman difieren para {lista([NOMBRE[v] for v in disc])}; en esos casos se prefiere Spearman, "
          "que no supone normalidad.")
    T["correlaciones"] = c1 + " " + c2

    # ---- dos grupos
    ct = _concuerdan("la t de Welch", f"*t*({f(dg['gl'], 1)}) = {f(dg['t'])}, {P(dg['p_t'])}", sig(dg["p_t"]),
                     "Mann-Whitney", f"*U* = {dg['U']:.0f}, {P(dg['p_u'])}", sig(dg["p_u"]))
    T["dos_grupos"] = (
        f"Los estudiantes que usan el celular {u} minutos o más antes de dormir (*n* = {dg['n_alto']}) tienen un PSQI promedio "
        f"de {f(dg['media_alto'])} (DE = {f(dg['sd_alto'])}), frente a {f(dg['media_bajo'])} (DE = {f(dg['sd_bajo'])}) de quienes "
        f"lo usan menos de {u} minutos (*n* = {dg['n_bajo']}). La diferencia entre grupos (alto menos bajo) es de {f(dg['diff'])} "
        f"puntos (IC 95 %: {f(dg['diff_lo'])} a {f(dg['diff_hi'])}) y {ct}. El tamaño del efecto es {mag_d(dg['d'])} "
        f"(*d* de Cohen = {f(dg['d'])}; IC 95 %: {f(dg['d_lo'])} a {f(dg['d_hi'])}). Las varianzas "
        f"{'son similares' if dg['levene_p'] >= ALFA else 'difieren'} (Levene, {P(dg['levene_p'])}).")

    # ---- ANOVA
    c1_, c2_ = an["cortes"][1], an["cortes"][2]
    t_ = {(x["a"], x["b"]): x for x in an["tukey"]}
    medias = [x["media"] for x in an["niveles"]]
    txt = (f"Se formaron terciles de horas de pantalla: bajo (hasta {f(c1_, 1)} h), medio ({f(c1_, 1)} a {f(c2_, 1)} h) y alto "
           f"(más de {f(c2_, 1)} h). El PSQI {'difiere' if sig(an['p']) else 'no difiere'} entre los tres niveles: "
           f"ANOVA *F*({an['gl1']}, {an['gl2']}) = {f(an['F'])}, {P(an['p'])}, η² = {f(an['eta2'], 3)} (efecto {mag_eta(an['eta2'])}); "
           f"Kruskal-Wallis *H* = {f(an['H'])}, {P(an['p_H'])}; homogeneidad de varianzas con Levene {P(an['levene_p'])}.")
    if sig(an["p"]):
        def par(x): return f"{x['a'].lower()} frente a {x['b'].lower()} (diferencia = {f(x['diff'])}; {P(x['p'])})"
        s_, n_ = [x for x in an["tukey"] if x["p"] < ALFA], [x for x in an["tukey"] if x["p"] >= ALFA]
        txt += " En la prueba de Tukey, "
        txt += f"difieren {lista([par(x) for x in s_])}"
        txt += (f"; no difieren {lista([par(x) for x in n_])}." if n_ else ".")
        bm, ba, ma = t_[("Bajo", "Medio")], t_[("Bajo", "Alto")], t_[("Medio", "Alto")]
        if bm["p"] < ALFA and ba["p"] < ALFA and ma["p"] >= ALFA and medias[0] < medias[1]:
            txt += " La diferencia se concentra entre el uso bajo y el resto, sin un aumento adicional claro entre medio y alto."
        elif all(x["p"] < ALFA for x in an["tukey"]) and medias[0] < medias[1] < medias[2]:
            txt += " El PSQI aumenta de forma progresiva con el nivel de uso."
    else:
        txt += " La prueba de Tukey no se interpreta porque el ANOVA no es significativo."
    T["anova"] = txt

    # ---- chi-cuadrado
    if ch:
        t = (f"{'Existe' if sig(ch['p']) else 'No existe'} asociación estadísticamente significativa entre el uso nocturno y la mala "
             f"calidad de sueño: χ²({ch['gl']}) = {f(ch['chi2'])}, {P(ch['p'])}, *V* de Cramér = {f(ch['v'], 3)} (efecto {mag_v(ch['v'])}). "
             f"Tiene mala calidad de sueño el {ch['pct_mala_alto']:.1f} % de los estudiantes con uso nocturno de {u} minutos o más, "
             f"frente al {ch['pct_mala_bajo']:.1f} % de los demás. El odds ratio es {f(ch['OR'])} (IC 95 %: {f(ch['or_lo'])} a {f(ch['or_hi'])}): "
             f"las probabilidades (odds) de mala calidad de sueño con uso nocturno alto son {f(ch['OR'])} veces las del grupo con uso bajo.")
        if ch["or_corregido"]:
            t += " Como una celda tiene frecuencia cero, el odds ratio se calculó con la corrección de Haldane-Anscombe (+0.5)."
        if ch["min_esperado"] >= 5:
            t += f" Todas las frecuencias esperadas superan 5 (mínima = {f(ch['min_esperado'], 1)}), por lo que se cumple el supuesto de la prueba."
        else:
            t += (f" Alguna frecuencia esperada es menor que 5 (mínima = {f(ch['min_esperado'], 1)}), por lo que no se cumple el supuesto "
                  f"del chi-cuadrado; la prueba exacta de Fisher da {P(ch['p_fisher'])}.")
        T["chi2"] = t
    else:
        T["chi2"] = "No se pudo calcular el chi-cuadrado porque no hay estudiantes en una de las categorías de calidad de sueño."

    # ---- regresión lineal
    T["ols_resumen"] = (f"El modelo {'es' if sig(ols['p']) else 'no es'} significativo, *F*({ols['gl1']}, {ols['gl2']}) = {f(ols['F'])}, {P(ols['p'])}, "
                        f"y explica el {100 * ols['r2']:.1f} % de la variabilidad del PSQI (*R*² ajustado = {100 * ols['r2_adj']:.1f} %).")
    partes = []
    if "horas_pantalla_dia" in ols["coef"]:
        c = ols["coef"]["horas_pantalla_dia"]
        partes.append(f"cada hora adicional de pantalla se asocia con {f(abs(c['b']))} puntos {'más' if c['b'] > 0 else 'menos'} de PSQI ({P(c['p'])})"
                      if sig(c["p"]) else f"las horas de pantalla no muestran una asociación significativa con el PSQI ({P(c['p'])})")
    if "pre_sueno_10min" in ols["coef"]:
        c = ols["coef"]["pre_sueno_10min"]
        partes.append(f"cada 10 minutos adicionales de uso nocturno se asocian con {f(abs(c['b']))} puntos {'más' if c['b'] > 0 else 'menos'} de PSQI ({P(c['p'])})"
                      if sig(c["p"]) else f"el uso nocturno no muestra una asociación significativa con el PSQI ({P(c['p'])})")
    efectos = "Manteniendo las demás variables constantes, " + "; ".join(partes) + "." if partes else ""
    ctrl_sig = [NOMBRE_CTRL[k] for k in NOMBRE_CTRL if k in ols["coef"] and sig(ols["coef"][k]["p"])]
    ctrl_no = [NOMBRE_CTRL[k] for k in NOMBRE_CTRL if k in ols["coef"] and not sig(ols["coef"][k]["p"])]
    if ctrl_sig and ctrl_no:
        efectos += f" Entre los controles, {lista(ctrl_sig)} {'tiene' if len(ctrl_sig) == 1 else 'tienen'} una asociación significativa con el PSQI y {lista(ctrl_no)} no."
    elif ctrl_sig:
        efectos += f" Todos los controles ({lista(ctrl_sig)}) tienen una asociación significativa con el PSQI."
    elif ctrl_no:
        efectos += f" Ningún control ({lista(ctrl_no)}) tiene una asociación significativa con el PSQI."
    T["ols_efectos"] = efectos.strip()

    o = ols
    s1 = (f"No hay multicolinealidad (VIF máximo = {f(o['vif_max'])})." if o["vif_max"] is not None and o["vif_max"] < 5
          else f"Hay indicios de multicolinealidad (VIF máximo = {f(o['vif_max'])})." if o["vif_max"] is not None else "")
    s2 = (f"Los residuos tienen varianza constante (Breusch-Pagan, {P(o['bp_p'])})." if o["bp_p"] >= ALFA
          else f"Los residuos muestran heterocedasticidad (Breusch-Pagan, {P(o['bp_p'])}); conviene usar errores estándar robustos.")
    s3 = (f"No hay autocorrelación relevante (Durbin-Watson = {f(o['dw'])})." if 1.5 <= o["dw"] <= 2.5
          else f"Hay posible autocorrelación (Durbin-Watson = {f(o['dw'])}).")
    if o["sw_p"] >= ALFA:
        s4 = f"Los residuos no se desvían de la normalidad (Shapiro-Wilk, *W* = {f(o['sw_w'], 3)}, {P(o['sw_p'])})."
    else:
        s4 = (f"Shapiro-Wilk detecta una desviación de la normalidad de los residuos (*W* = {f(o['sw_w'], 3)}, {P(o['sw_p'])}); "
              + ("con *n* ≥ 100 la inferencia es razonablemente robusta a desviaciones leves." if o["n"] >= 100
                 else "con una muestra pequeña los resultados deben interpretarse con cautela."))
    T["supuestos"] = " ".join(s for s in (s1, s2, s3, s4) if s)

    # ---- regresión logística
    if lg:
        t = (f"El modelo {'es' if sig(lg['p']) else 'no es'} significativo ({P(lg['p'])}; pseudo *R*² de McFadden = {f(lg['pseudo_r2'], 3)}) "
             f"y su capacidad de discriminar entre estudiantes con buena y mala calidad de sueño es {mag_auc(lg['auc'])} (AUC = {f(lg['auc'], 3)}).")
        piezas = []
        if "horas_pantalla_dia" in lg["OR"]:
            c = lg["OR"]["horas_pantalla_dia"]
            if sig(c["p"]):
                piezas.append(f"cada hora adicional de pantalla multiplica las probabilidades de mala calidad de sueño por {f(c['or'])} (IC 95 %: {f(c['lo'])} a {f(c['hi'])}; {P(c['p'])})")
        if "pre_sueno_10min" in lg["OR"]:
            c = lg["OR"]["pre_sueno_10min"]
            if sig(c["p"]):
                piezas.append(f"cada 10 minutos adicionales de uso nocturno las multiplican por {f(c['or'])} (IC 95 %: {f(c['lo'])} a {f(c['hi'])}; {P(c['p'])})")
        if piezas:
            t += " Con ajuste por las demás variables, " + "; ".join(piezas) + "."
        else:
            t += " Ni las horas de pantalla ni el uso nocturno resultan significativos al ajustar por las demás variables."
        otros = [NOMBRE_CTRL[k] for k in NOMBRE_CTRL if k in lg["OR"] and sig(lg["OR"][k]["p"])]
        t += (f" Entre los controles, {lista(otros)} {'tiene' if len(otros) == 1 else 'tienen'} una asociación significativa."
              if otros else " Ninguno de los controles tiene una asociación significativa.")
        T["logit"] = t
    else:
        T["logit"] = "No se pudo ajustar la regresión logística con estos datos (ver avisos)."

    # ---- discusión
    disc_p = []
    nombres = {"min_celular_antes_dormir": "el uso nocturno del celular", "horas_pantalla_dia": "las horas de pantalla", "horas_redes_dia": "las horas en redes sociales", "horas_videojuegos_dia": "las horas en videojuegos"}
    rechazadas = [nombres[v] for v in USO if v in corr and sig(corr[v]["p"])]
    if rechazadas:
        disc_p.append(f"Se rechaza H₀ para {lista(rechazadas)}: " + ("a mayor uso, peor calidad de sueño." if not sig_neg else "hay asociación con el PSQI (ver signos)."))
    else:
        disc_p.append("No se rechaza H₀: ninguna medida de uso muestra una asociación significativa con el PSQI.")
    pruebas = {
        "correlación (celular nocturno)": sig(corr["min_celular_antes_dormir"]["p"]) if "min_celular_antes_dormir" in corr else None,
        "correlación (pantalla)": sig(corr["horas_pantalla_dia"]["p"]) if "horas_pantalla_dia" in corr else None,
        "t de Welch": sig(dg["p_t"]), "Mann-Whitney": sig(dg["p_u"]), "ANOVA": sig(an["p"]), "Kruskal-Wallis": sig(an["p_H"]),
        "chi-cuadrado": sig(ch["p"]) if ch else None,
        "regresión lineal (nocturno)": mod_sig.get("min_celular_antes_dormir"),
        "regresión lineal (pantalla)": mod_sig.get("horas_pantalla_dia"),
    }
    pruebas = {k: v for k, v in pruebas.items() if v is not None}
    n_sig = sum(pruebas.values())
    if n_sig == len(pruebas):
        disc_p.append("Todas las técnicas aplicadas apuntan en la misma dirección (correlación, comparación de grupos, ANOVA, chi-cuadrado y regresión), lo que da consistencia al resultado.")
    elif n_sig == 0:
        disc_p.append("Ninguna de las técnicas aplicadas detecta una asociación significativa, de modo que el resultado es consistente entre ellas.")
    else:
        no = [k for k, v in pruebas.items() if not v]
        disc_p.append(f"Las técnicas no coinciden en todos los casos: {n_sig} de {len(pruebas)} resultan significativas y no lo son {lista(no)}. "
                      "Conviene interpretar con cautela y priorizar los modelos que ajustan por otras variables.")
    if len(mod_sig) == 2:
        bn, bp_ = ols["coef"]["pre_sueno_10min"]["beta"], ols["coef"]["horas_pantalla_dia"]["beta"]
        if all(mod_sig.values()):
            mayor_n = abs(bn) > abs(bp_)
            t = (f"Al ajustar por las demás variables, {'el uso nocturno' if mayor_n else 'las horas de pantalla'} tiene el coeficiente estandarizado más alto "
                 f"(β = {f(bn if mayor_n else bp_)}, frente a {f(bp_ if mayor_n else bn)} de {'las horas de pantalla' if mayor_n else 'el uso nocturno'}).")
            if mayor_n:
                t += " Esto coincide con la idea de que el momento del uso pesa más que la cantidad total (Chang et al., 2015)."
            disc_p.append(t)
        elif any(mod_sig.values()):
            conserva = "el uso nocturno" if mod_sig["min_celular_antes_dormir"] else "las horas de pantalla"
            pierde = "las horas de pantalla" if mod_sig["min_celular_antes_dormir"] else "el uso nocturno"
            disc_p.append(f"Al ajustar por las demás variables solo {conserva} mantiene una asociación significativa; la de {pierde} deja de serlo, "
                          "lo que sugiere que su asociación simple se explica en parte por las demás variables.")
        else:
            disc_p.append("Ni el uso nocturno ni las horas de pantalla mantienen una asociación significativa al ajustar por las demás variables.")
    if "horas_videojuegos_dia" in corr and not sig(corr["horas_videojuegos_dia"]["p"]) and (sig_pos or sig_neg):
        disc_p.append(f"Las horas en videojuegos no se asocian con el PSQI (*r* = {f(corr['horas_videojuegos_dia']['r'])}), lo que sugiere que no basta con medir las horas totales: importa también qué se hace y cuándo.")
    t = f"El modelo lineal explica el {100 * ols['r2']:.1f} % de la variabilidad del PSQI"
    t += ", de modo que la mayor parte del sueño depende de otros factores." if ols["r2"] < 0.5 else "."
    if "tazas_cafeina_dia" in ols["coef"] and not sig(ols["coef"]["tazas_cafeina_dia"]["p"]):
        t += (f" Que la cafeína no resulte significativa no prueba que no tenga efecto: con *n* = {n}, un efecto pequeño puede quedar sin detectar "
              f"(solo se detectan correlaciones de al menos |*r*| ≈ {f(R['r_minimo_detectable'])} con 80 % de potencia).")
    disc_p.append(t)
    T["discusion"] = disc_p

    # ---- limitaciones
    lim = []
    if simulados:
        lim.append("**Datos simulados.** La muestra no proviene de estudiantes reales, así que los resultados ilustran el método y no describen a ninguna población. "
                   "Al ser generados con una relación supuesta, es esperable que el análisis la recupere.")
    else:
        muestreo = meta.get("muestreo", "")
        lim.append({
            "Muestreo por conveniencia": "**Sesgo de selección.** El muestreo fue por conveniencia, por lo que los resultados no se generalizan sin reservas a toda la población estudiantil.",
            "Muestreo aleatorio simple": "**Generalización.** El muestreo aleatorio permite generalizar a la población de la que se extrajo la muestra, no a otras poblaciones.",
            "Muestreo estratificado": "**Generalización.** El muestreo estratificado permite generalizar a la población de origen; el análisis no incorpora ponderaciones por estrato.",
            "Censo / población completa": "**Alcance.** Se analizó a toda la población indicada; los valores p se interpretan como descripción de esa población y no como inferencia a otra.",
        }.get(muestreo, "**Diseño muestral.** No se especificó cómo se seleccionó la muestra, por lo que la generalización de los resultados es incierta."))
        lim.append("**Autorreporte.** Las horas de uso y el PSQI se obtienen por declaración de los estudiantes, con posible sesgo de memoria y de deseabilidad social.")
    lim.append("**Diseño transversal.** Una correlación no demuestra causalidad. También es posible la causalidad inversa: dormir mal puede llevar a usar más el celular por la noche.")
    lim.append("**Variables omitidas.** Estrés, horarios académicos, trabajo nocturno, ruido y salud mental pueden confundir la relación.")
    lim.append(f"**Potencia.** Con *n* = {n} y α = 0.05, la muestra detecta con 80 % de potencia correlaciones de alrededor de |*r*| = {f(R['r_minimo_detectable'])} o más; efectos menores pasarían inadvertidos.")
    cercanos = sorted({ETIQ_MODELO.get(k, ETIQUETAS.get(k, k))
                       for k, c in ols["coef"].items() if k != "Intercept" and 0.01 <= c["p"] < ALFA})
    t = "**Pruebas múltiples.** No se corrigió por el número de contrastes realizados"
    t += (f", por lo que los valores p entre 0.01 y 0.05 (en la regresión lineal: {lista(cercanos)}) deben leerse con cautela." if cercanos else ".")
    lim.append(t)
    lim.append(f"**Punto de corte.** El umbral de {u} minutos de uso nocturno es una decisión del análisis; otros umbrales pueden dar resultados distintos.")
    T["limitaciones"] = lim

    # ---- conclusiones
    con = []
    if "min_celular_antes_dormir" in corr and sig(corr["min_celular_antes_dormir"]["p"]):
        c = corr["min_celular_antes_dormir"]
        es_max = all(abs(c["r"]) >= abs(corr[v]["r"]) for v in USO if v in corr)
        tt = (f"El uso del celular antes de dormir {'es el factor más asociado con' if es_max and c['r'] > 0 else 'está asociado con'} "
              f"{'peor' if c['r'] > 0 else 'mejor'} calidad de sueño (*r* = {f(c['r'])}); la diferencia de PSQI entre quienes lo usan {u} minutos o más "
              f"y quienes no es de {f(dg['diff'])} puntos (*d* = {f(dg['d'])})")
        tt += (f", y la proporción con mala calidad de sueño es {ch['pct_mala_alto']:.1f} % frente a {ch['pct_mala_bajo']:.1f} % (OR = {f(ch['OR'])})." if ch else ".")
        con.append(tt)
    if "horas_pantalla_dia" in corr and sig(corr["horas_pantalla_dia"]["p"]):
        c = corr["horas_pantalla_dia"]
        tt = f"Las horas diarias de pantalla también se asocian con {'peor' if c['r'] > 0 else 'mejor'} calidad de sueño (*r* = {f(c['r'])}; ANOVA, {P(an['p'])})"
        if sig(an["p"]):
            bm, ba, ma = t_[("Bajo", "Medio")], t_[("Bajo", "Alto")], t_[("Medio", "Alto")]
            if bm["p"] < ALFA and ba["p"] < ALFA and ma["p"] >= ALFA:
                tt += ", con la mayor diferencia entre el uso bajo y el resto"
        con.append(tt + ".")
    ajustes = []
    if "horas_pantalla_dia" in ols["coef"] and sig(ols["coef"]["horas_pantalla_dia"]["p"]):
        c = ols["coef"]["horas_pantalla_dia"]
        ajustes.append(f"cada hora adicional de pantalla {'suma' if c['b'] > 0 else 'resta'} {f(abs(c['b']))} puntos de PSQI")
    if "pre_sueno_10min" in ols["coef"] and sig(ols["coef"]["pre_sueno_10min"]["p"]):
        c = ols["coef"]["pre_sueno_10min"]
        ajustes.append(f"cada 10 minutos de uso nocturno {'suman' if c['b'] > 0 else 'restan'} {f(abs(c['b']))}")
    if ajustes:
        con.append(f"Con ajuste por {ctrl_txt}, {lista(ajustes)}.")
    if not con:
        con.append(f"No se encontró evidencia estadística de asociación entre el uso de tecnologías digitales y la calidad del sueño en esta muestra (*n* = {n}). "
                   f"Esto no demuestra ausencia de efecto: la muestra solo detecta correlaciones de al menos |*r*| ≈ {f(R['r_minimo_detectable'])}.")
    con.append(f"El {R['pct_mala']:.1f} % de la muestra presenta mala calidad de sueño (PSQI > {corte}).")
    T["conclusiones"] = con

    if "min_celular_antes_dormir" in corr and sig(corr["min_celular_antes_dormir"]["p"]) and corr["min_celular_antes_dormir"]["r"] > 0:
        rec = ("Según estos resultados, reducir el uso del celular en la última hora antes de dormir es la medida con más respaldo estadístico.")
    elif sig_pos:
        rec = "Según estos resultados, moderar el uso de pantallas es la medida con más respaldo estadístico."
    else:
        rec = "Estos resultados no permiten recomendar una medida concreta sobre el uso de tecnologías para mejorar el sueño."
    if simulados:
        rec += " Para un estudio real, se recomienda aplicar el PSQI completo a una muestra aleatoria de estudiantes, medir también el horario de uso y repetir este análisis, idealmente con un diseño longitudinal."
    else:
        rec += " Para confirmarlo, se recomienda un diseño longitudinal o experimental que permita establecer el orden temporal entre uso y sueño."
    T["recomendacion"] = rec
    return T
