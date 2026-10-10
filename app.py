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
# 2. STYLE CSS (Cadre hospitalier chaleureux & coloré)
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
        margin-bottom: 1rem;
    }

    /* Badge Equipe des Urgences GHR */
    .team-badge {
        display: inline-block;
        background-color: #fef3c7;
        color: #b45309;
        font-weight: 700;
        padding: 6px 18px;
        border-radius: 20px;
        font-size: 0.95rem;
        border: 1px solid #fde68a;
        margin-bottom: 10px;
    }

    /* Carte de Profil / Inscription ajustée */
    .profile-card-header {
        background: white;
        border-top-left-radius: 24px;
        border-top-right-radius: 24px;
        padding: 25px 25px 10px 25px;
        border-top: 2px solid #99f6e4;
        border-left: 2px solid #99f6e4;
        border-right: 2px solid #99f6e4;
        max-width: 580px;
        margin: 0 auto;
        text-align: center;
    }

    /* Badge Animal Coloré */
    .animal-badge {
        display: inline-flex;
        align-items: center;
        gap: 15px;
        padding: 10px 25px;
        border-radius: 50px;
        background-color: #e0f2fe;
        border: 2px solid #38bdf8;
        box-shadow: 0 4px 12px rgba(56, 189, 248, 0.2);
        margin: 10px 0;
    }
    .animal-emoji { font-size: 2.4rem; }
    .animal-name { color: #0369a1; font-weight: 700; font-size: 1.25rem; }

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
    "Lapin": "🐇", "Ours": "🐻", "Castor": "🦫", "Elephant": "🐘", "Hamster": "🐹",
    "Panda": "🐼", "Kangourou": "🦘", "Dauphin": "🐬", "Faucon": "🦅", "Ecureuil": "🐿️",
    "Lynx": "🐆", "Lémurien": "🐒", "Ornithorinque": "🦆", "Loup": "🐺", "Hérisson": "🦔"
}

ANIMAUX = list(ANIMAL_TO_EMOJI.keys())
ADJECTIFS = ["Astucieux", "Timide", "Ambitieux", "Survolté", "Combatif", "Emotif", "Espiègle", "Gourmand", "Malin", "Optimiste"]

# Enregistrements en session
if "pseudos_reserves" not in st.session_state:
    st.session_state.pseudos_reserves = [{"animal": "Dauphin", "adjectif": "Malin"}]

if "user_pseudo" not in st.session_state:
    st.session_state.user_pseudo = None

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
            {"rang": "🥈 2ème", "pseudo": "Loup Combatif", "score": "9/10"}
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

    # Entête de la carte de profil
    st.markdown("""
        <div class='profile-card-header
