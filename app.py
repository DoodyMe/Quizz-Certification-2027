import datetime
import streamlit as st

# ------------------------------------------------------------------------------
# 1. CONFIGURATION ET STYLE CSS (Interface joyeuse & cartes douces)
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Challenge & Révision HAS 2027",
    page_icon="🧠",
    layout="wide"
)

st.markdown("""
<style>
    /* Style général doux et épuré */
    .stApp {
        background-color: #f8fafc;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Titre principal */
    .main-title {
        color: #1e293b;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    /* Style personnalisé pour les onglets */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        justify-content: center;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 24px;
        background-color: #ffffff;
        border-radius: 50px;
        font-weight: 600;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }
    .stTabs [aria-selected="true"] {
        background-color: #6366f1 !important;
        color: white !important;
        border-color: #6366f1 !important;
    }

    /* Carte centrale du profil */
    .profile-card {
        background-color: white;
        border-radius: 20px;
        padding: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        max-width: 650px;
        margin: 20px auto;
        text-align: center;
    }

    /* Vignette Animal avec Emoji (Forme douce & bleue) */
    .animal-badge {
        display: inline-flex;
        align-items: center;
        gap: 15px;
        padding: 12px 28px;
        border-radius: 50px;
        background-color: #DBEAFE; /* Bleu pastel */
        border: 2px solid #60A5FA;
        box-shadow: 0 4px 12px rgba(96, 165, 250, 0.2);
        margin: 15px 0;
    }
    .animal-emoji {
        font-size: 2.8rem;
    }
    .animal-name {
        color: #1E40AF;
        font-weight: 700;
        font-size: 1.4rem;
    }

    /* Aperçu du pseudo complet */
    .pseudo-badge {
        display: inline-block;
        padding: 14px 30px;
        border-radius: 50px;
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white;
        font-weight: 700;
        font-size: 1.3rem;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        margin: 10px 0;
    }

    /* Cartes pour le Podium */
    .podium-card {
        background-color: white;
        border-radius: 16px;
        padding: 16px 20px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.04);
        border: 1px solid #e2e8f0;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 2. DONNÉES (15 animaux, 10 adjectifs = 150 combinaisons uniques)
# ------------------------------------------------------------------------------
ANIMAL_TO_EMOJI = {
    "Lapin": "🐇",
    "Ours": "🐻",
    "Castor": "🦫",
    "Elephant": "🐘",
    "Hamster": "🐹",
    "Panda": "🐼",
    "Kangourou": "🦘",
    "Dauphin": "🐬",
    "Faucon": "🦅",
    "Ecureuil": "🐿️",
    "Lynx": "🐆",
    "Lémurien": "🐒",
    "Ornithorinque": "🦆",
    "Loup": "🐺",
    "Hérisson": "🦔"
}

ANIMAUX = list(ANIMAL_TO_EMOJI.keys())

ADJECTIFS = [
    "Astucieux", "Timide", "Ambitieux", "Survolté", "Combatif",
    "Emotif", "Espiègle", "Gourmand", "Malin", "Optimiste"
]

# Base de données temporaire en session (sera liée à Google Sheets par la suite)
if "pseudos_reserves" not in st.session_state:
    st.session_state.pseudos_reserves = [
        {"animal": "Dauphin", "adjectif": "Malin"},
        {"animal": "Hérisson", "adjectif": "Ambitieux"},
    ]

# ------------------------------------------------------------------------------
# 3. BASE DE DONNÉES QUIZZ (Référentiel HAS 2027)
# ------------------------------------------------------------------------------
QUIZZ_DATABASE = {
    "Session 1": {
        "titre": "Session #1 - Bientraitance & Droits du patient",
        "date_ouverture": datetime.date(2026, 10, 5),
        "date_fermeture": datetime.date(2026, 10, 18),
        "questions": [
            {
                "question": "1. Quel est l'élément clé de la bientraitance selon la HAS ?",
                "options": ["Le respect de la dignité", "L'évaluation financière", "L'organisation interne"],
                "reponse_correcte": "Le respect de la dignité",
                "explication": "La HAS place la dignité et l'autonomie du patient au cœur du référentiel 2027."
            }
        ]
    },
    "Session 2": {
        "titre": "Session #2 - Prise en charge médicamenteuse",
        "date_ouverture": datetime.date(2026, 10, 19),
        "date_fermeture": datetime.date(2026, 11, 1),
        "questions": []
    }
}

# ------------------------------------------------------------------------------
# 4. EN-TÊTE ET NAVIGATION
# ------------------------------------------------------------------------------
st.markdown("<h1 class='main-title'>🧠 Challenge Équipe - Révision HAS 2027</h1>", unsafe_allow_html=True)

tab_inscription, tab_quiz, tab_podium = st.tabs([
    "🎭 Mon Profil Anonyme", 
    "📝 Quiz de la Semaine", 
    "🏆 Podium & Corrections"
])

# ------------------------------------------------------------------------------
# TAB 1 : INSCRIPTION / SÉLECTION PAR FILTRAGE
# ------------------------------------------------------------------------------
with tab_inscription:
    st.subheader("Choisissez votre Avatar Anonyme")
    st.write("Sélectionnez votre animal puis votre adjectif pour réserver votre pseudo unique.")

    # Filtrage des animaux ayant au moins un adjectif disponible
    animaux_disponibles = []
    for animal in ANIMAUX:
        adjectifs_pris = [p["adjectif"] for p in st.session_state.pseudos_reserves if p["animal"] == animal]
        if len(adjectifs_pris) < len(ADJECTIFS):
            animaux_disponibles.append(animal)

    if not animaux_disponibles:
        st.error("Toutes les combinaisons ont été attribuées !")
    else:
        # Étape 1 : Animal
        animal_choisi = st.selectbox("1. Sélectionnez votre Animal :", options=["-- Choisir un animal --"] + animaux_disponibles)

        if animal_choisi != "-- Choisir un animal --":
            
            # Vignette dynamique
            emoji_animal = ANIMAL_TO_EMOJI[animal_choisi]
            st.markdown(f"""
                <div style='text-align: center;'>
                    <div class='animal-badge'>
                        <span class='animal-emoji'>{emoji_animal}</span>
                        <span class='animal-name'>{animal_choisi}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Étape 2 : Adjectifs encore disponibles pour cet animal
            adjectifs_pris = [p["adjectif"] for p in st.session_state.pseudos_reserves if p["animal"] == animal_choisi]
            adjectifs_disponibles = [adj for adj in ADJECTIFS if adj not in adjectifs_pris]

            adjectif_choisi = st.selectbox("2. Sélectionnez votre Adjectif :", options=["-- Choisir un adjectif --"] + adjectifs_disponibles)

            if adjectif_choisi != "-- Choisir un adjectif --":
                pseudo_final = f"{animal_choisi} {adjectif_choisi}"
                
                # Aperçu sous forme de bulle
                st.markdown(f"""
                    <div style='text-align: center; margin: 20px 0;'>
                        <div class='pseudo-badge'>✨ {pseudo_final}</div>
                    </div>
                """, unsafe_allow_html=True)

                if st.button("Valider et Réserver ce Profil", type="primary", use_container_width=True):
                    st.session_state.pseudos_reserves.append({"animal": animal_choisi, "adjectif": adjectif_choisi})
                    st.success(f"C'est validé ! Votre identifiant unique est : **{pseudo_final}**.")
                    st.rerun()

# ------------------------------------------------------------------------------
# TAB 2 : PASSAGE DU QUIZ (Bascule automatique Ouverture/Fermeture)
# ------------------------------------------------------------------------------
with tab_quiz:
    session_active = QUIZZ_DATABASE["Session 1"]
    aujourdhui = datetime.date.today()
    est_ouvert = session_active["date_ouverture"] <= aujourdhui <= session_active["date_fermeture"]

    st.subheader(session_active["titre"])
    
    col_d1, col_d2 = st.columns(2)
    col_d1.info(f"📅 **Ouverture :** {session_active['date_ouverture'].strftime('%d/%m/%Y')}")
    col_d2.warning(f"⏳ **Fermeture :** {session_active['date_fermeture'].strftime('%d/%m/%Y')}")

    if est_ouvert:
        st.success("🟢 Le quiz est actuellement **OUVERT**.")
        user_pseudo = st.text_input("Saisissez votre pseudo (ex: Dauphin Malin) :")
        
        if session_active["questions"]:
            with st.form("form_quiz"):
                reponses_user = {}
                for idx, q in enumerate(session_active["questions"]):
                    reponses_user[idx] = st.radio(q["question"], q["options"], key=f"q_{idx}")
                
                if st.form_submit_button("Valider mes réponses", type="primary"):
                    if not user_pseudo:
                        st.error("N'oubliez pas d'indiquer votre pseudo !")
                    else:
                        st.balloons()
                        st.success(f"Réponses enregistrées pour **{user_pseudo}** !")
        else:
            st.info("Les questions de cette session seront bientôt intégrées.")
    else:
        st.error("🔴 Cette session est actuellement fermée. Retrouvez les résultats dans l'onglet Podium & Corrections !")

# ------------------------------------------------------------------------------
# TAB 3 : PODIUM TOP 10 & CORRECTIONS
# ------------------------------------------------------------------------------
with tab_podium:
    st.subheader("🏆 Classement Top 10 & Corrections HAS")
    
    col_podium, col_correction = st.columns([1, 1])

    with col_podium:
        st.markdown("### 🥇 Top 10 de la Session")
        top_10 = [
            {"rang": "🥇 1er", "pseudo": "Dauphin Malin", "score": "10/10"},
            {"rang": "🥈 2ème", "pseudo": "Ecureuil Survolté", "score": "10/10"},
            {"rang": "🥉 3ème", "pseudo": "Hérisson Ambitieux", "score": "9/10"},
            {"rang": "4ème", "pseudo": "Castor Optimiste", "score": "9/10"},
            {"rang": "5ème", "pseudo": "Panda Gourmand", "score": "8/10"},
        ]
        for p in top_10:
            st.markdown(f"""
                <div class='podium-card'>
                    <span style='font-size: 1.1rem; font-weight: bold;'>{p['rang']}</span> - 
                    <span style='font-weight: 600;'>{p['pseudo']}</span> 
                    <span style='float: right; color: #6366f1; font-weight: bold;'>{p['score']}</span>
                </div>
            """, unsafe_allow_html=True)

    with col_correction:
        st.markdown("### 📖 Explications & Référentiel HAS 2027")
        with st.expander("Question 1 - Bientraitance & Droits du patient", expanded=True):
            st.write("**Bonne réponse :** Le respect de la dignité")
            st.info("💡 **Critère HAS 2027 :** L'évaluation de la bientraitance repose en priorité sur la prise en compte du projet de vie et du respect de la personne hébergée/soignée.")
