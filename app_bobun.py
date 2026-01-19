import streamlit as st
import pandas as pd

# Plotly (si pas installé, on affiche un fallback)
try:
    import plotly.graph_objects as go
    PLOTLY_OK = True
except ModuleNotFoundError:
    PLOTLY_OK = False


# =========================
# CONFIG PAGE + STYLE
# =========================
st.set_page_config(page_title="Quel bobun aujourd'hui ? 🍜", page_icon="🍜", layout="wide")

st.markdown(
    """
    <style>
    .main { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    h1 {
        color: #2d3748;
        text-align: center;
        font-size: 3rem !important;
        margin-bottom: 1rem;
    }
    .sub {
        text-align:center;
        color:#4a5568;
        margin-top:-10px;
        margin-bottom: 1.5rem;
        font-size: 1.2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("# 🍜 Quel bobun aujourd'hui ?")
st.markdown("<div class='sub'>Trouve ton resto parfait en ajustant tes préférences !</div>", unsafe_allow_html=True)


# =========================
# DATA LOADING (EXCEL)
# =========================
EXCEL_PATH = "20260119 - Benchmark - Bo Bun.xlsx"

DEFAULT_RESTOS = pd.DataFrame({
    "nom": ["Pho 11", "L'othentique Vietnam", "Banemi", "Song Heng", "Le petit Cambodge", "James Bun", "Entre 2 rives"],
    "temps_trajet": [12, 13, 18, 14, 13, 7, 10],
    "note": [3.8, 4.6, 4.6, 4.5, 4.8, 4.4, 4.5],
    "prix": [11.80, 15.00, 14.90, 13.00, 15.50, 14.50, 14.00],
})

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convertit une base Excel avec colonnes:
    - Restaurant
    - Temps de trajet
    - Note
    - Prix
    vers les noms internes:
    - nom, temps_trajet, note, prix
    Tolère quelques variantes (espaces, underscore, casse).
    """
    df = df.copy()

    # Nettoyage des noms de colonnes
    df.columns = [str(c).strip() for c in df.columns]

    # Mapping tolérant
    mapping = {}
    for c in df.columns:
        key = c.strip().lower().replace("_", " ")
        key = " ".join(key.split())  # espaces multiples -> un seul

        if key in ["restaurant", "resto", "nom", "name"]:
            mapping[c] = "nom"
        elif key in ["temps de trajet", "temps trajet", "trajet", "temps", "tps trajet", "tps de trajet"]:
            mapping[c] = "temps_trajet"
        elif key in ["note", "rating", "score", "avis"]:
            mapping[c] = "note"
        elif key in ["prix", "price", "tarif", "cout", "coût"]:
            mapping[c] = "prix"

    df = df.rename(columns=mapping)

    required = ["nom", "temps_trajet", "note", "prix"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes: {missing}. Colonnes détectées: {list(df.columns)}")

    # Cast types
    df["nom"] = df["nom"].astype(str).str.strip()
    df["temps_trajet"] = pd.to_numeric(df["temps_trajet"], errors="coerce")
    df["note"] = pd.to_numeric(df["note"], errors="coerce")
    df["prix"] = pd.to_numeric(df["prix"], errors="coerce")

    # On drop ce qui est incomplet
    df = df.dropna(subset=required)

    # Un peu de ménage
    df = df[df["nom"] != ""]
    return df


@st.cache_data
def load_restos_from_excel(path: str) -> pd.DataFrame:
    # Par défaut: première feuille
    df = pd.read_excel(path)
    return _normalize_columns(df)


def get_restos() -> pd.DataFrame:
    try:
        return load_restos_from_excel(EXCEL_PATH)
    except FileNotFoundError:
        st.warning(f"Fichier Excel introuvable (`{EXCEL_PATH}`). J'utilise une base intégrée temporaire.")
        return DEFAULT_RESTOS
    except Exception as e:
        st.error(f"Erreur lecture Excel: {e}")
        st.info("Je bascule sur la base intégrée temporaire.")
        return DEFAULT_RESTOS


restos = get_restos()


# =========================
# SIDEBAR (PREFERENCES)
# =========================
st.sidebar.markdown("## ⚙️ Ajuste tes priorités")
st.sidebar.markdown("---")

importance_temps = st.sidebar.slider(
    "⏱️ Importance du temps de trajet",
    min_value=0,
    max_value=10,
    value=5,
    help="Plus c'est élevé, plus tu privilégies la proximité",
)
importance_note = st.sidebar.slider(
    "⭐ Importance de la note",
    min_value=0,
    max_value=10,
    value=5,
    help="Plus c'est élevé, plus tu privilégies la qualité",
)
importance_prix = st.sidebar.slider(
    "💰 Importance du prix",
    min_value=0,
    max_value=10,
    value=5,
    help="Plus c'est élevé, plus tu privilégies les prix bas",
)

st.sidebar.markdown("---")
st.sidebar.caption("Astuce : tout à 0 = pondération égale 😉")


# =========================
# SCORING
# =========================
def safe_norm(series: pd.Series, invert: bool = False) -> pd.Series:
    """Normalise en [0,1]. Si constante => 1 partout. invert=True => 1 - norm."""
    mn, mx = series.min(), series.max()
    if pd.isna(mn) or pd.isna(mx):
        out = pd.Series([0.0] * len(series), index=series.index)
    elif mx == mn:
        out = pd.Series([1.0] * len(series), index=series.index)
    else:
        out = (series - mn) / (mx - mn)

    return 1 - out if invert else out


def calculer_scores(df: pd.DataFrame, w_temps: float, w_note: float, w_prix: float) -> pd.DataFrame:
    df = df.copy()

    # Scores critères (0..1)
    df["score_temps"] = safe_norm(df["temps_trajet"], invert=True)  # moins = mieux
    df["score_note"] = safe_norm(df["note"], invert=False)         # plus = mieux
    df["score_prix"] = safe_norm(df["prix"], invert=True)          # moins = mieux

    total_weight = w_temps + w_note + w_prix
    if total_weight == 0:
        w_temps = w_note = w_prix = 1
        total_weight = 3

    df["score_final"] = (
        df["score_temps"] * w_temps +
        df["score_note"] * w_note +
        df["score_prix"] * w_prix
    ) / total_weight * 100

    return df.sort_values("score_final", ascending=False)


restos_scores = calculer_scores(restos, importance_temps, importance_note, importance_prix)
top3 = restos_scores.head(3)

# =========================
# TOP 3 – VERSION CLEAN (HTML SAFE)
# =========================
st.markdown("## 🏆 Ton Top 3 du moment")

cols = st.columns(3)
order = [1, 0, 2]  # affichage #2 - #1 - #3

for col, idx in zip(cols, order):
    resto = top3.iloc[idx]

    col.html(f"""
    <div style="
        background: #FFFFFF;
        border: {'2px solid #4C51BF' if idx == 0 else '1px solid #E2E8F0'};
        border-radius: 18px;
        padding: 1.6rem;
        text-align: center;
        box-shadow: 0 8px 24px rgba(0,0,0,0.08);
    ">

        <div style="
            font-size: 0.85rem;
            color: #718096;
            margin-bottom: 0.4rem;
        ">
            #{idx + 1}
        </div>

        <div style="
            font-size: {'1.9rem' if idx == 0 else '1.5rem'};
            font-weight: 800;
            color: #1A202C;
            margin-bottom: 0.6rem;
        ">
            {resto["nom"]}
        </div>

        <div style="
            font-size: 2.4rem;
            font-weight: 900;
            color: #2B6CB0;
            margin-bottom: 0.8rem;
        ">
            {resto["score_final"]:.1f}
        </div>

        <div style="
            font-size: 0.95rem;
            color: #4A5568;
        ">
            ⏱️ {int(resto["temps_trajet"])} min &nbsp;•&nbsp;
            ⭐ {resto["note"]}/5 &nbsp;•&nbsp;
            💰 {resto["prix"]} €
        </div>
    </div>
    """)


# =========================
# WINNER DETAIL (RADAR)
# =========================
st.markdown("---")
st.markdown("## 📊 Profil détaillé du gagnant")

winner = top3.iloc[0]
categories = ["Proximité", "Qualité", "Prix"]
values = [winner["score_temps"] * 100, winner["score_note"] * 100, winner["score_prix"] * 100]

if PLOTLY_OK:
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        name=winner["nom"],
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False,
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Plotly n'est pas installé. Ajoute `plotly` dans requirements.txt pour afficher le radar.")
    st.dataframe(pd.DataFrame({"Critère": categories, "Score (0-100)": [round(v, 1) for v in values]}), use_container_width=True)


# =========================
# FULL RANKING
# =========================
with st.expander("📋 Voir le classement complet"):
    display_df = restos_scores[["nom", "temps_trajet", "note", "prix", "score_final"]].copy()
    display_df.columns = ["Restaurant", "Temps (min)", "Note /5", "Prix (€)", "Score"]
    display_df["Score"] = display_df["Score"].round(1)
    display_df.index = range(1, len(display_df) + 1)
    st.dataframe(display_df, use_container_width=True)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #718096;'>Bon appétit ! 🥢</p>", unsafe_allow_html=True)
