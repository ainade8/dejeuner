import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime
import json
import os
from pathlib import Path

# Configuration de la page
st.set_page_config(
    page_title="Lunch Tinder 🍽️",
    page_icon="🍽️",
    layout="centered"
)

# CSS personnalisé pour les animations et le style avec support tactile mobile
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        height: 50px;
        font-size: 18px;
        font-weight: bold;
    }
    
    .restaurant-card {
        background: white;
        border-radius: 20px;
        padding: 30px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        text-align: center;
        margin: 20px auto;
        max-width: 400px;
        cursor: grab;
        user-select: none;
        touch-action: none;
        position: relative;
        transition: transform 0.1s ease-out;
    }
    
    .restaurant-card:active {
        cursor: grabbing;
    }
    
    .restaurant-card h1 {
        font-size: 80px;
        margin: 20px 0;
    }
    
    .restaurant-card h2 {
        font-size: 28px;
        color: #333;
        margin: 15px 0;
    }
    
    .swipe-indicator {
        position: absolute;
        top: 50%;
        font-size: 120px;
        font-weight: bold;
        opacity: 0;
        transition: opacity 0.2s;
        pointer-events: none;
        z-index: 10;
    }
    
    .swipe-indicator.left {
        left: 20px;
        transform: translateY(-50%) rotate(-20deg);
    }
    
    .swipe-indicator.right {
        right: 20px;
        transform: translateY(-50%) rotate(20deg);
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: scale(0.9); }
        to { opacity: 1; transform: scale(1); }
    }
    
    @keyframes swipeLeftOut {
        from { transform: translateX(0) rotate(0deg); opacity: 1; }
        to { transform: translateX(-500px) rotate(-30deg); opacity: 0; }
    }
    
    @keyframes swipeRightOut {
        from { transform: translateX(0) rotate(0deg); opacity: 1; }
        to { transform: translateX(500px) rotate(30deg); opacity: 0; }
    }
    
    .swipe-left-out {
        animation: swipeLeftOut 0.5s forwards;
    }
    
    .swipe-right-out {
        animation: swipeRightOut 0.5s forwards;
    }
    
    .match-animation {
        background: linear-gradient(45deg, #ff6b6b, #feca57, #48dbfb, #ff9ff3);
        background-size: 400% 400%;
        animation: gradient 2s ease infinite;
        padding: 40px;
        border-radius: 20px;
        text-align: center;
        color: white;
        font-size: 48px;
        font-weight: bold;
        margin: 20px 0;
    }
    
    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .user-badge {
        display: inline-block;
        background: #667eea;
        color: white;
        padding: 5px 15px;
        border-radius: 15px;
        margin: 5px;
        font-weight: bold;
    }
    
    .swipe-buttons {
        display: flex;
        gap: 20px;
        justify-content: center;
        margin-top: 30px;
    }
    
    .swipe-btn {
        width: 70px;
        height: 70px;
        border-radius: 50%;
        border: none;
        font-size: 30px;
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    .swipe-btn:hover {
        transform: scale(1.1);
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
    }
    
    .swipe-btn:active {
        transform: scale(0.95);
    }
    
    .btn-dislike {
        background: linear-gradient(135deg, #ff6b6b, #ee5a6f);
        color: white;
    }
    
    .btn-like {
        background: linear-gradient(135deg, #51cf66, #37b24d);
        color: white;
    }
</style>

<script>
let touchStartX = 0;
let touchStartY = 0;
let currentX = 0;
let currentY = 0;
let isDragging = false;
let cardElement = null;
let leftIndicator = null;
let rightIndicator = null;

function initSwipe() {
    cardElement = document.querySelector('.restaurant-card');
    if (!cardElement) return;
    
    leftIndicator = document.createElement('div');
    leftIndicator.className = 'swipe-indicator left';
    leftIndicator.textContent = '👎';
    cardElement.appendChild(leftIndicator);
    
    rightIndicator = document.createElement('div');
    rightIndicator.className = 'swipe-indicator right';
    rightIndicator.textContent = '❤️';
    cardElement.appendChild(rightIndicator);
    
    // Touch events
    cardElement.addEventListener('touchstart', handleStart, { passive: false });
    cardElement.addEventListener('touchmove', handleMove, { passive: false });
    cardElement.addEventListener('touchend', handleEnd, { passive: false });
    
    // Mouse events for desktop testing
    cardElement.addEventListener('mousedown', handleStart);
    cardElement.addEventListener('mousemove', handleMove);
    cardElement.addEventListener('mouseup', handleEnd);
    cardElement.addEventListener('mouseleave', handleEnd);
}

function handleStart(e) {
    e.preventDefault();
    isDragging = true;
    
    const touch = e.touches ? e.touches[0] : e;
    touchStartX = touch.clientX;
    touchStartY = touch.clientY;
    
    cardElement.style.transition = 'none';
}

function handleMove(e) {
    if (!isDragging) return;
    e.preventDefault();
    
    const touch = e.touches ? e.touches[0] : e;
    currentX = touch.clientX - touchStartX;
    currentY = touch.clientY - touchStartY;
    
    const rotate = currentX / 20;
    cardElement.style.transform = `translate(${currentX}px, ${currentY}px) rotate(${rotate}deg)`;
    
    // Show indicators
    if (currentX < -50) {
        leftIndicator.style.opacity = Math.min(Math.abs(currentX) / 100, 1);
        rightIndicator.style.opacity = 0;
    } else if (currentX > 50) {
        rightIndicator.style.opacity = Math.min(currentX / 100, 1);
        leftIndicator.style.opacity = 0;
    } else {
        leftIndicator.style.opacity = 0;
        rightIndicator.style.opacity = 0;
    }
}

function handleEnd(e) {
    if (!isDragging) return;
    isDragging = false;
    
    const threshold = 100;
    
    if (currentX < -threshold) {
        // Swipe left (dislike)
        cardElement.style.transition = 'transform 0.5s ease-out';
        cardElement.style.transform = `translate(-500px, ${currentY}px) rotate(-30deg)`;
        setTimeout(() => {
            window.parent.postMessage({type: 'swipe', direction: 'left'}, '*');
        }, 500);
    } else if (currentX > threshold) {
        // Swipe right (like)
        cardElement.style.transition = 'transform 0.5s ease-out';
        cardElement.style.transform = `translate(500px, ${currentY}px) rotate(30deg)`;
        setTimeout(() => {
            window.parent.postMessage({type: 'swipe', direction: 'right'}, '*');
        }, 500);
    } else {
        // Return to center
        cardElement.style.transition = 'transform 0.3s ease-out';
        cardElement.style.transform = 'translate(0, 0) rotate(0deg)';
        leftIndicator.style.opacity = 0;
        rightIndicator.style.opacity = 0;
    }
    
    currentX = 0;
    currentY = 0;
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSwipe);
} else {
    setTimeout(initSwipe, 100);
}

// Re-initialize on Streamlit rerun
const observer = new MutationObserver(() => {
    setTimeout(initSwipe, 100);
});
observer.observe(document.body, { childList: true, subtree: true });
</script>
""", unsafe_allow_html=True)

# Fichiers de données
DATA_DIR = Path("lunch_tinder_data")
DATA_DIR.mkdir(exist_ok=True)
USERS_FILE = DATA_DIR / "users.json"
SWIPES_FILE = DATA_DIR / "swipes.json"

# Fonctions de gestion des données
def load_restaurants():
    """Charge la base de restaurants depuis Excel"""
    try:
        df = pd.read_excel("restaurants.xlsx")
        # S'assurer que la colonne 'Restaurant' existe
        if 'Restaurant' not in df.columns:
            st.error("❌ Le fichier Excel doit contenir une colonne 'Restaurant'")
            return pd.DataFrame()
        return df
    except FileNotFoundError:
        st.error("❌ Fichier restaurants.xlsx non trouvé!")
        return pd.DataFrame()

def load_users():
    """Charge les utilisateurs"""
    if USERS_FILE.exists():
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Création de l'admin par défaut
        admin_password = hashlib.sha256("admin".encode()).hexdigest()
        users = {
            "admin": {
                "prenom": "Admin",
                "nom": "Admin",
                "password": admin_password,
                "is_admin": True
            }
        }
        save_users(users)
        return users

def save_users(users):
    """Sauvegarde les utilisateurs"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_swipes():
    """Charge l'historique des swipes"""
    if SWIPES_FILE.exists():
        with open(SWIPES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_swipes(swipes):
    """Sauvegarde les swipes"""
    with open(SWIPES_FILE, 'w', encoding='utf-8') as f:
        json.dump(swipes, f, ensure_ascii=False, indent=2)

def get_today_key():
    """Retourne la clé pour aujourd'hui"""
    return datetime.now().strftime("%Y-%m-%d")

def add_swipe(username, restaurant_name, liked):
    """Ajoute un swipe"""
    swipes = load_swipes()
    today = get_today_key()
    
    if today not in swipes:
        swipes[today] = {}
    
    if username not in swipes[today]:
        swipes[today][username] = {}
    
    swipes[today][username][restaurant_name] = liked
    save_swipes(swipes)

def get_matches(username, restaurant_name):
    """Trouve les matches pour un restaurant"""
    swipes = load_swipes()
    today = get_today_key()
    
    if today not in swipes:
        return []
    
    matches = []
    for user, user_swipes in swipes[today].items():
        if user != username and restaurant_name in user_swipes and user_swipes[restaurant_name]:
            users = load_users()
            if user in users:
                matches.append(f"{users[user]['prenom']} {users[user]['nom']}")
    
    return matches

def get_user_swipes_today(username):
    """Retourne les restaurants déjà swipés aujourd'hui"""
    swipes = load_swipes()
    today = get_today_key()
    
    if today not in swipes or username not in swipes[today]:
        return {}
    
    return swipes[today][username]

# Initialisation de la session
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.current_resto_idx = 0
    st.session_state.show_match = False
    st.session_state.match_restaurant = None
    st.session_state.match_users = []
    st.session_state.swipe_trigger = 0

# Page de connexion
def login_page():
    st.title("🍽️ Lunch Tinder")
    st.subheader("Connectez-vous pour commencer")
    
    tab1, tab2 = st.tabs(["Connexion", "Inscription"])
    
    with tab1:
        username = st.text_input("Nom d'utilisateur", key="login_username")
        password = st.text_input("Mot de passe", type="password", key="login_password")
        
        if st.button("Se connecter", key="login_btn"):
            users = load_users()
            if username in users:
                hashed_pw = hashlib.sha256(password.encode()).hexdigest()
                if users[username]["password"] == hashed_pw:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.is_admin = users[username].get("is_admin", False)
                    st.rerun()
                else:
                    st.error("❌ Mot de passe incorrect")
            else:
                st.error("❌ Utilisateur non trouvé")
    
    with tab2:
        new_username = st.text_input("Nom d'utilisateur", key="signup_username")
        prenom = st.text_input("Prénom", key="signup_prenom")
        nom = st.text_input("Nom", key="signup_nom")
        new_password = st.text_input("Mot de passe", type="password", key="signup_password")
        confirm_password = st.text_input("Confirmer le mot de passe", type="password", key="signup_confirm")
        
        if st.button("S'inscrire", key="signup_btn"):
            if new_password != confirm_password:
                st.error("❌ Les mots de passe ne correspondent pas")
            elif not new_username or not prenom or not nom or not new_password:
                st.error("❌ Tous les champs sont obligatoires")
            else:
                users = load_users()
                if new_username in users:
                    st.error("❌ Ce nom d'utilisateur existe déjà")
                else:
                    hashed_pw = hashlib.sha256(new_password.encode()).hexdigest()
                    users[new_username] = {
                        "prenom": prenom,
                        "nom": nom,
                        "password": hashed_pw,
                        "is_admin": False
                    }
                    save_users(users)
                    st.success("✅ Compte créé avec succès! Vous pouvez maintenant vous connecter.")

# Page principale de swipe
def swipe_page():
    users = load_users()
    user_info = users[st.session_state.username]
    
    st.title(f"🍽️ Bonjour {user_info['prenom']} !")
    
    if st.button("🚪 Se déconnecter"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.current_resto_idx = 0
        st.rerun()
    
    # Afficher le match s'il y en a un
    if st.session_state.show_match:
        st.markdown(f"""
        <div class="match-animation">
            🎉 MATCH ! 🎉
            <div style="font-size: 24px; margin-top: 20px;">
                Pour {st.session_state.match_restaurant}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("👥 Vous pouvez déjeuner avec :")
        for user in st.session_state.match_users:
            st.markdown(f'<span class="user-badge">{user}</span>', unsafe_allow_html=True)
        
        if st.button("Continuer à swiper ➡️"):
            st.session_state.show_match = False
            st.rerun()
        
        return
    
    # Charger les restaurants
    restaurants = load_restaurants()
    if restaurants.empty:
        st.warning("Aucun restaurant disponible")
        return
    
    # Filtrer les restaurants déjà swipés aujourd'hui
    swipes_today = get_user_swipes_today(st.session_state.username)
    remaining_restaurants = restaurants[~restaurants['Restaurant'].isin(swipes_today.keys())]
    
    if remaining_restaurants.empty:
        st.success("🎉 Vous avez swipé tous les restaurants aujourd'hui!")
        
        # Afficher les restaurants likés
        liked_today = [resto for resto, liked in swipes_today.items() if liked]
        if liked_today:
            st.subheader("❤️ Vos restaurants préférés aujourd'hui:")
            for resto in liked_today:
                matches = get_matches(st.session_state.username, resto)
                st.markdown(f"**{resto}**")
                if matches:
                    st.write(f"   👥 Matches: {', '.join(matches)}")
        
        return
    
    # Restaurant actuel
    current_resto = remaining_restaurants.iloc[0]
    restaurant_name = str(current_resto['Restaurant'])
    
    # Afficher la carte du restaurant avec support swipe
    st.markdown(f"""
    <div class="restaurant-card" id="swipe-card">
        <h1>🍽️</h1>
        <h2>{restaurant_name}</h2>
        <p style="color: #666; font-size: 18px; margin-top: 20px;">
            Restaurant {len(swipes_today) + 1} sur {len(restaurants)}
        </p>
        <p style="color: #999; font-size: 14px; margin-top: 10px;">
            👆 Glissez la carte ou utilisez les boutons
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Boutons de swipe
    st.markdown('<div class="swipe-buttons">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.markdown("", unsafe_allow_html=True)
    
    with col2:
        subcol1, subcol2 = st.columns(2)
        with subcol1:
            if st.button("👎", key="dislike", help="Non merci"):
                add_swipe(st.session_state.username, restaurant_name, False)
                st.session_state.swipe_trigger += 1
                st.rerun()
        
        with subcol2:
            if st.button("❤️", key="like", help="J'y vais !"):
                add_swipe(st.session_state.username, restaurant_name, True)
                
                # Vérifier les matches
                matches = get_matches(st.session_state.username, restaurant_name)
                if matches:
                    st.session_state.show_match = True
                    st.session_state.match_restaurant = restaurant_name
                    st.session_state.match_users = matches
                
                st.session_state.swipe_trigger += 1
                st.rerun()
    
    with col3:
        st.markdown("", unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Admin page
def admin_page():
    st.title("👑 Panel Admin")
    
    if st.button("🚪 Se déconnecter"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()
    
    tab1, tab2, tab3 = st.tabs(["📊 Statistiques", "👥 Utilisateurs", "🍽️ Restaurants"])
    
    with tab1:
        st.subheader("📊 Statistiques du jour")
        swipes = load_swipes()
        today = get_today_key()
        
        if today in swipes:
            st.write(f"**Utilisateurs actifs:** {len(swipes[today])}")
            
            # Compter les likes par restaurant
            resto_likes = {}
            for user_swipes in swipes[today].values():
                for resto, liked in user_swipes.items():
                    if liked:
                        resto_likes[resto] = resto_likes.get(resto, 0) + 1
            
            if resto_likes:
                st.subheader("🏆 Top Restaurants")
                sorted_restos = sorted(resto_likes.items(), key=lambda x: x[1], reverse=True)
                for resto, count in sorted_restos[:5]:
                    st.write(f"**{resto}**: {count} like(s)")
        else:
            st.info("Aucune activité aujourd'hui")
    
    with tab2:
        st.subheader("👥 Liste des utilisateurs")
        users = load_users()
        for username, info in users.items():
            if username != "admin":
                st.write(f"**{info['prenom']} {info['nom']}** (@{username})")
    
    with tab3:
        st.subheader("🍽️ Liste des restaurants")
        restaurants = load_restaurants()
        if not restaurants.empty:
            st.dataframe(restaurants, use_container_width=True)

# Router principal
def main():
    if not st.session_state.logged_in:
        login_page()
    else:
        if st.session_state.get('is_admin', False):
            admin_page()
        else:
            swipe_page()

if __name__ == "__main__":
    main()