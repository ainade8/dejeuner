import streamlit as st
import pandas as pd
import os
from datetime import date

# ============================
# Constantes
# ============================

DATA_DIR = "data"
USERS_PATH = os.path.join(DATA_DIR, "users.csv")
SWIPES_PATH = os.path.join(DATA_DIR, "tinder_swipes.csv")
RESTAURANTS_PATH = "Restaurants.xlsx"


# ============================
# Utils fichiers
# ============================

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def load_users() -> pd.DataFrame:
    ensure_data_dir()
    if not os.path.exists(USERS_PATH):
        cols = ["user_id", "prenom", "nom", "password", "description"]
        return pd.DataFrame(columns=cols)
    return pd.read_csv(USERS_PATH, dtype=str)


def save_users(df: pd.DataFrame):
    ensure_data_dir()
    df.to_csv(USERS_PATH, index=False, encoding="utf-8")


def load_swipes() -> pd.DataFrame:
    ensure_data_dir()
    if not os.path.exists(SWIPES_PATH):
        cols = ["date", "user_id", "prenom", "nom", "restaurant", "decision"]
        return pd.DataFrame(columns=cols)
    return pd.read_csv(SWIPES_PATH, dtype=str)


def save_swipes(df: pd.DataFrame):
    ensure_data_dir()
    df.to_csv(SWIPES_PATH, index=False, encoding="utf-8")


def load_restaurants() -> pd.DataFrame:
    if not os.path.exists(RESTAURANTS_PATH):
        st.error(f"Fichier {RESTAURANTS_PATH} introuvable. Place-le dans le même dossier que app_tinder_resto.py.")
        st.stop()
    df = pd.read_excel(RESTAURANTS_PATH)
    if "Restaurant" not in df.columns:
        st.error("Le fichier Restaurants.xlsx doit contenir une colonne 'Restaurant'.")
        st.stop()
    return df


# ============================
# Session & Auth
# ============================

def init_session():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None
    if "prenom" not in st.session_state:
        st.session_state["prenom"] = None
    if "nom" not in st.session_state:
        st.session_state["nom"] = None
    if "swipe_index" not in st.session_state:
        st.session_state["swipe_index"] = 0
    if "last_feedback" not in st.session_state:
        st.session_state["last_feedback"] = ""


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
            stored_pwd = existing.iloc[0]["password"]
            if password == stored_pwd:
                st.session_state["logged_in"] = True
                st.session_state["user_id"] = user_id
                st.session_state["prenom"] = prenom.strip()
                st.session_state["nom"] = nom.strip()
                st.session_state["swipe_index"] = 0
                st.session_state["last_feedback"] = ""
                st.sidebar.success(f"Re-bonjour {prenom} !")
            else:
                st.sidebar.error("Mot de passe incorrect.")
        else:
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
            st.session_state["swipe_index"] = 0
            st.session_state["last_feedback"] = ""
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
            st.session_state["swipe_index"] = 0
            st.session_state["last_feedback"] = ""
            st.sidebar.info("Déconnecté.")


def delete_account_block():
    st.subheader("🗑️ Supprimer mon compte et mes swipes")
    st.caption("Tu peux supprimer ton compte et toutes tes réponses à tout moment.")

    if st.button("Supprimer mon compte et toutes mes réponses"):
        user_id = st.session_state.get("user_id")
        if not user_id:
            st.warning("Aucun compte connecté.")
            return

        users_df = load_users()
        users_df = users_df[users_df["user_id"] != user_id]
        save_users(users_df)

        swipes_df = load_swipes()
        swipes_df = swipes_df[swipes_df["user_id"] != user_id]
        save_swipes(swipes_df)

        st.session_state["logged_in"] = False
        st.session_state["user_id"] = None
        st.session_state["prenom"] = None
        st.session_state["nom"] = None
        st.session_state["swipe_index"] = 0
        st.session_state["last_feedback"] = ""

        st.success("Ton compte et toutes tes réponses ont été supprimés.")
        st.stop()


# ============================
# Swipe Logic
# ============================

def render_resto_card(row):
    """Affiche une carte sexy pour un resto."""
    name = row.get("Restaurant", "Restaurant mystère")
    type_txt = row.get("Filtre_Type", "")
    dist_txt = ""
    if "Distance (m à pieds)" in row and not pd.isna(row["Distance (m à pieds)"]):
        try:
            dist_txt = f"{int(row['Distance (m à pieds)'])} m à pieds"
        except Exception:
            pass

    subline = " • ".join([x for x in [type_txt, dist_txt] if x])

    card_html = f"""
    <div style="
        border-radius: 18px;
        padding: 22px;
        background: linear-gradient(135deg, #ffe6f0, #ffffff);
        box-shadow: 0 10px 25px rgba(0,0,0,0.08);
        margin: 10px 0 25px 0;
        border: 1px solid rgba(255, 192, 203, 0.5);
    ">
        <div style="font-size: 24px; font-weight: 700; margin-bottom: 6px; color: #333;">
            {name}
        </div>
        <div style="font-size: 13px; color: #777; margin-bottom: 10px;">
            {subline}
        </div>
        <div style="font-size: 13px; color: #999;">
            Swipe mentalement : est-ce que tu te verrais déjeuner là ?
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def swipe_tab(df: pd.DataFrame):
    st.header("💘 Swipe tes restos")

    today_str = date.today().isoformat()
    user_id = st.session_state["user_id"]

    # Boutons Reset & Retour arrière
    col_reset, col_back, _ = st.columns([1.5, 1.5, 3])
    with col_reset:
        if st.button("🧹 Réinitialiser mes choix d'aujourd'hui"):
            swipes_df = load_swipes()
            if not swipes_df.empty:
                mask = ~((swipes_df["user_id"] == user_id) & (swipes_df["date"] == today_str))
                swipes_df = swipes_df[mask]
                save_swipes(swipes_df)
            st.session_state["swipe_index"] = 0
            st.session_state["last_feedback"] = ""
            st.rerun()

    with col_back:
        if st.button("↩️ Revenir au précédent"):
            idx = st.session_state.get("swipe_index", 0)
            if idx <= 0:
                st.caption("Tu es déjà au début 😉")
            else:
                # On supprime le dernier swipe du jour pour cet utilisateur (quel que soit le resto)
                swipes_df = load_swipes()
                if not swipes_df.empty:
                    mask = (swipes_df["user_id"] == user_id) & (swipes_df["date"] == today_str)
                    last_swipes = swipes_df[mask]
                    if not last_swipes.empty:
                        last_idx = last_swipes.index[-1]
                        swipes_df = swipes_df.drop(last_idx)
                        save_swipes(swipes_df)
                st.session_state["swipe_index"] = idx - 1
                st.session_state["last_feedback"] = ""
                st.rerun()

    idx = st.session_state.get("swipe_index", 0)
    n = len(df)

    if n == 0:
        st.info("Aucun restaurant dans la base.")
        return

    if idx >= n:
        st.success("Tu as vu tous les restos ! Recommence ou va voir tes matchs 💘")
        return

    row = df.iloc[idx]
    render_resto_card(row)

    resto_name = row["Restaurant"]
    prenom = st.session_state["prenom"]
    nom = st.session_state["nom"]

    # On regarde les likes des autres AUJOURD'HUI
    swipes_df_before = load_swipes()
    if not swipes_df_before.empty:
        likes_others = swipes_df_before[
            (swipes_df_before["restaurant"] == resto_name)
            & (swipes_df_before["decision"] == "like")
            & (swipes_df_before["user_id"] != user_id)
            & (swipes_df_before["date"] == today_str)
        ]
    else:
        likes_others = pd.DataFrame(columns=["user_id", "prenom", "nom", "restaurant", "decision", "date"])

    col_no, col_yes = st.columns(2)
    with col_no:
        no_btn = st.button("❌ Pas chaud", use_container_width=True)
    with col_yes:
        yes_btn = st.button("❤️ Chaud", use_container_width=True)

    feedback = ""

    if yes_btn:
        swipes_df = load_swipes()
        new_row = {
            "date": today_str,
            "user_id": user_id,
            "prenom": prenom,
            "nom": nom,
            "restaurant": resto_name,
            "decision": "like",
        }
        swipes_df = pd.concat([swipes_df, pd.DataFrame([new_row])], ignore_index=True)
        save_swipes(swipes_df)

        if not likes_others.empty:
            feedback = "MATCH 💥"
            names = [f"{r['prenom']} {r['nom']}" for _, r in likes_others.iterrows()]
            names_str = ", ".join(sorted(set(names)))
            st.markdown(
                f"<div style='padding:12px 18px; border-radius:999px; background:#ffe6f0; "
                f"display:inline-block; font-weight:600; color:#c2185b; margin-top:5px;'>"
                f"MATCH avec {names_str} sur **{resto_name}** 💘"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            feedback = "Premier like sur ce resto, tu ouvres la voie 😉"
            st.caption(feedback)

        st.session_state["swipe_index"] = idx + 1
        st.session_state["last_feedback"] = feedback
        st.rerun()

    if no_btn:
        swipes_df = load_swipes()
        new_row = {
            "date": today_str,
            "user_id": user_id,
            "prenom": prenom,
            "nom": nom,
            "restaurant": resto_name,
            "decision": "dislike",
        }
        swipes_df = pd.concat([swipes_df, pd.DataFrame([new_row])], ignore_index=True)
        save_swipes(swipes_df)

        if not likes_others.empty:
            st.caption("Dommage, t'as manqué un match 😅 (mais t'as le droit d'avoir du goût différent)")
        st.session_state["swipe_index"] = idx + 1
        st.session_state["last_feedback"] = ""
        st.rerun()

    if st.session_state.get("last_feedback"):
        st.caption(st.session_state["last_feedback"])


# ============================
# Matchs tab
# ============================

def matches_tab():
    st.header("💞 Mes matchs (aujourd'hui)")

    user_id = st.session_state["user_id"]
    swipes_df = load_swipes()

    if swipes_df.empty:
        st.info("Tu n'as encore swipé aucun resto.")
        return

    today_str = date.today().isoformat()
    swipes_df = swipes_df[swipes_df["date"] == today_str]

    if swipes_df.empty:
        st.info("Aucun swipe pour aujourd'hui (toi ou les autres).")
        return

    my_likes = swipes_df[
        (swipes_df["user_id"] == user_id) & (swipes_df["decision"] == "like")
    ]

    if my_likes.empty:
        st.info("Tu n'as pas encore liké de resto aujourd'hui. Va swiperrr 💘")
        return

    matches_data = []
    all_matched_people = set()

    for _, row in my_likes.iterrows():
        resto = row["restaurant"]
        others = swipes_df[
            (swipes_df["restaurant"] == resto)
            & (swipes_df["decision"] == "like")
            & (swipes_df["user_id"] != user_id)
        ]
        if others.empty:
            continue

        names = sorted(
            set(f"{r['prenom']} {r['nom']}" for _, r in others.iterrows())
        )
        for n in names:
            all_matched_people.add(n)

        matches_data.append(
            {
                "Restaurant": resto,
                "Autres personnes": ", ".join(names),
            }
        )

    if not matches_data:
        st.info("Pour l'instant, aucun resto que tu as liké n'a été liké par quelqu'un d'autre aujourd'hui.")
        return

    st.subheader("🍽️ Restos en commun (MATCH aujourd'hui)")
    df_matches = pd.DataFrame(matches_data).drop_duplicates()
    st.dataframe(df_matches, use_container_width=True)

    st.subheader("👥 Les personnes avec qui tu as matché aujourd'hui")
    for person in sorted(all_matched_people):
        st.markdown(f"- **{person}**")


# ============================
# Main app
# ============================

def main():
    st.set_page_config(page_title="Tinder des restos", page_icon="💘", layout="wide")

    init_session()
    login_block()

    st.title("💘 Tinder des restos")

    if not st.session_state["logged_in"]:
        st.info("Connecte-toi dans la barre latérale pour commencer à swiper.")
        return

    df_restos = load_restaurants()

    tab_swipe, tab_matches = st.tabs(["💖 Swipe", "💞 Mes matchs"])

    with tab_swipe:
        swipe_tab(df_restos)

    with tab_matches:
        matches_tab()

    st.markdown("---")
    delete_account_block()


if __name__ == "__main__":
    main()
