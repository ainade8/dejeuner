# app_tinder_resto.py

import streamlit as st
import pandas as pd
import os
import random
from datetime import date

# ============================
# Constantes
# ============================

DATA_DIR = "data"
USERS_PATH = os.path.join(DATA_DIR, "users.csv")
SWIPES_PATH = os.path.join(DATA_DIR, "tinder_swipes.csv")
RESTAURANTS_PATH = "Restaurants.xlsx"

ADMIN_USER_ID = "admin admin"


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
    if "is_admin" not in st.session_state:
        st.session_state["is_admin"] = False
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
    if "match_popup" not in st.session_state:
        st.session_state["match_popup"] = {"show": False, "resto": None, "people": [], "index": 0}


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

        # === Cas ADMIN ===
        if prenom.strip().lower() == "admin" and nom.strip().lower() == "admin":
            if password == "admin":
                st.session_state["logged_in"] = True
                st.session_state["is_admin"] = True
                st.session_state["user_id"] = ADMIN_USER_ID
                st.session_state["prenom"] = "admin"
                st.session_state["nom"] = "admin"
                st.session_state["swipe_index"] = 0
                st.session_state["last_feedback"] = ""
                st.session_state["match_popup"] = {"show": False, "resto": None, "people": [], "index": 0}
                st.sidebar.success("Connecté en tant qu'admin.")
            else:
                st.sidebar.error("Mot de passe admin incorrect.")
            return

        # === Cas utilisateur normal ===
        users_df = load_users()
        user_id = f"{prenom.strip()} {nom.strip()}"
        existing = users_df[users_df["user_id"] == user_id]

        if not existing.empty:
            stored_pwd = existing.iloc[0]["password"]
            if password == stored_pwd:
                st.session_state["logged_in"] = True
                st.session_state["is_admin"] = False
                st.session_state["user_id"] = user_id
                st.session_state["prenom"] = prenom.strip()
                st.session_state["nom"] = nom.strip()
                st.session_state["swipe_index"] = 0
                st.session_state["last_feedback"] = ""
                st.session_state["match_popup"] = {"show": False, "resto": None, "people": [], "index": 0}
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
            st.session_state["is_admin"] = False
            st.session_state["user_id"] = user_id
            st.session_state["prenom"] = prenom.strip()
            st.session_state["nom"] = nom.strip()
            st.session_state["swipe_index"] = 0
            st.session_state["last_feedback"] = ""
            st.session_state["match_popup"] = {"show": False, "resto": None, "people": [], "index": 0}
            st.sidebar.success(f"Bienvenue {prenom}, ton compte a été créé !")

    if st.session_state["logged_in"]:
        if st.session_state["is_admin"]:
            st.sidebar.markdown("✅ Connecté en tant que **admin**")
        else:
            st.sidebar.markdown(
                f"✅ Connecté en tant que **{st.session_state['prenom']} {st.session_state['nom']}**"
            )
        if st.sidebar.button("Se déconnecter"):
            st.session_state["logged_in"] = False
            st.session_state["is_admin"] = False
            st.session_state["user_id"] = None
            st.session_state["prenom"] = None
            st.session_state["nom"] = None
            st.session_state["swipe_index"] = 0
            st.session_state["last_feedback"] = ""
            st.session_state["match_popup"] = {"show": False, "resto": None, "people": [], "index": 0}
            st.sidebar.info("Déconnecté.")


def delete_account_block():
    st.subheader("🗑️ Supprimer mon compte et mes swipes")
    st.caption("Tu peux supprimer ton compte et toutes tes réponses à tout moment.")

    if st.session_state.get("is_admin"):
        st.info("Tu es connecté en admin, gère les suppressions depuis le panneau admin.")
        return

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
        st.session_state["is_admin"] = False
        st.session_state["user_id"] = None
        st.session_state["prenom"] = None
        st.session_state["nom"] = None
        st.session_state["swipe_index"] = 0
        st.session_state["last_feedback"] = ""
        st.session_state["match_popup"] = {"show": False, "resto": None, "people": [], "index": 0}

        st.success("Ton compte et toutes tes réponses ont été supprimés.")
        st.stop()


# ============================
# Panneau admin
# ============================

def admin_panel():
    st.title("🔑 Panneau admin – gestion globale")

    users_df = load_users()
    swipes_df = load_swipes()

    today_str = date.today().isoformat()
    total_users = len(users_df)
    total_swipes = len(swipes_df)
    swipes_today = len(swipes_df[swipes_df["date"] == today_str]) if not swipes_df.empty else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Utilisateurs inscrits", total_users)
    with col2:
        st.metric("Swipes totaux", total_swipes)
    with col3:
        st.metric("Swipes aujourd'hui", swipes_today)

    st.markdown("---")
    st.subheader("👥 Utilisateurs")

    if users_df.empty:
        st.info("Aucun utilisateur inscrit.")
    else:
        st.dataframe(users_df[["user_id", "prenom", "nom", "description"]].reset_index(drop=True))

        user_ids = users_df["user_id"].tolist()
        selected_user = st.selectbox("Choisir un utilisateur à supprimer", user_ids)

        if st.button("❌ Supprimer cet utilisateur et toutes ses réponses"):
            users_df = users_df[users_df["user_id"] != selected_user]
            save_users(users_df)

            swipes_df = swipes_df[swipes_df["user_id"] != selected_user]
            save_swipes(swipes_df)

            st.success(f"Utilisateur '{selected_user}' et ses swipes ont été supprimés.")
            st.rerun()

    st.markdown("---")
    st.subheader("🧹 Nettoyage des swipes")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🗑️ Supprimer tous les swipes d'aujourd'hui"):
            if not swipes_df.empty:
                swipes_df = swipes_df[swipes_df["date"] != today_str]
                save_swipes(swipes_df)
            st.success("Tous les swipes d'aujourd'hui ont été supprimés.")
            st.rerun()

    with col_b:
        if st.button("🔥 Supprimer tous les swipes (toutes dates)"):
            empty = pd.DataFrame(columns=["date", "user_id", "prenom", "nom", "restaurant", "decision"])
            save_swipes(empty)
            st.success("Tous les swipes ont été supprimés.")
            st.rerun()


# ============================
# Swipe Logic
# ============================

def render_resto_card(row):
    """Affiche une carte sexy pour un resto, pensée mobile (quasi plein écran)."""
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
        height: 75vh;
        max-height: 680px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-top: -40px;
    ">
      <div style="
          width: 100%;
          max-width: 420px;
          border-radius: 24px;
          padding: 24px 20px;
          background: linear-gradient(145deg, #ffe6f0, #ffffff);
          box-shadow: 0 14px 35px rgba(0,0,0,0.12);
          border: 1px solid rgba(255, 192, 203, 0.6);
      ">
          <div style="font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: #e91e63; margin-bottom: 6px;">
              🍽️ Proposition de dej
          </div>
          <div style="font-size: 26px; font-weight: 800; margin-bottom: 8px; color: #333;">
              {name}
          </div>
          <div style="font-size: 13px; color: #777; margin-bottom: 14px;">
              {subline}
          </div>
          <div style="font-size: 12px; color: #999;">
              Imagine que tu swipes à droite ou à gauche : est-ce que tu te verrais déjeuner ici aujourd'hui ?
          </div>
      </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def swipe_tab(df: pd.DataFrame):
    # pas de gros header ici pour que la carte remonte au max

    today_str = date.today().isoformat()
    user_id = st.session_state["user_id"]

    # === Popup MATCH prioritaire si présente ===
    popup = st.session_state.get("match_popup", None)
    if popup and popup.get("show"):
        resto_name = popup.get("resto", "Restaurant mystère")
        people = popup.get("people", [])
        base_idx = popup.get("index", 0)

        names_html = "<br>".join([f"• {p}" for p in people]) if people else "… et d'autres peut-être"

        popup_html = f"""
        <div style="
            height: 75vh;
            max-height: 680px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-top: -40px;
        ">
          <div style="
              width: 100%;
              max-width: 420px;
              border-radius: 24px;
              padding: 26px 22px;
              background: radial-gradient(circle at top, #ff97b7, #8e24aa);
              box-shadow: 0 18px 40px rgba(0,0,0,0.35);
              color: white;
              text-align: center;
          ">
              <div style="font-size: 34px; font-weight: 900; letter-spacing: 2px; margin-bottom: 6px;">
                  MATCH 💘
              </div>
              <div style="font-size: 18px; margin-bottom: 16px;">
                  sur <span style="font-weight: 800;">{resto_name}</span>
              </div>
              <div style="font-size: 13px; opacity: 0.9; margin-bottom: 10px;">
                  Vous avez liké ce resto en commun avec :
              </div>
              <div style="font-size: 15px; font-weight: 600; margin-bottom: 18px;">
                  {names_html}
              </div>
              <div style="font-size: 11px; opacity: 0.8;">
                  (Et peut-être d'autres collègues inconnus de l'algorithme 🤫)
              </div>
          </div>
        </div>
        """
        st.markdown(popup_html, unsafe_allow_html=True)

        st.write("")
        # bouton à droite
        col_spacer, col_btn = st.columns([3, 1])
        with col_btn:
            if st.button("➡️ Suivant"):
                st.session_state["swipe_index"] = base_idx + 1
                st.session_state["match_popup"]["show"] = False
                st.session_state["last_feedback"] = ""
                st.rerun()
        return

    # Index & contrôles swipe
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

    # Boutons OUI / NON côte à côte (sur desktop ; sur mobile Streamlit les empilera)
    col_no, col_yes = st.columns(2)
    with col_no:
        no_btn = st.button("❌ Pas chaud")
    with col_yes:
        yes_btn = st.button("❤️ Chaud")

    # Boutons reset / back en dessous
    col_reset, col_back = st.columns(2)
    with col_reset:
        if st.button("🧹 Réinitialiser mes choix d'aujourd'hui"):
            swipes_df = load_swipes()
            if not swipes_df.empty:
                mask = ~((swipes_df["user_id"] == user_id) & (swipes_df["date"] == today_str))
                swipes_df = swipes_df[mask]
                save_swipes(swipes_df)
            st.session_state["swipe_index"] = 0
            st.session_state["last_feedback"] = ""
            st.session_state["match_popup"] = {"show": False, "resto": None, "people": [], "index": 0}
            st.rerun()

    with col_back:
        if st.button("↩️ Revenir au précédent"):
            if idx <= 0:
                st.caption("Tu es déjà au début 😉")
            else:
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
                st.session_state["match_popup"] = {"show": False, "resto": None, "people": [], "index": 0}
                st.rerun()

    # === LIKE ===
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
            names = [f"{r['prenom']} {r['nom']}" for _, r in likes_others.iterrows()]
            names = list(sorted(set(names)))
            if len(names) > 3:
                names_sample = random.sample(names, 3)
            else:
                names_sample = names

            st.session_state["match_popup"] = {
                "show": True,
                "resto": resto_name,
                "people": names_sample,
                "index": idx,
            }
            st.rerun()
        else:
            st.session_state["swipe_index"] = idx + 1
            st.session_state["last_feedback"] = "Premier like sur ce resto, tu ouvres la voie 😉"
            st.session_state["match_popup"] = {"show": False, "resto": None, "people": [], "index": 0}
            st.rerun()

    # === DISLIKE ===
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
        st.session_state["match_popup"] = {"show": False, "resto": None, "people": [], "index": 0}
        st.rerun()

    if st.session_state.get("last_feedback"):
        st.caption(st.session_state["last_feedback"])


# ============================
# Matchs tab
# ============================

def matches_tab():
    st.header("💞 Mes matchs (aujourd'hui)")

    # 🔁 bouton pour actualiser les matchs
    if st.button("🔄 Actualiser les matchs"):
        st.rerun()

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

    if not st.session_state["logged_in"]:
        # page très light pour que dès connexion on soit sur la carte
        st.markdown("## 💘 Tinder des restos")
        st.info("Connecte-toi dans la barre latérale pour commencer à swiper.")
        return

    if st.session_state["is_admin"]:
        admin_panel()
        return

    # pas de gros titre ici, on passe directement aux tabs & à la carte
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
