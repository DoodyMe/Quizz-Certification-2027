import datetime
import streamlit as st

# ------------------------------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Révisions Équipe HAS 2027",
    page_icon="🧠",
    layout="wide"
)

# ------------------------------------------------------------------------------
# 2. STYLE CSS (Cadre hospitalier chaleureux & vignettes)
# ------------------------------------------------------------------------------
st.markdown("""
<style>
    /* Fond général : Dégradé Vert Menthe & Bleu Doux */
    .stApp {
        background: linear-gradient(135deg, #e6fffa 0%, #f0f9ff 50%, #f5f3ff 100%);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* Titres principaux */
    .main-title {
        color: #0f766e;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.2rem;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.05);
    }
    
    .subtitle {
        color: #0369a1;
        text-align: center;
        font-weight: 600;
        margin-bottom: 1.5rem;
    }

    /* Carte de Profil / Inscription */
    .profile-card-header {
        background: white;
        border-radius: 24px;
        padding: 20px;
        border: 2px solid #99f6e4;
        max-width: 650px;
        margin: 0 auto 20px auto;
        text-align: center;
        box-shadow: 0 4px 15px rgba(15, 118, 110, 0.08);
    }

    /* Vignette Animal Sélectionné */
    .animal-selected-badge {
        display: inline-flex;
        align-items: center;
        gap: 12px;
        padding: 10px 25px;
        border-radius: 50px;
        background-color: #e0f2fe;
        border: 2px solid #38bdf8;
        box-shadow: 0 4px 12px rgba(56, 189, 248, 0.2);
        margin: 10px 0;
    }
    .animal-selected-emoji { font-size: 2.2rem; }
    .animal-selected-name { color: #0369a1; font-weight: 700; font-size: 1.2rem; }

    /* Header connecté */
    .user-header {
        background: linear-gradient(135deg, #0d9488 0%, #0284c7 100%);
        color: white;
        padding: 12px 26px;
        border-radius: 50px;
        display: inline-block;
        font-weight: 700;
        font-size: 1.1rem;
        box-shadow: 0 4px 15px rgba(13, 148, 136, 0.3);
    }

    /* Boîtes colorées des semaines */
    .card-actuelle {
        background-color: #ffffff;
        border-radius: 20px;
        padding: 25px;
        border-left: 8px solid #10b981;
        box-shadow: 0 8px 20px rgba(16, 185, 129, 0.08);
        margin-bottom: 20px;
    }

    .card-passee {
        background-color: #f8fafc;
        border-radius: 20px;
        padding: 20px;
        border-left: 8px solid #6366f1;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        margin-bottom: 15px;
    }

    .card-avenir {
        background-color: #fffbeb;
        border-radius: 20px;
        padding: 20px;
        border-left: 8px solid #f59e0b;
        margin-bottom: 15px;
    }

    /* Customisation des onglets */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        justify-content: center;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 30px;
        padding: 10px 24px;
        font-weight: 700;
        color: #0f766e;
        border: 1px solid #ccfbf1;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #0d9488 0%, #0284c7 100%) !important;
        color: white !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 3. DONNÉES DE L'APPLICATION (15 Animaux x 10 Adjectifs = 150 Combinaisons)
# ------------------------------------------------------------------------------
ANIMAL_TO_EMOJI = {
    "Lapin": "🐇", "Ours": "🐻", "Cochon": "🐷", "Elephant": "🐘", "Hamster": "🐹",
    "Panda": "🐼", "Kangourou": "🦘", "Dauphin": "🐬", "Faucon": "🦅", "Ecureuil": "🐿️",
    "Lynx": "🐆", "Lémurien": "🐒", "Canard": "🦆", "Loup": "🐺", "Hérisson": "🦔"
}

ANIMAUX = list(ANIMAL_TO_EMOJI.keys())
ADJECTIFS = ["Astucieux", "Timide", "Ambitieux", "Survolté", "Combatif", "Emotif", "Espiègle", "Gourmand", "Malin", "Optimiste"]

# Enregistrements en session
if "pseudos_reserves" not in st.session_state:
    st.session_state.pseudos_reserves = [{"animal": "Dauphin", "adjectif": "Malin"}]

if "user_pseudo" not in st.session_state:
    st.session_state.user_pseudo = None

if "animal_selectionne" not in st.session_state:
    st.session_state.animal_selectionne = None

def fixer_animal(nom_animal):
    st.session_state.animal_selectionne = nom_animal

# Programme des sessions de révision
SESSIONS = [
    {
        "id": 1,
        "titre": "Semaine 1 - Droits du patient & Bientraitance",
        "statut": "Passee",
        "dates": "Du 21/09 au 04/10",
        "questions": [
            {"q": "1. Quel est le délai légal de communication du dossier médical au patient ?", "options": ["48 heures", "8 jours", "15 jours"], "rep": "8 jours"}
        ],
        "podium": [
            {"rang": "🥇 1er", "pseudo": "Dauphin Malin", "score": "10/10"},
            {"rang": "🥈 2ème", "pseudo": "Loup Combatif", "score": "10/10"},
            {"rang": "🥉 3ème", "pseudo": "Panda Optimiste", "score": "9/10"},
            {"rang": "4ème", "pseudo": "Cochon Survolté", "score": "9/10"},
            {"rang": "5ème", "pseudo": "Canard Astucieux", "score": "8/10"},
            {"rang": "6ème", "pseudo": "Lynx Ambitieux", "score": "8/10"},
            {"rang": "7ème", "pseudo": "Hérisson Timide", "score": "7/10"},
            {"rang": "8ème", "pseudo": "Faucon Espiègle", "score": "7/10"},
            {"rang": "9ème", "pseudo": "Hamster Gourmand", "score": "6/10"},
            {"rang": "10ème", "pseudo": "Ours Emotif", "score": "6/10"}
        ]
    },
    {
        "id": 2,
        "titre": "Semaine 2 - Evaluation & Prise en charge de la douleur",
        "statut": "Actuelle",
        "dates": "Du 05/10 au 18/10",
        "questions": [
            {"q": "1. Quelle échelle est recommandée pour l'auto-évaluation de la douleur chez l'adulte communiquant ?", "options": ["EVA / EN", "ALGOPLUS", "DN4"], "rep": "EVA / EN"},
            {"q": "2. Dans quel délai maximal la re-évaluation de la douleur doit-elle être tracée après antalgique IV ?", "options": ["15 à 30 minutes", "1 à 2 heures", "Au changement d'équipe"], "rep": "15 à 30 minutes"}
        ]
    },
    {
        "id": 3,
        "titre": "Semaine 3 - Circuit du médicament & Identitovigilance",
        "statut": "A venir",
        "dates": "Du 19/10 au 01/11",
        "questions": []
    }
]

# ------------------------------------------------------------------------------
# 4. ÉCRAN 1 : SÉLECTION DU PSEUDO (SI NON CONNECTÉ)
# ------------------------------------------------------------------------------
if not st.session_state.user_pseudo:
    st.markdown("<h1 class='main-title'>🧠 Pause Révision HAS 2027</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Espace ludique & anonyme pour l'équipe soignante</p>", unsafe_allow_html=True)

    st.markdown("""
        <div class='profile-card-header'>
            <h3 style='color:#0f766e; margin:0;'>🎭 Choisissez votre Avatar Anonyme</h3>
            <p style='color:#64748b; font-size:0.95rem; margin-top:5px;'>1. Cliquez sur votre animal &nbsp;•&nbsp; 2. Choisissez votre adjectif</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<h4 style='text-align:center; color:#0f766e;'>Étape 1 : Cliquez sur un Animal</h4>", unsafe_allow_html=True)

    # Grille de vignettes d'animaux (5 colonnes)
    cols = st.columns(5)
    for idx, animal in enumerate(ANIMAUX):
        emoji = ANIMAL_TO_EMOJI[animal]
        col = cols[idx % 5]
        
        is_selected = (st.session_state.animal_selectionne == animal)
        btn_label = f"{emoji} {animal}"
        btn_type = "primary" if is_selected else "secondary"
        
        col.button(
            btn_label, 
            key=f"btn_anim_{animal}", 
            type=btn_type, 
            use_container_width=True,
            on_click=fixer_animal,
            args=(animal,)
        )

    # Étape 2 : Choix de l'adjectif (S'affiche dès qu'un animal est cliqué)
    if st.session_state.animal_selectionne:
        animal_choisi = st.session_state.animal_selectionne
        emoji_choisi = ANIMAL_TO_EMOJI[animal_choisi]

        st.markdown("---")
        
        col_l, col_center, col_r = st.columns([1, 2, 1])
        with col_center:
            st.markdown(
                f"<div style='text-align:center;'><div class='animal-selected-badge'><span class='animal-selected-emoji'>{emoji_choisi}</span><span class='animal-selected-name'>Animal choisi : {animal_choisi}</span></div></div>",
                unsafe_allow_html=True
            )

            # Recherche des adjectifs déjà pris pour cet animal
            adjectifs_pris = [
                p["adjectif"] for p in st.session_state.pseudos_reserves 
                if isinstance(p, dict) and p.get("animal") == animal_choisi
            ]
            adjectifs_disponibles = [adj for adj in ADJECTIFS if adj not in adjectifs_pris]

            adjectif_choisi = st.selectbox(
                "Étape 2 : Choisissez votre Adjectif :", 
                options=["-- Sélectionner un adjectif --"] + adjectifs_disponibles
            )

            if adjectif_choisi != "-- Sélectionner un adjectif --":
                pseudo_complet = f"{animal_choisi} {adjectif_choisi}"
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button(f"✨ Entrer en tant que {pseudo_complet}", type="primary", use_container_width=True):
                    st.session_state.pseudos_reserves.append({"animal": animal_choisi, "adjectif": adjectif_choisi})
                    st.session_state.user_pseudo = pseudo_complet
                    st.rerun()

# ------------------------------------------------------------------------------
# 5. ÉCRAN 2 : TABLEAU DE BORD CONNECTÉ
# ------------------------------------------------------------------------------
else:
    # Header profil
    col_head1, col_head2 = st.columns([4, 1])
    with col_head1:
        st.markdown(
            f"<div class='user-header'>🧠 Profil actif : {st.session_state.user_pseudo}</div>",
            unsafe_allow_html=True
        )
    with col_head2:
        if st.button("Changer de profil"):
            st.session_state.user_pseudo = None
            st.session_state.animal_selectionne = None
            st.rerun()

    st.markdown("<h1 class='main-title' style='text-align:left; margin-top:15px;'>🎯 Tableau de bord des Révisions</h1>", unsafe_allow_html=True)

    tab_actuel, tab_historique, tab_avenir = st.tabs(["🔥 Semaine Actuelle", "📜 Semaines Passées & Corrections", "📅 Semaines À Venir"])

    # --- TAB 1 : QUIZ EN COURS ---
    with tab_actuel:
        session_active = next(s for s in SESSIONS if s["statut"] == "Actuelle")
        
        st.markdown(
            f"<div class='card-actuelle'><h3 style='color:#0f766e;'>📝 {session_active['titre']}</h3><p style='color:#64748b; font-size:0.9rem;'>📅 Session ouverte : {session_active['dates']}</p></div>",
            unsafe_allow_html=True
        )

        with st.form("quiz_form"):
            reponses = {}
            for idx, q in enumerate(session_active["questions"]):
                st.write(f"**{q['q']}**")
                reponses[idx] = st.radio("Votre réponse :", q["options"], key=f"q_{idx}", index=None)
                st.divider()

            if st.form_submit_button("🚀 Envoyer mes réponses", type="primary"):
                if None in reponses.values():
                    st.error("Veuillez répondre à l'ensemble des questions avant de valider !")
                else:
                    st.balloons()
                    st.success(f"Réponses enregistrées avec succès pour **{st.session_state.user_pseudo}** !")

    # --- TAB 2 : HISTORIQUE & CORRECTIONS ---
    with tab_historique:
        sessions_passees = [s for s in SESSIONS if s["statut"] == "Passee"]
        for s in sessions_passees:
            st.markdown(
                f"<div class='card-passee'><h3 style='color:#4338ca;'>{s['titre']}</h3><p style='color:#64748b; font-size:0.9rem;'>Clôturé : {s['dates']}</p>",
                unsafe_allow_html=True
            )

            col_pod, col_corr = st.columns(2)
            
            with col_pod:
                st.markdown("#### 🏆 Top 10 - Classement")
                for p in s.get("podium", [])[:10]:
                    st.write(f"**{p['rang']}** — {p['pseudo']} ({p['score']})")

            with col_corr:
                st.markdown("#### 📖 Corrections & Explications")
                for q in s["questions"]:
                    with st.expander(q["q"]):
                        st.success(f"Bonne réponse : {q['rep']}")
            
            st.markdown("</div>", unsafe_allow_html=True)

    # --- TAB 3 : SEMAINES À VENIR ---
    with tab_avenir:
        sessions_futures = [s for s in SESSIONS if s["statut"] == "A venir"]
        for s in sessions_futures:
            st.markdown(
                f"<div class='card-avenir'><h4 style='color:#b45309;'>🔒 {s['titre']}</h4><p style='margin:0;'>📅 Ouverture prévue : <strong>{s['dates']}</strong></p></div>",
                unsafe_allow_html=True
            )
