# app_dejeuner.py

import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import date

# ==============================
# Constantes et chemins
# ==============================

DATA_DIR = "data"
USERS_PATH = os.path.join(DATA_DIR, "users.csv")
TOPS_PATH = os.path.join(DATA_DIR, "tops.csv")
RESTAURANTS_PATH = "Restaurants.xlsx"


# ==============================
# Utils fichiers & données
# ==============================

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def charger_restaurants(path: str = RESTAURANTS_PATH) -> pd.DataFrame:
    """Charge la base de restaurants."""
    if not os.path.exists(path):
        st.error(f"Fichier {path} introuvable. Place-le dans le même dossier que app_dejeuner.py.")
        st.stop()
    df = pd.read_excel(path)
    return df


def load_users() -> pd.DataFrame:
    ensure_data_dir()
    if not os.path.exists(USERS_PATH):
        cols = ["user_id", "prenom", "nom", "password", "description"]
        return pd.DataFrame(columns=cols)
    return pd.read_csv(USERS_PATH, dtype=str)


def save_users(df: pd.DataFrame):
    ensure_data_dir()
    df.to_csv(USERS_PATH, index=False, encoding="utf-8")


def load_tops() -> pd.DataFrame:
    ensure_data_dir()
    if not os.path.exists(TOPS_PATH):
        cols = [
            "date",
            "user_id",
            "prenom",
            "nom",
            "Restau_1",
            "Restau_2",
            "Restau_3",
            "Score_1",
            "Score_2",
            "Score_3",
        ]
        return pd.DataFrame(columns=cols)
    return pd.read_csv(TOPS_PATH, dtype=str)


def save_tops(df: pd.DataFrame):
    ensure_data_dir()
    df.to_csv(TOPS_PATH, index=False, encoding="utf-8")


# ==============================
# Utils scoring restos
# ==============================

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

    low_is_best = True si, conceptuellement, on veut favoriser les valeurs basses.
    """
    if slider_val == 5:
        return None

    if slider_val > 5:
        # On préfère les valeurs hautes
        if low_is_best:
            score = 11 - serie
        else:
            score = serie
    else:
        # slider < 5 -> on préfère les valeurs basses
        if low_is_best:
            score = serie
        else:
            score = 11 - serie

    score = score.clip(lower=1, upper=10)
    return score


def calculer_score_global(df, coeffs, scores_dyn):
    """
    df : DataFrame filtré
    coeffs : dict nom_critère -> coefficient (float)
    scores_dyn : dict nom_critère -> série de scores (alignée sur df)
    """
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
        # Aucun critère -> moyenne simple des scores de base
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
# Utils similarité entre personnes
# ==============================

def calculer_similarites(tops_df: pd.DataFrame, current_user_id: str):
    """
    tops_df : dataframe filtré sur la date du jour.
    Retourne une liste de dicts :
      {"user_id", "prenom", "nom", "description", "score_sim", "restos_communs"}
    """
    if tops_df.empty:
        return []

    # On a besoin aussi du fichier users pour la description
    users_df = load_users()

    # Trouver le top de l'utilisateur courant
    my_rows = tops_df[tops_df["user_id"] == current_user_id]
    if my_rows.empty:
        return []

    my_row = my_rows.iloc[0]
    my_top = [my_row["Restau_1"], my_row["Restau_2"], my_row["Restau_3"]]
    my_pos = {r: i + 1 for i, r in enumerate(my_top) if isinstance(r, str)}

    similitudes = []

    others = tops_df[tops_df["user_id"] != current_user_id]

    for _, row in others.iterrows():
        other_top = [row["Restau_1"], row["Restau_2"], row["Restau_3"]]
        other_pos = {r: i + 1 for i, r in enumerate(other_top) if isinstance(r, str)}

        communs = set(my_pos.keys()) & set(other_pos.keys())
        if not communs:
            continue

        # scoring : (4 - rang_moi) + (4 - rang_autre) par resto commun
        score_sim = 0
        for resto in communs:
            score_sim += (4 - my_pos[resto]) + (4 - other_pos[resto])

        # Récup description
        u = users_df[users_df["user_id"] == row["user_id"]]
        desc = ""
        if not u.empty:
            desc = u.iloc[0].get("description", "")

        similitudes.append(
            {
                "user_id": row["user_id"],
                "prenom": row["prenom"],
                "nom": row["nom"],
                "description": desc,
                "score_sim": score_sim,
                "restos_communs": ", ".join(communs),
            }
        )

    similitudes.sort(key=lambda x: x["score_sim"], reverse=True)
    return similitudes


# ==============================
# Auth & session
# ==============================

def init_session():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None
    if "prenom" not in st.session_state:
        st.session_state["prenom"] = None
    if "nom" not in st.session_state:
        st.session_state["nom"] = None


def login_block():
    st.sidebar.header("👤 Connexion / Création de compte")

    prenom = st.sidebar.text_input("Prénom")
    nom = st.sidebar.text_input("Nom")
    password = st.sidebar.text_input("Mot de passe", type="password")
    description = st.sidebar.text_area(
        "Décris rapidement ce que tu aimes manger (optionnel)",
        height=80
    )

    if st.sidebar.button("Entrer"):
        if not prenom or not nom or not password:
            st.sidebar.error("Prénom, nom et mot de passe sont obligatoires.")
            return

        users_df = load_users()
        user_id = f"{prenom.strip()} {nom.strip()}"

        existing = users_df[users_df["user_id"] == user_id]

        if not existing.empty:
            # Utilisateur existe -> on vérifie le mot de passe
            stored_pwd = existing.iloc[0]["password"]
            if password == stored_pwd:
                st.session_state["logged_in"] = True
                st.session_state["user_id"] = user_id
                st.session_state["prenom"] = prenom.strip()
                st.session_state["nom"] = nom.strip()
                st.sidebar.success(f"Re-bonjour {prenom} !")
            else:
                st.sidebar.error("Mot de passe incorrect.")
        else:
            # Nouvel utilisateur -> on crée le compte
            new_row = {
                "user_id": user_id,
                "prenom": prenom.strip(),
                "nom": nom.strip(),
                "password": password,
                "description": description.strip() if description else "",
            }
            users_df = pd.concat([users_df, pd.DataFrame([new_row])], ignore_index=True)
            save_users(users_df)

            st.session_state["logged_in"] = True
            st.session_state["user_id"] = user_id
            st.session_state["prenom"] = prenom.strip()
            st.session_state["nom"] = nom.strip()
            st.sidebar.success(f"Bienvenue {prenom}, ton compte a été créé !")

    if st.session_state["logged_in"]:
        st.sidebar.markdown(
            f"✅ Connecté en tant que **{st.session_state['prenom']} {st.session_state['nom']}**"
        )
        if st.sidebar.button("Se déconnecter"):
            st.session_state["logged_in"] = False
            st.session_state["user_id"] = None
            st.session_state["prenom"] = None
            st.session_state["nom"] = None
            st.sidebar.info("Déconnecté.")


def delete_account_block():
    st.subheader("🗑️ Supprimer mon compte et mes réponses")
    st.caption("Ce n'est pas critique, tu peux supprimer ton identifiant à tout moment.")

    if st.button("Supprimer mon compte et toutes mes réponses"):
        user_id = st.session_state.get("user_id")
        if not user_id:
            st.warning("Aucun compte connecté.")
            return

        # Supprimer des users
        users_df = load_users()
        users_df = users_df[users_df["user_id"] != user_id]
        save_users(users_df)

        # Supprimer des tops
        tops_df = load_tops()
        tops_df = tops_df[tops_df["user_id"] != user_id]
        save_tops(tops_df)

        # Reset session
        st.session_state["logged_in"] = False
        st.session_state["user_id"] = None
        st.session_state["prenom"] = None
        st.session_state["nom"] = None

        st.success("Ton compte et tes réponses ont été supprimés.")
        st.stop()


# ==============================
# App principale
# ==============================

def main():
    st.set_page_config(page_title="App Déjeuner", page_icon="🍽️", layout="wide")

    init_session()
    login_block()

    st.title("🍽️ Choisis ton déjeuner idéal")

    if not st.session_state["logged_in"]:
        st.info("Connecte-toi dans la barre latérale pour commencer.")
        return

    df = charger_restaurants()

    # Nettoyage des NaN sur les colonnes de score
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

    st.write(
        "Réponds à quelques questions, on pondère les critères, "
        "et on te propose le **top 3** des restos qui te correspondent le mieux."
    )

    # ==========================
    # 1️⃣ Importance des critères
    # ==========================

    st.header("1️⃣ Tes priorités (importance de chaque critère)")

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
    # 2️⃣ Style de déjeuner
    # ==========================

    st.header("2️⃣ Style de déjeuner")

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
    # 3️⃣ Contraintes fortes
    # ==========================

    st.header("3️⃣ Contraintes fortes")

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
    if "Filtre_Type" in df_filtre.columns:
        types_dispos = sorted(df_filtre["Filtre_Type"].dropna().unique().tolist())
        no_go = st.multiselect(
            "Y a-t-il des **no-go** ? (types de resto à exclure)",
            options=types_dispos,
            help="Les types sélectionnés seront exclus des propositions."
        )

        if no_go:
            no_go_str = ", ".join([f"<span style='color:red'>{t}</span>" for t in no_go])
            st.markdown(f"No-go sélectionnés : {no_go_str}", unsafe_allow_html=True)

            df_filtre = df_filtre[~df_filtre["Filtre_Type"].isin(no_go)]
    else:
        st.warning("Colonne 'Filtre_Type' absente, impossible de gérer les no-go.")

    if df_filtre.empty:
        st.error("Aucun restaurant ne correspond à ces filtres (conventionnel / no-go). Allège un peu les contraintes 😉")
        st.stop()

    # ==========================
    # 4️⃣ Calcul des scores et top 3 / top 10
    # ==========================

    max_coeff_base = max(distance_coeff, prix_coeff, quantite_coeff, gourmandise_coeff)
    filtre_coeff_base = max_coeff_base if max_coeff_base > 0 else 1

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
        "chaleur": None,
        "healthy": None,
        "sandwich": None,
    }

    if "Filtre_Chaleur" in df_filtre.columns:
        score_chaleur = construire_score_directionnel(df_filtre["Filtre_Chaleur"], chaleur_slider, low_is_best=False)
        scores_dyn["chaleur"] = score_chaleur
        if score_chaleur is not None:
            coeffs["chaleur"] = filtre_coeff_base

    if "Filtre_Healthy" in df_filtre.columns:
        score_healthy = construire_score_directionnel(df_filtre["Filtre_Healthy"], healthy_slider, low_is_best=False)
        scores_dyn["healthy"] = score_healthy
        if score_healthy is not None:
            coeffs["healthy"] = filtre_coeff_base

    if "Filtre_Sandwich" in df_filtre.columns:
        score_sandwich = construire_score_directionnel(df_filtre["Filtre_Sandwich"], sandwich_slider, low_is_best=False)
        scores_dyn["sandwich"] = score_sandwich
        if score_sandwich is not None:
            coeffs["sandwich"] = filtre_coeff_base

    df_scored = df_filtre.copy()
    df_scored = calculer_score_global(df_scored, coeffs, scores_dyn)
    df_scored = df_scored.sort_values("Score_Global", ascending=False)

    st.header("4️⃣ Résultat")

    st.subheader("🏆 Ton Top 3")
    top3 = df_scored.head(3)

    if top3.empty:
        st.warning("Aucun restaurant après calcul des scores. Essaie de relâcher quelques contraintes.")
    else:
        cols_top = st.columns(len(top3))

        for idx, (_, row) in enumerate(top3.iterrows()):
            with cols_top[idx]:
                nom_restau = row["Restaurant"] if "Restaurant" in row else f"Restaurant #{idx+1}"
                st.markdown(f"### #{idx+1} {nom_restau}")
                if "Filtre_Type" in row:
                    st.caption(f"Type : {row['Filtre_Type']}")
                if "Distance (m à pieds)" in row:
                    try:
                        dist_m = int(row["Distance (m à pieds)"])
                        st.write(f"🚶‍♀️ Distance : **{dist_m} m**")
                    except Exception:
                        pass

                st.metric("Score global", f"{row['Score_Global']}/10")
                st.progress(min(max(row["Score_Global"] / 10, 0), 1))

                st.write("**Détails des scores :**")
                st.write(
                    f"- Distance : {row['Score_Distance'] if 'Score_Distance' in row else 'n.a.'}\n"
                    f"- Prix : {row['Score_Prix'] if 'Score_Prix' in row else 'n.a.'}\n"
                    f"- Quantité : {row['Score_Quantite'] if 'Score_Quantite' in row else 'n.a.'}\n"
                    f"- Gourmandise : {row['Score_Gourmandise'] if 'Score_Gourmandise' in row else 'n.a.'}"
                )

    # Top 10
    show_top10 = st.toggle("📜 Voir le top 10")
    if show_top10:
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

        if not colonnes_affichage:
            st.dataframe(top10)
        else:
            df_aff = top10[colonnes_affichage].reset_index(drop=True)
            if "Score_Global" in df_aff.columns:
                st.dataframe(
                    df_aff.style.highlight_max(subset=["Score_Global"], color="#d4edda")
                )
            else:
                st.dataframe(df_aff)

    # ==========================
    # 5️⃣ Sauvegarde du top 3 du jour + similarités
    # ==========================

    st.header("5️⃣ Partage & similarités")

    today_str = date.today().isoformat()
    user_id = st.session_state["user_id"]
    prenom = st.session_state["prenom"]
    nom = st.session_state["nom"]

    if not top3.empty:
        if st.button("💾 Enregistrer mon top 3 pour aujourd'hui"):
            tops_df = load_tops()

            # On supprime l'éventuel enregistrement existant pour ce user et ce jour
            mask = ~((tops_df["user_id"] == user_id) & (tops_df["date"] == today_str))
            tops_df = tops_df[mask]

            # Construire la nouvelle ligne
            r1 = top3.iloc[0]["Restaurant"] if "Restaurant" in top3.columns else ""
            r2 = top3.iloc[1]["Restaurant"] if len(top3) > 1 and "Restaurant" in top3.columns else ""
            r3 = top3.iloc[2]["Restaurant"] if len(top3) > 2 and "Restaurant" in top3.columns else ""

            s1 = top3.iloc[0]["Score_Global"] if "Score_Global" in top3.columns else ""
            s2 = top3.iloc[1]["Score_Global"] if len(top3) > 1 and "Score_Global" in top3.columns else ""
            s3 = top3.iloc[2]["Score_Global"] if len(top3) > 2 and "Score_Global" in top3.columns else ""

            new_row = {
                "date": today_str,
                "user_id": user_id,
                "prenom": prenom,
                "nom": nom,
                "Restau_1": r1,
                "Restau_2": r2,
                "Restau_3": r3,
                "Score_1": str(s1),
                "Score_2": str(s2),
                "Score_3": str(s3),
            }

            tops_df = pd.concat([tops_df, pd.DataFrame([new_row])], ignore_index=True)
            save_tops(tops_df)

            st.success("Ton top 3 du jour a été enregistré ✅")

    # Similarités
    tops_df = load_tops()
    tops_today = tops_df[tops_df["date"] == today_str]

    st.subheader("👥 Qui te ressemble aujourd'hui ?")
    if tops_today.empty:
        st.info("Personne n'a encore enregistré son top 3 aujourd'hui.")
    else:
        similitudes = calculer_similarites(tops_today, user_id)
        if not any((tops_today["user_id"] == user_id)):
            st.caption("Enregistre ton top 3 pour voir avec qui tu matches 😉")
        elif not similitudes:
            st.info("Personne n'a de resto en commun avec toi dans le top 3 aujourd'hui.")
        else:
            for s in similitudes:
                st.markdown(
                    f"**{s['prenom']} {s['nom']}** — Score de similarité : **{s['score_sim']}**"
                )
                if s["description"]:
                    st.caption(f"_\"{s['description']}\"_")
                st.write(f"🌯 Restos en commun dans le top 3 : **{s['restos_communs']}**")
                st.markdown("---")

    # ==========================
    # 6️⃣ Suppression de compte
    # ==========================

    delete_account_block()


if __name__ == "__main__":
    main()
