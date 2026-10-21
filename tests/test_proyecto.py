"""Pruebas del proyecto: análisis, textos condicionales, informe PDF y app."""
import io
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import analisis as an
import informe
import textos as tx

BASE = Path(__file__).resolve().parent.parent
META = dict(titulo="Prueba", titulo_corto="Prueba", autor="Autora de Prueba", institucion="Universidad", curso="Estadística",
            simulados=True, ejemplo_intacto=False, fuente="", muestreo="No especificado")


@pytest.fixture(scope="module")
def muestra():
    df, errores, _ = an.validar(pd.read_csv(BASE / "datos_simulados.csv"))
    assert not errores
    return df


@pytest.fixture(scope="module")
def resultados(muestra):
    R, figs = an.analizar(muestra)
    return R, an.figuras_a_png(figs)


# ------------------------------------------------------------------ análisis
def test_reproduce_las_cifras_del_informe(resultados):
    R, _ = resultados
    esperado = [
        (R["correlaciones"]["min_celular_antes_dormir"]["r"], 0.389),
        (R["correlaciones"]["horas_pantalla_dia"]["r"], 0.308),
        (R["dos_grupos"]["t"], 4.53), (R["dos_grupos"]["d"], 0.68), (R["dos_grupos"]["diff"], 1.54),
        (R["anova"]["F"], 6.98), (R["anova"]["eta2"], 0.066),
        (R["chi2"]["chi2"], 12.43), (R["chi2"]["OR"], 2.99),
        (R["ols"]["r2"], 0.203), (R["ols"]["F"], 8.19), (R["logit"]["auc"], 0.737),
    ]
    for obtenido, valor in esperado:
        assert obtenido == pytest.approx(valor, abs=0.006)
    assert R["pct_mala"] == 41.5 and R["n"] == 200


def test_resultados_serializables(resultados):
    import json
    json.dumps(resultados[0])


def test_validar_detecta_problemas(muestra):
    crudo = pd.read_csv(BASE / "datos_simulados.csv")
    _, err, _ = an.validar(crudo.drop(columns=["edad"]))
    assert any("edad" in e for e in err)
    malo = crudo.copy(); malo.loc[0, "psqi_total"] = 25
    assert any("PSQI" in e for e in an.validar(malo)[1])
    assert any("al menos" in e for e in an.validar(crudo.head(10))[1])
    coma = crudo.copy(); coma["horas_pantalla_dia"] = coma["horas_pantalla_dia"].astype(str).str.replace(".", ",", regex=False)
    df, err, _ = an.validar(coma)
    assert not err and len(df) == 200
    raro = crudo.copy(); raro.loc[0, "sexo"] = "otro"
    df, _, avisos = an.validar(raro)
    assert len(df) == 199 and any("otro" in a for a in avisos)


def test_umbral_imposible_da_error_claro(muestra):
    with pytest.raises(an.AnalisisError, match="umbral"):
        an.analizar(muestra, umbral_noct=500)


# ------------------------------------------------------------------ textos condicionales
def test_textos_con_relacion(resultados):
    R, _ = resultados
    T = tx.construir(R, dict(META))
    assert "se asocian con peor calidad de sueño" in T["resumen"]
    assert T["discusion"][0].startswith("Se rechaza H₀")
    assert "Datos simulados" in T["limitaciones"][0]


def test_textos_sin_relacion_no_afirman_efectos(muestra):
    rng = np.random.default_rng(7)
    df = muestra.copy()
    df["psqi_total"] = rng.permutation(df["psqi_total"].to_numpy())  # rompe toda relación
    R, figs = an.analizar(df)
    an.figuras_a_png(figs)
    T = tx.construir(R, dict(META))
    assert "no se encontró una asociación" in T["resumen"]
    assert T["discusion"][0].startswith("No se rechaza H₀")
    assert not any("Se rechaza H₀" in p for p in T["discusion"])
    assert T["conclusiones"][0].startswith("No se encontró evidencia")
    assert "no permiten recomendar" in T["recomendacion"]


# ------------------------------------------------------------------ informe LaTeX / PDF
def test_tex_escapa_caracteres_especiales():
    assert informe.tex("100 % & _x_ #1") == r"100\,\% \& \_x\_ \#1"
    assert informe.tex("**negrita** y *cursiva*") == r"\textbf{negrita} y \emph{cursiva}"
    assert "$\\alpha$" in informe.tex("α = 0.05")


def test_zip_autocontenido(resultados):
    R, pngs = resultados
    res = informe.generar(R, dict(META), pngs, compilar=False)
    import zipfile
    nombres = zipfile.ZipFile(io.BytesIO(res["zip"])).namelist()
    assert "informe.tex" in nombres and "figuras/f1_distribuciones.png" in nombres


needs_latex = pytest.mark.skipif(shutil.which("pdflatex") is None, reason="pdflatex no disponible")


@needs_latex
def test_pdf_se_compila(resultados):
    R, pngs = resultados
    meta = dict(META, titulo="Título con & y % especiales", autor="Ñandú Pérez")
    res = informe.generar(R, meta, pngs)
    assert res["ok"], res["motivo"]
    assert res["pdf"].startswith(b"%PDF") and len(res["pdf"]) > 100_000
    from pypdf import PdfReader
    lector = PdfReader(io.BytesIO(res["pdf"]))
    assert 9 <= len(lector.pages) <= 16
    texto = " ".join(p.extract_text() for p in lector.pages)
    for frase in ("Datos simulados", "Resumen", "Conclusiones", "Referencias", "0.389"):
        assert frase in texto


@needs_latex
def test_pdf_con_datos_reales_no_dice_simulados(muestra):
    R, figs = an.analizar(muestra)
    pngs = an.figuras_a_png(figs)
    meta = dict(META, simulados=False, fuente="Encuesta aplicada a 200 estudiantes de la UMG.", muestreo="Muestreo por conveniencia")
    res = informe.generar(R, meta, pngs)
    assert res["ok"], res["motivo"]
    assert "simulados" not in res["tex"].lower()
    assert "Sesgo de selección" in res["tex"] and "Encuesta aplicada" in res["tex"]


@needs_latex
def test_pdf_cuando_no_hay_relacion(muestra):
    df = muestra.copy()
    df["psqi_total"] = np.random.default_rng(7).permutation(df["psqi_total"].to_numpy())
    R, figs = an.analizar(df)
    res = informe.generar(R, dict(META), an.figuras_a_png(figs))
    assert res["ok"], res["motivo"]


# ------------------------------------------------------------------ app
def test_app_arranca_y_genera_pdf():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(BASE / "app.py"), default_timeout=180).run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.tabs) == 6
    assert not at.error
    boton = next(b for b in at.button if b.label == "Generar informe PDF")
    boton.click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    res = at.session_state["informe"]
    if shutil.which("pdflatex"):
        assert res["ok"], res["motivo"]
        assert res["pdf"].startswith(b"%PDF")
    assert res["zip"]


def test_app_cambia_el_umbral_y_recalcula():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(BASE / "app.py"), default_timeout=180).run()
    r30 = at.session_state["R"]["dos_grupos"]["diff"]
    at.slider[0].set_value(45).run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["R"]["umbral_noct"] == 45
    assert at.session_state["R"]["dos_grupos"]["diff"] != pytest.approx(r30)


# ------------------------------------------------------------------ casos límite
OBLIGATORIAS = an.REQUERIDAS


@needs_latex
def test_sin_columnas_opcionales(muestra):
    df = muestra[OBLIGATORIAS].copy()
    R, figs = an.analizar(df)
    res = informe.generar(R, dict(META), an.figuras_a_png(figs))
    assert res["ok"], res["motivo"]
    assert "Videojuegos" not in res["tex"] and "redes sociales" not in tx.construir(R, dict(META))["resumen"]


@needs_latex
def test_variable_de_control_constante_se_omite(muestra):
    df = muestra.copy()
    df["tazas_cafeina_dia"] = 1
    R, figs = an.analizar(df)
    assert "tazas_cafeina_dia" not in R["ols"]["coef"]
    assert any("constantes" in a for a in R["avisos"])
    res = informe.generar(R, dict(META), an.figuras_a_png(figs))
    assert res["ok"], res["motivo"]


@needs_latex
def test_muestra_pequena_de_un_solo_sexo(muestra):
    df = muestra[muestra["sexo"] == "Femenino"].head(40).copy()
    R, figs = an.analizar(df)
    assert "masculino" not in R["ols"]["coef"]
    res = informe.generar(R, dict(META), an.figuras_a_png(figs))
    assert res["ok"], res["motivo"]


@needs_latex
def test_sin_estudiantes_con_mala_calidad(muestra):
    df = muestra.copy()
    df["psqi_total"] = np.minimum(df["psqi_total"], 5)  # nadie supera el corte
    R, figs = an.analizar(df)
    assert R["chi2"] is None and R["logit"] is None
    T = tx.construir(R, dict(META))
    assert "No se pudo calcular el chi-cuadrado" in T["chi2"]
    res = informe.generar(R, dict(META), an.figuras_a_png(figs))
    assert res["ok"], res["motivo"]


@needs_latex
def test_varios_autores_en_portada(resultados):
    R, pngs = resultados
    meta = dict(META, autor="Ana Pérez, Luis Gómez – 123", autores=["Ana Pérez", "Luis Gómez – 123", "Ñoño Ruiz"])
    res = informe.generar(R, meta, pngs)
    assert res["ok"], res["motivo"]
    from pypdf import PdfReader
    portada = PdfReader(io.BytesIO(res["pdf"])).pages[0].extract_text()
    assert "Ana Pérez" in portada and "Luis Gómez" in portada and "Ñoño Ruiz" in portada
