"""
Generación de datos SIMULADOS para el proyecto:
"Análisis estadístico sobre el uso de tecnologías digitales y su impacto
en la calidad del sueño en la población estudiantil".

Los datos NO provienen de una encuesta real. Se generan con una semilla fija
y una estructura causal plausible (basada en lo reportado en la literatura:
mayor uso nocturno de pantallas -> peor calidad de sueño) para ilustrar el
análisis estadístico.
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(2026)
N = 200

edad = np.clip(np.round(rng.normal(21.5, 2.2, N)), 18, 30).astype(int)
sexo = rng.choice(["Femenino", "Masculino"], N, p=[0.52, 0.48])
carrera = rng.choice(
    ["Ing. en Sistemas", "Ing. Industrial", "Administración", "Derecho", "Psicología"],
    N, p=[0.30, 0.20, 0.20, 0.15, 0.15],
)
ciclo = rng.integers(1, 11, N)

# Uso de tecnología
horas_redes = np.clip(rng.gamma(4.0, 0.75, N), 0.3, 9)            # h/día
horas_juegos = np.clip(rng.gamma(1.2, 0.9, N), 0, 8)
juegos_mult = np.where(sexo == "Masculino", 1.6, 0.7)
horas_juegos = np.clip(horas_juegos * juegos_mult, 0, 8)
horas_otros = np.clip(rng.normal(3.0, 1.2, N), 0.5, 7)             # video, estudio digital, etc.
horas_pantalla = np.clip(horas_redes + horas_juegos + horas_otros, 1.5, 17)

# Minutos de uso del celular en la hora previa a dormir (correlacionado con redes)
pre_sueno = np.clip(
    8 * horas_redes + rng.normal(10, 22, N) + 4 * horas_juegos, 0, 120
)

# Controles
cafeina = np.clip(np.round(rng.gamma(1.6, 0.9, N)), 0, 6).astype(int)   # tazas/día
horas_estudio_trabajo = np.clip(rng.normal(7.0, 2.3, N), 1, 14)

# Calidad del sueño (PSQI, 0-21; más alto = peor)
ruido = rng.normal(0, 2.3, N)
psqi_latente = (
    2.2
    + 0.020 * pre_sueno
    + 0.22 * horas_pantalla
    + 0.30 * cafeina
    + 0.10 * (horas_estudio_trabajo - 7)
    + ruido
)
psqi = np.clip(np.round(psqi_latente), 0, 21).astype(int)

# Horas de sueño (descriptivo, dependiente de las mismas variables)
horas_sueno = np.clip(
    7.8 - 0.012 * pre_sueno - 0.10 * horas_pantalla - 0.12 * cafeina + rng.normal(0, 0.8, N),
    3.5, 10,
)

df = pd.DataFrame({
    "id": np.arange(1, N + 1),
    "edad": edad,
    "sexo": sexo,
    "carrera": carrera,
    "ciclo": ciclo,
    "horas_pantalla_dia": horas_pantalla.round(1),
    "horas_redes_dia": horas_redes.round(1),
    "horas_videojuegos_dia": horas_juegos.round(1),
    "min_celular_antes_dormir": pre_sueno.round(0).astype(int),
    "tazas_cafeina_dia": cafeina,
    "horas_estudio_trabajo_dia": horas_estudio_trabajo.round(1),
    "horas_sueno_noche": horas_sueno.round(1),
    "psqi_total": psqi,
})
df["mala_calidad_sueno"] = (df["psqi_total"] > 5).astype(int)

import os
out = os.path.dirname(os.path.abspath(__file__))
df.to_csv(os.path.join(out, "datos_simulados.csv"), index=False, encoding="utf-8")
print(df.shape)
print(df.describe().T.round(2).to_string())
print("\nMala calidad (PSQI>5):", df["mala_calidad_sueno"].mean().round(3))
