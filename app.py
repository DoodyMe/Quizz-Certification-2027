import datetime
import os
import base64
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from streamlit_pdf_viewer import pdf_viewer

# ------------------------------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Révisions Équipe HAS 2027 - Urgences Mulhouse",
    page_icon="🧠",
    layout="wide"
)

# ------------------------------------------------------------------------------
# 2. CONNEXION GOOGLE SHEETS VIA GSPREAD
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
    except Exception:
        return {}

def ajouter_utilisateur(pseudo, mdp):
    try:
        sheet = get_sheet().worksheet("Utilisateurs")
        date_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        sheet.append_row([date_str, str(pseudo), str(mdp)])
        return True
    except Exception as e:
        st.error(f"Erreur d'enregistrement Google Sheets : {e}")
        return False

def charger_notes_utilisateur(pseudo):
    try:
        sheet = get_sheet().worksheet("Reponses")
        records = sheet.get_all_records()
        return [r for r in records if str(r.get("Pseudo")) == str(pseudo)]
    except Exception:
        return []

def enregistrer_reponse(pseudo, semaine_id, score, total):
    try:
        sheet = get_sheet().worksheet("Reponses")
        date_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        sheet.append_row([date_str, str(pseudo), int(semaine_id), int(score), int(total)])
        return True
    except Exception as e:
        st.error(f"Erreur de sauvegarde : {e}")
        return False

# Fonction pour afficher et proposer le téléchargement d'un vrai PDF depuis le dossier fiches_pdf/
def afficher_et_telecharger_pdf(semaine_id, metier_slug, nom_affichage):
    chemin_pdf = f"fiches_pdf/semaine{semaine_id}_{metier_slug}.pdf"
    
    if os.path.exists(chemin_pdf):
        with open(chemin_pdf, "rb") as f:
            pdf_bytes = f.read()
            
        # 1. Bouton de téléchargement propre
        st.download_button(
            label=f"📥 Télécharger la Fiche Mémo ({nom_affichage}) - PDF",
            data=pdf_bytes,
            file_name=f"HAS_2027_Semaine_{semaine_id}_{metier_slug}.pdf",
            mime="application/pdf",
            key=f"dl_pdf_{semaine_id}_{metier_slug}"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 2. Affichage visuel direct et intégré de la jolie fiche dans l'app
        with st.expander(f"👁️ Afficher la Fiche Mémo en un coup d'œil ({nom_affichage})", expanded=True):
            pdf_viewer(input=pdf_bytes, width=700)
            
    else:
        st.info(f"💡 Le fichier PDF officiel pour **{nom_affichage}** sera bientôt déposé.")

# ------------------------------------------------------------------------------
# 3. STYLE CSS (DESIGN PASTEL HOSPITALIER & VIGNETTES COULEURS)
# ------------------------------------------------------------------------------
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #e6fffa 0%, #f0f9ff 50%, #f5f3ff 100%);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .main-title { color: #0f766e; font-weight: 800; margin-bottom: 0rem; }
    .subtitle { color: #0369a1; font-weight: 600; margin-top: 0.2rem; }
    
    .service-logo img {
        border-radius: 20px;
        border: 3px solid #99f6e4;
        box-shadow: 0 6px 20px rgba(15, 118, 110, 0.12);
        max-width: 130px;
    }

    .auth-card-header {
        background: white; border-radius: 20px; padding: 20px;
        border: 2px solid #99f6e4; max-width: 600px; margin: 0 auto 15px auto;
        text-align: center; box-shadow: 0 4px 15px rgba(15, 118, 110, 0.08);
    }
    .animal-selected-badge {
        display: inline-flex; align-items: center; gap: 12px; padding: 8px 20px;
        border-radius: 50px; background-color: #e0f2fe; border: 2px solid #38bdf8; margin: 10px 0;
    }
    .animal-selected-emoji { font-size: 2rem; }
    .animal-selected-name { color: #0369a1; font-weight: 700; font-size: 1.1rem; }
    .user-header {
        background: linear-gradient(135deg, #0d9488 0%, #0284c7 100%);
        color: white; padding: 12px 26px; border-radius: 50px; display: inline-block; font-weight: 700;
    }
    .card-progression { background-color: #ffffff; border-radius: 20px; padding: 20px; border: 2px solid #38bdf8; margin-bottom: 20px; }
    .card-actuelle { background-color: #ffffff; border-radius: 20px; padding: 25px; border-left: 8px solid #10b981; margin-bottom: 20px; }
    .card-avenir { background-color: #fffbeb; border-radius: 20px; padding: 20px; border-left: 8px solid #f59e0b; margin-bottom: 15px; }
    
    .question-card {
        background: white; border-radius: 24px; padding: 30px;
        border: 2px solid #99f6e4; box-shadow: 0 10px 25px rgba(15, 118, 110, 0.08); margin-bottom: 20px;
    }
    .question-badge {
        background: #ccfbf1; color: #0f766e; padding: 6px 16px;
        border-radius: 30px; font-weight: 700; font-size: 0.9rem; display: inline-block; margin-bottom: 15px;
    }
    .question-title { color: #0f766e; font-weight: 700; font-size: 1.25rem; margin-bottom: 20px; line-height: 1.5; }

    /* BILAN DE FIN DE QUIZ STATIQUE */
    .result-card-ok {
        background: #f0fdf4; border-radius: 16px; padding: 18px;
        border: 2px solid #86efac; margin-bottom: 15px;
    }
    .result-card-err {
        background: #fef2f2; border-radius: 16px; padding: 18px;
        border: 2px solid #fca5a5; margin-bottom: 15px;
    }

    /* VIGNETTES SEMAINES PASSÉES & STYLES COULEURS PAR MÉTIER */
    .vignette-semaine {
        background: #ffffff; border-radius: 24px; padding: 25px;
        border: 2px solid #cbd5e1; box-shadow: 0 8px 25px rgba(148, 163, 184, 0.1); margin-bottom: 30px;
    }
    .vignette-header {
        background: linear-gradient(135deg, #0f766e 0%, #0369a1 100%);
        color: white; padding: 12px 20px; border-radius: 14px; font-weight: 800; font-size: 1.2rem; margin-bottom: 15px;
    }

    /* CODE COULEURS PASTELS PAR MÉTIER */
    .memo-box-tc { background: #f0f9ff; border-radius: 16px; padding: 20px; border-left: 6px solid #0284c7; }
    .memo-box-ide { background: #f0fdf4; border-radius: 16px; padding: 20px; border-left: 6px solid #16a34a; }
    .memo-box-as { background: #fffbeb; border-radius: 16px; padding: 20px; border-left: 6px solid #d97706; }
    .memo-box-med { background: #f5f3ff; border-radius: 16px; padding: 20px; border-left: 6px solid #7c3aed; }
    .memo-box-arm { background: #faf5ff; border-radius: 16px; padding: 20px; border-left: 6px solid #c026d3; }
    .memo-box-acc { background: #f0fdfa; border-radius: 16px; padding: 20px; border-left: 6px solid #0d9488; }
    .memo-box-branc { background: #fdf2f8; border-radius: 16px; padding: 20px; border-left: 6px solid #db2777; }
    .memo-box-ash { background: #f1f5f9; border-radius: 16px; padding: 20px; border-left: 6px solid #475569; }
    .memo-box-cadre { background: #fff7ed; border-radius: 16px; padding: 20px; border-left: 6px solid #ea580c; }

    .memo-title-text { font-weight: 800; font-size: 1.15rem; margin-bottom: 10px; color: #1e293b; }

    .stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: flex-start; }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff; border-radius: 20px; padding: 8px 18px; font-weight: 700; color: #334155; border: 1px solid #cbd5e1;
    }
    .stTabs [aria-selected="true"] {
        background: #0f766e !important; color: white !important; border: none !important;
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

if "login_animal_selectionne" not in st.session_state:
    st.session_state.login_animal_selectionne = None

if "current_q_index" not in st.session_state:
    st.session_state.current_q_index = 0

if "user_quiz_answers" not in st.session_state:
    st.session_state.user_quiz_answers = {}

if "quiz_paused" not in st.session_state:
    st.session_state.quiz_paused = False

def fixer_animal(nom_animal):
    st.session_state.animal_selectionne = nom_animal

def fixer_animal_login(nom_animal):
    st.session_state.login_animal_selectionne = nom_animal

# --- SESSIONS DE QUIZ & FICHES MÉMO HAS 2027 ---
SESSIONS = [
    {
        "id": 0,
        "titre": "Semaine 0 - Session de Démonstration & Test",
        "date_debut": datetime.date(2026, 1, 1),
        "date_fin": datetime.date(2027, 12, 31),
        "tronc_commun": [
            {
                "q": "🔎 [Démo Tronc Commun] Quel est l'objectif principal de cette plateforme de révision automatisée ?",
                "options": [
                    "Sanctionner les soignants qui manquent de temps de formation",
                    "Offrir un outil ludique, anonyme et régulier pour préparer sereinement la certification HAS 2027",
                    "Remplacer les réunions d'équipe physiques"
                ],
                "rep": "Offrir un outil ludique, anonyme et régulier pour préparer sereinement la certification HAS 2027"
            },
            {
                "q": "🛡️ [Démo Tronc Commun] Comment la confidentialité des soignants est-elle garantie sur le site ?",
                "options": [
                    "Par un identifiant unique combinant un Avatar Animal + un Adjectif et un mot de passe personnel",
                    "En publiant les noms et prénoms réels des soignants sur le tableau de garde",
                    "En envoyant les résultats par mail à la direction"
                ],
                "rep": "Par un identifiant unique combinant un Avatar Animal + un Adjectif et un mot de passe personnel"
            },
            {
                "q": "📋 [Démo Tronc Commun] Lors de la visite des experts HAS, quelle est la priorité concernant l'identitovigilance aux urgences ?",
                "options": [
                    "Vérifier le bracelet d'identification à chaque étape de la prise en charge (soins, examens, transports)",
                    "Demander au patient de garder ses papiers d'identité dans sa poche",
                    "Coller une étiquette sur la blouse du soignant"
                ],
                "rep": "Vérifier le bracelet d'identification à chaque étape de la prise en charge (soins, examens, transports)"
            },
            {
                "q": "🤝 [Démo Tronc Commun] Quelle est la définition de la bientraitance retenue par la HAS aux urgences ?",
                "options": [
                    "Une posture globale de respect, d'écoute, de préservation de l'intimité et de prise en charge de la douleur",
                    "L'obligation d'offrir un café à chaque accompagnant",
                    "L'absence de plainte enregistrée durant l'année"
                ],
                "rep": "Une posture globale de respect, d'écoute, de préservation de l'intimité et de prise en charge de la douleur"
            },
            {
                "q": "🚨 [Démo Tronc Commun] En cas d'Événement Indésirable (EI), quelle est la culture de sécurité prônée par l'établissement ?",
                "options": [
                    "Chercher immédiatement un responsable à sanctionner",
                    "Déclarer l'événement sans crainte de blâme pour analyser collectivement les causes et améliorer le système",
                    "Cacher l'incident si le patient ne s'en est pas rendu compte"
                ],
                "rep": "Déclarer l'événement sans crainte de blâme pour analyser collectivement les causes et améliorer le système"
            }
        ],
        "metiers": {
            "IDE": [{"q": "[Démo IDE] Quelle est l'obligation de traçabilité lors de la réévaluation de la douleur après administration antalgique ?", "options": ["Tracer l'horaire, l'échelle de douleur réévaluée et l'efficacité sur le dossier patient informatique", "Informer oralement la collègue de la relève uniquement", "Attendre la fin du poste pour noter une note globale"], "rep": "Tracer l'horaire, l'échelle de douleur réévaluée et l'efficacité sur le dossier patient informatique"}],
            "AS": [{"q": "[Démo AS] Quelle échelle d'évaluation de la douleur est privilégiée chez le sujet âgé non communicant ?", "options": ["L'échelle comportementale ALGOPLUS", "L'Échelle Visuelle Analogique (EVA)", "L'Échelle Numérique (EN)"], "rep": "L'échelle comportementale ALGOPLUS"}],
            "Médecin": [{"q": "[Démo Médecin] Quelle procédure doit être tracée lors d'une décision de Limitation ou Arrêt de Traitement (LAT) ?", "options": ["La décision collégiale, la consultation de la personne de confiance/directives anticipées", "Un simple mot dans le dossier sans avis collégial", "L'accord verbal du chef de service uniquement"], "rep": "La décision collégiale, la consultation de la personne de confiance/directives anticipées"}],
            "ARM": [{"q": "[Démo ARM] Quel élément d'identitovigilance est indispensable lors de la création d'un dossier de régulation ?", "options": ["Nom de naissance, prénom, date de naissance et vérification de l'absence de doublon", "Surnom habituel du patient", "Uniquement l'adresse de l'intervention"], "rep": "Nom de naissance, prénom, date de naissance et vérification de l'absence de doublon"}],
            "Accueil": [{"q": "[Démo Accueil] Quelle attitude adopter si un patient en salle d'attente signale une douleur thoracique aiguë ?", "options": ["Prévenir immédiatement l'IAO pour une évaluation clinique sans délai", "Lui dire de remettre son ticket dans la borne", "Lui proposer un verre d'eau"], "rep": "Prévenir immédiatement l'IAO pour une évaluation clinique sans délai"}],
            "Brancardier": [{"q": "[Démo Brancardier] Quelle action est obligatoire avant de transférer un patient vers le scanner ?", "options": ["Vérifier la concordance de l'identité sur le bracelet d'identification", "Regarder uniquement le numéro de box", "Demander au patient son numéro de téléphone"], "rep": "Vérifier la concordance de l'identité sur le bracelet d'identification"}],
            "ASH": [{"q": "[Démo ASH] Quel produit doit être utilisé pour la désinfection d'un box d'urgences entre deux patients ?", "options": ["Un détergent-désinfectant homologué selon le protocole de l'établissement", "Uniquement de l'eau claire", "Du produit à vitres classique"], "rep": "Un détergent-désinfectant homologué selon le protocole de l'établissement"}],
            "Cadre": [{"q": "[Démo Cadre] Quel outil permet de suivre le niveau de préparation de l'équipe aux exigences HAS ?", "options": ["Le suivi automatisé des participations et du taux de réussite global sur le tableau de bord", "Une interrogation orale individuelle impromptue", "Le contrôle des heures de présence uniquement"], "rep": "Le suivi automatisé des participations et du taux de réussite global sur le tableau de bord"}]
        },
        "fiches_reflexes": {
            "Tronc Commun": {
                "class": "memo-box-tc",
                "slug": "tronc_commun",
                "points": [
                    "**Identitovigilance** : Contrôle obligatoire des 3 items (Nom de naissance, Prénom, Date de naissance) sur le bracelet d'identification à chaque étape de soins.",
                    "**Bientraitance** : Posture de respect, préservation systématique de l'intimité (fermeture des box) et évaluation prioritaire de la douleur.",
                    "**Culture de Sécurité** : Déclaration systématique et non punitive des Événements Indésirables (EI) sur le logiciel institutionnel pour l'analyse d'équipe."
                ]
            },
            "IDE": {
                "class": "memo-box-ide",
                "slug": "ide",
                "points": [
                    "**Traçabilité Douleur** : Inscription obligatoire de l'échelle initiale ET de la réévaluation post-antalgique avec délai d'efficacité sur l'EPR.",
                    "**Sécurité de l'Administration** : Vérification concordante du bracelet d'identification avant toute injection ou pose de voie veineuse."
                ]
            },
            "AS": {
                "class": "memo-box-as",
                "slug": "as",
                "points": [
                    "**Évaluation de la Douleur** : Utilisation privilégiée de l'échelle comportementale ALGOPLUS pour les sujets âgés non communicants ou confus.",
                    "**Prévention** : Recherche systématique des causes réversibles d'inconfort ou d'agitation (globe vésical, fécalome, douleur non verbalisée)."
                ]
            },
            "Médecin": {
                "class": "memo-box-med",
                "slug": "medecin",
                "points": [
                    "**Décisions de LAT** : Traçabilité obligatoire de la procédure collégiale, de la recherche des directives anticipées et de la consultation de la personne de confiance.",
                    "**Comptes-rendus de passage** : Rédaction et transmission au médecin traitant ou remise au patient garantie sous 24 heures."
                ]
            },
            "ARM": {
                "class": "memo-box-arm",
                "slug": "arm",
                "points": [
                    "**Identitovigilance SAMU** : Recueil rigoureux du nom de naissance, prénom et date de naissance avec recherche d'antériorité pour éviter les doublons.",
                    "**Confidentialité** : Strict respect du secret professionnel lors de la réception des appels de tiers."
                ]
            },
            "Accueil & Admission": {
                "class": "memo-box-acc",
                "slug": "accueil",
                "points": [
                    "**Vigilance Salle d'Attente** : Alerte immédiate de l'IAO en cas de signalement de douleur aiguë, malaise ou dégradation clinique d'un usager.",
                    "**Confidentialité au Guichet** : Maintien des distances de sécurité et discrétion lors du recueil des données nominatives."
                ]
            },
            "Brancardier": {
                "class": "memo-box-branc",
                "slug": "brancardier",
                "points": [
                    "**Transferts Sécurisés** : Vérification active du bracelet d'identification avant tout déplacement vers un plateau technique (Scanner, Radio).",
                    "**Pudeur et Sécurité** : Relevage systématique des ridelles et recouvrement du patient par un drap de protection."
                ]
            },
            "ASH": {
                "class": "memo-box-ash",
                "slug": "ash",
                "points": [
                    "**Bio-nettoyage** : Application rigoureuse des procédures de désinfection des surfaces et mobilier au produit détergent-désinfectant homologué entre deux patients.",
                    "**Hygiène des Mains** : Friction hydro-alcoolique obligatoire avant d'entrer et en sortant de chaque box."
                ]
            },
            "Cadre de Santé": {
                "class": "memo-box-cadre",
                "slug": "cadre",
                "points": [
                    "**Management de la Qualité** : Pilotage bienveillant des indicateurs de préparation HAS et promotion de la culture positive de l'erreur (CREX / REX).",
                    "**Accompagnement** : Soutien des équipes dans la mise en œuvre au quotidien des procédures de bientraitance."
                ]
            }
        }
    },
    {
        "id": 1,
        "titre": "Semaine 1 - Droits du patient & Bientraitance",
        "date_debut": datetime.date(2026, 10, 16),
        "date_fin": datetime.date(2026, 11, 1),
        "tronc_commun": [
            {
                "q": "1. [Tronc Commun] Un patient accueilli aux urgences refuse un examen complémentaire. Quelle est la conduite à tenir légale ?",
                "options": [
                    "Réaliser l'examen malgré tout au vu de l'urgence médicale",
                    "Respecter son refus après lui avoir délivré une information claire sur les risques encourus",
                    "L'obliger à signer une décharge avant de le faire sortir immédiatement"
                ],
                "rep": "Respecter son refus après lui avoir délivré une information claire sur les risques encourus"
            },
            {
                "q": "2. [Tronc Commun] Quel est le délai légal de communication du dossier médical pour des soins datant de moins de 5 ans ?",
                "options": [
                    "48 heures maximum",
                    "8 jours maximum après un délai de réflexion de 48h",
                    "15 jours maximum"
                ],
                "rep": "8 jours maximum après un délai de réflexion de 48h"
            },
            {
                "q": "3. [Tronc Commun] Concernant la personne de confiance désignée par le patient, quelle affirmation est EXACTE ?",
                "options": [
                    "Elle prévaut obligatoirement sur les directives anticipées",
                    "Son avis prévaut sur celui de la famille si le patient ne peut plus s'exprimer",
                    "Elle est automatiquement destinataire du dossier médical du vivant du patient"
                ],
                "rep": "Son avis prévaut sur celui de la famille si le patient ne peut plus s'exprimer"
            },
            {
                "q": "4. [Tronc Commun] Lors de la prise en charge d'un patient sous mesure de protection juridique (Tutelle), qui consent aux soins d'urgence ?",
                "options": [
                    "Le tuteur obligatoirement, quel que soit l'état d'urgence",
                    "Le patient lui-même si son état le permet, l'urgence médicale prime sur l'accord du tuteur",
                    "Le juge des contentieux de la protection"
                ],
                "rep": "Le patient lui-même si son état le permet, l'urgence médicale prime sur l'accord du tuteur"
            },
            {
                "q": "5. [Tronc Commun] Dans un box d'urgences, la bientraitance et le respect de l'intimité imposent prioritairement de :",
                "options": [
                    "Fermer les rideaux/portes et baisser la voix lors de l'interrogatoire et des soins",
                    "Demander systématiquement à la famille de sortir pendant toute la durée du passage aux urgences",
                    "Ne pas poser de questions sur le mode de vie du patient"
                ],
                "rep": "Fermer les rideaux/portes et baisser la voix lors de l'interrogatoire et des soins"
            }
        ],
        "metiers": {
            "IDE": [
                {"q": "6. [Module IDE] Lors de l'administration d'un traitement antalgique réévalué aux urgences, quelle traçabilité minimale exige la HAS ?", "options": ["Horaire, molécule et nom du prescripteur uniquement sur le logiciel", "Score de douleur avant administration, re-évaluation post-injection et traçabilité de l'efficacité", "Transmission orale au médecin au changement d'équipe"], "rep": "Score de douleur avant administration, re-évaluation post-injection et traçabilité de l'efficacité"},
                {"q": "7. [Module IDE] En cas d'accueil aux urgences d'un mineur non accompagné refusant l'avertissement de ses parents, que devez-vous appliquer ?", "options": ["Refuser la prise en charge sans l'accord écrit parental", "Dispenser les soins d'urgence si le mineur le demande expressément et se faire accompagner par un majeur protecteur", "Appeler immédiatement la gendarmerie"], "rep": "Dispenser les soins d'urgence si le mineur le demande expressément et se faire accompagner par un majeur protecteur"},
                {"q": "8. [Module IDE] Dans la prise en charge des personnes victimes de violences aux urgences, quelle est la priorité de soins IDE ?", "options": ["Exiger un dépôt de plainte immédiat avant d'installer le patient", "Garantir un espace sécurisé, assurer la traçabilité des lésions sur certificat médical et orienter vers la prise en charge médico-psychologique", "Contacter directement le procureur sans l'accord du patient"], "rep": "Garantir un espace sécurisé, assurer la traçabilité des lésions sur certificat médical et orienter vers la prise en charge médico-psychologique"},
                {"q": "9. [Module IDE] Quelle règle d'identitovigilance s'impose avant toute pose de voie veineuse ou injection aux urgences ?", "options": ["Interroger le patient sur son nom/prénom/date de naissance et vérifier la concordance avec son bracelet", "Faire confiance au numéro de box indiqué sur le tableau d'affichage", "Regarder le nom écrit au crayon sur la perfusion"], "rep": "Interroger le patient sur son nom/prénom/date de naissance et vérifier la concordance avec son bracelet"},
                {"q": "10. [Module IDE] Quelle est la conduite à tenir face à la suspicion d'une erreur d'administration de traitement sans conséquence grave immédiate ?", "options": ["Ne rien dire pour éviter de perturber le patient", "Prévenir le médecin, surveiller le patient et déclarer l'Événement Indésirable (EI) sur le logiciel institutionnel", "Modifier discrètement la prescription a posteriori"], "rep": "Prévenir le médecin, surveiller le patient et déclarer l'Événement Indésirable (EI) sur le logiciel institutionnel"}
            ],
            "AS": [
                {"q": "6. [Module AS] Quelle mesure de bientraitance est prioritaire lors de la prise en charge d'une personne âgée confuse aux urgences ?", "options": ["Appliquer immédiatement des ridelles et une contention pelvienne pour éviter les chutes", "Évaluer la douleur, chercher des causes réversibles (globe, fécalome) et rassurer avec la présence d'un proche", "L'isoler dans une chambre fermée pour limiter les stimulations"], "rep": "Évaluer la douleur, chercher des causes réversibles (globe, fécalome) et rassurer avec la présence d'un proche"},
                {"q": "7. [Module AS] Un brancardage entre les urgences et la radiologie nécessite le respect de l'intimité. Quelle est la bonne pratique ?", "options": ["Déplacer le patient en blouse d'examen sans couverture s'il fait chaud", "Veiller au recouvrement du corps avec un drap/couverture et préserver le secret professionnel pendant le trajet", "Discuter du motif d'admission du patient avec le brancardier dans le couloir"], "rep": "Veiller au recouvrement du corps avec un drap/couverture et préserver le secret professionnel pendant le trajet"},
                {"q": "8. [Module AS] Un patient dépendant réclame de l'eau aux urgences alors qu'il est en attente d'avis médical. Que devez-vous faire ?", "options": ["Lui donner un grand verre d'eau immédiatement pour son confort", "Vérifier auprès de l'IDE si le patient est à jeun strict avant toute administration de boisson", "Lui dire d'attendre sa sortie des urgences"], "rep": "Vérifier auprès de l'IDE si le patient est à jeun strict avant toute administration de boisson"},
                {"q": "9. [Module AS] Lors de l'installation d'un patient fragile sur un brancard d'urgence, quel est le moyen prioritaire de prévention des escarres ?", "options": ["Laisser le patient sur le même drap pendant 12 heures", "Changer régulièrement les points d'appui, utiliser un matelas réducteur de pression et signaler tout érythème", "Mettre du talc sous les talons"], "rep": "Changer régulièrement les points d'appui, utiliser un matelas réducteur de pression et signaler tout érythème"},
                {"q": "10. [Module AS] Quelle est la bonne réaction si un proche agressif exige d'entrer dans la zone de soins ?", "options": ["L'insulter en retour pour imposer son autorité", "Garder son calme, utiliser une communication apaisante (Méthode DESC) et faire appel à l'équipe ou à la sécurité si nécessaire", "Fermer à clé la porte du box et laisser le proche seul"], "rep": "Garder son calme, utiliser une communication apaisante (Méthode DESC) et faire appel à l'équipe ou à la sécurité si nécessaire"}
            ],
            "Médecin": [
                {"q": "6. [Module Médecin] Concernant les directives anticipées aux urgences, quelle est la règle applicable pour le médecin ?", "options": ["Elles ont une durée de validité limitée à 3 ans", "Elles s'imposent pour toute décision de limitation/arrêt de traitement (sauf urgence vitale le temps de l'évaluation)", "Elles ne sont qu'un simple avis consultatif que le médecin peut ignorer librement"], "rep": "Elles s'imposent pour toute décision de limitation/arrêt de traitement (sauf urgence vitale le temps de l'évaluation)"},
                {"q": "7. [Module Médecin] Lors d'une décision de Limitation ou Arrêt de Traitement (LAT) aux urgences, quelle est l'obligation réglementaire ?", "options": ["Décider seul pour ne pas perdre de temps", "Organiser une procédure collégiale, consulter la personne de confiance/directives anticipées et tracer la décision dans le dossier", "Demander l'autorisation préalable au directeur de l'hôpital"], "rep": "Organiser une procédure collégiale, consulter la personne de confiance/directives anticipées et tracer la décision dans le dossier"},
                {"q": "8. [Module Médecin] Un proche réclame des informations médicales sur un patient majeur hospitalisé aux urgences. Le médecin peut lui répondre si :", "options": ["Le proche prouve son lien de parenté direct (livret de famille)", "Le patient ne s'y est pas opposé et a autorisé la transmission d'informations à ce proche", "Le proche habite sous le même toit que le patient"], "rep": "Le patient ne s'y est pas opposé et a autorisé la transmission d'informations à ce proche"},
                {"q": "9. [Module Médecin] Quelle information minimale doit obligatoirement être tracée dans l'EPR lors d'une sortie contre avis médical ?", "options": ["L'information claire délivrée sur les risques vitaux encourus, la proposition d'alternatives et la signature du formulaire dédié", "La mention 'Patient parti' sans autre précision", "Le règlement des frais de séjour"], "rep": "L'information claire délivrée sur les risques vitaux encourus, la proposition d'alternatives et la signature du formulaire dédié"},
                {"q": "10. [Module Médecin] Dans le cadre de la certification HAS, quel est le délai recommandé pour la rédaction et la transmission du compte-rendu de passage aux urgences ?", "options": ["Dans les 8 jours suivant la sortie", "Remis au patient à sa sortie ou transmis au médecin traitant dans les 24 heures maximum", "Dans le mois qui suit"], "rep": "Remis au patient à sa sortie ou transmis au médecin traitant dans les 24 heures maximum"}
            ],
            "ARM": [
                {"q": "6. [Module ARM] Lors de la création d'un dossier au SAMU/SAS, quelle est la priorité d'identitovigilance pour éviter les doublons ?", "options": ["Saisir uniquement le prénom et le numéro de téléphone portable", "Saisir le nom de naissance, le prénom, la date de naissance et vérifier l'existence d'un dossier antérieur", "Utiliser le pseudonyme donné par le patient à l'oral"], "rep": "Saisir le nom de naissance, le prénom, la date de naissance et vérifier l'existence d'un dossier antérieur"},
                {"q": "7. [Module ARM] Un appelant demande confirmation de l'admission aux urgences de son voisin par téléphone. Quelle est votre obligation ?", "options": ["Lui donner la réponse s'il connaît le nom et le prénom du patient", "Refuser poliment de répondre pour respecter le secret professionnel et la confidentialité", "Lui transférer immédiatement la ligne du médecin régulateur"], "rep": "Refuser poliment de répondre pour respecter le secret professionnel et la confidentialité"},
                {"q": "8. [Module ARM] Lors de la régulation d'un appel urgent pour détresse vitale, quelle traçabilité est exigée dans le logiciel d'appel ?", "options": ["Rédiger un compte-rendu uniquement si le patient est transporté par le SMUR", "Enregistrer l'horodatage des décisions, le motif de régulation et les moyens envoyés", "Ne rien saisir et faire confiance à la bande d'enregistrement audio"], "rep": "Enregistrer l'horodatage des décisions, le motif de régulation et les moyens envoyés"},
                {"q": "9. [Module ARM] Que faire en cas de réception d'un appel concernant une suspicion de violence intrafamiliale aiguë ?", "options": ["Passer l'appel en attente indéfinie", "Recueillir la localisation exacte, transmettre immédiatement au médecin régulateur et appliquer la procédure d'alerte dédiée", "Conseiller à la personne de rappeler le lendemain"], "rep": "Recueillir la localisation exacte, transmettre immédiatement au médecin régulateur et appliquer la procédure d'alerte dédiée"},
                {"q": "10. [Module ARM] Quelle est la règle concernant le partage d'informations médicales entre l'ARM et les équipes de secours sur le terrain ?", "options": ["Interdiction totale de donner la moindre information", "Transmettre uniquement les éléments strictement nécessaires à la sécurité de l'intervention et à la prise en charge du patient", "Lire l'intégralité de l'historique médical du patient sur la fréquence radio publique"], "rep": "Transmettre uniquement les éléments strictement nécessaires à la sécurité de l'intervention et à la prise en charge du patient"}
            ],
            "Accueil": [
                {"q": "6. [Module Accueil] Lors de l'enregistrement administratif d'un patient à la banque d'accueil, quel document doit être privilégié pour vérifier l'identité ?", "options": ["La carte de mutuelle ou un justificatif de domicile", "Une pièce d'identité officielle avec photo (CNI, passeport, titre de séjour) complétée de la carte Vitale", "La carte de fidélité ou le permis de conduire uniquement"], "rep": "Une pièce d'identité officielle avec photo (CNI, passeport, titre de séjour) complétée de la carte Vitale"},
                {"q": "7. [Module Accueil] Dans la salle d'attente, un patient vous informe d'une dégradation de son état ou d'une douleur aiguë. Quelle est votre action immédiate ?", "options": ["Lui demander de patienter gentiment que son nom soit appelé", "Alerter immédiatement l'Infirmier/ère d'Accueil et d'Orientation (IAO) pour une réévaluation clinique", "Lui donner un antalgique disponible dans le tirant du guichet"], "rep": "Alerter immédiatement l'Infirmier/ère d'Accueil et d'Orientation (IAO) pour une réévaluation clinique"},
                {"q": "8. [Module Accueil] Comment garantir la confidentialité des données lors des échanges à la banque d'accueil des urgences ?", "options": ["Répéter à haute voix la date de naissance du patient pour que toute la file d'attente l'entende", "Maintenir la distance de sécurité entre usagers, baisser la voix et ne pas laisser d'écrans nominatifs visibles du public", "Mettre le dossier papier en évidence sur le guichet"], "rep": "Maintenir la distance de sécurité entre usagers, baisser la voix et ne pas laisser d'écrans nominatifs visibles du public"},
                {"q": "9. [Module Accueil] Lors de l'accueil d'un patient sous protection juridique (Tutelle), quelle pièce administrative doit être réclamée pour le dossier ?", "options": ["Le jugement de tutelle désignant le tuteur légal et les coordonnées de ce dernier", "L'accord écrit du maire de la commune", "Une attestation sur l'honneur du voisin"], "rep": "Le jugement de tutelle désignant le tuteur légal et les coordonnées de ce dernier"},
                {"q": "10. [Module Accueil] En cas de forte affluence en salle d'attente des urgences, quelle information globale doit être délivrée aux usagers ?", "options": ["Informer de manière transparente sur les modalités de prise en charge basées sur le niveau de gravité et non l'ordre d'arrivée", "Donner un horaire de passage exact à chaque patient pour éviter les questions", "Fermer le guichet d'accueil jusqu'à désengorgement"], "rep": "Informer de manière transparente sur les modalités de prise en charge basées sur le niveau de gravité et non l'ordre d'arrivée"}
            ],
            "Brancardier": [
                {"q": "6. [Module Brancardier] Quelle vérification minimale d'identitovigilance est obligatoire AVANT de déplacer un patient des urgences vers le scanner ?", "options": ["Appeler le patient par son prénom dans le couloir sans vérifier le dossier", "Vérifier l'identité sur le bracelet d'identification (Nom, Prénom, Date de naissance) et la faire confirmer par le patient si possible", "Se fier uniquement au numéro de box inscrit sur le tableau"], "rep": "Vérifier l'identité sur le bracelet d'identification (Nom, Prénom, Date de naissance) et la faire confirmer par le patient si possible"},
                {"q": "7. [Module Brancardier] Quelle est la règle de sécurité et de bientraitance lors du transport d'un patient en brancard dans les couloirs ?", "options": ["Transporter le patient sans barrières s'il promet de ne pas bouger", "Mettre systématiquement les ridelles/barrières relevées, recouvrir le corps d'un drap et respecter sa pudeur", "Discuter de l'état de santé du patient avec un collègue dans l'ascenseur public"], "rep": "Mettre systématiquement les ridelles/barrières relevées, recouvrir le corps d'un drap et respecter sa pudeur"},
                {"q": "8. [Module Brancardier] Concernant l'hygiène du matériel de transport entre deux passages de patients, que devez-vous appliquer ?", "options": ["Nettoyer le brancard uniquement à la fin du poste de travail", "Désinfecter les surfaces de contact du brancard/fauteuil avec un produit détergent-désinfectant homologué entre chaque patient", "Passer un coup d'eau tiède sans produit détergent"], "rep": "Désinfecter les surfaces de contact du brancard/fauteuil avec un produit détergent-désinfectant homologué entre chaque patient"},
                {"q": "9. [Module Brancardier] Lors du déplacement d'un patient sous oxygénothérapie, quelle précaution matérielle s'impose ?", "options": ["Poser la bouteille d'oxygène entre les jambes du patient", "Fixer solidement l'obus d'oxygène dans son support dédié et vérifier l'autonomie du manomètre avant le départ", "Laisser la bouteille rouler au pied du brancard"], "rep": "Fixer solidement l'obus d'oxygène dans son support dédié et vérifier l'autonomie du manomètre avant le départ"},
                {"q": "10. [Module Brancardier] Quelle attitude adopter si un patient manifeste une anxiété importante durant le trajet vers un examen ?", "options": ["L'ignorer et accélérer l'allure pour finir le transport au plus vite", "Rassurer le patient, lui expliquer simplement la destination et maintenir une communication bienveillante", "Lui dire de se taire"], "rep": "Rassurer le patient, lui expliquer simplement la destination et maintenir une communication bienveillante"}
            ],
            "ASH": [
                {"q": "6. [Module ASH] Quelle est la règle essentielle de bio-nettoyage d'un box d'urgences après la sortie d'un patient ?", "options": ["Vider uniquement les poubelles et passer un coup de balai sec", "Réaliser un bio-nettoyage complet des surfaces et du mobilier avec un produit détergent-désinfectant selon le protocole du service", "Attendre le lendemain matin pour désinfecter la pièce"], "rep": "Réaliser un bio-nettoyage complet des surfaces et du mobilier avec un produit détergent-désinfectant selon le protocole du service"},
                {"q": "7. [Module ASH] Dans quelle filière d'élimination des déchets devez-vous jeter les gants et compresses usagés non souillés de sang ?", "options": ["Filière DAOM (Déchets Assimilables aux Ordures Ménagères - Sac Noir)", "Filière DASRI (Déchets d'Activités de Soins à Risques Infectieux - Sac Jaune)", "Dans le conteneur pour objets perforants"], "rep": "Filière DAOM (Déchets Assimilables aux Ordures Ménagères - Sac Noir)"},
                {"q": "8. [Module ASH] Lors de votre intervention dans un box occupé par un patient, quelle est la posture de bientraitance attendue ?", "options": ["Entrer sans frapper et faire du bruit avec le matériel sans parler au patient", "Taper à la porte, se présenter, expliquer la présence pour le nettoyage et respecter l'intimité du soin", "Poser des questions médicales personnelles au patient"], "rep": "Taper à la porte, se présenter, expliquer la présence pour le nettoyage et respecter l'intimité du soin"},
                {"q": "9. [Module ASH] Que devez-vous faire si vous constatez la présence d'une aiguille usagée abandonnée sur un adaptable ?", "options": ["La ramasser à la main et la jeter dans la poubelle noire", "Ne pas toucher l'aiguille à main nue et prévenir immédiatement un soignant pour élimination sécurisée dans le collecteur d'OPCT", "La cacher sous le drap"], "rep": "Ne pas toucher l'aiguille à main nue et prévenir immédiatement un soignant pour élimination sécurisée dans le collecteur d'OPCT"},
                {"q": "10. [Module ASH] Quelle est la règle d'hygiène des mains à respecter obligatoirement avant d'entrer et en sortant d'un box ?", "options": ["Réaliser une friction hydro-alcoolique (PHA) des mains", "Se rincer les mains à l'eau claire uniquement", "Mettre une paire de gants sans se laver les mains"], "rep": "Réaliser une friction hydro-alcoolique (PHA) des mains"}
            ],
            "Cadre": [
                {"q": "6. [Module Cadre] Suite à la déclaration d'un Événement Indésirable Grave (EIGS) aux urgences, quelle est la priorité managériale ?", "options": ["Blâmer immédiatement le soignant impliqué dans la fiche d'événement", "Organiser une analyse systémique des causes (REX / CREX) sans recherche de coupable et suivre le plan d'actions correctives", "Classer le dossier sans suite pour ne pas inquiéter la direction"], "rep": "Organiser une analyse systémique des causes (REX / CREX) sans recherche de coupable et suivre le plan d'actions correctives"},
                {"q": "7. [Module Cadre] Quelle traçabilité minimale devez-vous contrôler concernant la sécurité du chariot d'urgence du service ?", "options": ["Une vérification trimestrielle informelle", "Un contrôle quotidien de l'intégrité du scellé et une traçabilité de la vérification des péremptions sur le registre dédié", "Le contrôle par la pharmacie une fois par an uniquement"], "rep": "Un contrôle quotidien de l'intégrité du scellé et une traçabilité de la vérification des péremptions sur le registre dédié"},
                {"q": "8. [Module Cadre] Dans le cadre de l'évaluation HAS sur la bientraitance, quel rôle clé tient le Cadre de Santé au quotidien ?", "options": ["Superviser uniquement les plannings sans aller sur le terrain", "Promouvoir la culture de bientraitance, réaliser des audits flash (douleur, contention) et accompagner les équipes", "Interdire les visites de famille aux urgences"], "rep": "Promouvoir la culture de bientraitance, réaliser des audits flash (douleur, contention) et accompagner les équipes"},
                {"q": "9. [Module Cadre] Comment s'assurer du respect des règles de confidentialité et de secret professionnel au sein de l'équipe ?", "options": ["Rappeler régulièrement les règles de discrétion lors des réunions, veiller à la fermeture des sessions informatiques et auditer la bonne tenue des transmissions", "Attendre qu'un patient porte plainte pour faire une mise au point", "Interdire aux soignants de se parler entre eux"], "rep": "Rappeler régulièrement les règles de discrétion lors des réunions, veiller à la fermeture des sessions informatiques et auditer la bonne tenue des transmissions"},
                {"q": "10. [Module Cadre] Quel indicateur clé permet au Cadre d'évaluer la dynamique collective de préparation à la certification HAS ?", "options": ["Le taux de participation globale des soignants aux quiz de révision et les thématiques à renforcer", "Le nombre de cafés consommés en salle de repos", "L'ancienneté moyenne des agents du service"], "rep": "Le taux de participation globale des soignants aux quiz de révision et les thématiques à renforcer"}
            ]
        },
        "fiches_reflexes": {
            "Tronc Commun": {
                "class": "memo-box-tc",
                "slug": "tronc_commun",
                "points": [
                    "**Information & Refus de Soins** : L'information délivrée au patient doit être claire, loyale et appropriée (Critère HAS). En cas de refus, l'expert recherche la traçabilité de l'information sur les risques encourus.",
                    "**Dossier Médical & Délais** : Communication du dossier sous 8 jours maximum (après un délai de réflexion obligatoire de 48 heures).",
                    "**Personne de Confiance** : Son avis prévaut sur celui de la famille si le patient n'est plus en mesure d'exprimer sa volonté.",
                    "**Protection Juridique (Tutelle)** : Le majeur protégé consent lui-même si son état le permet. L'urgence médicale prime si le tuteur est injoignable."
                ]
            },
            "IDE": {
                "class": "memo-box-ide",
                "slug": "ide",
                "points": [
                    "**Traçabilité Antalgique (Critère Majeur HAS)** : Obligation de tracer l'évaluation initiale de la douleur ET sa réévaluation post-administration.",
                    "**Prise en charge des Mineurs** : Soins d'urgence dispensés sans accord parental si le mineur le demande (avec un majeur protecteur)."
                ]
            },
            "AS": {
                "class": "memo-box-as",
                "slug": "as",
                "points": [
                    "**Bientraitance du Sujet Âgé** : Échelle ALGOPLUS. Recherche de causes réversibles (globe, fécalome) avant toute contention.",
                    "**Brancardage & Intimité** : Respect absolu du pudeur, ridelles levées et secret professionnel."
                ]
            },
            "Médecin": {
                "class": "memo-box-med",
                "slug": "medecin",
                "points": [
                    "**Directives Anticipées & LAT** : Procédure collégiale formalisée et traçabilité obligatoire dans le dossier.",
                    "**Sortie Contre Avis Médical** : Traçabilité des informations sur les risques vitaux encourus et formulaire signé."
                ]
            },
            "ARM": {
                "class": "memo-box-arm",
                "slug": "arm",
                "points": [
                    "**Identitovigilance SAMU / SAS** : Recueil rigoureux du triptyque (Nom de naissance, Prénom, Date de naissance).",
                    "**Secret Professionnel** : Interdiction absolue de confirmer la présence d'un patient par téléphone à un tiers."
                ]
            },
            "Accueil & Admission": {
                "class": "memo-box-acc",
                "slug": "accueil",
                "points": [
                    "**Identitovigilance Admission** : Contrôle sur pièce d'identité officielle avec photo + carte Vitale.",
                    "**Vigilance Salle d'Attente** : Alerte immédiate de l'IAO au moindre signe d'aggravation."
                ]
            },
            "Brancardier": {
                "class": "memo-box-branc",
                "slug": "brancardier",
                "points": [
                    "**Identitovigilance Transport** : Contrôle actif du bracelet d'identification avant tout déplacement.",
                    "**Sécurité des Matériels** : Arrimage obligatoire des obus d'oxygène et vérification de la réserve."
                ]
            },
            "ASH": {
                "class": "memo-box-ash",
                "slug": "ash",
                "points": [
                    "**Bio-nettoyage des Box** : Désinfection rigoureuse avec produit détergent-désinfectant homologué.",
                    "**Filières Déchets** : Séparation stricte DAOM (Sac noir) et DASRI (Sac jaune)."
                ]
            },
            "Cadre de Santé": {
                "class": "memo-box-cadre",
                "slug": "cadre",
                "points": [
                    "**Management de la Qualité & REX** : Analyses systémiques non punitives suite à un EIGS.",
                    "**Sécurité Chariot d'Urgence** : Contrôle quotidien formalisé de l'intégrité du scellé."
                ]
            }
        }
    }
]

def obtenir_statut_session(session):
    today = datetime.date.today()
    if today < session["date_debut"]:
        return "A venir"
    elif session["date_debut"] <= today <= session["date_fin"]:
        return "Actuelle"
    else:
        return "Passee"

# ------------------------------------------------------------------------------
# 6. BANNIÈRE EN-TÊTE AVEC VOTRE LOGO LOCAL (logo.jpg)
# ------------------------------------------------------------------------------
col_logo, col_titre = st.columns([1, 4])

with col_logo:
    try:
        st.markdown("<div class='service-logo'>", unsafe_allow_html=True)
        st.image("logo.jpg")
        st.markdown("</div>", unsafe_allow_html=True)
    except Exception:
        st.warning("⚠️ Fichier 'logo.jpg' introuvable dans le dossier. Veuillez y déposer votre logo.")

with col_titre:
    st.markdown("<h1 class='main-title'>🧠 Pause Révision HAS 2027</h1>", unsafe_allow_html=True)
    st.markdown("<h3 class='subtitle'>Service des Urgences & SAMU — Mulhouse</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color:#64748b; margin-bottom:0;'>Plateforme ludo-pédagogique d'équipe pour la préparation à la certification</p>", unsafe_allow_html=True)

st.divider()

# ------------------------------------------------------------------------------
# 7. ÉCRAN D'AUTHENTIFICATION
# ------------------------------------------------------------------------------
if not st.session_state.user_pseudo:
    tab_login, tab_register = st.tabs(["🔑 Se connecter", "✨ Créer un compte (1ère visite)"])
    comptes_existants = charger_utilisateurs()

    with tab_login:
        st.markdown("<div class='auth-card-header'><h3 style='color:#0f766e; margin:0;'>Connexion rapide à votre espace</h3><p style='color:#64748b; font-size:0.9rem; margin-top:5px;'>Sélectionnez votre animal pour retrouver votre profil</p></div>", unsafe_allow_html=True)
        
        st.markdown("<h4 style='text-align:center; color:#0f766e;'>Étape 1 : Cliquez sur votre Animal</h4>", unsafe_allow_html=True)
        cols_login = st.columns(5)
        for idx, animal in enumerate(ANIMAUX):
            emoji = ANIMAL_TO_EMOJI[animal]
            col = cols_login[idx % 5]
            is_selected = (st.session_state.login_animal_selectionne == animal)
            btn_type = "primary" if is_selected else "secondary"
            
            col.button(
                f"{emoji} {animal}", 
                key=f"btn_login_anim_{animal}", 
                type=btn_type, 
                use_container_width=True,
                on_click=fixer_animal_login,
                args=(animal,)
            )

        if st.session_state.login_animal_selectionne:
            animal_actif = st.session_state.login_animal_selectionne
            emoji_actif = ANIMAL_TO_EMOJI[animal_actif]

            st.markdown("---")
            col_l, col_center, col_r = st.columns([1, 2, 1])
            with col_center:
                st.markdown(
                    f"<div style='text-align:center;'><div class='animal-selected-badge'><span class='animal-selected-emoji'>{emoji_actif}</span><span class='animal-selected-name'>Animal : {animal_actif}</span></div></div>",
                    unsafe_allow_html=True
                )

                pseudos_animal = [p for p in comptes_existants.keys() if p.startswith(animal_actif)]

                if not pseudos_animal:
                    st.warning(f"Aucun compte enregistré pour l'animal {animal_actif}. Créez-en un dans l'onglet à côté !")
                else:
                    pseudo_choisi = st.selectbox("Étape 2 : Choisissez votre Pseudo exact :", options=pseudos_animal)
                    mdp_saisi = st.text_input("Étape 3 : Mot de passe :", type="password", key="login_mdp")

                    if st.button("🚀 Me connecter", type="primary", use_container_width=True):
                        if mdp_saisi:
                            mdp_attendu = comptes_existants.get(pseudo_choisi)
                            if str(mdp_saisi) == str(mdp_attendu):
                                st.session_state.user_pseudo = pseudo_choisi
                                st.rerun()
                            else:
                                st.error("Mot de passe incorrect !")
                        else:
                            st.warning("Veuillez saisir votre mot de passe.")

    with tab_register:
        st.markdown("""
            <div class='auth-card-header'>
                <h3 style='color:#0f766e; margin:0;'>🎭 Créez votre Avatar & Mot de passe</h3>
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
# 8. TABLEAU DE BORD CONNECTÉ
# ------------------------------------------------------------------------------
else:
    col_head1, col_head2 = st.columns([4, 1])
    with col_head1:
        st.markdown(f"<div class='user-header'>🧠 Profil actif : {st.session_state.user_pseudo}</div>", unsafe_allow_html=True)
    with col_head2:
        if st.button("🔒 Déconnexion"):
            st.session_state.user_pseudo = None
            st.session_state.animal_selectionne = None
            st.session_state.login_animal_selectionne = None
            st.session_state.current_q_index = 0
            st.session_state.user_quiz_answers = {}
            st.session_state.quiz_paused = False
            st.rerun()

    st.markdown("<h2 style='color:#0f766e; margin-top:15px;'>🎯 Tableau de bord des Révisions</h2>", unsafe_allow_html=True)

    tab_actuel, tab_progression, tab_historique, tab_avenir = st.tabs([
        "🔥 Semaine Actuelle", 
        "📊 Ma Progression", 
        "📜 Semaines Passées", 
        "📅 Semaines À Venir"
    ])

    # --- TAB 1 : QUIZ INTERACTIF ---
    with tab_actuel:
        session_active = next((s for s in SESSIONS if obtenir_statut_session(s) == "Actuelle"), None)
        
        if not session_active:
            st.info("🔒 Aucune session de quiz n'est ouverte aujourd'hui. Veuillez consulter le calendrier des 'Semaines À Venir' !")
        else:
            st.markdown(
                f"<div class='card-actuelle'><h3 style='color:#0f766e;'>📝 {session_active['titre']}</h3><p style='color:#64748b; font-size:0.9rem;'>⚡ Session de révision interactive</p></div>",
                unsafe_allow_html=True
            )

            if st.session_state.quiz_paused:
                st.warning(f"⏸️ **Quiz en pause détecté !** Vous étiez à la question {st.session_state.current_q_index + 1}.")
                c_rep, c_raz = st.columns([1, 1])
                with c_rep:
                    if st.button("▶️ Reprendre mon quiz", type="primary", use_container_width=True):
                        st.session_state.quiz_paused = False
                        st.rerun()
                with c_raz:
                    if st.button("🔄 Recommencer depuis le début", type="secondary", use_container_width=True):
                        st.session_state.current_q_index = 0
                        st.session_state.user_quiz_answers = {}
                        st.session_state.quiz_paused = False
                        st.rerun()
            else:
                # LISTE DES MÉTIERS TRIÉE STRICTEMENT PAR ORDRE ALPHABÉTIQUE
                metiers_tries_alphabetique = [
                    "-- Choisir ma fonction --",
                    "ARM (Assistant/e de Régulation Médicale)",
                    "AS (Aide-Soignant/e)",
                    "ASH (Agent de Service Hospitalier)",
                    "Brancardier",
                    "Cadre de Santé / Encadrement",
                    "Hôte / Hôtesse d'accueil & Admission",
                    "IDE (Infirmier/ère)",
                    "Médecin"
                ]

                role_soignant = st.selectbox(
                    "Sélectionnez votre fonction pour personnaliser votre parcours :",
                    options=metiers_tries_alphabetique
                )

                if role_soignant != "-- Choisir ma fonction --":
                    questions_quiz = list(session_active.get("tronc_commun", []))
                    
                    if "IDE" in role_soignant:
                        questions_quiz.extend(session_active["metiers"].get("IDE", []))
                    elif "AS (" in role_soignant:
                        questions_quiz.extend(session_active["metiers"].get("AS", []))
                    elif "Médecin" in role_soignant:
                        questions_quiz.extend(session_active["metiers"].get("Médecin", []))
                    elif "ARM" in role_soignant:
                        questions_quiz.extend(session_active["metiers"].get("ARM", []))
                    elif "accueil" in role_soignant:
                        questions_quiz.extend(session_active["metiers"].get("Accueil", []))
                    elif "Brancardier" in role_soignant:
                        questions_quiz.extend(session_active["metiers"].get("Brancardier", []))
                    elif "ASH" in role_soignant:
                        questions_quiz.extend(session_active["metiers"].get("ASH", []))
                    elif "Cadre" in role_soignant:
                        questions_quiz.extend(session_active["metiers"].get("Cadre", []))

                    total_q = len(questions_quiz)
                    current_idx = st.session_state.current_q_index

                    if current_idx < total_q:
                        q_data = questions_quiz[current_idx]
                        
                        col_prog, col_pause = st.columns([4, 1])
                        with col_prog:
                            st.progress((current_idx + 1) / total_q)
                            st.caption(f"Question {current_idx + 1} sur {total_q}")
                        with col_pause:
                            if st.button("⏸️ Pause", help="Mettre le quiz en pause pour revenir plus tard"):
                                st.session_state.quiz_paused = True
                                st.rerun()

                        st.markdown(f"""
                            <div class="question-card">
                                <span class="question-badge">{'Tronc Commun' if current_idx < 5 else 'Spécifique ' + role_soignant.split(' ')[0]}</span>
                                <div class="question-title">{q_data['q']}</div>
                            </div>
                        """, unsafe_allow_html=True)

                        existing_ans = st.session_state.user_quiz_answers.get(current_idx, None)
                        choix = st.radio(
                            "Sélectionnez votre réponse :", 
                            q_data["options"], 
                            index=q_data["options"].index(existing_ans) if existing_ans in q_data["options"] else None,
                            key=f"q_dyn_{current_idx}"
                        )

                        st.markdown("<br>", unsafe_allow_html=True)
                        col_prev, col_next = st.columns([1, 1])

                        with col_prev:
                            if current_idx > 0:
                                if st.button("⬅️ Question précédente", use_container_width=True):
                                    if choix:
                                        st.session_state.user_quiz_answers[current_idx] = choix
                                    st.session_state.current_q_index -= 1
                                    st.rerun()

                        with col_next:
                            btn_label = "Suivant ➡️" if current_idx < total_q - 1 else "🏁 Terminer & Valider"
                            if st.button(btn_label, type="primary", use_container_width=True):
                                if not choix:
                                    st.warning("Veuillez sélectionner une réponse avant de continuer !")
                                else:
                                    st.session_state.user_quiz_answers[current_idx] = choix
                                    st.session_state.current_q_index += 1
                                    st.rerun()

                    else:
                        st.balloons()
                        st.markdown("### 🎉 Quiz Terminé avec succès !")
                        
                        score_obtenu = sum(
                            1 for idx, q in enumerate(questions_quiz) 
                            if st.session_state.user_quiz_answers.get(idx) == q["rep"]
                        )

                        st.metric("Votre score final", f"{score_obtenu} / {total_q}")

                        if enregistrer_reponse(st.session_state.user_pseudo, session_active["id"], score_obtenu, total_q):
                            st.success(f"Félicitations **{st.session_state.user_pseudo}** ! Vos résultats ont été enregistrés sur Google Sheets.")

                        st.divider()
                        st.markdown("### 📖 Bilan des Réponses")
                        
                        for idx, q in enumerate(questions_quiz):
                            rep_soignant = st.session_state.user_quiz_answers.get(idx, "Non répondu")
                            est_correct = (rep_soignant == q["rep"])
                            
                            card_class = "result-card-ok" if est_correct else "result-card-err"
                            icon_status = "✅ Correct" if est_correct else "❌ Erreur"
                            
                            st.markdown(f"""
                                <div class="{card_class}">
                                    <div style="font-weight:700; color:#1e293b; margin-bottom:6px;">
                                        Question {idx+1} : {q['q']}
                                    </div>
                                    <div style="font-size:0.95rem; margin-bottom:4px;">
                                        <strong>Votre réponse :</strong> {rep_soignant} <span style="font-weight:700;">({icon_status})</span>
                                    </div>
                                    {f'<div style="font-size:0.95rem; color:#15803d; font-weight:700;"><strong>Bonne réponse HAS :</strong> {q["rep"]}</div>' if not est_correct else ''}
                                </div>
                            """, unsafe_allow_html=True)

                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("🔄 Recommencer le quiz", type="secondary"):
                            st.session_state.current_q_index = 0
                            st.session_state.user_quiz_answers = {}
                            st.session_state.quiz_paused = False
                            st.rerun()

    # --- TAB 2 : MA PROGRESSION ---
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

    # --- TAB 3 : SEMAINES PASSÉES & SEMAINE 0 ---
    with tab_historique:
        # On affiche la Semaine 0 (toujours accessible) + toutes les semaines passées
        sessions_passees = [s for s in SESSIONS if obtenir_statut_session(s) == "Passee" or s["id"] == 0]
        if not sessions_passees:
            st.info("Aucune semaine archivée pour le moment.")
        else:
            for s in sessions_passees:
                str_debut = s['date_debut'].strftime('%d/%m/%Y')
                str_fin = s['date_fin'].strftime('%d/%m/%Y')
                
                st.markdown(f"""
                    <div class="vignette-semaine">
                        <div class="vignette-header">
                            📜 {s['titre']}
                        </div>
                        <p style="color:#64748b; font-size:0.9rem; margin-bottom:15px;">
                            Session archivée du <strong>{str_debut}</strong> au <strong>{str_fin}</strong>
                        </p>
                """, unsafe_allow_html=True)

                if "fiches_reflexes" in s:
                    fiches = s["fiches_reflexes"]
                    st.markdown("<h5 style='color:#0f766e;'>📌 Fiches Mémos & Synthèses HAS 2027 :</h5>", unsafe_allow_html=True)
                    
                    onglets_metiers = list(fiches.keys())
                    tabs_m = st.tabs(onglets_metiers)
                    
                    for idx_m, nom_m in enumerate(onglets_metiers):
                        fiche_info = fiches[nom_m]
                        css_class = fiche_info.get("class", "memo-box-tc")
                        slug_metier = fiche_info.get("slug", "tronc_commun")
                        points_list = fiche_info.get("points", [])
                        
                        with tabs_m[idx_m]:
                            st.markdown(f"<div class='{css_class}'><div class='memo-title-text'>Synthèse HAS — {nom_m}</div>", unsafe_allow_html=True)
                            for pt in points_list:
                                st.markdown(f"• {pt}")
                            st.markdown("</div>", unsafe_allow_html=True)
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            # Appel de la fonction PDF (Visualisation directe + Bouton de téléchargement)
                            afficher_et_telecharger_pdf(s["id"], slug_metier, nom_m)

                st.markdown("</div>", unsafe_allow_html=True)

    # --- TAB 4 : SEMAINES À VENIR ---
    with tab_avenir:
        sessions_futures = [s for s in SESSIONS if obtenir_statut_session(s) == "A venir"]
        if not sessions_futures:
            st.info("Aucune session future n'est programmée pour l'instant.")
        else:
            for s in sessions_futures:
                str_debut = s['date_debut'].strftime('%d/%m/%Y')
                str_fin = s['date_fin'].strftime('%d/%m/%Y')
                
                st.markdown(
                    f"<div class='card-avenir'><h4 style='color:#b45309;'>🔒 {s['titre']}</h4><p style='margin:0;'>📅 Ouverture prévue du <strong>{str_debut} au {str_fin}</strong></p></div>",
                    unsafe_allow_html=True
                )
