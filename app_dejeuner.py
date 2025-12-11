# app_dejeuner.py

import streamlit as st
import pandas as pd
import numpy as np
import os


# ==============================
# Utils
# ==============================

def charger_restaurants(path: str = "Restaurants.xlsx") -> pd.DataFrame:
    """Charge la base de restaurants."""
    if not os.path.exists(path):
        st.error(f"Fichier {path} introuvable. Place-le dans le même dossier que app_dejeuner.py.")
        st.stop()
    df = pd.read_excel(path)
    return df


def construire_score_directionnel(serie, slider_val, low_is_best=False):
    """
    Transforme une série de 1 à 10 en un score aligné avec la préférence de l'utilisateur.

    slider_val va de 0 à 10 :
      - 5 = pas de préférence -> renvoie None (pas utilisé)
      - >5 = préfère 'haut' (10)
      - <5 = préfère 'bas' (1)

    low_is_best = False pour :
        - Chaleur : 1 = froid, 10 = chaud
        - Healthy : 1 = pas healthy, 10 = healthy
        - Sandwich : 1 = bol, 10 = sandwich

    low_is_best = True si, conceptuellement, on veut favoriser les valeurs basses
    (ici on n’en a pas vraiment besoin, mais je laisse l’option).
    """
    # Pas de critère si pile au milieu
    if slider_val == 5:
        return None

    if slider_val > 5:
        # On préfère les valeurs "hautes"
        if low_is_best:
            # Si on préfère haut mais que le "bon" est en bas, on inverse
            score = 11 - serie
        else:
            score = serie
    else:
        # slider < 5 -> on préfère les valeurs "basses"
        if low_is_best:
            score = serie
        else:
            score = 11 - serie

    # On borne par précaution
    score = score.clip(lower=1, upper=10)
    return score


def calculer_score_global(df, coeffs, scores_dyn):
    """
    df : DataFrame filtré
    coeffs : dict nom_critère -> coefficient (float)
    scores_dyn : dict nom_critère -> série de scores (alignée sur df)
    """
    # Construit une matrice de contributions coeff * score
    contributions = []
    poids = []

    for name, coeff in coeffs.items():
        if coeff is None or coeff <= 0:
            continue
        score_serie = scores_dyn.get(name)
        if score_serie is None:
            continue
        contributions.append(coeff * score_serie)
        poids.append(coeff)

    if len(contributions) == 0:
        # Aucun critère -> fallback : moyenne simple des scores de base
        base_cols = ["Score_Distance", "Score_Prix", "Score_Quantite", "Score_Gourmandise"]
        existantes = [c for c in base_cols if c in df.columns]
        if not existantes:
            st.error("Impossible de calculer un score global : aucune colonne de score trouvée.")
            st.stop()
        df["Score_Global"] = df[existantes].mean(axis=1)
        df["Score_Global"] = df["Score_Global"].round(2)
        st.info("Aucun critère sélectionné : classement basé sur la moyenne des scores de base.")
        return df

    total_poids = sum(poids)
    score_global = sum(contributions) / total_poids
    df["Score_Global"] = score_global.round(2)
    return df


# ==============================
# App
# ==============================

def main():
    st.set_page_config(page_title="App Déjeuner", page_icon="🍽️", layout="wide")

    st.title("🍽️ Choisis ton déjeuner idéal")
    st.write(
        "Réponds à quelques questions, on pondère les critères, "
        "et on te propose le **top 3** des restos qui te correspondent le mieux."
    )

    df = charger_restaurants()

    # S'assure qu'il n'y a pas de NaN sur les colonnes de score (on remplace par la moyenne si besoin)
    score_cols = [
        "Score_Distance",
        "Score_Prix",
        "Score_Quantite",
        "Score_Gourmandise",
        "Filtre_Chaleur",
        "Filtre_Healthy",
        "Filtre_Sandwich",
    ]
    for col in score_cols:
        if col in df.columns and df[col].isna().any():
            df[col].fillna(df[col].mean(), inplace=True)

    # ==========================
    # Bloc 1 : Importance des scores "classiques"
    # ==========================

    st.header("1️⃣ Tes priorités")

    col1, col2 = st.columns(2)

    with col1:
        distance_coeff = st.slider(
            "À quel point tu veux un resto **proche** ?",
            min_value=0,
            max_value=10,
            value=5,
            help="0 = la distance ne compte pas, 10 = c'est hyper important."
        )
        if distance_coeff == 0:
            st.caption("🚶‍♀️ La distance n'est **pas un critère** pour toi.")
        else:
            st.caption(f"🚶‍♀️ Importance de la distance : **{distance_coeff}/10**")

        prix_coeff = st.slider(
            "Est-ce que le **prix** compte ?",
            min_value=0,
            max_value=10,
            value=5,
            help="0 = le prix ne compte pas, 10 = tu veux optimiser le budget."
        )
        if prix_coeff == 0:
            st.caption("💸 Le prix n'est **pas un critère** pour toi.")
        else:
            st.caption(f"💸 Importance du prix : **{prix_coeff}/10**")

    with col2:
        quantite_coeff = st.slider(
            "T'as **très faim** ou ce n'est pas un critère ? (quantité)",
            min_value=0,
            max_value=10,
            value=5,
            help="0 = la quantité ne compte pas, 10 = tu veux bien manger."
        )
        if quantite_coeff == 0:
            st.caption("🍽️ La quantité n'est **pas un critère** pour toi.")
        else:
            st.caption(f"🍽️ Importance de la quantité : **{quantite_coeff}/10**")

        gourmandise_coeff = st.slider(
            "Tu cherches du **gourmand** ou pas vraiment ?",
            min_value=0,
            max_value=10,
            value=5,
            help="0 = la gourmandise ne compte pas, 10 = tu veux te faire plaisir."
        )
        if gourmandise_coeff == 0:
            st.caption("🤤 La gourmandise n'est **pas un critère** pour toi.")
        else:
            st.caption(f"🤤 Importance de la gourmandise : **{gourmandise_coeff}/10**")

    # ==========================
    # Bloc 2 : Filtres directionnels (chaud/froid, healthy, sandwich/bol)
    # ==========================

    st.header("2️⃣ Style de déjeuner")

    max_coeff_base = max(distance_coeff, prix_coeff, quantite_coeff, gourmandise_coeff)
    # Si aucun critère de base sélectionné, les filtres prendront coeff = 1
    filtre_coeff_base = max_coeff_base if max_coeff_base > 0 else 1

    col3, col4, col5 = st.columns(3)

    with col3:
        chaleur_slider = st.slider(
            "Plutôt **froid** ou **chaud** ?",
            min_value=0,
            max_value=10,
            value=5,
            help="0 = très froid, 10 = très chaud, 5 = peu importe."
        )
        if chaleur_slider == 5:
            st.caption("🌡️ Température : **pas un critère**.")
        elif chaleur_slider > 5:
            st.caption("🌡️ Tu es plutôt d'humeur **chaud** 🔥")
        else:
            st.caption("🌡️ Tu es plutôt d'humeur **froid** 🧊")

    with col4:
        healthy_slider = st.slider(
            "Tu veux du **healthy** ?",
            min_value=0,
            max_value=10,
            value=5,
            help="0 = pas healthy (comfort food), 10 = très healthy, 5 = peu importe."
        )
        if healthy_slider == 5:
            st.caption("🥗 Healthy : **pas un critère**.")
        elif healthy_slider > 5:
            st.caption("🥗 Tu penches vers du **healthy**.")
        else:
            st.caption("🍔 Tu penches vers du **pas trop healthy** (comfort food).")

    with col5:
        sandwich_slider = st.slider(
            "Plutôt **bol** ou **sandwich** ?",
            min_value=0,
            max_value=10,
            value=5,
            help="0 = bol, 10 = sandwich, 5 = peu importe."
        )
        if sandwich_slider == 5:
            st.caption("🥪 / 🥣 Format : **pas un critère**.")
        elif sandwich_slider > 5:
            st.caption("🥪 Tu es plutôt dans un mood **sandwich**.")
        else:
            st.caption("🥣 Tu es plutôt dans un mood **bol**.")

    # ==========================
    # Bloc 3 : Filtres "durs" (conventionnel + no-go)
    # ==========================

    st.header("3️⃣ Contraintes fortes")

    # Filtre conventionnel (0/1)
    col6, col7 = st.columns(2)

    with col6:
        conv_choice = st.radio(
            "Tu veux une solution de déjeuner plutôt **conventionnelle** ?",
            options=["Peu importe", "Oui, conventionnel uniquement"],
            index=0,
            help="Si tu choisis 'Oui', on ne garde que les restaurants marqués comme conventionnels."
        )

    df_filtre = df.copy()

    if conv_choice == "Oui, conventionnel uniquement":
        if "Filtre_Convention" in df_filtre.columns:
            df_filtre = df_filtre[df_filtre["Filtre_Convention"] == 1]
        else:
            st.warning("Colonne 'Filtre_Convention' absente, impossible d'appliquer ce filtre.")

    # No-go sur Filtre_Type
    with col7:
        if "Filtre_Type" in df_filtre.columns:
            types_dispos = sorted(df_filtre["Filtre_Type"].dropna().unique().tolist())
            no_go = st.multiselect(
                "Y a-t-il des **no-go** ? (types de resto à exclure)",
                options=types_dispos,
                help="Les types sélectionnés seront exclus des propositions."
            )

            if no_go:
                # Affichage en rouge des no-go
                no_go_str = ", ".join([f"<span style='color:red'>{t}</span>" for t in no_go])
                st.markdown(f"No-go sélectionnés : {no_go_str}", unsafe_allow_html=True)

                df_filtre = df_filtre[~df_filtre["Filtre_Type"].isin(no_go)]
        else:
            st.warning("Colonne 'Filtre_Type' absente, impossible de gérer les no-go.")

    if df_filtre.empty:
        st.error("Aucun restaurant ne correspond à ces filtres (conventionnel / no-go). Allège un peu les contraintes 😉")
        st.stop()

    # ==========================
    # Calcul des scores dynamiques
    # ==========================

    # 1) Scores "classiques" : on utilise directement les colonnes existantes
    scores_dyn = {}

    scores_dyn["distance"] = df_filtre["Score_Distance"] if "Score_Distance" in df_filtre.columns else None
    scores_dyn["prix"] = df_filtre["Score_Prix"] if "Score_Prix" in df_filtre.columns else None
    scores_dyn["quantite"] = df_filtre["Score_Quantite"] if "Score_Quantite" in df_filtre.columns else None
    scores_dyn["gourmandise"] = df_filtre["Score_Gourmandise"] if "Score_Gourmandise" in df_filtre.columns else None

    coeffs = {
        "distance": distance_coeff,
        "prix": prix_coeff,
        "quantite": quantite_coeff,
        "gourmandise": gourmandise_coeff,
        "chaleur": None,         # on les remplira en dessous
        "healthy": None,
        "sandwich": None,
    }

    # 2) Chaleur
    if "Filtre_Chaleur" in df_filtre.columns:
        score_chaleur = construire_score_directionnel(df_filtre["Filtre_Chaleur"], chaleur_slider, low_is_best=False)
        scores_dyn["chaleur"] = score_chaleur
        if score_chaleur is not None:
            coeffs["chaleur"] = filtre_coeff_base

    # 3) Healthy
    if "Filtre_Healthy" in df_filtre.columns:
        score_healthy = construire_score_directionnel(df_filtre["Filtre_Healthy"], healthy_slider, low_is_best=False)
        scores_dyn["healthy"] = score_healthy
        if score_healthy is not None:
            coeffs["healthy"] = filtre_coeff_base

    # 4) Sandwich / bol
    if "Filtre_Sandwich" in df_filtre.columns:
        score_sandwich = construire_score_directionnel(df_filtre["Filtre_Sandwich"], sandwich_slider, low_is_best=False)
        scores_dyn["sandwich"] = score_sandwich
        if score_sandwich is not None:
            coeffs["sandwich"] = filtre_coeff_base

    # ==========================
    # Bouton de calcul
    # ==========================

    st.header("4️⃣ Résultat")

    if "show_top10" not in st.session_state:
        st.session_state["show_top10"] = False

    col_btn1, col_btn2 = st.columns([2, 1])

    with col_btn1:
        lancer = st.button("🔍 Trouver mon déjeuner idéal")

    with col_btn2:
        if st.button("📜 Voir / masquer le top 10"):
            st.session_state["show_top10"] = not st.session_state["show_top10"]

    if lancer:
        # Calcul du score global
        df_scored = df_filtre.copy()
        df_scored = calculer_score_global(df_scored, coeffs, scores_dyn)

        # Tri décroissant
        df_scored = df_scored.sort_values("Score_Global", ascending=False)

        # Affichage Top 3
        st.subheader("🏆 Ton Top 3")

        top3 = df_scored.head(3)

        if top3.empty:
            st.warning("Aucun restaurant après calcul des scores. Essaie de relâcher quelques contraintes.")
        else:
            cols_top = st.columns(len(top3))

            for idx, (_, row) in enumerate(top3.iterrows()):
                with cols_top[idx]:
                    st.markdown(f"### #{idx+1} {row['Restaurant']}")
                    if "Filtre_Type" in row:
                        st.caption(f"Type : {row['Filtre_Type']}")
                    if "Distance (m à pieds)" in row:
                        st.write(f"🚶‍♀️ Distance : **{int(row['Distance (m à pieds)'])} m**")

                    st.metric("Score global", f"{row['Score_Global']}/10")
                    # Barre de progression sur base 10
                    st.progress(min(max(row["Score_Global"] / 10, 0), 1))

                    # Petit récap des scores principaux
                    st.write("**Détails des scores :**")
                    st.write(
                        f"- Distance : {row['Score_Distance'] if 'Score_Distance' in row else 'n.a.'}\n"
                        f"- Prix : {row['Score_Prix'] if 'Score_Prix' in row else 'n.a.'}\n"
                        f"- Quantité : {row['Score_Quantite'] if 'Score_Quantite' in row else 'n.a.'}\n"
                        f"- Gourmandise : {row['Score_Gourmandise'] if 'Score_Gourmandise' in row else 'n.a.'}"
                    )

        # Affichage Top 10 détaillé (toggle)
        if st.session_state["show_top10"]:
            st.subheader("📜 Top 10 détaillé")

            top10 = df_scored.head(10).copy()
            colonnes_affichage = [
                "Restaurant",
                "Filtre_Type",
                "Distance (m à pieds)",
                "Score_Global",
                "Score_Distance",
                "Score_Prix",
                "Score_Quantite",
                "Score_Gourmandise",
            ]
            colonnes_affichage = [c for c in colonnes_affichage if c in top10.columns]

            st.dataframe(
                top10[colonnes_affichage]
                .reset_index(drop=True)
                .style.highlight_max(subset=["Score_Global"], color="#d4edda")
            )
        else:
            st.caption("Clique sur **« Voir / masquer le top 10 »** pour dérouler la liste complète.")


if __name__ == "__main__":
    main()
