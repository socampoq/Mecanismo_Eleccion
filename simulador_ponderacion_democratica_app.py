import math
import random
from typing import Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Simulador de ponderación democrática", layout="wide")

# ============================================================
# Configuración base
# ============================================================
ESTAMENTOS = ["Profesores", "Estudiantes", "Trabajadores", "Egresados"]
SEDES = ["Amazonia", "Bogotá", "Caribe", "La Paz", "Manizales", "Medellín", "Orinoquia", "Palmira", "Tumaco"]
FACULTADES = ["Ciencias", "Ingeniería", "Artes", "Ciencias Sociales", "Economía"]


def normalize(values: List[float]) -> List[float]:
    total = sum(max(v, 0.0) for v in values)
    if total <= 0:
        return [1 / len(values)] * len(values)
    return [max(v, 0.0) / total for v in values]


def power_weight(x: float, alpha: float) -> float:
    # Generalización de raíz: x^alpha, con alpha en (0,1] para concavidad.
    return x ** alpha if x > 0 else 0.0


def initialize_state(n_candidates: int):
    candidates = [f"Candidatura {i + 1}" for i in range(n_candidates)]

    # Pesos políticos del primer nivel
    estamento_weights = {e: random.uniform(10, 40) for e in ESTAMENTOS}

    # Estructura jerárquica: estamento -> sede -> facultad -> candidato
    raw_counts = {}
    for e in ESTAMENTOS:
        raw_counts[e] = {}
        for s in SEDES:
            raw_counts[e][s] = {}
            for f in FACULTADES:
                raw_counts[e][s][f] = {}
                for c in candidates:
                    raw_counts[e][s][f][c] = random.randint(0, 100)

    st.session_state.candidates = candidates
    st.session_state.estamento_weights = estamento_weights
    st.session_state.raw_counts = raw_counts


# ============================================================
# Estado inicial
# ============================================================
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    initialize_state(3)

st.title("Simulador pedagógico de ponderación democrática")
st.caption(
    "Simula un mecanismo jerárquico de participación: estamentos → sedes → facultades → candidaturas."
)

with st.sidebar:
    st.header("Configuración general")

    n_candidates = st.slider("Número de candidaturas", min_value=2, max_value=5, value=len(st.session_state.candidates))

    alpha_sede = st.slider(
        "Pendiente concava para sedes (x^α)", min_value=0.20, max_value=1.00, value=0.50, step=0.05,
        help="0.50 equivale a raíz cuadrada. Entre más pequeño α, mayor corrección concava."
    )
    alpha_fac = st.slider(
        "Pendiente concava para facultades (y^β)", min_value=0.20, max_value=1.00, value=0.50, step=0.05,
        help="0.50 equivale a raíz cuadrada."
    )

    if st.button("Reinicializar aleatoriamente") or n_candidates != len(st.session_state.candidates):
        initialize_state(n_candidates)
        st.rerun()

    st.markdown("---")
    st.subheader("Interpretación rápida")
    st.write(
        "1. Cada estamento recibe una porción política del total.\n"
        "2. Dentro de cada estamento, las sedes se ponderan con una función concava.\n"
        "3. Dentro de cada sede, las facultades se ponderan también con una función concava.\n"
        "4. Al final, se agregan los votos ponderados por candidatura."
    )

candidates = st.session_state.candidates
estamento_weights = st.session_state.estamento_weights
raw_counts = st.session_state.raw_counts

# ============================================================
# Edición de pesos políticos del primer nivel
# ============================================================
st.subheader("1) Peso político de los estamentos")
cols = st.columns(len(ESTAMENTOS))
for i, e in enumerate(ESTAMENTOS):
    estamento_weights[e] = cols[i].number_input(
        f"{e}", min_value=0.0, value=float(estamento_weights[e]), step=1.0, key=f"peso_{e}"
    )

estamento_shares = dict(zip(ESTAMENTOS, normalize(list(estamento_weights.values()))))

peso_df = pd.DataFrame({
    "Estamento": ESTAMENTOS,
    "Peso bruto": [estamento_weights[e] for e in ESTAMENTOS],
    "Peso normalizado": [estamento_shares[e] for e in ESTAMENTOS],
})

col_a, col_b = st.columns([1, 1])
with col_a:
    st.dataframe(peso_df, use_container_width=True)
with col_b:
    fig_pie = px.pie(peso_df, names="Estamento", values="Peso normalizado", title="Distribución política del total")
    st.plotly_chart(fig_pie, use_container_width=True)

# ============================================================
# Edición jerárquica de votos
# ============================================================
st.subheader("2) Votos brutos por sede, facultad y candidatura")
st.write(
    "Puedes dejar la simulación aleatoria o editar manualmente los valores. El resultado final mostrará el efecto de la ponderación."
)

selected_estamento = st.selectbox("Estamento a editar", ESTAMENTOS)
selected_sede = st.selectbox("Sede a editar", SEDES)
selected_fac = st.selectbox("Facultad a editar", FACULTADES)

edit_cols = st.columns(len(candidates))
for i, c in enumerate(candidates):
    raw_counts[selected_estamento][selected_sede][selected_fac][c] = edit_cols[i].number_input(
        f"{c}",
        min_value=0,
        value=int(raw_counts[selected_estamento][selected_sede][selected_fac][c]),
        step=1,
        key=f"edit_{selected_estamento}_{selected_sede}_{selected_fac}_{c}",
    )

# ============================================================
# Cálculo del mecanismo
# ============================================================
def compute_results(alpha_sede: float, alpha_fac: float):
    final_scores = {c: 0.0 for c in candidates}
    detailed_rows = []
    faculty_rows = []
    sede_rows = []

    for e in ESTAMENTOS:
        est_weight = estamento_shares[e]

        # Totales brutos por sede dentro del estamento
        sede_totals = []
        for s in SEDES:
            total_s = 0.0
            for f in FACULTADES:
                total_s += sum(raw_counts[e][s][f].values())
            sede_totals.append(total_s)

        sede_adjusted = [power_weight(x, alpha_sede) for x in sede_totals]
        sede_shares = dict(zip(SEDES, normalize(sede_adjusted)))

        for s in SEDES:
            sede_rows.append({
                "Estamento": e,
                "Sede": s,
                "Voto bruto sede": sum(sum(raw_counts[e][s][f].values()) for f in FACULTADES),
                "Peso sede ajustado": sede_shares[s],
                "Contribución sede": est_weight * sede_shares[s],
            })

            # Totales brutos por facultad dentro de la sede
            fac_totals = []
            for f in FACULTADES:
                fac_totals.append(sum(raw_counts[e][s][f].values()))

            fac_adjusted = [power_weight(x, alpha_fac) for x in fac_totals]
            fac_shares = dict(zip(FACULTADES, normalize(fac_adjusted)))

            for f in FACULTADES:
                faculty_rows.append({
                    "Estamento": e,
                    "Sede": s,
                    "Facultad": f,
                    "Voto bruto facultad": sum(raw_counts[e][s][f].values()),
                    "Peso facultad ajustado": fac_shares[f],
                    "Contribución facultad": est_weight * sede_shares[s] * fac_shares[f],
                })

                cand_votes = [raw_counts[e][s][f][c] for c in candidates]
                cand_shares = dict(zip(candidates, normalize(cand_votes)))

                for c in candidates:
                    contribution = est_weight * sede_shares[s] * fac_shares[f] * cand_shares[c]
                    final_scores[c] += contribution
                    detailed_rows.append({
                        "Estamento": e,
                        "Sede": s,
                        "Facultad": f,
                        "Candidatura": c,
                        "Voto bruto candidatura": raw_counts[e][s][f][c],
                        "Participación interna": cand_shares[c],
                        "Contribución final": contribution,
                    })

    result_df = pd.DataFrame({
        "Candidatura": list(final_scores.keys()),
        "Puntaje final": list(final_scores.values())
    }).sort_values("Puntaje final", ascending=False)

    result_df["Puntaje final"] = result_df["Puntaje final"] / result_df["Puntaje final"].sum()
    return result_df, pd.DataFrame(detailed_rows), pd.DataFrame(faculty_rows), pd.DataFrame(sede_rows)


result_df, detail_df, faculty_df, sede_df = compute_results(alpha_sede, alpha_fac)

# ============================================================
# Resultados principales
# ============================================================
st.subheader("3) Resultado agregado")
col1, col2 = st.columns([1, 1])
with col1:
    st.dataframe(result_df, use_container_width=True)
with col2:
    fig_bar = px.bar(result_df, x="Candidatura", y="Puntaje final", title="Resultado ponderado final")
    st.plotly_chart(fig_bar, use_container_width=True)

winner = result_df.iloc[0]["Candidatura"]
st.success(f"Ganadora provisional: {winner}")

# ============================================================
# Comparación bruto vs ponderado
# ============================================================
st.subheader("4) Comparación entre voto bruto y resultado ponderado")

raw_totals = {c: 0 for c in candidates}
for e in ESTAMENTOS:
    for s in SEDES:
        for f in FACULTADES:
            for c in candidates:
                raw_totals[c] += raw_counts[e][s][f][c]

raw_df = pd.DataFrame({
    "Candidatura": list(raw_totals.keys()),
    "Voto bruto total": list(raw_totals.values())
})
raw_df["Participación bruta"] = raw_df["Voto bruto total"] / raw_df["Voto bruto total"].sum()

compare_df = raw_df.merge(result_df, on="Candidatura")
compare_long = compare_df.melt(
    id_vars="Candidatura",
    value_vars=["Participación bruta", "Puntaje final"],
    var_name="Tipo",
    value_name="Valor"
)

fig_compare = px.bar(compare_long, x="Candidatura", y="Valor", color="Tipo", barmode="group", title="Bruto vs ponderado")
st.plotly_chart(fig_compare, use_container_width=True)

# ============================================================
# Detalle por niveles
# ============================================================
with st.expander("Ver efecto de la ponderación por sedes"):
    st.dataframe(sede_df, use_container_width=True)
    fig_sede = px.treemap(
        sede_df,
        path=["Estamento", "Sede"],
        values="Contribución sede",
        title="Contribución de sedes dentro de cada estamento"
    )
    st.plotly_chart(fig_sede, use_container_width=True)

with st.expander("Ver efecto de la ponderación por facultades"):
    st.dataframe(faculty_df, use_container_width=True)
    fig_fac = px.treemap(
        faculty_df,
        path=["Estamento", "Sede", "Facultad"],
        values="Contribución facultad",
        title="Contribución de facultades dentro de cada sede"
    )
    st.plotly_chart(fig_fac, use_container_width=True)

with st.expander("Ver detalle completo por candidatura"):
    st.dataframe(detail_df, use_container_width=True)

# ============================================================
# Visual pedagógica de la función concava
# ============================================================
st.subheader("5) Función de ponderación concava")
x_values = [i / 100 for i in range(1, 101)]
func_df = pd.DataFrame({
    "x": x_values,
    "Sedes": [power_weight(x, alpha_sede) for x in x_values],
    "Facultades": [power_weight(x, alpha_fac) for x in x_values],
})

fig_func = go.Figure()
fig_func.add_trace(go.Scatter(x=func_df["x"], y=func_df["Sedes"], mode="lines", name="Sedes"))
fig_func.add_trace(go.Scatter(x=func_df["x"], y=func_df["Facultades"], mode="lines", name="Facultades"))
fig_func.update_layout(title="Curvas concavas usadas en la ponderación", xaxis_title="Participación bruta", yaxis_title="Peso transformado")
st.plotly_chart(fig_func, use_container_width=True)

# ============================================================
# Nota metodológica
# ============================================================
with st.expander("Supuesto de cálculo usado en esta versión"):
    st.markdown(
        """
        **Fórmula resumida**

        Para cada candidatura, el puntaje final se calcula como la suma de:

        **peso del estamento × peso ajustado de la sede × peso ajustado de la facultad × participación interna de la candidatura**

        donde:
        - el peso del estamento se define políticamente,
        - el peso de la sede se obtiene aplicando una función concava al tamaño bruto de la sede,
        - el peso de la facultad se obtiene aplicando una función concava al tamaño bruto de la facultad,
        - la participación interna de la candidatura se calcula dentro de cada facultad.

        Esta app está diseñada como una **maqueta pedagógica**: sirve para mostrar visualmente cómo cambian los resultados al modificar la estructura del mecanismo.
        """
    )
