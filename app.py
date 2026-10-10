import datetime
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# ------------------------------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Révisions Équipe HAS 2027",
    page_icon="🧠",
    layout="wide"
)

# ------------------------------------------------------------------------------
# 2. CONNEXION SÉCURISÉE À GOOGLE SHEETS VIA GSPREAD
# ------------------------------------------------------------------------------
@st.cache_resource
def get_gspread_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    return gspread.authorize(credentials)

def get_sheet():
    client = get_gspread_client()
    return client.open_by_url(st.secrets["spreadsheet_url"])

def charger_utilisateurs():
    try:
        sheet = get_sheet().worksheet("Utilisateurs")
        records = sheet.get_all_records()
        return {str(r["Pseudo"]): str(r["Mot_De_Passe"]) for r in records if "Pseudo" in r and r["Pseudo"]}
    except Exception as e:
        st.error(f"Erreur lors de la lecture des utilisateurs : {e}")
        return {}

def ajouter_utilisateur(pseudo, mdp):
    try:
        sheet = get_sheet().worksheet("Utilisateurs")
        date_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        sheet.append_row([date_str, str(pseudo), str(mdp)])
        return True
    except Exception as e:
        st.error(f"Erreur d'enregistrement dans Google Sheets : {e}")
        return False

def charger_notes_utilisateur(pseudo):
    try:
        sheet = get_sheet().worksheet("Reponses")
        records = sheet.get_all_records()
        return [r for r in records if str(r.get("Pseudo")) == str(pseudo)]
    except Exception as e:
        st.error(f"Erreur lors du chargement des notes : {e}")
        return []

def enregistrer_reponse(pseudo, semaine_id, score, total):
    try:
        sheet = get_sheet().worksheet("Reponses")
        date_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        sheet.append_row([date_str, str(pseudo), int(semaine_id), int(score), int(total)])
        return True
    except Exception as e:
        st.error(f"Erreur de sauvegarde des réponses : {e}")
        return False

# ------------------------------------------------------------------------------
# 3. STYLE CSS (Thème hospitalier chaleureux & coloré)
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

    /* Cartes de connexion / profil */
    .auth-card-header {
        background: white;
        border-radius: 20px;
        padding: 20px;
        border: 2px solid #99f6e4;
        max-width: 600px;
        margin: 0 auto 15px auto;
        text-align: center;
        box-shadow: 0 4px 15px rgba(15, 118, 110, 0.08);
    }

    /* Vignette Animal Sélectionné */
    .animal-selected-badge {
        display: inline-flex;
        align-items: center;
        gap: 12px;
        padding: 8px 20px;
        border-radius: 50px;
        background-color: #e0f2fe;
        border: 2px solid #38bdf8;
        box-shadow: 0 4px 12px rgba(56, 189, 248, 0.2);
        margin: 10px 0;
    }
    .animal-selected-emoji { font-size: 2rem; }
    .animal-selected-name { color: #0369a1; font-weight: 700; font-size: 1.1rem; }

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

    /* Cartes colorées du tableau de bord */
    .card-progression {
        background-color: #ffffff;
        border-radius: 20px;
        padding: 20px;
        border: 2px solid #38bdf8;
        box-shadow: 0 6px 18px rgba(56, 189, 248, 0.12);
        margin-bottom: 20px;
    }

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

    /* Onglets sur-mesure */
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
# 4. DONNÉES & VARIABLES DE SESSION
# ------------------------------------------------------------------------------
ANIMAL_TO_EMOJI = {
    "Lapin": "🐇", "Ours": "🐻", "Cochon": "🐷", "Elephant": "🐘", "Hamster": "🐹",
    "Panda": "🐼", "Kangourou": "🦘", "Dauphin": "🐬", "Faucon": "🦅", "Ecureuil": "🐿️",
    "Lynx": "🐆", "Lémurien": "🐒", "Canard": "🦆", "Loup": "🐺", "Hérisson": "🦔"
}

ANIMAUX = list(ANIMAL_TO_EMOJI.keys())
ADJECTIFS = ["Astucieux", "Timide", "Ambitieux", "Survolté", "Combatif", "Emotif", "Espiègle", "Gourmand", "Malin", "Optimiste"]

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
# 5. ÉCRAN D'AUTHENTIFICATION (SI NON CONNECTÉ)
# ------------------------------------------------------------------------------
if not st.session_state.user_pseudo:
    st.markdown("<h1 class='main-title'>🧠 Pause Révision HAS 2027</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Espace ludique, individuel & sécurisé</p>", unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["🔑 Se connecter", "✨ Créer un compte (1ère visite)"])

    comptes_existants = charger_utilisateurs()

    # --- ONGLET 1 : CONNEXION ---
    with tab_login:
        st.markdown("<div class='auth-card-header'><h3 style='color:#0f766e; margin:0;'>Connexion à votre espace</h3></div>", unsafe_allow_html=True)
        
        col_l, col_center, col_r = st.columns([1, 2, 1])
        with col_center:
            pseudos_liste = list(comptes_existants.keys())
            if not pseudos_liste:
                st.info("Aucun compte créé pour le moment. Allez dans l'onglet 'Créer un compte' !")
            else:
                pseudo_saisi = st.selectbox("Choisissez votre Pseudo :", options=["-- Sélectionner --"] + pseudos_liste)
                mdp_saisi = st.text_input("Mot de passe :", type="password")

                if st.button("🚀 Me connecter", type="primary", use_container_width=True):
                    if pseudo_saisi != "-- Sélectionner --" and mdp_saisi:
                        mdp_attendu = comptes_existants.get(pseudo_saisi)
                        if str(mdp_saisi) == str(mdp_attendu):
                            st.session_state.user_pseudo = pseudo_saisi
                            st.rerun()
                        else:
                            st.error("Mot de passe incorrect !")
                    else:
                        st.warning("Veuillez sélectionner un pseudo et saisir votre mot de passe.")

    # --- ONGLET 2 : CRÉATION DE COMPTE ---
    with tab_register:
        st.markdown("""
            <div class='auth-card-header'>
                <h3 style='color:#0f766e; margin:0;'>🎭 Choisissez votre Avatar & Mot de passe</h3>
                <p style='color:#64748b; font-size:0.9rem; margin-top:5px;'>Ce pseudo et ce mot de passe vous suivront tout au long des révisions.</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<h4 style='text-align:center; color:#0f766e;'>Étape 1 : Cliquez sur un Animal</h4>", unsafe_allow_html=True)

        cols = st.columns(5)
        for idx, animal in enumerate(ANIMAUX):
            emoji = ANIMAL_TO_EMOJI[animal]
            col = cols[idx % 5]
            
            is_selected = (st.session_state.animal_selectionne == animal)
            btn_label = f"{emoji} {animal}"
            btn_type = "primary" if is_selected else "secondary"
            
            col.button(
                btn_label, 
                key=f"btn_reg_anim_{animal}", 
                type=btn_type, 
                use_container_width=True,
                on_click=fixer_animal,
                args=(animal,)
            )

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

                # Filtrer les adjectifs déjà pris pour cet animal
                adjectifs_pris = [p.split(" ")[1] for p in comptes_existants.keys() if p.startswith(animal_choisi) and " " in p]
                adjectifs_disponibles = [adj for adj in ADJECTIFS if adj not in adjectifs_pris]

                adjectif_choisi = st.selectbox("Étape 2 : Choisissez votre Adjectif :", options=["-- Sélectionner un adjectif --"] + adjectifs_disponibles)

                if adjectif_choisi != "-- Sélectionner un adjectif --":
                    pseudo_cree = f"{animal_choisi} {adjectif_choisi}"
                    
                    st.markdown("##### Étape 3 : Créez un mot de passe simple")
                    nouveau_mdp = st.text_input("Mot de passe (5 à 10 caractères) :", type="password", key="new_mdp_input")
                    
                    if st.button(f"✨ Enregistrer mon compte ({pseudo_cree})", type="primary", use_container_width=True):
                        if len(nouveau_mdp) < 3:
                            st.error("Veuillez saisir un mot de passe d'au moins 3 caractères.")
                        else:
                            if ajouter_utilisateur(pseudo_cree, nouveau_mdp):
                                st.session_state.user_pseudo = pseudo_cree
                                st.success(f"Compte créé avec succès ! Bienvenue {pseudo_cree}.")
                                st.rerun()

# ------------------------------------------------------------------------------
# 6. ÉCRAN TABLEAU DE BORD CONNECTÉ
# ------------------------------------------------------------------------------
else:
    col_head1, col_head2 = st.columns([4, 1])
    with col_head1:
        st.markdown(f"<div class='user-header'>🧠 Profil actif : {st.session_state.user_pseudo}</div>", unsafe_allow_html=True)
    with col_head2:
        if st.button("🔒 Déconnexion"):
            st.session_state.user_pseudo = None
            st.session_state.animal_selectionne = None
            st.rerun()

    st.markdown("<h1 class='main-title' style='text-align:left; margin-top:15px;'>🎯 Tableau de bord des Révisions</h1>", unsafe_allow_html=True)

    tab_actuel, tab_progression, tab_historique, tab_avenir = st.tabs([
        "🔥 Semaine Actuelle", 
        "📊 Ma Progression", 
        "📜 Semaines Passées", 
        "📅 Semaines À Venir"
    ])

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
                    # Calcul de la note exacte
                    score_obtenu = sum(1 for idx, q in enumerate(session_active["questions"]) if reponses[idx] == q["rep"])
                    total_q = len(session_active["questions"])
                    
                    if enregistrer_reponse(st.session_state.user_pseudo, session_active["id"], score_obtenu, total_q):
                        st.balloons()
                        st.success(f"Réponses enregistrées dans Google Sheets pour **{st.session_state.user_pseudo}** ! Score : {score_obtenu}/{total_q}")

    # --- TAB 2 : MA PROGRESSION PERSONNELLE ---
    with tab_progression:
        st.markdown("<div class='card-progression'>", unsafe_allow_html=True)
        st.markdown(f"### 📈 Progression de **{st.session_state.user_pseudo}**")
        
        mes_notes = charger_notes_utilisateur(st.session_state.user_pseudo)
        
        if not mes_notes:
            st.info("Vous n'avez pas encore répondu à un quiz. Participez à la semaine actuelle pour voir apparaître vos statistiques !")
        else:
            total_points = sum(int(item["Score"]) for item in mes_notes if "Score" in item)
            total_possible = sum(int(item["Total_Questions"]) for item in mes_notes if "Total_Questions" in item)
            pourcentage = int((total_points / total_possible) * 100) if total_possible > 0 else 0

            c1, c2, c3 = st.columns(3)
            c1.metric("Quiz complétés", len(mes_notes))
            c2.metric("Total des points", f"{total_points} / {total_possible}")
            c3.metric("Taux de réussite", f"{pourcentage} %")

            st.divider()
            st.markdown("#### 📜 Historique détaillé de vos notes :")
            for item in mes_notes:
                st.write(f"• **Semaine {item.get('Semaine_ID')}** (le {item.get('Horodateur')}) : **{item.get('Score')}/{item.get('Total_Questions')}**")

        st.markdown("</div>", unsafe_allow_html=True)

    # --- TAB 3 : SEMAINES PASSÉES ---
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

    # --- TAB 4 : SEMAINES À VENIR ---
    with tab_avenir:
        sessions_futures = [s for s in SESSIONS if s["statut"] == "A venir"]
        for s in sessions_futures:
            st.markdown(
                f"<div class='card-avenir'><h4 style='color:#b45309;'>🔒 {s['titre']}</h4><p style='margin:0;'>📅 Ouverture prévue : <strong>{s['dates']}</strong></p></div>",
                unsafe_allow_html=True
            )
