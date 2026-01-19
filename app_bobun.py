import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configuration de la page
st.set_page_config(page_title="Quel bobun aujourd'hui ? 🍜", page_icon="🍜", layout="wide")

# Style CSS personnalisé
st.markdown("""
    <style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    h1 {
        color: #2d3748;
        text-align: center;
        font-size: 3rem !important;
        margin-bottom: 2rem;
    }
    .podium-container {
        background: white;
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        margin: 2rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Titre
st.markdown("# 🍜 Quel bobun aujourd'hui ?")
st.markdown("### Trouve ton resto parfait en ajustant tes préférences !")

# Base de données des restos
restos = pd.DataFrame({
    'nom': ['Pho 11', 'L\'othentique Vietnam', 'Banemi', 'Song Heng', 
            'Le petit Cambodge', 'James Bun', 'Entre 2 rives'],
    'temps_trajet': [12, 13, 18, 14, 13, 7, 10],  # en minutes
    'note': [3.8, 4.6, 4.6, 4.5, 4.8, 4.4, 4.5],  # sur 5
    'prix': [11.80, 15.00, 14.90, 13.00, 15.50, 14.50, 14.00]  # en euros
})

# Sidebar pour les préférences
st.sidebar.markdown("## ⚙️ Ajuste tes priorités")
st.sidebar.markdown("---")

importance_temps = st.sidebar.slider(
    "⏱️ Importance du temps de trajet",
    min_value=0,
    max_value=10,
    value=5,
    help="Plus c'est élevé, plus tu privilégies la proximité"
)

importance_note = st.sidebar.slider(
    "⭐ Importance de la note",
    min_value=0,
    max_value=10,
    value=5,
    help="Plus c'est élevé, plus tu privilégies la qualité"
)

importance_prix = st.sidebar.slider(
    "💰 Importance du prix",
    min_value=0,
    max_value=10,
    value=5,
    help="Plus c'est élevé, plus tu privilégies les prix bas"
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Astuce :** Tout à 0 = tous les critères comptent pareil ! 😉")

# Fonction de scoring
def calculer_scores(df, w_temps, w_note, w_prix):
    # Normaliser les valeurs entre 0 et 1
    # Pour le temps et le prix, inverser (moins = mieux)
    df = df.copy()
    df['score_temps'] = 1 - (df['temps_trajet'] - df['temps_trajet'].min()) / (df['temps_trajet'].max() - df['temps_trajet'].min())
    df['score_note'] = (df['note'] - df['note'].min()) / (df['note'].max() - df['note'].min())
    df['score_prix'] = 1 - (df['prix'] - df['prix'].min()) / (df['prix'].max() - df['prix'].min())
    
    # Si tous les poids sont à 0, utiliser des poids égaux
    total_weight = w_temps + w_note + w_prix
    if total_weight == 0:
        w_temps, w_note, w_prix = 1, 1, 1
        total_weight = 3
    
    # Calculer le score final pondéré
    df['score_final'] = (
        df['score_temps'] * w_temps +
        df['score_note'] * w_note +
        df['score_prix'] * w_prix
    ) / total_weight * 100
    
    return df.sort_values('score_final', ascending=False)

# Calculer les scores
restos_scores = calculer_scores(restos, importance_temps, importance_note, importance_prix)
top3 = restos_scores.head(3)

# Affichage du podium
st.markdown("## 🏆 Ton Top 3 du moment")

col1, col2, col3 = st.columns([1, 1, 1])

# Médailles et couleurs
medals = ['🥇', '🥈', '🥉']
colors = ['#FFD700', '#C0C0C0', '#CD7F32']
positions = [col2, col1, col3]  # Pour afficher 2-1-3
podium_heights = ['120px', '150px', '100px']

for i, (idx, resto) in enumerate(top3.iterrows()):
    with positions[i]:
        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, {colors[i]}20 0%, {colors[i]}40 100%);
                border-radius: 15px;
                padding: 1.5rem;
                text-align: center;
                border: 3px solid {colors[i]};
                height: {podium_heights[i]};
                display: flex;
                flex-direction: column;
                justify-content: center;
            '>
                <div style='font-size: 3rem;'>{medals[i]}</div>
                <div style='font-size: 1.3rem; font-weight: bold; color: #2d3748; margin: 0.5rem 0;'>
                    {resto['nom']}
                </div>
                <div style='font-size: 2rem; font-weight: bold; color: {colors[i]};'>
                    {resto['score_final']:.1f}/100
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
            <div style='text-align: center; margin-top: 1rem; font-size: 0.9rem;'>
                ⏱️ {resto['temps_trajet']} min | ⭐ {resto['note']}/5 | 💰 {resto['prix']}€
            </div>
        """, unsafe_allow_html=True)

# Graphique radar pour le gagnant
st.markdown("---")
st.markdown("## 📊 Profil détaillé du gagnant")

winner = top3.iloc[0]

fig = go.Figure()

categories = ['Proximité', 'Qualité', 'Prix']
values = [
    winner['score_temps'] * 100,
    winner['score_note'] * 100,
    winner['score_prix'] * 100
]

fig.add_trace(go.Scatterpolar(
    r=values + [values[0]],
    theta=categories + [categories[0]],
    fill='toself',
    name=winner['nom'],
    line_color='#667eea',
    fillcolor='rgba(102, 126, 234, 0.3)'
))

fig.update_layout(
    polar=dict(
        radialaxis=dict(
            visible=True,
            range=[0, 100]
        )
    ),
    showlegend=False,
    height=400,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)'
)

st.plotly_chart(fig, use_container_width=True)

# Tableau complet
with st.expander("📋 Voir le classement complet"):
    display_df = restos_scores[['nom', 'temps_trajet', 'note', 'prix', 'score_final']].copy()
    display_df.columns = ['Restaurant', 'Temps (min)', 'Note /5', 'Prix (€)', 'Score']
    display_df['Score'] = display_df['Score'].round(1)
    display_df.index = range(1, len(display_df) + 1)
    st.dataframe(display_df, use_container_width=True)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #718096;'>Bon appétit ! 🥢</p>", unsafe_allow_html=True)