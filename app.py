import datetime
import os
import base64
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from streamlit_pdf_viewer import pdf_viewer

@st.cache_data(ttl=300)
def charger_donnees_scores():
    return sheet.get_all_records()

# ------------------------------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Révisions Équipe HAS 2027 - Urgences Mulhouse",
    page_icon="🧠",
    layout="wide"
)

# ------------------------------------------------------------------------------
# 2. CONNEXION GOOGLE SHEETS VIA GSPREAD & CACHING
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

# Instance globale de la feuille
try:
    sheet = get_sheet()
except Exception:
    sheet = None

@st.cache_data(ttl=60)
def charger_utilisateurs_cached():
    try:
        ws = sheet.worksheet("Utilisateurs")
        records = ws.get_all_records()
        return {str(r["Pseudo"]): str(r.get("Mot_De_Passe", "")) for r in records if "Pseudo" in r and r["Pseudo"]}
    except Exception:
        return {}

def charger_utilisateurs():
    return charger_utilisateurs_cached()

def ajouter_utilisateur(pseudo, mdp, animal=""):
    try:
        ws = sheet.worksheet("Utilisateurs")
        date_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        ws.append_row([date_str, str(pseudo), str(mdp), str(animal)])
        charger_utilisateurs_cached.clear()
        return True
    except Exception as e:
        st.error(f"Erreur d'enregistrement Google Sheets : {e}")
        return False

@st.cache_data(ttl=300)
def charger_reponses_globales():
    try:
        ws = sheet.worksheet("Reponses")
        return ws.get_all_records()
    except Exception:
        return []

@st.cache_data(ttl=60)
def charger_notes_utilisateur_cached(pseudo):
    try:
        records = charger_reponses_globales()
        return [r for r in records if str(r.get("Pseudo")) == str(pseudo)]
    except Exception:
        return []

def charger_notes_utilisateur(pseudo):
    return charger_notes_utilisateur_cached(pseudo)

def enregistrer_reponse(pseudo, semaine_id, score, total, role=""):
    try:
        ws = sheet.worksheet("Reponses")
        date_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        ws.append_row([date_str, str(pseudo), int(semaine_id), int(score), int(total), str(role)])
        charger_reponses_globales.clear()
        return True
    except Exception as e:
        st.error(f"Erreur de sauvegarde : {e}")
        return False

def charger_top10_semaine(semaine_id):
    try:
        records = charger_reponses_globales()
        reponses_semaine = [r for r in records if str(r.get("Semaine_ID")) == str(semaine_id)]
        
        meilleurs_scores = {}
        for r in reponses_semaine:
            pseudo = str(r.get("Pseudo"))
            score = int(r.get("Score", 0))
            total = int(r.get("Total_Questions", 10))
            
            if pseudo not in meilleurs_scores or score > meilleurs_scores[pseudo]["score"]:
                meilleurs_scores[pseudo] = {"score": score, "total": total}
        
        classement = sorted(meilleurs_scores.items(), key=lambda x: x[1]["score"], reverse=True)
        top10 = []
        medailles = ["🥇 1er", "🥈 2ème", "🥉 3ème"]
        for idx, (pseudo, stats) in enumerate(classement[:10]):
            rang = medailles[idx] if idx < 3 else f"{idx+1}ème"
            top10.append({
                "rang": rang,
                "pseudo": pseudo,
                "score": f"{stats['score']}/{stats['total']}"
            })
        return top10
    except Exception:
        return []

def calculer_scores_podium():
    try:
        records = charger_reponses_globales()
        tentatives_uniques = {}
        
        for r in records:
            pseudo = str(r.get("Pseudo"))
            semaine_id = str(r.get("Semaine_ID"))
            try:
                score = int(r.get("Score", 0))
            except ValueError:
                score = 0
                
            if pseudo and semaine_id:
                if pseudo not in tentatives_uniques:
                    tentatives_uniques[pseudo] = {}
                if semaine_id not in tentatives_uniques[pseudo]:
                    tentatives_uniques[pseudo][semaine_id] = score
                    
        classement = []
        for pseudo, semaines_dict in tentatives_uniques.items():
            total_points = sum(semaines_dict.values())
            nb_quiz = len(semaines_dict)
            classement.append({
                "Pseudo": pseudo,
                "Total_Points": total_points,
                "Quiz_Completes": nb_quiz
            })
            
        return sorted(classement, key=lambda x: x["Total_Points"], reverse=True)
    except Exception:
        return []

def calculer_scores_podium_par_metier():
    try:
        records = charger_reponses_globales()
        scores_par_metier = {}
        
        mapping_metiers = {
            "ARM": "ARM (Assistant/e de Régulation Médicale)",
            "médecin": "Medecin",
        }
        
        for r in records:
            pseudo = str(r.get("Pseudo"))
            semaine_id = str(r.get("Semaine_ID"))
            metier = str(r.get("Role", r.get("Metier", "Autre"))).strip()
            if not metier or metier == "":
                metier = "Général / Non renseigné"
            else:
                metier = mapping_metiers.get(metier, metier)
                
            try:
                score = int(r.get("Score", 0))
            except ValueError:
                score = 0

            if pseudo and semaine_id:
                if metier not in scores_par_metier:
                    scores_par_metier[metier] = {}
                if pseudo not in scores_par_metier[metier]:
                    scores_par_metier[metier][pseudo] = {}
                if semaine_id not in scores_par_metier[metier][pseudo]:
                    scores_par_metier[metier][pseudo][semaine_id] = score

        podiums_metiers = {}
        for metier, users_dict in scores_par_metier.items():
            classement = []
            for pseudo, semaines_dict in users_dict.items():
                classement.append({
                    "Pseudo": pseudo,
                    "Total_Points": sum(semaines_dict.values()),
                    "Quiz_Completes": len(semaines_dict)
                })
            podiums_metiers[metier] = sorted(classement, key=lambda x: x["Total_Points"], reverse=True)
            
        return podiums_metiers
    except Exception:
        return {}


def afficher_et_telecharger_pdf(semaine_id, metier_slug, nom_affichage):
    chemin_pdf = f"fiches_pdf/semaine{semaine_id}_{metier_slug}.pdf"
    if os.path.exists(chemin_pdf):
        with open(chemin_pdf, "rb") as f:
            pdf_bytes = f.read()
            
        st.download_button(
            label=f"📥 Télécharger la Fiche Mémo ({nom_affichage}) - PDF",
            data=pdf_bytes,
            file_name=f"HAS_2027_Semaine_{semaine_id}_{metier_slug}.pdf",
            mime="application/pdf",
            key=f"dl_pdf_{semaine_id}_{metier_slug}"
        )
        st.markdown("<br>", unsafe_allow_html=True)
        pdf_viewer(input=pdf_bytes, width=500)
    else:
        st.info(f"💡 Le fichier PDF officiel pour **{nom_affichage}** sera bientôt disponible (chemin cherché : `{chemin_pdf}`).")

# ------------------------------------------------------------------------------
# 3. STYLE CSS (PASTEL HOSPITALIER & DESIGN UNIVERSEL MAC/MOBILE)
# ------------------------------------------------------------------------------
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #e6fffa 0%, #f0f9ff 50%, #f5f3ff 100%);
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .main-title { color: #0f766e; font-weight: 800; margin-bottom: 0rem; }
    .subtitle { color: #0369a1; font-weight: 600; margin-top: 0.2rem; }
    
    .service-logo img {
        border-radius: 20px;
        border: 3px solid #99f6e4;
        box-shadow: 0 6px 20px rgba(15, 118, 110, 0.12);
        max-width: 110px;
    }

    @media screen and (max-width: 768px) {
        .main-title { font-size: 1.1rem !important; }
        .subtitle { font-size: 0.85rem !important; }
        .service-logo img { max-width: 60px !important; }
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
    .card-passee { background-color: #f8fafc; border-radius: 20px; padding: 20px; border-left: 8px solid #6366f1; margin-bottom: 15px; }
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

    .result-card-ok { background: #f0fdf4; border-radius: 16px; padding: 18px; border: 2px solid #86efac; margin-bottom: 15px; }
    .result-card-err { background: #fef2f2; border-radius: 16px; padding: 18px; border: 2px solid #fca5a5; margin-bottom: 15px; }

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

    .stTabs [data-baseweb="tab-list"] { gap: 12px; justify-content: center; }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff; border-radius: 30px; padding: 10px 24px; font-weight: 700; color: #0f766e; border: 1px solid #ccfbf1;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #0d9488 0%, #0284c7 100%) !important; color: white !important; border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 4. DONNÉES ET ÉTATS DE SESSION (AVEC SEMAINES 0, 1 ET 2 INTÉGRALES)
# ------------------------------------------------------------------------------
ANIMAL_TO_EMOJI = {
    "Lapin": "🐇", "Ours": "🐻", "Cochon": "🐷", "Elephant": "🐘", "Hamster": "🐹",
    "Panda": "🐼", "Kangourou": "🦘", "Dauphin": "🐬", "Faucon": "🦅", "Ecureuil": "🐿️",
    "Lynx": "🐆", "Lémurien": "🐒", "Canard": "🦆", "Loup": "🐺", "Hérisson": "🦔",
    "Koala": "🐨", "Licorne": "🦄"
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

# --- SESSIONS DE QUIZ INTÉGRALES ---
SESSIONS = [
    {
        "id": 0,
        "titre": "Semaine 0 - Session de Démonstration & Test",
        "date_debut": datetime.date(2026, 1, 1),
        "date_fin": datetime.date(2026, 10, 25),
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
            "Medecin": [{"q": "[Démo Medecin] Quelle procédure doit être tracée lors d'une décision de Limitation ou Arrêt de Traitement (LAT) ?", "options": ["La décision collégiale, la consultation de la personne de confiance/directives anticipées", "Un simple mot dans le dossier sans avis collégial", "L'accord verbal du chef de service uniquement"], "rep": "La décision collégiale, la consultation de la personne de confiance/directives anticipées"}],
            "ARM (Assistant/e de Régulation Médicale)": [{"q": "[Démo ARM] Quel élément d'identitovigilance est indispensable lors de la création d'un dossier de régulation ?", "options": ["Nom de naissance, prénom, date de naissance et vérification de l'absence de doublon", "Surnom habituel du patient", "Uniquement l'adresse de l'intervention"], "rep": "Nom de naissance, prénom, date de naissance et vérification de l'absence de doublon"}],
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
                    "**Identitovigilance** : Contrôle obligatoire des 3 items sur le bracelet d'identification.",
                    "**Bientraitance** : Respect, intimité (box fermés) et évaluation prioritaire de la douleur.",
                    "**Culture de Sécurité** : Déclaration systématique et non punitive des EI."
                ]
            }
        }
    },
    {
        "id": 1,
        "titre": "Semaine 1 - Droits du patient & Bientraitance",
        "date_debut": datetime.date(2026, 10, 26),
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
                {"q": "6. [Module IDE] Lors de l'administration d'un traitement antalgique réévalué aux urgences, quelle traçabilité minimale exige la HAS ?", "options": ["Horaire, molécule et nom du prescripteur uniquement sur le logiciel", "Score de douleur avant administration, re-évaluation post-injection et traçabilité de l'efficacité", "Transmission orale au Medecin au changement d'équipe"], "rep": "Score de douleur avant administration, re-évaluation post-injection et traçabilité de l'efficacité"},
                {"q": "7. [Module IDE] En cas d'accueil aux urgences d'un mineur non accompagné refusant l'avertissement de ses parents, que devez-vous appliquer ?", "options": ["Refuser la prise en charge sans l'accord écrit parental", "Dispenser les soins d'urgence si le mineur le demande expressément et se faire accompagner par un majeur protecteur", "Appeler immédiatement la gendarmerie"], "rep": "Dispenser les soins d'urgence si le mineur le demande expressément et se faire accompagner par un majeur protecteur"},
                {"q": "8. [Module IDE] Dans la prise en charge des personnes victimes de violences aux urgences, quelle est la priorité de soins IDE ?", "options": ["Exiger un dépôt de plainte immédiat avant d'installer le patient", "Garantir un espace sécurisé, assurer la traçabilité des lésions sur certificat médical et orienter vers la prise en charge médico-psychologique", "Contacter directement le procureur sans l'accord du patient"], "rep": "Garantir un espace sécurisé, assurer la traçabilité des lésions sur certificat médical et orienter vers la prise en charge médico-psychologique"},
                {"q": "9. [Module IDE] Quelle règle d'identitovigilance s'impose avant toute pose de voie veineuse ou injection aux urgences ?", "options": ["Interroger le patient sur son nom/prénom/date de naissance et vérifier la concordance avec son bracelet", "Faire confiance au numéro de box indiqué sur le tableau d'affichage", "Regarder le nom écrit au crayon sur la perfusion"], "rep": "Interroger le patient sur son nom/prénom/date de naissance et vérifier la concordance avec son bracelet"},
                {"q": "10. [Module IDE] Quelle est la conduite à tenir face à la suspicion d'une erreur d'administration de traitement sans conséquence grave immédiate ?", "options": ["Ne rien dire pour éviter de perturber le patient", "Prévenir le Medecin, surveiller le patient et déclarer l'Événement Indésirable (EI) sur le logiciel institutionnel", "Modifier discrètement la prescription a posteriori"], "rep": "Prévenir le Medecin, surveiller le patient et déclarer l'Événement Indésirable (EI) sur le logiciel institutionnel"}
            ],
            "AS": [
                {"q": "6. [Module AS] Quelle mesure de bientraitance est prioritaire lors de la prise en charge d'une personne âgée confuse aux urgences ?", "options": ["Appliquer immédiatement des ridelles et une contention pelvienne pour éviter les chutes", "Évaluer la douleur, chercher des causes réversibles (globe, fécalome) et rassurer avec la présence d'un proche", "L'isoler dans une chambre fermée pour limiter les stimulations"], "rep": "Évaluer la douleur, chercher des causes réversibles (globe, fécalome) et rassurer avec la présence d'un proche"},
                {"q": "7. [Module AS] Un brancardage entre les urgences et la radiologie nécessite le respect de l'intimité. Quelle est la bonne pratique ?", "options": ["Déplacer le patient en blouse d'examen sans couverture s'il fait chaud", "Veiller au recouvrement du corps avec un drap/couverture et préserver le secret professionnel pendant le trajet", "Discuter du motif d'admission du patient avec le brancardier dans le couloir"], "rep": "Veiller au recouvrement du corps avec un drap/couverture et préserver le secret professionnel pendant le trajet"},
                {"q": "8. [Module AS] Un patient dépendant réclame de l'eau aux urgences alors qu'il est en attente d'avis médical. Que devez-vous faire ?", "options": ["Lui donner un grand verre d'eau immédiatement pour son confort", "Vérifier auprès de l'IDE si le patient est à jeun strict avant toute administration de boisson", "Lui dire d'attendre sa sortie des urgences"], "rep": "Vérifier auprès de l'IDE si le patient est à jeun strict avant toute administration de boisson"},
                {"q": "9. [Module AS] Lors de l'installation d'un patient fragile sur un brancard d'urgence, quel est le moyen prioritaire de prévention des escarres ?", "options": ["Laisser le patient sur le même drap pendant 12 heures", "Changer régulièrement les points d'appui, utiliser un matelas réducteur de pression et signaler tout érythème", "Mettre du talc sous les talons"], "rep": "Changer régulièrement les points d'appui, utiliser un matelas réducteur de pression et signaler tout érythème"},
                {"q": "10. [Module AS] Quelle est la bonne réaction si un proche agressif exige d'entrer dans la zone de soins ?", "options": ["L'insulter en retour pour imposer son autorité", "Garder son calme, utiliser une communication apaisante (Méthode DESC) et faire appel à l'équipe ou à la sécurité si nécessaire", "Fermer à clé la porte du box et laisser le proche seul"], "rep": "Garder son calme, utiliser une communication apaisante (Méthode DESC) et faire appel à l'équipe ou à la sécurité si nécessaire"}
            ],
            "Medecin": [
                {"q": "6. [Module Medecin] Concernant les directives anticipées aux urgences, quelle est la règle applicable pour le Medecin ?", "options": ["Elles ont une durée de validité limitée à 3 ans", "Elles s'imposent pour toute décision de limitation/arrêt de traitement (sauf urgence vitale le temps de l'évaluation)", "Elles ne sont qu'un simple avis consultatif que le Medecin peut ignorer librement"], "rep": "Elles s'imposent pour toute décision de limitation/arrêt de traitement (sauf urgence vitale le temps de l'évaluation)"},
                {"q": "7. [Module Medecin] Lors d'une décision de Limitation ou Arrêt de Traitement (LAT) aux urgences, quelle est l'obligation réglementaire ?", "options": ["Décider seul pour ne pas perdre de temps", "Organiser une procédure collégiale, consulter la personne de confiance/directives anticipées et tracer la décision dans le dossier", "Demander l'autorisation préalable au directeur de l'hôpital"], "rep": "Organiser une procédure collégiale, consulter la personne de confiance/directives anticipées et tracer la décision dans le dossier"},
                {"q": "8. [Module Medecin] Un proche réclame des informations médicales sur un patient majeur hospitalisé aux urgences. Le Medecin peut lui répondre si :", "options": ["Le proche prouve son lien de parenté direct (livret de famille)", "Le patient ne s'y est pas opposé et a autorisé la transmission d'informations à ce proche", "Le proche habite sous le même toit que le patient"], "rep": "Le patient ne s'y est pas opposé et a autorisé la transmission d'informations à ce proche"},
                {"q": "9. [Module Medecin] Quelle information minimale doit obligatoirement être tracée dans le Dossier Patient Informatisé lors d'une sortie contre avis médical ?", "options": ["L'information claire délivrée sur les risques vitaux encourus, la proposition d'alternatives et la signature du formulaire dédié", "La mention 'Patient parti' sans autre précision", "Le règlement des frais de séjour"], "rep": "L me l'information claire délivrée sur les risques vitaux encourus, la proposition d'alternatives et la signature du formulaire dédié"},
                {"q": "10. [Module Medecin] Dans le cadre de la certification HAS, quel est le délai recommandé pour la rédaction et la transmission du compte-rendu de passage aux urgences ?", "options": ["Dans les 8 jours suivant la sortie", "Remis au patient à sa sortie ou transmis au Medecin traitant dans les 24 heures maximum", "Dans le mois qui suit"], "rep": "Remis au patient à sa sortie ou transmis au Medecin traitant dans les 24 heures maximum"}
            ],
            "ARM (Assistant/e de Régulation Médicale)": [
                {"q": "6. [Module ARM] Lors de la création d'un dossier au SAMU/SAS, quelle est la priorité d'identitovigilance pour éviter les doublons ?", "options": ["Saisir uniquement le prénom et le numéro de téléphone portable", "Saisir le nom de naissance, le prénom, la date de naissance et vérifier l'existence d'un dossier antérieur", "Utiliser le pseudonyme donné par le patient à l'oral"], "rep": "Saisir le nom de naissance, le prénom, la date de naissance et vérifier l'existence d'un dossier antérieur"},
                {"q": "7. [Module ARM] Un appelant demande confirmation de l'admission aux urgences de son voisin par téléphone. Quelle est votre obligation ?", "options": ["Lui donner la réponse s'il connaît le nom et le prénom du patient", "Refuser poliment de répondre pour respecter le secret professionnel et la confidentialité", "Lui transférer immédiatement la ligne du Medecin régulateur"], "rep": "Refuser poliment de répondre pour respecter le secret professionnel et la confidentialité"},
                {"q": "8. [Module ARM] Lors de la régulation d'un appel urgent pour détresse vitale, quelle traçabilité est exigée dans le logiciel d'appel ?", "options": ["Rédiger un compte-rendu uniquement si le patient est transporté par le SMUR", "Enregistrer l'horodatage des décisions, le motif de régulation et les moyens envoyés", "Ne rien saisir et faire confiance à la bande d'enregistrement audio"], "rep": "Enregistrer l'horodatage des décisions, le motif de régulation et les moyens envoyés"},
                {"q": "9. [Module ARM] Que faire en cas de réception d'un appel concernant une suspicion de violence intrafamiliale aiguë ?", "options": ["Passer l'appel en attente indéfinie", "Recueillir la localisation exacte, transmettre immédiatement au Medecin régulateur et appliquer la procédure d'alerte dédiée", "Conseiller à la personne de rappeler le lendemain"], "rep": "Recueillir la localisation exacte, transmettre immédiatement au Medecin régulateur et appliquer la procédure d'alerte dédiée"},
                {"q": "10. [Module ARM] Quelle est la règle concernant le partage d'informations médicales entre l'ARM et les équipes de secours sur le terrain ?", "options": ["Interdiction totale de donner la moindre information", "Transmettre uniquement les éléments strictly nécessaires à la sécurité de l'intervention et à la prise en charge du patient", "Lire l'intégralité de l'historique médical du patient sur la fréquence radio publique"], "rep": "Transmettre uniquement les éléments strictly nécessaires à la sécurité de l'intervention et à la prise en charge du patient"}
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
                {"q": "9. [Module ASH] Que devez-vous faire si vous constatez la présence d'une aiguille usagée abandonnée sur un adaptable ?", "options": ["La ramasser à la hand et la jeter dans la poubelle noire", "Ne pas toucher l'aiguille à main nue et prévenir immédiatement un soignant pour élimination sécurisée dans le collecteur d'OPCT", "La cacher sous le drap"], "rep": "Ne pas toucher l'aiguille à main nue et prévenir immédiatement un soignant pour élimination sécurisée dans le collecteur d'OPCT"},
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
            "Medecin": {
                "class": "memo-box-med",
                "slug": "medecin",
                "points": [
                    "**Directives Anticipées & LAT** : Procédure collégiale formalisée et traçabilité obligatoire dans le dossier.",
                    "**Sortie Contre Avis Médical** : Traçabilité des informations sur les risques vitaux encourus et formulaire signé."
                ]
            },
            "ARM (Assistant/e de Régulation Médicale)": {
                "class": "memo-box-arm",
                "slug": "ARM (Assistant/e de Régulation Médicale)",
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
    },
     {
        "id": 2,
        "titre": "Semaine 2 - Situations Sanitaires Exceptionnelles (SSE) & Mode Dégradé",
        "date_debut": datetime.date(2026, 11, 2),
        "date_fin": datetime.date(2026, 11, 8),
        "tronc_commun": [
            {
                "q": "1. [Tronc Commun] Lors du déclenchement d'un Plan Blanc aux urgences, quel est le critère organisationnel déterminant validé par la HAS concernant la libération des lits d'aval ?",
                "options": [
                    "L'annulation systématique et immédiate de l'ensemble des interventions chirurgicales programmées non urgentes de tout l'établissement",
                    "L'identification anticipée des patients extractibles (sorties anticipées, transferts inter-services) selon un protocole médico-administratif prédéfini",
                    "La fermeture unilatérale de la zone d'accueil et d'orientation (IAO) aux nouveaux arrivants"
                ],
                "rep": "L'identification anticipée des patients extractibles (sorties anticipées, transferts inter-services) selon un protocole médico-administratif prédéfini"
            },
            {
                "q": "2. [Tronc Commun] En cas de panne informatique totale du dossier patient informatisé, la bascule sur le mode dégradé papier impose :",
                "options": [
                    "La duplication immédiate de l'ensemble des dossiers des patients présents par photocopie des archives papier de la veille",
                    "L'utilisation des dossiers papiers pré-imprimés standardisés de crise, comportant obligatoirement l'horodatage et la double signature pour chaque prescription",
                    "Le report de l'ensemble des transmissions écrites à la fin de la panne informatique sans traçabilité intermédiaire"
                ],
                "rep": "L'utilisation des dossiers papiers pré-imprimés standardisés de crise, comportant obligatoirement l'horodatage et la double signature pour chaque prescription"
            },
            {
                "q": "3. [Tronc Commun] Quelle est la règle réglementaire absolue régissant la chaîne hiérarchique au sein de la Cellule de Crise Hospitalière (CCH) ?",
                "options": [
                    "Le directeur de l'établissement prend toutes les décisions médicales d'urgence",
                    "Le Directeur des Soins Infirmiers gère l'ensemble de la stratégie tactique du terrain",
                    "Le Directeur d'établissement (ou son représentant) assure le commandement général, tandis que le Directeur Médical de Crise (DMC) pilote la stratégie médicale"
                ],
                "rep": "Le Directeur d'établissement (ou son représentant) assure le commandement général, tandis que le Directeur Médical de Crise (DMC) pilote la stratégie médicale"
            },
            {
                "q": "4. [Tronc Commun] Face à une intrusion armée dans l'établissement (alerte attentat), quelle est la chronologie des consignes de sécurité édictées par le secrétariat général de la défense (SGDSN) ?",
                "options": [
                    "Se barricader immédiatement dans le bureau le plus proche sans chercher à fuir",
                    "Fuir en zone ouverte en emportant impératif le matériel informatique et les dossiers",
                    "Fuir, à défaut se cacher et se confiner en silence, puis alerter les forces de l'ordre dès que l'accès est possible."
                ],
                "rep": "Fuir, à défaut se cacher et se confiner en silence, puis alerter les forces de l'ordre dès que l'accès est possible."
            },
            {
                "q": "5. [Tronc Commun] En situation d'afflux massif de victimes (plan AMAVI) avec saturation de la capacité d'identification administrative, quel système d'identitovigilance de crise est activé ?",
                "options": [
                    "L'attribution immédiate d'un avatar (Animal + couleur) pré-imprimés",
                    "L'utilisation du numéro de sécurité sociale provisoire à 9 chiffres",
                    "L'inscription au feutre indélébile du prénom d'usage sur l'avant-bras du patient"
                ],
                "rep": "L'attribution immédiate d'un avatar (Animal + couleur) pré-imprimés"
            }
        ],
    "metiers": {
            "IDE": [
                {
                    "q": "6. [Module IDE] Lors d'un tri IAO en situation d'afflux massif de victimes (Plan Blanc), quelle modalité de réévaluation des patients en attente est exigée par la HAS ?",
                    "options": [
                        "Une réévaluation clinique selon une périodicité stricte adaptée au niveau de criticité initial.",
                        "Une réévaluation déclenchée par l'appel spontané du patient ou de son accompagnant en cas de besoin.",
                        "Un contrôle visuel global de la salle d'attente réalisé par l'IDE toutes les heures."
                    ],
                    "rep": "Une réévaluation clinique selon une périodicité stricte adaptée au niveau de criticité initial."
                },
                {
                    "q": "7. [Module IDE] En mode dégradé informatique (panne totale de l'EPR), quelle règle de double contrôle s'applique pour l'administration des médicaments à haut risque (MHR) ?",
                    "options": [
                        "La préparation et l'administration par un seul soignant de garde pour aller plus vite, sous réserve de validation informatique le lendemain.",
                        "Le double contrôle nominatif (préparateur et administrant) croisé avec la prescription écrite et signée sur le support papier de crise.",
                        "La suspension immédiate de l'administration de tout médicament à haut risque jusqu'au rétablissement complet du réseau."
                    ],
                    "rep": "Le double contrôle nominatif (préparateur et administrant) croisé avec la prescription écrite et signée sur le support papier de crise."
                },
                {
                    "q": "8. [Module IDE] Face à la gestion des déchets d'activités de soins (DASRI) dans un secteur confiné d'urgence, quel critère réglementaire de conditionnement est audité ?",
                    "options": [
                        "L'utilisation exclusive de sacs poubelles noirs renforcés pour tous les types de déchets afin de faciliter l'évacuation rapide.",
                        "Le respect impératif des limites de remplissage des fûts et conteneurs d'OPCT avec fermeture hermétique provisoire dès que les trois quarts sont atteints.",
                        "Le stockage temporaire des déchets souillés sur les plans de travail des box en attendant la fin de la vacation."
                    ],
                    "rep": "Le respect impératif des limites de remplissage des fûts et conteneurs d'OPCT avec fermeture hermétique provisoire dès que les trois quarts sont atteints."
                },
                {
                    "q": "9. [Module IDE] En situation de tension extrême avec des patients agités, à quel moment la pose d'une contention physique peut-elle être initiée par l'IDE ?",
                    "options": [
                        "Dès l'apparition de cris/coups, de manière préventive pour protéger le matériel de soins et les autres patients.",
                        "Sur prescription médicale écrite après échec des alternatives.",
                        "Sur décision de l'IDE en accord avec les agents de sécurité de l'hôpital et du Medecin."
                    ],
                    "rep": "Sur prescription médicale écrite après échec des alternatives."
                },
                {
                    "q": "10. [Module IDE] Quelle est l'exigence de la HAS concernant les transmissions écrites inter-équipes en période de crise sanitaire (Plan Blanc) ?",
                    "options": [
                        "Le remplacement de tout support écrit par des transmissions orales pour s'adapter à la vitesse de l'événement.",
                        "L'utilisation des supports de traçabilité de crise formalisés consignant l'état des patients, les examens en attente et les alertes.",
                        "Le report global de la rédaction des dossiers de soins."
                    ],
                    "rep": "L'utilisation des supports de traçabilité de crise formalisés consignant l'état des patients, les examens en attente et les alertes."
                }
            ],
            "AS": [
                {
                    "q": "6. [Module AS] Lors de l'activation et de l'aménagement de la Zone de Regroupement des Victimes (ZRV) aux urgences, quel contrôle logistique relève de la responsabilité de l'AS ?",
                    "options": [
                        "L'inventaire des dossiers administratifs et des cartes Vitale des patients.",
                        "La vérification de la disponibilité et de l'intégrité opérationnelle des kits d'oxygénothérapie de secours et des dispositifs d'évacuation rapide.",
                        "Le paramétrage des écrans d'affichage dynamique de la salle d'attente."
                    ],
                    "rep": "La vérification de la disponibilité et de l'intégrité opérationnelle des kits d'oxygénothérapie de secours et des dispositifs d'évacuation rapide."
                },
                {
                    "q": "7. [Module AS] En mode dégradé logistique (rupture des flux informatisés de réapprovisionnement), comment l'AS trace-t-elle les consommables utilisés ?",
                    "options": [
                        "En ne notant rien, les stocks étant régulés automatiquement par l'établissement en fin de mois.",
                        "En reportant les consommations sur les bons de sortie de stock papier de crise spécifiques pour permettre au cadre de réajuster les commandes.",
                        "En stockant de manière individuelle le matériel excédentaire dans le casier de l'équipe."
                    ],
                    "rep": "En reportant les consommations sur les bons de sortie de stock papier de crise spécifiques pour permettre au cadre de réajuster les commandes."
                },
                {
                    "q": "8. [Module AS] Face à un patient grabataire maintenu de façon prolongée sur un brancard de crise aux urgences, quelle action de prévention des escarres est attendue ?",
                    "options": [
                        "L'application biquotidienne de talc sur les zones d'appui sans modifier la position du patient.",
                        "La réalisation de changements posturaux réguliers (toutes les 3 à 4 heures), l'inspection cutanée et la traçabilité des mesures de prévention.",
                        "Le maintien strict de la position allongée à plat dos pour éviter tout risque de glissement."
                    ],
                    "rep": "La réalisation de changements posturaux réguliers (toutes les 3 à 4 heures), l'inspection cutanée et la traçabilité des mesures de prévention."
                },
                {
                    "q": "9. [Module AS] Quelle est la règle d'hygiène des mains à observer rigoureusement lors de l'enchaînement des soins auprès de multiples victimes en ZRV ?",
                    "options": [
                        "Conserver la même paire de gants propres du début à la fin de la vacation pour gagner du temps.",
                        "Effectuer une friction hydro-alcoolique (PHA) entre chaque patient et procéder à un changement systématique de gants en cas de contact avec des fluides biologiques.",
                        "Se laver les mains uniquement à l'eau tiède sans solution hydro-alcoolique entre chaque patient."
                    ],
                    "rep": "Effectuer une friction hydro-alcoolique (PHA) entre chaque patient et procéder à un changement systématique de gants en cas de contact avec des fluides biologiques."
                },
                {
                    "q": "10. [Module AS] Comment l'AS doit-elle gérer la communication avec les proches de patients présents dans les couloirs lors d'une tension extrême ?",
                    "options": [
                        "Leur communiquer les premiers éléments de diagnostic médical pour dissiper leur inquiétude.",
                        "Accueillir avec empathie, rappeler les règles de circulation de crise et orienter vers la structure d'information dédiée sans divulguer de données nominatives.",
                        "Exiger leur sortie immédiate de l'enceinte de l'hôpital sous peine d'appel des forces de l'ordre."
                    ],
                    "rep": "Accueillir avec empathie, rappeler les règles de circulation de crise et orienter vers la structure d'information dédiée sans divulguer de données nominatives."
                }
            ],
            "Medecin": [
                {
                    "q": "6. [Module Medecin] En situation de saturation aiguë des urgences (Plan Blanc), quel critère médico-légal valide la décision de sortie précoce ou d'orientation directe vers l'aval ?",
                    "options": [
                        "L'absence de réclamation du patient après quatre heures d'attente dans les couloirs.",
                        "La formalisation d'une évaluation médicale de sécurité, la validation des critères de stabilité et la transmission des consignes écrites au Medecin traitant.",
                        "L'accord tacite du Medecin, qui sera tracé plus tard."
                    ],
                    "rep": "La formalisation d'une évaluation médicale de sécurité, la validation des critères de stabilité et la transmission des consignes écrites au Medecin traitant."
                },
                {
                    "q": "7. [Module Medecin] Lors d'un afflux massif de victimes (AMV), sur quoi se fonde la doctrine de triage médico-chirurgical (PMA / Accueil des urgences) ?",
                    "options": [
                        "L'ordre d'arrivée chronologique des patients sur le site des urgences.",
                        "La hiérarchisation rapide de la criticité (urgences absolues U1 vs relatives U2/U3) pour optimiser l'allocation immédiate des ressources vitales.",
                        "La réalisation systématique d'un examen clinique médical complet avant l'orientation."
                    ],
                    "rep": "La hiérarchisation rapide de la criticité (urgences absolues U1 vs relatives U2/U3) pour optimiser l'allocation immédiate des ressources vitales."
                },
                {
                    "q": "8. [Module Medecin] En mode dégradé informatique, quelles mentions obligatoires doivent impérativement figurer sur une prescription médicale d'urgence rédigée sur papier ?",
                    "options": [
                        "Le tampon de l'hôpital, la signature et les initiales du Medecin.",
                        "L'identification nominative du prescripteur, sa signature manuscrite, la date et l'horodatage de manière lisible.",
                        "La transcription ultérieure par le secrétariat sans contre-signature du Medecin prescripteur."
                    ],
                    "rep": "L'identification nominative du prescripteur, sa signature manuscrite, la date et l'horodatage de manière lisible."
                },
                {
                    "q": "9. [Module Medecin] En contexte de tension extrême aux urgences, quelle règle encadre la prise de décision collégiale de limitation ou d'arrêt de traitement (LAT) ?",
                    "options": [
                        "La décision du Medecin s'occupant du patient suffit.",
                        "Malgré la situation, il faut respecter la procédure collégiale, la consultation des directives anticipées ou de la personne de confiance, et la traçabilité formelle de la discussion.",
                        "Le report de la discussion au-delà de la fin de la vague épidémique ou de la crise est possible."
                    ],
                    "rep": "Malgré la situation, il faut respecter la procédure collégiale, la consultation des directives anticipées ou de la personne de confiance, et la traçabilité formelle de la discussion."
                },
                {
                    "q": "10. [Module Medecin] Quelle est l'attente majeure de la HAS concernant l'organisation du retour d'expérience (REX) après une séquence de crise SSE ?",
                    "options": [
                        "La constitution d'un rapport de synthèse anonyme classé immédiatement dans les archives de l'hôpital.",
                        "La mise en place d'une analyse systémique non punitive (CREX) des dysfonctionnements pour transformer les retours de terrain en plans d'actions correctives.",
                        "La recherche individuelle d'un responsable à sanctionner en cas de dépassement des délais de prise en charge."
                    ],
                    "rep": "La mise en place d'une analyse systémique non punitive (CREX) des dysfonctionnements pour transformer les retours de terrain en plans d'actions correctives."
                }
            ],
            "ARM (Assistant/e de Régulation Médicale)": [
                {
                    "q": "6. [Module ARM] Lors de la prise d'un appel signalant un Événement Impliquant de Multiples Victimes (EIMV), quel est le triptyque de qualification prioritaire pour l'ARM ?",
                    "options": [
                        "L'identité de l'appelant, son opérateur téléphonique et son adresse mail.",
                        "La localisation exacte de l'événement, la nature précise du vecteur/de l'étiologie, et l'estimation chiffrée du nombre de impliqués.",
                        "La disponibilité immédiate des ambulances privées de la commune voisine."
                    ],
                    "rep": "La localisation exacte de l'événement, la nature précise du vecteur/de l'étiologie, et l'estimation chiffrée du nombre de impliqués."
                },
                {
                    "q": "7. [Module ARM] En cas d'effet d'appel massif saturant les lignes d'urgence du SAMU, quelle est la conduite à tenir immédiate pour l'ARM ?",
                    "options": [
                        "Décrocher et maintenir les appelants non urgents en ligne pour leur expliquer la situation de saturation.",
                        "Activer le protocole de régulation de crise, prioriser l'accès aux lignes dédiées/rouges et appliquer les messages pré-enregistrés de filtrage.",
                        "Fermer le standard téléphonique en redirigeant vers le 15 national général."
                    ],
                    "rep": "Activer le protocole de régulation de crise, prioriser l'accès aux lignes dédiées/rouges et appliquer les messages pré-enregistrés de filtrage."
                },
                {
                    "q": "8. [Module ARM] Quelle est la règle déontologique stricte de l'ARM face à un tiers réclamant des informations sur des victimes transportées lors d'un accident majeur ?",
                    "options": [
                        "Confirmer la prise en charge si l'appelant donne le nom de famille exact du patient.",
                        "Maintenir le secret professionnel absolu, refuser toute divulgation d'identité par téléphone et orienter vers la cellule d'information officielle.",
                        "Transmettre le dossier médical complet par fax ou mail sécurisé."
                    ],
                    "rep": "Maintenir le secret professionnel absolu, refuser toute divulgation d'identité par téléphone et orienter vers la cellule d'information officielle."
                },
                {
                    "q": "9. [Module ARM] En mode dégradé des outils informatiques de régulation (CENTAURE), que doit faire l'ARM ?",
                    "options": [
                        "Suspendre l'enregistrement des départs de moyens en attendant le redémarrage informatique.",
                        "Recourir immédiatement aux fiches de régulation papier de secours et consigner de façon chronologique et doublement horodatée chaque engagement.",
                        "Utiliser un carnet de notes personnel non standardisé qui sera détruit en fin de poste."
                    ],
                    "rep": "Recourir immédiatement aux fiches de régulation papier de secours et consigner de façon chronologique et doublement horodatée chaque engagement."
                },
                {
                    "q": "10. [Module ARM] Comment l'ARM sécurise-t-elle la coordination des moyens héliportés ou terrestres engagés sur une SSE ?",
                    "options": [
                        "En coupant les communications radio dès que le vecteur quitte la base héliportée.",
                        "En assurant un suivi de liaison continu, en validant les consignes de guidage et en traçant infailliblement les heures d'engagement et de libération.",
                        "En déléguant le suivi des transmissions aux conducteurs eux-mêmes."
                    ],
                    "rep": "En assurant un suivi de liaison continu, en validant les consignes de guidage et en traçant infailliblement les heures d'engagement et de libération."
                }
            ],
            "Accueil": [
                {
                    "q": "6. [Module Accueil] Face à l'afflux de familles aux urgences cherchant des informations sur des impliqués lors d'un Plan Blanc, quelle est la règle administrative ?",
                    "options": [
                        "Afficher la liste des entrées sur un tableau d'affichage à l'entrée de la salle d'attente.",
                        "Appliquer la non-divulgation stricte des identités par les agents d'accueil et orienter impérativement les familles vers la Cellule d'Information du Public (CIP).",
                        "Autoriser les familles à accéder aux box de soins pour identifier leur proche."
                    ],
                    "rep": "Appliquer la non-divulgation stricte des identités par les agents d'accueil et orienter impérativement les familles vers la Cellule d'Information du Public (CIP)."
                },
                {
                    "q": "7. [Module Accueil] En cas de panne informatique des logiciels d'admission, comment l'agent d'accueil procède-t-il ?",
                    "options": [
                        "Refuser l'enregistrement administratif des patients jusqu'au retour complet de la connexion réseau.",
                        "Utiliser les registres et feuillets d'admission papier de crise, consigner les identités (ou triptyques) et assurer la rétro-saisie informatique différée.",
                        "Créer des dossiers fictifs avec des numéros aléatoires sans lien avec l'état civil."
                    ],
                    "rep": "Utiliser les registres et feuillets d'admission papier de crise, consigner les identités (ou triptyques) et assurer la rétro-saisie informatique différée."
                },
                {
                    "q": "8. [Module Accueil] Quel est le rôle de l'agent d'accueil dans la sécurisation physique de la zone d'admission lors d'une alerte de type menace extérieure ?",
                    "options": [
                        "Laisser les portes automatiques ouvertes pour faciliter l'évacuation rapide des usagers de la salle d'attente.",
                        "Activer le verrouillage des accès du guichet selon les consignes du PC de crise, filtrer les entrées et déclencher les alarmes dédiées si requis.",
                        "Demander l'avis de chaque patient avant d'envisager la fermeture des portes."
                    ],
                    "rep": "Activer le verrouillage des accès du guichet selon les consignes du PC de crise, filtrer les entrées et déclencher les alarmes dédiées si requis."
                },
                {
                    "q": "9. [Module Accueil] Comment maintenir la confidentialité des données à la banque d'accueil en situation d'afflux tendu ?",
                    "options": [
                        "Énoncer à haute voix les motifs de consultation pour accélérer la rotation de la file d'attente.",
                        "Respecter la distance de discrétion, veiller à l'invisibilité des écrans nominatifs pour le public et baisser la voix lors des recueils d'état civil.",
                        "Laisser les dossiers ouverts sur le comptoir en l'absence de l'agent."
                    ],
                    "rep": "Respecter la distance de discrétion, veiller à l'invisibilité des écrans nominatifs pour le public et baisser la voix lors des recueils d'état civil."
                },
                {
                    "q": "10. [Module Accueil] Quelle est la procédure pour la gestion des objets de valeur d'un patient pris en charge en urgence absolue de crise ?",
                    "options": [
                        "Laisser les effets personnels dans les vêtements posés au pied du brancard.",
                        "Réaliser un inventaire contradictoire formalisé et transférer immédiatement les valeurs dans le coffre sécurisé de l'établissement.",
                        "Confier les objets au premier accompagnant présent dans les couloirs."
                    ],
                    "rep": "Réaliser un inventaire contradictoire formalisé et transférer immédiatement les valeurs dans le coffre sécurisé de l'établissement."
                }
            ],
            "Brancardier": [
                {
                    "q": "6. [Module Brancardier] En situation de Plan Blanc, quelle règle régit les déplacements des brancards au sein de l'établissement ?",
                    "options": [
                        "Emprunter les trajets les plus courts en traversant les zones confinées sans signalisation.",
                        "Respecter strictly le plan de circulation sectorisé et les sens unidirectionnels (séparation des flux entrants/sortants et propres/contaminés) définis par la logistique de crise.",
                        "Utiliser exclusivement les ascenseurs publics de l'hôpital."
                    ],
                    "rep": "Respecter strictement le plan de circulation sectorisé et les sens unidirectionnels (séparation des flux entrants/sortants et propres/contaminés) définis par la logistique de crise."
                },
                {
                    "q": "7. [Module Brancardier] Quelle vérification d'identitovigilance le brancardier réalise-t-il impérativement avant tout transport de patient vers l'imagerie ?",
                    "options": [
                        "Interroger le patient sur son numéro de chambre.",
                        "Contrôler la concordance stricte entre l'identité figurant sur le bon de transport et celle inscrite sur le bracelet d'identification physique du patient.",
                        "Se fier uniquement à l'indication verbale du numéro de box."
                    ],
                    "rep": "Contrôler la concordance stricte entre l'identité figurant sur le bon de transport et celle inscrite sur le bracelet d'identification physique du patient."
                },
                {
                    "q": "8. [Module Brancardier] En contexte d'afflux massif, quelle est la cadence de désinfection exigée pour le matériel de brancardage ?",
                    "options": [
                        "Un nettoyage hebdomadaire du parc de brancards le week-end.",
                        "Une désinfection systématique des surfaces de contact (matelas, ridelles, poignées) avec un produit détergent-désinfectant homologué entre chaque patient.",
                        "Un simple essuyage à l'eau claire sans produit actif."
                    ],
                    "rep": "Une désinfection systématique des surfaces de contact (matelas, ridelles, poignées) avec un produit détergent-désinfectant homologué entre chaque patient."
                },
                {
                    "q": "9. [Module Brancardier] Quelle précaution d'arrimage est indispensable lors du transport d'un patient sous oxygénothérapie ?",
                    "options": [
                        "Poser la bouteille d'oxygène à plat le long des jambes du patient sur le brancard.",
                        "Fixer solidement l'obus dans son support dédié attitré, vérifier l'autonomie et s'assurer que les ridelles du brancard sont relevées.",
                        "Porter la bouteille à la main en marchant à côté du brancard."
                    ],
                    "rep": "Fixer solidement l'obus dans son support dédié attitré, vérifier l'autonomie et s'assurer que les ridelles du brancard sont relevées."
                },
                {
                    "q": "10. [Module Brancardier] Quelle est l'action du brancardier en cas de modification de l'état clinique d'un patient pendant son transport ?",
                    "options": [
                        "Poursuivre le trajet jusqu'à la destination finale sans modifier son allure.",
                        "Alerter immédiatement l'équipe médicale ou paramédicale d'accueil à l'arrivée (ou via les canaux de crise) et transmettre les observations cliniques.",
                        "Faire demi-tour de sa propre initiative sans prévenir."
                    ],
                    "rep": "Alerter immédiatement l'équipe médicale ou paramédicale d'accueil à l'arrivée (ou via les canaux de crise) et transmettre les observations cliniques."
                }
            ],
            "ASH": [
                {
                    "q": "6. [Module ASH] En cas de risque contaminant avéré (biologique ou chimique) lors d'une SSE, quelle méthode de bio-nettoyage l'ASH applique-t-il ?",
                    "options": [
                        "Un balayage à sec pour éliminer rapidement les débris au sol.",
                        "L'application rigoureuse du protocole de désinfection terminale renforcée avec des produits virucides/sporicides aux temps de contact requis, en portant les EPI adaptés.",
                        "Un lavage des surfaces avec du savon classique sans temps de pose."
                    ],
                    "rep": "L'application rigoureuse du protocole de désinfection terminale renforcée avec des produits virucides/sporicides aux temps de contact requis, en portant les EPI adaptés."
                },
                {
                    "q": "7. [Module ASH] Quelle est la règle de tri et d'évacuation des linges et déchets souillés en période de crise ?",
                    "options": [
                        "Regrouper l'ensemble des linges et des déchets dans les mêmes grands conteneurs municipaux.",
                        "Respecter la séparation stricte des filières (DASRI, DAOM, linges en sacs hydrosolubles étanches) pour prévenir toute contamination croisée.",
                        "Jeter les déchets par les ouvertures des box de soins."
                    ],
                    "rep": "Respecter la séparation stricte des filières (DASRI, DAOM, linges en sacs hydrosolubles étanches) pour prévenir toute contamination croisée."
                },
                {
                    "q": "8. [Module ASH] Quelle est l'exigence d'hygiène des mains pour l'ASH manipulant des zones ou des déchets à risque ?",
                    "options": [
                        "Garder la même paire de gants tout au long de la journée sans friction.",
                        "Réaliser une friction hydro-alcoolique avant et après chaque manipulation de déchets ou de zone contaminée, et obligatoirement après le retrait des gants.",
                        "Se rincer les mains à l'eau tiède sans solution hydro-alcoolique."
                    ],
                    "rep": "Réaliser une friction hydro-alcoolique avant et après chaque manipulation de déchets ou de zone contaminée, et obligatoirement après le retrait des gants."
                },
                {
                    "q": "9. [Module ASH] Que doit faire l'ASH s'il découvre un instrument piquant/tranchant abandonné sur un plan de travail ?",
                    "options": [
                        "Le ramasser à main nue pour le jeter dans la poubelle d'ordures ménagères.",
                        "Ne jamais toucher le dispositif à main nue, baliser la zone si nécessaire et prévenir immédiatement un soignant pour élimination sécurisée dans un collecteur d'OPCT.",
                        "Le glisser sous le matelas du box de soin."
                    ],
                    "rep": "Ne jamais toucher le dispositif à main nue, baliser la zone si nécessaire et prévenir immédiatement un soignant pour élimination sécurisée dans un collecteur d'OPCT."
                },
                {
                    "q": "10. [Module ASH] Comment l'ASH concilie-t-il bientraitance environnementale et tension de crise lors de l'entretien d'un box occupé ?",
                    "options": [
                        "Pénétrer dans le box sans frapper et sans adresser la parole au patient.",
                        "Frapper à la porte, se présenter, expliquer l'intervention de nettoyage, respecter l'intimité et veiller à préserver un cadre propre et apaisant malgré la tension.",
                        "Nettoyer uniquement le centre de la pièce sans se préoccuper du confort du patient."
                    ],
                    "rep": "Frapper à la porte, se présenter, expliquer l'intervention de nettoyage, respecter l'intimité et veiller à préserver un cadre propre et apaisant malgré la tension."
                }
            ],
            "Cadre": [
                {
                    "q": "6. [Module Cadre] Quels indicateurs de tension opérationnelle le Cadre de Santé doit-il suivre et remonter en temps réel à la cellule de crise ?",
                    "options": [
                        "Le nombre de pauses café réalisées par l'équipe administrative de garde.",
                        "Le taux d'occupation des box, le volume de patients en attente d'aval (beds-blocking), les délais d'attente à l'IAO et l'adéquation des effectifs soignants.",
                        "Le total des heures de nuit cumulées sur le mois précédent."
                    ],
                    "rep": "Le taux d'occupation des box, le volume de patients en attente d'aval (beds-blocking), les délais d'attente à l'IAO et l'adéquation des effectifs soignants."
                },
                {
                    "q": "7. [Module Cadre] Face à l'épuisement des équipes en situation de crise prolongée, quelle est la responsabilité managériale prioritaire du Cadre ?",
                    "options": [
                        "Exiger des journées de travail continues de 24 heures sans interruption pour maintenir les effectifs.",
                        "Planifier des rotations équitables, veiller au respect des temps de pause obligatoires, mettre en place un soutien et surveiller les signes d'épuisement.",
                        "Ignorer la fatigue des agents tant que les indicateurs de flux restent stables."
                    ],
                    "rep": "Planifier des rotations équitables, veiller au respect des temps de pause obligatoires, mettre en place un soutien et surveiller les signes d'épuisement."
                },
                {
                    "q": "8. [Module Cadre] Comment le Cadre s'assure-t-il de la sécurité des soins en mode dégradé informatique dans son unité ?",
                    "options": [
                        "Laisser chaque agent s'organiser de manière autonome sans contrôle des supports papier.",
                        "Superviser la mise en place immédiate des dossiers papier de crise, auditer leur conformité (signatures, horodatages) et valider la traçabilité des transmissions.",
                        "Interdire la prescription de tout traitement durant toute la durée de la panne informatique."
                    ],
                    "rep": "Superviser la mise en place immédiate des dossiers papier de crise, auditer leur conformité (signatures, horodatages) et valider la traçabilité des transmissions."
                },
                {
                    "q": "9. [Module Cadre] Quelle démarche le Cadre adopte-t-il face aux signalements d'Événements Indésirables (EI) survenus pendant la gestion de la crise ?",
                    "options": [
                        "Dissimuler les incidents pour ne pas pénaliser l'image de l'établissement auprès de la direction.",
                        "Promouvoir la culture positive de sécurité, encourager la déclaration immédiate des EI et animer l'analyse collective des causes pour ajuster les pratiques.",
                        "Sanctionner immédiatement l'agent impliqué dans l'incident sans analyse systémique."
                    ],
                    "rep": "Promouvoir la culture positive de sécurité, encourager la déclaration immédiate des EI et animer l'analyse collective des causes pour ajuster les pratiques."
                },
                {
                    "q": "10. [Module Cadre] Dans le cadre de la préparation à la visite HAS, quel rôle d'évaluation interne joue le Cadre de Santé sur le terrain ?",
                    "options": [
                        "Remplir les dossiers de manière fictive la veille du passage des experts de la HAS.",
                        "Réaliser des audits flash réguliers (traçabilité de la douleur, identitovigilance, chariots d'urgence) et impliquer l'équipe dans l'démarche qualité continue.",
                        "Interdire aux experts d'interroger les soignants non cadres de l'unité."
                    ],
                    "rep": "Réaliser des audits flash réguliers (traçabilité de la douleur, identitovigilance, chariots d'urgence) et impliquer l'équipe dans l'démarche qualité continue."
                }
            ]
        },
        "fiches_reflexes": {
            "Tronc Commun": {
                "class": "memo-box-tc",
                "slug": "tronc_commun",
                "points": [
                    "**Plan Blanc & Gouvernance** : Activation conjointe direction / commandement médical de crise (DMC) et libération programmée de l'aval.",
                    "**Modes Dégradés & Traçabilité** : Utilisation obligatoire des dossiers papier normalisés de crise avec double signature et horodatage strict en cas de panne informatique.",
                    "**Sécurité Active (Intrusion)** : Maîtrise des consignes de sauvegarde (Fuir - Se cacher - Alerter).",
                    "**Plan Blanc & Cellule de Crise** : Déclenchement officiel par la Direction / ARS. Ouverture des lits d'aval et des zones tampons.",
                    "**Tri & Afflux Massif (NOVI)** : Utilisation des méthodes de tri standardisées (START / fiches de tri).",
                    "**Mode Dégradé & Informatique** : Recours immédiat aux dossiers papiers de crise nominatifs et traçabilité chronologique rigoureuse.",
                    "**Communication de Crise** : Interdiction absolue de divulguer des données nominatives à l'extérieur (cellule de communication officielle)."
                ]
            },
            "IDE": {
                "class": "memo-box-ide",
                "slug": "ide",
                "points": [
                    "**Tri Pré-hospitalier/Intra-hospitalier** : Application rigoureuse des échelles de criticité pour l'identification immédiate des urgences absolues (U1).",
                    "**Traçabilité de Crise** : Maintien d'un enregistrement minimal mais infaillible des soins critiques administrés sous triptyque de crise.",
                    "**Tri IAO de Crise** : Identification immédiate des urgences absolues (UA) en zone d'accueil renforcée.",
                    "**Sécurité des Soins en Mode Dégradé** : Double lecture des prescriptions et traçabilité papier nominative et horodatée."
                ]
            },
            "AS": {
                "class": "memo-box-as",
                "slug": "as",
                "points": [
                    "**Logistique Opérationnelle** : Mobilisation instantanée des chariots de crise et des stocks de brancardage normé.",
                    "**Sécurisation des Flux** : Participation active à l'aménagement des zones tampons et de la ZRV.",
                    "**Logistique de Crise** : Renfort immédiat pour l'installation des zones d'extension et l'acheminement du matériel lourd.",
                    "**Identitovigilance SSE** : Utilisation des bracelets et numéros de crise provisoires pour les victimes anonymes."
                ]
            },
            "Medecin": {
                "class": "memo-box-med",
                "slug": "medecin",
                "points": [
                    "**Régulation & Coordination Interne** : Supervision médicale du tri, arbitrage des priorités d'examens et pilotage des sorties directes vers l'aval.",
                    "**Validation des Prescriptions de Crise** : Traçabilité formalisée des décisions d'urgence sous contrainte de plateau technique dégradé.",
                    "**Commandement Médical & Triage** : Rôle du Medecin chef de triage et coordination étroite avec le SAMU-Centre 15.",
                    "**Traçabilité Allégée de Crise** : Conservation des informations cliniques essentielles sur support papier de crise."
                ]
            },
            "ARM (Assistant/e de Régulation Médicale)": {
                "class": "memo-box-arm",
                "slug": "ARM (Assistant/e de Régulation Médicale)",
                "points": [
                    "**Qualification de l'EIMV** : Recueil normé du triptyque d'alerte (Cinétique, Nombre d'impliqués, Gravité potentielle) pour le Medecin régulateur.",
                    "**Sécurisation des Réseaux** : Utilisation exclusive des canaux de communication dédiés en situation critique.",
                    "**Régulation en Flux Tendu** : Priorisation des appels d'urgence vitale et main courante papier de secours.",
                    "**Orientation des Familles** : Redirection systématique vers la cellule d'information du public (CIP)."
                ]
            },
            "Accueil & Admission": {
                "class": "memo-box-acc",
                "slug": "accueil",
                "points": [
                    "**Filtrage & Protection des Données** : Application stricte des consignes de non-divulgation des identités et orientation des familles vers la CIP.",
                    "**Sécurité des Accès** : Verrouillage physique des entrées de l'unité sous tension.",
                    "**Filtrage & Admissions Rapides** : Bascule sur le circuit papier d'urgence et gestion rigoureuse des flux de proches.",
                    "**Sécurité & Médias** : Refus d'accès aux journalistes et orientation vers le point d'accueil familles (PAF)."
                ]
            },
            "Brancardier": {
                "class": "memo-box-branc",
                "slug": "brancardier",
                "points": [
                    "**Respect des Circulations** : Application stricte des plans de flux unidirectionnels et sectorisés (propres/contaminés).",
                    "**Coordination** : Liaison permanente avec le poste de commandement logistique de crise.",
                    "**Fluidité & Évacuations** : Priorisation des transferts urgents (imagerie, bloc) et application des consignes d'évacuation PMR.",
                    "**Vérification Matériel** : Disponibilité permanente des brancards, chaises d'évacuation et obus d'oxygène."
                ]
            },
            "ASH": {
                "class": "memo-box-ash",
                "slug": "ash",
                "points": [
                    "**Bio-nettoyage de Crise** : Application des protocoles spécifiques de désinfection renforcée en zone contaminée.",
                    "**EPI & Filières** : Port obligatoire des équipements adaptés et gestion sécurisée des flux de déchets spécifiques.",
                    "**Bio-nettoyage en Rotation Rapide** : Désinfection active et continue des box de soins en flux tendu.",
                    "**Gestion des Déchets de Crise** : Multiplication des collecteurs DASRI au plus près des zones de soins."
                ]
            },
            "Cadre de Santé": {
                "class": "memo-box-cadre",
                "slug": "cadre",
                "points": [
                    "**Pilotage & Reporting** : Remontée en temps réel des indicateurs de tension (saturation, lits d'aval, absentéisme/renforts).",
                    "**Soutien Managérial** : Organisation des rotations d'équipes et accompagnement opérationnel sous tension.",
                    "**Management Opérationnel & Rappel** : Activation du plan de rappel, soutien psychologique et gestion des temps de pause.",
                    "**REX Post-Crise** : Organisation obligatoire du retour d'expérience à chaud et rédaction du plan d'actions correctives."
                ]
            }
        }
    },
        {
        "id": 3,
        "titre": "Semaine 3 - Médicaments, Prescriptions & Sécurité des Soins",
        "date_debut": datetime.date(2026, 11, 9),
        "date_fin": datetime.date(2026, 11, 15),
        "tronc_commun": [
            {
                "q": "1. [Tronc Commun] Un patient arrive aux urgences sans papiers, somnolent. On lui attribue un dossier 'X'. Au bout d'une heure, un proche apporte sa carte vitale. Quelle est la règle HAS impérative pour la gestion du dossier et des prescriptions déjà initiées ?",
                "options": [
                    "Laisser le dossier en 'X' jusqu'à la fin de la prise en charge pour éviter toute rupture de traçabilité informatique, puis demander le transfert à la bonne identité une fois la PEC terminée.",
                    "Réaliser immédiatement une fusion des dossiers et une vérification croisée de la traçabilité des prescriptions administrées sous 'X'.",
                    "Clôturer le dossier 'X' et en recréer un nouveau, puis demander la fusion ensuite."
                ],
                "rep": "Réaliser immédiatement une fusion des dossiers et une vérification croisée de la traçabilité des prescriptions administrées sous 'X'."
            },
            {
                "q": "2. [Tronc Commun] En urgence, un patient âgé arrive avec un traitement chronique complexe. L'interne transcrit rapidement les médicaments de tête. Que dit la HAS sur la réconciliation médicamenteuse en structure d'urgence ?",
                "options": [
                    "Elle est optionnelle aux urgences en raison de l'urgence vitale et reportée à l'hospitalisation en aval.",
                    "Elle doit être amorcée dès l'accueil (recherche d'ordonnance, entretien) et formalisée pour les patients à risque (âgés, polypathologiques) avant toute prescription de sortie ou d'aval.",
                    "Elle est réalisée de manière systématique par l'équipe médicale uniquement pour les patients orientés vers l'hospitalisation, mais facultative pour ceux retournant à domicile puisque le Medecin traitant reprend le relais."
                ],
                "rep": "Elle doit être amorcée dès l'accueil (recherche d'ordonnance, entretien) et formalisée pour les patients à risque (âgés, polypathologiques) avant toute prescription de sortie ou d'aval."
            },
            {
                "q": "3. [Tronc Commun] Concernant le stockage et la double vérification des Médicaments à Haut Risque (MHR, ex: insuline, potassium injectable, anticoagulants) aux urgences en période de tension :",
                "options": [
                    "Le double contrôle visuel et nominatif est requis uniquement en réanimation, les urgences étant soumises à une règle de rapidité dérogatoire.",
                    "Le double contrôle avant administration est une exigence forte de sécurité des soins HAS pour tous les MHR, même en contexte de tension.",
                    "Le double contrôle peut être allégé ou réalisé a posteriori par un seul soignant si le service est confronté à un afflux massif de patients, sous réserve de validation médicale globale en fin de poste."
                ],
                "rep": "Le double contrôle avant administration est une exigence forte de sécurité des soins HAS pour tous les MHR, même en contexte de tension."
            },
            {
                "q": "4. [Tronc Commun] Suite à une erreur d'administration d'un antibiotique (allergie connue mais non lue sur le dossier), le patient n'a finalement pas de réaction clinique grave. Que préconise la culture de sécurité HAS ?",
                "options": [
                    "Ne rien signaler puisque le patient n'a pas eu de dommage clinique avéré (quasi-erreur non déclarée pour éviter la surcharge administrative).",
                    "Réaliser une FEI pour analyser les causes systémiques et ajuster les pratiques.",
                    "Faire un simple rappel à l'ordre verbal au Medecin et à l'IDE concernés pour éviter que cela ne se reproduise, sans trace écrite."
                ],
                "rep": "Réaliser une FEI pour analyser les causes systémiques et ajuster les pratiques."
            },
            {
                "q": "5. [Tronc Commun] En cas de dispensation d'un stupéfiant (ex: morphine) en urgence vitale sans validation préalable complète du stock informatisé :",
                "options": [
                    "Noter la sortie sur un papier avec l'identité du patient receveur et demander à un collègue de régulariser dans le registre des stupéfiants pendant qu'on dispense le traitement rapidement.",
                    "Assurer une traçabilité immédiate et conjointe (prescription, registre papier/numérique de stups, double signature) garantissant l'exhaustivité de la traçabilité, malgré l'urgence vitale.",
                    "En cas d'urgence vitale, l'administration immédiate prime : on utilise le stock et on tracera dans le registre des stupéfiants dès que possible par la suite."
                ],
                "rep": "Assurer une traçabilité immédiate et conjointe (prescription, registre papier/numérique de stups, double signature) garantissant l'exhaustivité de la traçabilité, malgré l'urgence vitale."
            }
        ],
        "metiers": {
            "IDE": [
                {
                    "q": "6. [Module IDE] Lors de la pose d'une perfusion de noradrénaline sur une voie périphérique en urgence, quel piège quotidien la HAS épingle-t-elle ?",
                    "options": [
                        "L'utilisation d'une tubulure standard sans purge préalable d'air.",
                        "L'absence de pose sur une voie veineuse centrale (ou voie dédiée validée) et de dispositif de perfusion sécurisé anti-flux libre, risquant une extravasation ou un bolus accidentel.",
                        "Le changement de flacon toutes les 48 heures sans désinfection du robinet."
                    ],
                    "rep": "L'absence de pose sur une voie veineuse centrale (ou voie dédiée validée) et de dispositif de perfusion sécurisé anti-flux libre, risquant une extravasation ou un bolus accidentel."
                },
                {
                    "q": "7. [Module IDE] Vous préparez de l'insuline IV en PSE en binôme IDE. Votre collègue est appelé en urgence sur un arrêt cardiaque au milieu de la préparation. Que faites-vous ?",
                    "options": [
                        "Vous terminez la préparation et l'administrez seul(e) pour ne pas retarder le traitement du patient.",
                        "Vous suspendez l'administration ou attendez qu'un(e) autre collègue puisse effectuer la double vérification conjointe avec vous avant la pose.",
                        "Votre collègue signe le double contrôle et vous laisse terminer la préparation."
                    ],
                    "rep": "Vous suspendez l'administration ou attendez qu'un(e) autre collègue puisse effectuer la double vérification conjointe avec vous avant la pose."
                },
                {
                    "q": "8. [Module IDE] Il reste de la morphine injectable dans une ampoule après administration de la dose prescrite. Quelle est la règle réglementaire de gestion du reliquat ?",
                    "options": [
                        "Stocker le reliquat dans le frigo sécurisé des stups, étiqueté au nom du patient, pour pouvoir injecter le solde lors de la prochaine réévaluation de la douleur si le Medecin le prescrit.",
                        "Procéder à l'élimination sécurisée et traçable du reliquat (jeté avec témoin ou destruction selon protocole) pour éviter tout détournement ou erreur.",
                        "Jeter le reliquat dans le conteneur en fin de tour, et le noter pour régulariser le registre des stups en fin de semaine."
                    ],
                    "rep": "Procéder à l'élimination sécurisée et traçable du reliquat (jeté avec témoin ou destruction selon protocole) pour éviter tout détournement ou erreur."
                },
                {
                    "q": "9. [Module IDE] Un patient présente des gélules à libération prolongée écrasées pour passage en SNG en urgence. Quelle est l'analyse de cette pratique ?",
                    "options": [
                        "C'est la procédure standard pour faciliter l'absorption rapide par la sonde.",
                        "C'est une erreur médicamenteuse grave : les formes à libération prolongée ou entériques ne doivent jamais être écrasées sans avis pharmacologique, au risque d'un surdosage brutal.",
                        "Il faut diluer les gélules dans du jus de fruit acide pour éviter le surdosage."
                    ],
                    "rep": "C'est une erreur médicamenteuse grave : les formes à libération prolongée ou entériques ne doivent jamais être écrasées sans avis pharmacologique, au risque d'un surdosage brutal."
                },
                {
                    "q": "10. [Module IDE] En mode dégradé informatique (panne du DPI), vous avez tracé l'administration d'un antalgique majeur sur la feuille papier de crise. Le réseau revient en fin de service alors que vous êtes en plein passage de relèves. Quelle est la règle HAS pour la retranscription informatique ?",
                    "options": [
                        "Laisser uniquement la trace papier dans le dossier physique du patient, le dossier informatique n'ayant plus besoin d'être mis à jour rétrospectivement puisque l'acte a été réalisé pendant la panne.",
                        "Saisir immédiatement l'administration sur le DPI dès le retour du réseau en modifiant la date de l'acte pour qu'elle corresponde à l'heure exacte de la ressaisie informatique, afin de faire propre dans les courbes de l'application.",
                        "Reporter les données sur le DPI avec l'horodatage réel de l'administration (et non de la saisie), puis viser et archiver la feuille de crise papier selon le circuit institutionnel défini."
                    ],
                    "rep": "Reporter les données sur le DPI avec l'horodatage réel de l'administration (et non de la saisie), puis viser et archiver la feuille de crise papier selon le circuit institutionnel défini."
                }
            ],
            "AS": [
                {
                    "q": "6. [Module AS] Un patient âgé grabataire réclame à boire juste avant l'administration orale de ses comprimés par l'IDE. L'AS lui tend un grand verre d'eau en position semi-assise basse. Quel risque la HAS met-elle en avant ?",
                    "options": [
                        "Un risque d'altération de la consistance des comprimés par contact prolongé avec un volume d'eau trop important avant l'action de l'IDE.",
                        "Un risque de fausse route par fausse coïncidence entre la déglutition d'un grand volume d'eau et la prise simultanée des comprimés en position non strictement assise.",
                        "Une dilution excessive des médicaments dans l'estomac rendant le traitement inefficace."
                    ],
                    "rep": "Un risque de fausse route par fausse coïncidence entre la déglutition d'un grand volume d'eau et la prise simultanée des comprimés en position non strictement assise."
                },
                {
                    "q": "7. [Module AS] L'IDE demande à l'AS de déplacer un sachet nominatif de médicaments d'un box à un autre car elle est occupée en urgence sur un autre patient. Que doit faire l'AS selon les exigences de sécurité HAS ?",
                    "options": [
                        "Accepter de transporter le sachet, puisque l'IDE en reste le prescripteur et que cela fait gagner du temps à l'équipe.",
                        "Refuser d'assurer le transport de produits de santé nominatifs, le circuit du médicament et sa dispensation exclusive relevant de la responsabilité propre des professionnels habilités.",
                        "Déposer le sachet directement dans le box d'arrivée en attendant que l'IDE vienne valider l'administration."
                    ],
                    "rep": "Refuser d'assurer le transport de produits de santé nominatifs, le circuit du médicament et sa dispensation exclusive relevant de la responsabilité propre des professionnels habilités."
                },
                {
                    "q": "8. [Module AS] En rangeant un box après le passage de l'équipe médicale, l'AS trouve une seringue non utilisée avec son aiguille nue sur le plan de travail. Quelle est la bonne attitude ?",
                    "options": [
                        "Reboucher la seringue et la jeter dans la poubelle d'ordures ménagères car elle n'a pas servi.",
                        "Activer la sécurité de l'aiguille (si dispositif sécurisé) ou jeter l'ensemble dans le conteneur OPCT rigide le plus proche sans recapuchonner.",
                        "Aller signaler l'aiguille sans la toucher."
                    ],
                    "rep": "Activer la sécurité de l'aiguille (si dispositif sécurisé) ou jeter l'ensemble dans le conteneur OPCT rigide le plus proche sans recapuchonner."
                },
                {
                    "q": "9. [Module AS] Un patient sous anticoagulant oral direct (AOD) reçoit son repas. L'AS remarque un complément alimentaire riche en vitamine K apporté par la famille. Que doit faire l'AS ?",
                    "options": [
                        "Laisser le patient consommer le complément sans rien dire car c'est son habitude.",
                        "Alerter l'IDE ou le Medecin avant toute administration de ce complément qui pourrait interférer avec l'équilibre de l'hémostase ou la prescription.",
                        "Jeter directement le produit en expliquant au patient le fait que cela risque d'interférer avec son traitement."
                    ],
                    "rep": "Alerter l'IDE ou le Medecin avant toute administration de ce complément qui pourrait interférer avec l'équilibre de l'hémostase ou la prescription."
                },
                {
                    "q": "10. [Module AS] Un patient agité sous traitement sédatif refuse de s'hydrater toute la journée. L'AS se dit qu'il boira quand il aura soif. Quelle est la bonne pratique HAS ?",
                    "options": [
                        "Laisser faire le patient pour éviter les fausses routes, ou demander la mise en place d'une hydratation sous-cutanée.",
                        "Proposer régulièrement de petites quantités d'eau, surveiller l'état cutanéo-muqueux et tracer les apports pour prévenir la déshydratation iatrogène.",
                        "Forcer le patient à boire, car il n'est pas en état de se réguler seul."
                    ],
                    "rep": "Proposer régulièrement de petites quantités d'eau, surveiller l'état cutanéo-muqueux et tracer les apports pour prévenir la déshydratation iatrogène."
                }
            ],
            "Medecin": [
                {
                    "q": "6. [Module Medecin] Le logiciel d'urgences émet une alerte rouge d'intéraction médicamenteuse majeure lors de la prescription d'un traitement. Pressé par la file d'attente, vous décidez de passer outre l'alerte sans commentaire. Que dit la certification HAS ?",
                    "options": [
                        "C'est toléré si le Medecin estime l'urgence clinique supérieure au risque théorique.",
                        "Le franchissement d'une alerte critique requiert une justification tracée dans le dossier et une évaluation bénéfice-risque explicite, la simple cécité aux alertes étant une non-conformité majeure.",
                        "Les alertes logicielles n'ont aucune valeur réglementaire, elles peuvent être désactivées globalement."
                    ],
                    "rep": "Le franchissement d'une alerte critique requiert une justification tracée dans le dossier et une évaluation bénéfice-risque explicite, la simple cécité aux alertes étant une non-conformité majeure."
                },
                {
                    "q": "7. [Module Medecin] Un patient âgé sous anticoagulants et IEC est admis pour une déshydratation aiguë avec insuffisance rénale aiguë modérée. Lors de la rédaction de l'ordonnance de sortie, vous omettez de réajuster les posologies en fonction de la clairance de la créatinine de sortie stabilisée. Quel piège la HAS épingle-t-elle ?",
                    "options": [
                        "Une simple divergence d'affichage informatique entre le dossier des urgences et le portail de la biologie, sans impact clinique immédiat puisque le traitement de ville était déjà connu.",
                        "Un défaut de réévaluation pharmacologique post-épisode aigu : le maintien à l'identique de doses inadaptées à la fonction rénale récupérée (ou non) expose le patient à un surdosage iatrogène majeur (hémorragie ou toxicité rénale).",
                        "Une non-conformité mineure de traçabilité, le Medecin traitant étant seul garant de l'adaptation des posologies lors du premier renouvellement d'ordonnance au cabinet."
                    ],
                    "rep": "Un défaut de réévaluation pharmacologique post-épisode aigu : le maintien à l'identique de doses inadaptées à la fonction rénale récupérée (ou non) expose le patient à un surdosage iatrogène majeur (hémorragie ou toxicité rénale)."
                },
                {
                    "q": "8. [Module Medecin] En plein choc anaphylactique, vous donnez un ordre verbal d'injection d'adrénaline à l'IDE. Quelle est l'exigence HAS de traçabilité a posteriori ?",
                    "options": [
                        "L'acte étant déjà tracé dans le dossier de soins infirmier par l'exécutant(e), la signature médicale a posteriori de la prescription verbale peut être omise.",
                        "La prescription verbale doit être retranscrite et signée par le Medecin prescripteur dans le dossier patient dès que l'urgence immédiate est levée.",
                        "La régularisation doit obligatoirement être validée en double signature médicale lors de la transmission de poste du soir."
                    ],
                    "rep": "La prescription verbale doit être retranscrite et signée par le Medecin prescripteur dans le dossier patient dès que l'urgence immédiate est levée."
                },
                {
                    "q": "9. [Module Medecin] Face à une infection suspectée aux urgences, l'interne prescrit une antibiothérapie large spectre sans prélèvement bactériologique préalable. Quelle est l'exigence qualité HAS ?",
                    "options": [
                        "Les urgences n'étant pas propices aux prélèvements bactériologiques (absence de fièvre lors du passage, germes croisés du fait du flux...), cela est autorisé dans ce contexte.",
                        "La stratégie probabiliste doit s'accompagner de la réalisation des prélèvements microbiologiques avant antibiothérapie et d'une réévaluation à 48-72h.",
                        "L'antibiothérapie probabiliste devra du coup être poursuivie telle qu'elle."
                    ],
                    "rep": "La stratégie probabiliste doit s'accompagner de la réalisation des prélèvements microbiologiques avant antibiothérapie et d'une réévaluation à 48-72h."
                },
                {
                    "q": "10. [Module Medecin] En cas de panne du DPI, vous rédigez une ordonnance de sortie manuscrite. Quelles mentions sont obligatoires selon les exigences de sécurité HAS ?",
                    "options": [
                        "Le nom du patient, sa date de naissance. Puis le nom du médicament, sa posologie, la durée du traitement et les moments de prise en '1-1-1'.",
                        "L'identification claire du prescripteur (RPPS, nom, signature), l'identité complète du patient, la date, la posologie et le smoments de prises de manière explicite (matin/midi/soir), et la mention manuscrite de l'absence d'informatisation si requis.",
                        "L'identité du patient, le tampon de l'hôpital, le médicament et sa posologie avec la durée à établie par le pharmacien."
                    ],
                    "rep": "L'identification claire du prescripteur (RPPS, nom, signature), l'identité complète du patient, la date, la posologie et le smoments de prises de manière explicite (matin/midi/soir), et la mention manuscrite de l'absence d'informatisation si requis."
                }
            ],
            "ARM (Assistant/e de Régulation Médicale)": [
                {
                    "q": "6. [Module ARM] Un appelant signale qu'un patient a pris une dose massive de paracétamol il y a 2 heures. Que doit faire l'ARM immédiatement ?",
                    "options": [
                        "Conseiller de lui donner du lait et de surveiller s'il a mal au ventre demain matin.",
                        "Transférer immédiatement l'appel au Medecin régulateur pour évaluation toxicologique urgente.",
                        "Envoyer une ambulance privée immédiatement, au vu de l'intoxication médicamenteuse volontaire suspectée."
                    ],
                    "rep": "Transférer immédiatement l'appel au Medecin régulateur pour évaluation toxicologique urgente."
                },
                {
                    "q": "7. [Module ARM] Lors de l'engagement d'une équipe SMUR pour un malaise grave, l'ARM retrouve sur un appel précédent les traitements du patient (notamment insuline/anticoagulants). Que fait l'ARM ?",
                    "options": [
                        "Note l'information dans le DRM pour que le SMUR le lise sur SMUR-tab.",
                        "Transmet l'information au MRU pour voir s'il contacte le SMUR lui-même ou non.",
                        "Contacte immédiatement l'équipe SMUR en route par la radio pour lui communiquer la liste des médicaments afin qu'elle gagne du temps à l'arrivée."
                    ],
                    "rep": "Transmet l'information au MRU pour voir s'il contacte le SMUR lui-même ou non."
                },
                {
                    "q": "8. [Module ARM] Un tiers appelle car un enfant a ingéré un produit ménager. L'ARM donne de tête le protocole de dilution et fait vomir. Est-ce conforme ?",
                    "options": [
                        "Oui, l'ARM a l'expérience des produits courants.",
                        "Non, l'ARM ne doit jamais donner de consigne médicale d'administration ou de vomissement et doit basculer immédiatement l'appel vers le Medecin régulateur ou le Centre Antipoison.",
                        "Oui, à condition de lui rappeler rapidement ensuite pour refaire le point."
                    ],
                    "rep": "Non, l'ARM ne doit jamais donner de consigne médicale d'administration ou de vomissement et doit basculer immédiatement l'appel vers le Medecin régulateur ou le Centre Antipoison."
                },
                {
                    "q": "9. [Module ARM] Un patient appelle pour savoir s'il peut doubler sa dose de traitement habituel car ses symptômes persistent. L'ARM lui répond oralement que oui. Faut-il tracer ?",
                    "options": [
                        "Non, la bande enregistrée permet déjà le traçage.",
                        "Oui, après avis auprès du Medecin régulateur.",
                        "Oui, l'ARM le note dans le DRM avant de raccrocher."
                    ],
                    "rep": "Oui, après avis auprès du Medecin régulateur."
                },
                {
                    "q": "10. [Module ARM] Un pharmacien d'officine appelle le SAMU pour savoir si tel patient a été hospitalisé et quel traitement lui a été administré. Que répond l'ARM ?",
                    "options": [
                        "Donne les détails du traitement pour aider le pharmacien pour la délivrance der traitements de l'ordonnance de sortie.",
                        "Applique le secret professionnel strict, ne confirme ni n'infirme sans validation médicale et oriente vers le Medecin régulateur.",
                        "Explique au pharmacien que le patient a un compte-rendu avec ces informations là, et qu'il doit s'y référer."
                    ],
                    "rep": "Applique le secret professionnel strict, ne confirme ni n'infirme sans validation médicale et oriente vers le Medecin régulateur."
                }
            ],
            "Accueil": [
                {
                    "q": "6. [Module Accueil] Un patient arrive aux urgences avec un sac rempli de ses médicaments de ville. Que fait l'agent d'accueil s'il participe au pré-accueil ?",
                    "options": [
                        "Demander au patient de les jeter dans la poubelle de la salle d'attente.",
                        "Orienter le patient et ses traitements vers l'équipe soignante pour la sécurisation, le recensement et la mise en coffre ou la réconciliation médicamenteuse.",
                        "Conserver le sac de médicaments sous le comptoir d'accueil pour éviter la perte, et le remettre à la famille quand elle arrive."
                    ],
                    "rep": "Orienter le patient et ses traitements vers l'équipe soignante pour la sécurisation, le recensement et la mise en coffre ou la réconciliation médicamenteuse."
                },
                {
                    "q": "7. [Module Accueil] Un patient se présente en donnant le nom de son frère pour bénéficier des soins. Quel impact direct sur la sécurité des soins et des médicaments ?",
                    "options": [
                        "Aucun, l'essentiel est qu'il soit soigné rapidement.",
                        "Un risque iatrogène majeur (allergies croisées, antécédents, posologies inadaptées basées sur un dossier erroné) entraînant une non-conformité critique HAS.",
                        "Une simple modification administrative de facture sans incidence clinique."
                    ],
                    "rep": "Un risque iatrogène majeur (allergies croisées, antécédents, posologies inadaptées basées sur un dossier erroné) entraînant une non-conformité critique HAS."
                },
                {
                    "q": "8. [Module Accueil] Un patient amène un traitement personnel onéreux (ex: biothérapie spécifique) dans son sac d'admission. Quelle est la règle ?",
                    "options": [
                        "Le laisser dans le sac au pied du brancard, en demandant au patient de bien le surveiller.",
                        "Le noter dans l'inventaire et le sécuriser (frigo si chaîne du froid, coffre si besoin).",
                        "Le confier à la famille si elle est présente et leur demander de le ramener au domicile."
                    ],
                    "rep": "Le noter dans l'inventaire et le sécuriser (frigo si chaîne du froid, coffre si besoin)."
                },
                {
                    "q": "9. [Module Accueil] Un proche demande à l'accueil si le patient se voit administrer des psychotropes car il le trouve étrange au téléphone. Que répond l'agent ?",
                    "options": [
                        "Refuser de donner toute information à l'accueil et dire aux proches d'attendre qu'on les appelle.",
                        "Transmettre l'appel ou orienter vers l'IDE ou le Medecin de la zone assignée en rappelant qu'aucun détail de traitement ne doit être délivré directement par l'agent d'accueil au comptoir.",
                        "Indiquer au proche, sans nommer de molécule précise, que le patient est pris en charge par l'équipe pour être soulagé."
                    ],
                    "rep": "Transmettre l'appel ou orienter vers l'IDE ou le Medecin de la zone assignée en rappelant qu'aucun détail de traitement ne doit être délivré directement par l'agent d'accueil au comptoir."
                },
                {
                    "q": "10. [Module Accueil] En panne informatique, comment l'agent garantit-il la transmission des identifiants corrects pour le circuit du médicament ?",
                    "options": [
                        "En utilisant des avatars Animal + Couleur, puis en récupérant les données réelles une fois la panne passée.",
                        "En utilisant les fiches d'admission papier de crise avec le triptyque d'identité vérifié (Nom, Prénom, Date de naissance) pour que l'IDE puisse administrer en sécurité.",
                        "En imprimant les anciens dossiers des patients présents dans le logiciel, afin que l'IDE puisse avoir les antécédents, allergies etc."
                    ],
                    "rep": "En utilisant les fiches d'admission papier de crise avec le triptyque d'identité vérifié (Nom, Prénom, Date de naissance) pour que l'IDE puisse administrer en sécurité."
                }
            ],
            "Brancardier": [
                {
                    "q": "6. [Module Brancardier] Le brancardier est invité à transporter un flacon de perfusion ou un produit sanguin labile (PSL) d'un service à un autre en urgence. Quelle est la règle HAS ?",
                    "options": [
                        "Accepter de transporter tout type de produit de santé sans condition de température ni de traçabilité.",
                        "Le transport des PSL et certains médicaments thermosensibles obéit à des règles strictes de chaîne du froid et de traçabilité inter-services avec des contenants agréés, hors des missions standard de brancardage non formées.",
                        "Se dépêcher pour que le transfert soit le plus court possible et que ça ne pose aucun soucis, même si un maintien au froid est nécessaire."
                    ],
                    "rep": "Le transport des PSL et certains médicaments thermosensibles obéit à des règles strictes de chaîne du froid et de traçabilité inter-services avec des contenants agréés, hors des missions standard de brancardage non formées."
                },
                {
                    "q": "7. [Module Brancardier] Un patient perfusé (soluté médicamenteux) doit être transporté en imagerie. La perfusion sonne (occlusion ou fin de flacon). Que fait le brancardier ?",
                    "options": [
                        "Arrête l'alarme.",
                        "Ne touche jamais aux réglages de la perfusion ou de la seringue électrique et alerte immédiatement l'IDE ou l'équipe médicale.",
                        "Clampe la tubulure définitivement pour stopper le débit pendant le trajet."
                    ],
                    "rep": "Ne touche jamais aux réglages de la perfusion ou de la seringue électrique et alerte immédiatement l'IDE ou l'équipe médicale."
                },
                {
                    "q": "8. [Module Brancardier] Lors du transport d'un patient sous traitement intraveineux multiple, la potence vacille. Quelle est la bonne conduite ?",
                    "options": [
                        "Continuer en courant pour arriver vite avant que ça ne tombe.",
                        "Sécuriser immédiatement le matériel, s'assurer de la stabilité du dispositif de perfusion sur le brancard avant de reprendre le déplacement.",
                        "Détacher les flacons et les porter à la main au-dessus du patient."
                    ],
                    "rep": "Sécuriser immédiatement le matériel, s'assurer de la stabilité du dispositif de perfusion sur le brancard avant de reprendre le déplacement."
                },
                {
                    "q": "9. [Module Brancardier] Le brancardier vient chercher un patient pour une radio. Le patient n'a pas de bracelet. Que fait le brancardier ?",
                    "options": [
                        "Emmène le patient quand même, le radiologue vérifiera.",
                        "Refuse le départ et demande à l'IDE de poser le bracelet d'identitovigilance conforme avant tout déplacement.",
                        "Demande au patient de décliner son nom et l'emmène s'il répond correctement."
                    ],
                    "rep": "Refuse le départ et demande à l'IDE de poser le bracelet d'identitovigilance conforme avant tout déplacement."
                },
                {
                    "q": "10. [Module Brancardier] Un brancardier transporte un patient porteur d'une bactérie multirésistante (BMR) vers une unité d'imagerie. Quelles sont les exigences de gestion du matériel à l'issue du transport selon les protocoles HAS de prévention des transmissions croisées ?",
                    "options": [
                        "Le patient étant simplement transporté assis sans contact direct prolongé avec le matelas, une simple aération de la civière de 15 minutes suffit avant le brancardage suivant.",
                        "Le brancardier réalise immédiatement la désinfection de contact des points de contact (barrières, poignées, matelas) avec le produit détergent-désinfectant homologué du circuit, conformément à la traçabilité des protocoles d'hygiène.",
                        "Le brancardier doit immédiatement isoler le brancard hors service pendant 1 heure en zone propre pour neutraliser par déperdition naturelle la charge bactérienne résiduelle, après l'avoir désinfecté."
                    ],
                    "rep": "Désinfection systématique des surfaces de contact du brancard avec un produit homologué entre chaque patient pour éviter toute transmission croisée."
                }
            ],
            "ASH": [
                {
                    "q": "6. [Module ASH] L'ASH trouve un flacon de chimiothérapie ou un résidu de médicament cytotoxique dans une poubelle de ménage (DAOM) d'un box. Quelle est la conduite à tenir ?",
                    "options": [
                        "Laisser le flacon dans la poubelle car c'est déjà jeté.",
                        "Alerter immédiatement l'équipe soignante et reconditionner le déchet dans la filière spécifique adaptée (filière DASRI / cytotoxiques) pour éviter un risque toxique et environnemental majeur.",
                        "Regarder si le flacon est vide ou non, et le vider dans le lavabo s'il en reste, pour pouvoir mettre le flacon dans la poubelle après."
                    ],
                    "rep": "Alerter immédiatement l'équipe soignante et reconditionner le déchet dans la filière spécifique adaptée (filière DASRI / cytotoxiques) pour éviter un risque toxique et environnemental majeur."
                },
                {
                    "q": "7. [Module ASH] Lors du bio-nettoyage du chariot de soins infirmiers, l'ASH déplace des boîtes de médicaments entamées. Quelle est la règle ?",
                    "options": [
                        "Ne jamais manipuler ou déplacer les produits de santé et médicaments posés sur les plans de travail mobiles sans l'accord et la présence de l'IDE.",
                        "Nettoyer autour des boites, pour ne pas déranger.",
                        "Ranger les boites dans le même ordre sur le plan de travail à côté, avant de les remettre à leur place ensuite."
                    ],
                    "rep": "Ne jamais manipuler ou déplacer les produits de santé et médicaments posés sur les plans de travail mobiles sans l'accord et la présence de l'IDE."
                },
                {
                    "q": "8. [Module ASH] L'ASH nettoie le sol d'un box et trouve un capuchon d'aiguille et une compresse souillée de sang séché. Que fait-elle vis-à-vis du risque iatrogène ?",
                    "options": [
                        "Ramasse à main nue, le sang étant sec.",
                        "Utilise des gants et signale le risque de matériel piquant/tranchant abandonné.",
                        "Le signale aux soignants pour qu'ils s'en chargent"
                    ],
                    "rep": "Utilise des gants et signale le risque de matériel piquant/tranchant abandonné."
                },
                {
                    "q": "9. [Module ASH] L'ASH transvase un produit de désinfection de surface dans une bouteille d'eau vide laissée dans un local de soins. Quel danger majeur la HAS pointe-t-elle ?",
                    "options": [
                        "Aucun, le flacon est propre.",
                        "Un risque d'erreur médicamenteuse ou d'ingestion accidentelle toxique gravissime par confusion avec une boisson (non-respect de l'interdiction de transvaser dans des contenants alimentaires).",
                        "Un risque mineur si l'étiquette de la bouteille est enlevée et que la mention 'Produit ménager' est inscrite sur le contenant."
                    ],
                    "rep": "Un risque d'erreur médicamenteuse ou d'ingestion accidentelle toxique gravissime par confusion avec une boisson (non-respect de l'interdiction de transvaser dans des contenants alimentaires)."
                },
                {
                    "q": "10. [Module ASH] Après avoir vidé les conteneurs DASRI des box d'urgence, l'ASH enchaîne avec le nettoyage d'un autre secteur sans friction. Quelle est la règle d'or ?",
                    "options": [
                        "La friction hydro-alcoolique est obligatoire après le retrait des gants et entre chaque manipulation à risque biologique.",
                        "Les gants étanches suffisent à protéger, sans hygiène des mains.",
                        "Se rincer les mains à l'eau froide suffit."
                    ],
                    "rep": "La friction hydro-alcoolique est obligatoire après le retrait des gants et entre chaque manipulation à risque biologique."
                }
            ],
            "Cadre": [
                {
                    "q": "6. [Module Cadre] Quelle est l'exigence majeure du Cadre de Santé concernant le contrôle des péremptions et de l'intégrité du chariot d'urgence ?",
                    "options": [
                        "Un contrôle visuel annuel par une équipe dédiée.",
                        "Une traçabilité rigoureuse, formalisée et hebdomadaire (ou selon protocole) des péremptions, de l'intégrité des scellés et de la conformité de la dotation en médicaments d'urgence.",
                        "Laisser chaque équipe vérifier si elle a le temps."
                    ],
                    "rep": "Une traçabilité rigoureuse, formalisée et hebdomadaire (ou selon protocole) des péremptions, de l'intégrité des scellés et de la conformité de la dotation en médicaments d'urgence."
                },
                {
                    "q": "7. [Module Cadre] Suite à un surdosage médicamenteux grave dans l'unité, quelle est la première action managériale attendue du Cadre selon la culture de sécurité HAS ?",
                    "options": [
                        "Identifier immédiatement le coupable pour engager une procédure disciplinaire exemplaire.",
                        "Sécuriser la situation immédiate, soutenir l'équipe, encourager la déclaration (CREX) et initier une analyse systémique des causes (sans rechercher de bouc émissaire).",
                        "Dissimuler l'incident dans le rapport mensuel pour préserver la réputation du service."
                    ],
                    "rep": "Sécuriser la situation immédiate, soutenir l'équipe, encourager la déclaration (CREX) et initier une analyse systémique des causes (sans rechercher de bouc émissaire)."
                },
                {
                    "q": "8. [Module Cadre] Le Cadre constate que le double contrôle des MHR (Médicaments à haut risque) n'est pas fait systématiquement par manque de temps. Quelle action corrective mène-t-il ?",
                    "options": [
                        "Supprime la règle du double contrôle pour fluidifier les passages aux urgences.",
                        "Analyse les freins organisationnels car ce double contrôle est non nagociable, puis met en place des rappels de procédures ou des binômes formels.",
                        "Fait un rappel à l'ordre sur le panneau d'affichage et lors des staff."
                    ],
                    "rep": "Analyse les freins organisationnels car ce double contrôle est non nagociable, puis met en place des rappels de procédures ou des binômes formels."
                },
                {
                    "q": "9. [Module Cadre] En cas de rupture de stock d'un soluté ou d'un antibiotique critique aux urgences, quel rôle joue le Cadre ?",
                    "options": [
                        "Demander aux soignants de voir avec d'autres unités si elles ont un stock",
                        "Coordonner la sécurisation d'une alternative validée avec la pharmacie (PUI), informer l'équipe médicale et afficher le protocole de remplacement temporaire.",
                        "Alerter la direction pour qu'il réarme le stock."
                    ],
                    "rep": "Coordonner la sécurisation d'une alternative validée avec la pharmacie (PUI), informer l'équipe médicale et afficher le protocole de remplacement temporaire."
                },
                {
                    "q": "10. [Module Cadre] Dans le cadre de la démarche qualité et de la préparation de la certification HAS concernant le circuit du médicament, quelle méthode de pilotage le cadre de santé doit-il privilégier pour l'évaluation des pratiques professionnelles (EPP) ?",
                    "options": [
                        "Rédiger de nouveaux protocoles papier exhaustifs affichés dans les couloirs.",
                        "Mettre en place des audits flash partagés (traçabilité des stups, conformité des réconciliations, analyse des FEI), ancrés dans le quotidien des 6 box par IDE, pour impliquer activement les équipes et repérer les écarts réels.",
                        "Déléguer la surveillance des pratiques à la pharmacie à usage interne (PUI)."
                    ],
                    "rep": "Mettre en place des audits flash partagés (traçabilité des stups, conformité des réconciliations, analyse des FEI), ancrés dans le quotidien des 6 box par IDE, pour impliquer activement les équipes et repérer les écarts réels."
                }
            ]
        },
        "fiches_reflexes": {
            "Tronc Commun": {
                "class": "memo-box-tc",
                "slug": "tronc_commun",
                "points": [
                    "**Identitovigilance & Dossier Unique** : Fusion immédiate et obligatoire des dossiers 'X' dès l'obtention de l'identité civile réelle afin de sécuriser le circuit du médicament et d'éviter les télescopages d'antécédents.",
                    "**Réconciliation Médicamenteuse** : Démarche indispensable amorcée dès l'accueil (recueil exhaustif des ordonnances de ville et des compléments) pour prévenir la iatrogénie médicamenteuse post-urgences chez les sujets vulnérables.",
                    "**Médicaments à Haut Risque (MHR)** : Application rigoureuse et non négociable du double contrôle soignant (visuel, qualitatif et quantitatif) avant toute administration, y compris lors des pics d'activité intense.",
                    "**Culture de Sécurité & Signalement** : Obligation de déclarer tout Événement Indésirable (EI) ou 'quasi-erreur' via le dispositif interne (FEI/ALARM) pour alimenter l'analyse systémique (CREX) sans recherche de culpabilité individuelle."
                ]
            },
            "IDE": {
                "class": "memo-box-ide",
                "slug": "ide",
                "points": [
                    "**Sécurité des Voies et des MHR** : Utilisation exclusive de voies veineuses dédiées ou centrales pour les amines/solutés à risque, avec tubulures sécurisées et traçabilité horodatée réelle sur le dossier patient.",
                    "**Gestion Stricte des Reliquats et Stupéfiants** : Interdiction absolue de conserver des seringues ou ampoules entamées pour un autre patient ; destruction et traçabilité conjointe immédiate dans le registre des stupéfiants.",
                    "**Formes Galéniques & SNG** : Interdiction formelle de broyer des gélules à libération prolongée ou des formes entériques sans validation pharmaceutique préalable pour écarter tout risque de surdosage pernicieux."
                ]
            },
            "AS": {
                "class": "memo-box-as",
                "slug": "as",
                "points": [
                    "**Prévention des Risques de Fausse Route** : Vigilance accrue lors de l'aide à l'hydratation ou à l'alimentation concomitante aux prises médicamenteuses, en respectant impérativement une position assise ou semi-assise sécurisée.",
                    "**Interdiction de Dispensation** : Refus systématique de transporter, manipuler ou distribuer des traitements médicamenteux d'un box à un autre (le circuit du médicament relève exclusivement des professionnels habilités).",
                    "**Sécurité Environnementale** : Élimination immédiate des objets piquants/tranchants trouvés dans les box dans les conteneurs rigides OPCT sans jamais tenter de les recapuchonner."
                ]
            },
            "Medecin": {
                "class": "memo-box-med",
                "slug": "medecin",
                "points": [
                    "**Maîtrise des Alertes Logicielles** : Interdiction de contourner par automatisme les alertes d'interactions médicamenteuses majeures émises par le DPI ; toute validation outrepassée requiert une justification clinique tracée.",
                    "**Sécurisation des Sorties et Réconciliation** : Obligation de vérifier et de réconcilier les ordonnances de ville à l'admission et à la sortie pour éviter les redondances thérapeutiques ou l'arrêt brutal de traitements au long cours.",
                    "**Traçabilité des Prescriptions Verbales** : Régularisation écrite et signature obligatoire de toute prescription verbale d'urgence dès que la situation critique immédiate est stabilisée."
                ]
            },
            "ARM (Assistant/e de Régulation Médicale)": {
                "class": "memo-box-arm",
                "slug": "ARM (Assistant/e de Régulation Médicale)",
                "points": [
                    "**Filtrage et Sécurité Toxicologique** : Refus absolu de délivrer des conseils d'inadmentation ou de vomissement par téléphone ; transfert immédiat des appels d'intoxication ou de posologies au Medecin régulateur ou au Centre Antipoison.",
                    "**Transmission Ciblée au SMUR** : Restitution systématique et immédiate des antécédents médicamenteux connus aux équipes préhospitalières engagées pour sécuriser l'intervention d'urgence."
                ]
            },
            "Accueil & Admission": {
                "class": "memo-box-acc",
                "slug": "accueil",
                "points": [
                    "**Recensement des Traitements Personnels** : Identification et mise en sécurité rigoureuse des sacs de médicaments de ville ou des traitements onéreux apportés par le patient (via la mise en coffre ou le circuit pharmaceutique dédié).",
                    "**Vigilance Identitovigilance** : Garantie du triptyque d'identité lors des admissions (même en mode dégradé papier) pour empêcher toute confusion de dossier source d'erreurs thérapeutiques en amont des soins."
                ]
            },
            "Brancardier": {
                "class": "memo-box-branc",
                "slug": "brancardier",
                "points": [
                    "**Intégrité des Dispositifs de Perfusion** : Interdiction absolue d'intervenir sur les débits, les pompes ou les seringues électriques durant les transferts intra-hospitaliers ; alerte immédiate de l'équipe soignante en cas de signal sonore.",
                    "**Contrôle du Bracelet d'Identité** : Exigence de la présence du bracelet d'identitovigilance conforme avant tout départ en imagerie ou vers un secteur d'aval."
                ]
            },
            "ASH": {
                "class": "memo-box-ash",
                "slug": "ash",
                "points": [
                    "**Respect Strict des Filières de Déchets** : Isolement immédiat des déchets de type cytotoxique ou DASRI égarés dans les poubelles banales et alerte de l'équipe soignante pour écarter tout risque toxique ou environnemental.",
                    "**Interdiction de Manipulation** : Proscription absolue de manipuler, déplacer ou nettoyer les plans de travail mobiles et les chariots de soins infirmiers en l'absence des soignants.",
                    "**Filières de Déchets & Risques** : Respect strict des filières DASRI/cytotoxiques, interdiction absolue de manipuler les chariots de soins ou de transvaser des produits."
                ]
            },
            "Cadre de Santé": {
                "class": "memo-box-cadre",
                "slug": "cadre",
                "points": [
                    "**Gouvernance et Audits Flash** : Planification et réalisation d'audits réguliers portant sur la péremptions du chariot d'urgence, la traçabilité des stupéfiants et la conformité des dossiers de soins de crise.",
                    "**Management Non-Punitif** : Animation des retours d'expérience (CREX) suite à un incident médicamenteux pour transformer l'erreur humaine en opportunité d'amélioration organisationnelle durable.",
                    "**Management de la Sécurité** : Contrôle hebdomadaire des chariots d'urgence, gestion non punitive des EIGS et animation des audits flash HAS."
               ]
            }
        }
    },
        {
        "id": 4,
        "titre": "Semaine 4 - Parcours patient, Fluidité & Sujets vulnérables",
        "date_debut": datetime.date(2026, 11, 16),
        "date_fin": datetime.date(2026, 11, 22),
        "tronc_commun": [
            {
                "id": "TC1",
                "q": "Lors de l'admission d'une personne âgée vulnérable en situation de perte d'autonomie majeure ou de dénutrition, quel est le premier réflexe exigé par les critères HAS de repérage des vulnérabilités aux urgences ?",
                "options": [
                    "Reporter l'évaluation gérontologique à la sortie des urgences : pour l'instant, la somatique aiguë compte.",
                    "Demander un transfert direct en USLD.",
                    "Formaliser dès l'admission le repérage des risques (escarres, chutes, dénutrition, troubles cognitifs) et l'initier dans le dossier patient informatisé (DPI)."
                ],
                "rep": "Formaliser dès l'admission le repérage des risques (escarres, chutes, dénutrition, troubles cognitifs) et l'initier dans le dossier patient informatisé (DPI)."
            },
            {
                "id": "TC2",
                "q": "En période de tension sur les capacités d'aval, quel indicateur HAS permet de piloter la sécurité des soins des patients en attente prolongée dans la structure ?",
                "options": [
                    "Le temps d'attente au guichet administratif avant la prise de constantes.",
                    "Le temps de passage aux urgences (TPU) et la traçabilité des re-titrations/surveillances des patients en 'brancard couloir' ou UHCD.",
                    "Le nombre de dossiers papier classés en fin de vacation."
                ],
                "rep": "Le temps de passage aux urgences (TPU) et la traçabilité des re-titrations/surveillances des patients en 'brancard couloir' ou UHCD."
            },
            {
                "id": "TC3",
                "q": "Face à un patient vulnérable présentant des signes d'alerte évoquant une maltraitance (lésions atypiques, discours discordant de l'entourage), quelle est la procédure HAS à enclencher ?",
                "options": [
                    "Demander des explications à l'accompagnant.",
                    "Tracer les constatations factuelles dans le DPI, alerter le Medecin sénior de zone et déclencher la filière de signalement (fiche FEI / assistance sociale / cadre).",
                    "Hospitaliser obligatoirement le patient afin que le service se charge de la mise en place de protection pour la personne vulnérable."
                ],
                "rep": "Tracer les constatations factuelles dans le DPI, alerter le Medecin sénior de zone et déclencher la filière de signalement (fiche FEI / assistance sociale / cadre)."
            },
            {
                "id": "TC4",
                "q": "Qu'implique la conciliation médicamenteuse d'admission pour une personne âgée polypathologique transférée d'EHPAD ?",
                "options": [
                    "Réaliser le bilan comparatif entre l'ordonnance de l'EHPAD et les prescriptions d'urgence pour prévenir la iatrogénie et tracer les arrêts/poursuites.",
                    "Stopper tous les traitements habituels par précaution pendant 24 heures.",
                    "Reconduire l'ordonnance d'entrée sans réévaluer la fonction rénale ni l'état aigu."
                ],
                "rep": "Réaliser le bilan comparatif entre l'ordonnance de l'EHPAD et les prescriptions d'urgence pour prévenir la iatrogénie et tracer les arrêts/poursuites."
            },
            {
                "id": "TC5",
                "q": "Comment la HAS préconise-t-elle d'évaluer la douleur chez un patient vulnérable non communicant (troubles cognitifs sévères, coma, aphasie) ?",
                "options": [
                    "Conclure à l'absence de douleur si le patient ne verbalise aucune plainte.",
                    "Administrer d'emblée une dose maximale de morphine sans observation préalable.",
                    "Utiliser une échelle d'hétéro-évaluation comportementale validée (ex: Algoplus/Doloplus) et tracer la réévaluation après antalgie."
                ],
                "rep": "Utiliser une échelle d'hétéro-évaluation comportementale validée (ex: Algoplus/Doloplus) et tracer la réévaluation après antalgie."
            }
        ],
        "metiers": {
            "IDE": [
                {
                    "id": "IDE1",
                    "q": "Dans votre zone de box au circuit Long, un patient vulnérable et désorienté présente un risque élevé de chute et de déambulation. Quelle est la conduite appropriée ?",
                    "options": [
                        "Verrouiller la porte du box à clé de l'extérieur pour poursuivre vos soins dans les autres box.",
                        "Adapter l'environnement (barrières, sonnette à portée, rapprochement du poste si possible), tracer le risque et coordonner la surveillance avec l'AS de la zone.",
                        "Attacher le patient aux quatre membres puis aller avoir le Medecin pour le signaler et avoir la prescription."
                    ],
                    "rep": "Adapter l'environnement (barrières, sonnette à portée, rapprochement du poste si possible), tracer le risque et coordonner la surveillance avec l'AS de la zone."
                },
                {
                    "id": "IDE2",
                    "q": "Vous devez administrer un traitement IV à haut risque chez un patient vulnérable sous tutelle. Le tuteur est joignable mais pas sur place. Que devez-vous vérifier ?",
                    "options": [
                        "Vérifier la prescription médicale validée dans le DPI, l'identité du patient (identitovigilance) et tracer l'administration en informant la personne de confiance/tuteur selon le degré d'urgence.",
                        "Attendre le déplacement physique du tuteur avant d'injecter, quelle que soit l'urgence thérapeutique.",
                        "Faire signer un accord à l'ambulancier qui a transporté le patient."
                    ],
                    "rep": "Vérifier la prescription médicale validée dans le DPI, l'identité du patient (identitovigilance) et tracer l'administration en informant la personne de confiance/tuteur selon le degré d'urgence."
                },
                {
                    "id": "IDE3",
                    "q": "Un patient très âgé en brancard de couloir attend un lit d'aval depuis 8 heures dans votre zone. Quelle surveillance IDE est indispensable pour la certification ?",
                    "options": [
                        "Seuls les paramètres vitaux matin/midi/soir doivent être tracés, ainsi que les repas donnés.",
                        "Etat cutané (prévention escarres), hydratation/miction, paramètres vitaux, douleur et tolérance de l'attente.",
                        "Passer s'assurer que le patient va bien et lui demander s'il a besoin de quelques chose suffit."
                    ],
                    "rep": "Etat cutané (prévention escarres), hydratation/miction, paramètres vitaux, douleur et tolérance de l'attente."
                },
                {
                    "id": "IDE4",
                    "q": "Lors de la relève inter-équipe dans votre zone en Long, quelle information est prioritaire pour un patient vulnérable ?",
                    "options": [
                        "Pas plus d'informations que les autres : la place de son brancard, son histoire et les médicaments donnés.",
                        "La couleur des vêtements du patient, au cas où il s'enfuit.",
                        "La transmission ciblée précisant l'autonomie, les risques identifiés (fausse route, fuite, escarre), les réévaluations médicamenteuses et le statut du lit d'aval."
                    ],
                    "rep": "La transmission ciblée précisant l'autonomie, les risques identifiés (fausse route, fuite, escarre), les réévaluations médicamenteuses et le statut du lit d'aval."
                },
                {
                    "id": "IDE5",
                    "q": "Face à une suspicion d'erreur de dosage médicamenteux chez un patient fragile transféré d'une autre structure, quelle est l'action IDE immédiate ?",
                    "options": [
                        "Corriger la dose dans le DPI, puisque ça n'a pas eu de conséquence.",
                        "Attendre la fin du poste pour voir si des effets secondaires apparaissent.",
                        "Suspendre l'administration, alerter immédiatement le Medecin de la zone et déclarer l'événement indésirable (FEI)."
                    ],
                    "rep": "Suspendre l'administration, alerter immédiatement le Medecin de la zone et déclarer l'événement indésirable (FEI)."
                }
            ],
            "Medecin": [
                {
                    "id": "MED1",
                    "q": "En tant que Medecin référent de vos 2 zones du Long, vous devez prescrire une contention physique pour un patient dément en agitation sévère mettant en danger ses soins vitaux. Quelle règle appliquez-vous ?",
                    "options": [
                        "Donner une consigne orale à l'équipe et leur demander de réévaluer dans quelques heures.",
                        "Rédiger une prescription médicale écrite, datée, limitée dans le temps, motivée au regard de la balance bénéfice/risque et assortie d'une surveillance tracée.",
                        "Demander à l'équipe d'accueil d'appeler la police pour gérer l'agitation."
                    ],
                    "rep": "Rédiger une prescription médicale écrite, datée, limitée dans le temps, motivée au regard de la balance bénéfice/risque et assortie d'une surveillance tracée."
                },
                {
                    "id": "MED2",
                    "q": "Lors de la sortie ou du transfert d'un patient fragile aux antécédents complexes, quel document médical garantit la continuité de la prise en charge selon la HAS ?",
                    "options": [
                        "La lettre de liaison de sortie (ou résumé d'urgence) validée et transmise le jour même, incluant le traitement d'entrée/sortie et les consignes de suivi.",
                        "Une simple consigne orale donnée au brancardier lors du départ.",
                        "Un mot manuscrit succinct sur un morceau de papier déposé dans la poche du patient."
                    ],
                    "rep": "La lettre de liaison de sortie (ou résumé d'urgence) validée et transmise le jour même, incluant le traitement d'entrée/sortie et les consignes de suivi."
                },
                {
                    "id": "MED3",
                    "q": "Comment adapter la prescription médicamenteuse chez un sujet très âgé en insuffisance rénale aiguë admis dans l'une de vos zones ?",
                    "options": [
                        "Se fier seulement au DFG pour qualifier l'IRA et arrêter les traitements néphrotoxiques.",
                        "Consulter la créatinine habituelle pour valider la réelle présence d'une IRA, réévaluer les rapports bénéfice/risque des molécules néphrotoxiques et expliciter l'adaptation posologique dans le DPI.",
                        "Maintenir les posologies habituelles du VIDAL."
                    ],
                    "rep": "Consulter la créatinine habituelle pour valider la réelle présence d'une IRA, réévaluer les rapports bénéfice/risque des molécules néphrotoxiques et expliciter l'adaptation posologique dans le DPI."
                },
                {
                    "id": "MED4",
                    "q": "En situation d'engorgement majeur des 2 zones du Long avec attente prolongée de lits d'aval, quel est le rôle du Medecin sénior de zone ?",
                    "options": [
                        "Effectuer des réévaluations cliniques régulières des patients en attente, réajuster les prescriptions et signaler le niveau d'engorgement à la régulation/cadre (le protocole HET du service est tout en bas du meuble où sont les prescriptions bio/EFS etc).",
                        "Fermer et quitter le service. Y'en a marre à la fin.",
                        "Valider des sorties et transferts prématurés pour vider les box."
                    ],
                    "rep": "Effectuer des réévaluations cliniques régulières des patients en attente, réajuster les prescriptions et signaler le niveau d'engorgement à la régulation/cadre (le protocole HET du service est tout en bas du meuble où sont les prescriptions bio/EFS etc)."
                },
                {
                    "id": "MED5",
                    "q": "Prise en charge d'un patient vulnérable sans personne de confiance identifiée nécessitant une décision médicale lourde non urgente. Quelle est la démarche réglementaire ?",
                    "options": [
                        "Décider seul dans son coin sans en parler à quiconque.",
                        "Appeler la famille pour demander leur avis, qui prévaudra.",
                        "Rechercher l'existence de directives anticipées, solliciter les aidants/tuteur et formaliser une procédure collégiale tracée dans le dossier."
                    ],
                    "rep": "Rechercher l'existence de directives anticipées, solliciter les aidants/tuteur et formaliser une procédure collégiale tracée dans le dossier."
                }
            ],
            "AS": [
                {
                    "id": "AS1",
                    "q": "Vous installez une personne âgée dénutrie et dépendante dans un box de votre zone. Quel soin de prévention mettez-vous en place d'emblée ?",
                    "options": [
                        "Laisser le patient sur le brancard sans changer sa position pendant 6 heures.",
                        "Mettre en place les supports anti-escarres adaptés, veiller au positionnement (décharge des points d'appui) et signaler l'état cutané initial à l'IDE.",
                        "Mettre un plateau repas à côté."
                    ],
                    "rep": "Mettre en place les supports anti-escarres adaptés, veiller au positionnement (décharge des points d'appui) et signaler l'état cutané initial à l'IDE."
                },
                {
                    "id": "AS2",
                    "q": "Lors de la distribution des repas/collations dans les box de la zone, un patient vulnérable présente des troubles de la déglutition identifiés. Que faites-vous ?",
                    "options": [
                        "Vérifier la texture prescrite (haché/mixé, eau gélifiée), assister l'installation à 90°, surveiller le repas et transmettre l'ingestion à l'IDE.",
                        "Poser le plateau standard et demander à l'accompagnant de signaler s'il y a une fausse route.",
                        "Ne rien donner au patient, par précaution, et proposer une pose d'hydratation IV ou sous-cutanée."
                    ],
                    "rep": "Vérifier la texture prescrite (haché/mixé, eau gélifiée), assister l'installation à 90°, surveiller le repas et transmettre l'ingestion à l'IDE."
                },
                {
                    "id": "AS3",
                    "q": "Un patient vulnérable et confus tente de se lever seul de sa chaise au risque de tomber. Quelle est la réaction à avoir selon la HAS ?",
                    "options": [
                        "Le réinstaller, évaluer son besoin immédiat (miction, soif, douleur), solliciter l'IDE et rester à ses côtés pour assurer une présence rassurante.",
                        "Le rappeler à l'ordre avec fermeté et le sécuriser avec un drap au niveau de la taille.",
                        "Ignorer la situation tant que le patient n'est pas tombé par terre : y'a pas le temps dans ce service..."
                    ],
                    "rep": "Le réinstaller, évaluer son besoin immédiat (miction, soif, douleur), solliciter l'IDE et rester à ses côtés pour assurer une présence rassurante."
                },
                {
                    "id": "AS4",
                    "q": "Vous observez une rougeur sacrée fixée (érythème ne s'effaçant pas à la pression) lors du change d'un patient vulnérable. Que faites-vous ?",
                    "options": [
                        "Appliquer une crème type Bepanthen.",
                        "Alerter l'IDE de la zone pour évaluation/transmission, consigner le constat dans le dossier de soins et adapter le positionnement.",
                        "Mettre un pansement."
                    ],
                    "rep": "Alerter l'IDE de la zone pour évaluation/transmission, consigner le constat dans le dossier de soins et adapter le positionnement."
                },
                {
                    "id": "AS5",
                    "q": "Comment préserver la dignité d'un patient vulnérable lors des soins d'hygiène ou d'installation en zone de soins très fréquentée ?",
                    "options": [
                        "Laisser la porte du box ouverte sur le couloir pour maintenir la sécurité de chacun.",
                        "Parler entre les soignants pendant le change, comme si le patient ne comprenait pas ce qui se disait.",
                        "Utiliser systématiquement les paravents/fermetures de box, couvrir le patient et s'adresser directement à lui avec bienveillance."
                    ],
                    "rep": "Utiliser systématiquement les paravents/fermetures de box, couvrir le patient et s'adresser directement à lui avec bienveillance."
                }
            ],
            "ARM (Assistant/e de Régulation Médicale)": [
                {
                    "id": "ARM1",
                    "q": "Un appel concerne un sujet très âgé vivant seul, en rupture de contacts depuis 48h, signalé par un voisin. Selon la HAS, comment l'ARM doit-il qualifier cette vulnérabilité ?",
                    "options": [
                        "Classer l'appel en démarche sociale non urgente.",
                        "Évaluer le risque d'isolement/détresse potentielle, rechercher des signes d'urgence vitale/traumatique et transmettre immédiatement au MRU pour décision.",
                        "Demander au voisin de trouver un moyen d'ouvrir la porte avant de rappeler s'il n'y parvient pas."
                    ],
                    "rep": "Évaluer le risque d'isolement/détresse potentielle, rechercher des signes d'urgence vitale/traumatique et transmettre immédiatement au MRU pour décision."
                },
                {
                    "id": "ARM2",
                    "q": "Lors du décrochage pour une personne vulnérable désorientée en ligne, quelle est la priorité de l'ARM pour sécuriser le parcours ?",
                    "options": [
                        "Localiser précisément le lieu, garder le contact pour rassurer, identifier l'entourage et transmettre les éléments clés au MRU.",
                        "Couper la communication dès que le Medecin régulateur prend la main sans rien noter.",
                        "Recommander au patient de prendre un somnifère pour se calmer."
                    ],
                    "rep": "Localiser précisément le lieu, garder le contact pour rassurer, identifier l'entourage et transmettre les éléments clés au MRU."
                },
                {
                    "id": "ARM3",
                    "q": "L'ARM reçoit un appel d'un EHPAD pour une décompensation aiguë chez un patient vulnérable possédant des directives anticipées d'arrêt de soins. Un état gravissime semble être présent à l'appel. Que fait l'ARM ?",
                    "options": [
                        "Refuser d'envoyer tout secours, et dire à l'appelant de voir avec le Medecin coordonateur ou la HAD.",
                        "Envoyer le SMUR en P0 puis en informer le MRU.",
                        "Noter la présence des directives anticipées et passer l'appel en priorité au MRU."
                    ],
                    "rep": "Noter la présence des directives anticipées et passer l'appel en priorité au MRU."
                },
                {
                    "id": "ARM4",
                    "q": "Comment l'ARM traite-t-il une alerte de maltraitance à domicile formulée par une aide ménagère au téléphone ?",
                    "options": [
                        "Passer l'appel au 17 si aucun motif de détresse médicale immédiate n'est présent.",
                        "Recueillir les déclarations, consigner dans le DRM et alerter le MRU.",
                        "Rappeler la famille pour enquêter."
                    ],
                    "rep": "Recueillir les déclarations, consigner dans le DRM et alerter le MRU."
                },
                {
                    "id": "ARM5",
                    "q": "Dans la chaîne de transmission, qui est le SEUL interlocuteur habilité à transmettre une consigne médicale ou un antécédent lourd à l'équipe SMUR engagée ?",
                    "options": [
                        "Le MRU, l'ARM assurant le lien logistique et la qualification de l'appel.",
                        "L'ARM en direct dès qu'il a l'information.",
                        "L'ARM superviseur."
                    ],
                    "rep": "Le MRU, l'ARM assurant le lien logistique et la qualification de l'appel."
                }
            ],
            "Accueil": [
                {
                    "id": "ACC1",
                    "q": "Une personne âgée désorientée sans identité arrive seule à l'accueil. Quelle est la prise en charge immédiate par l'agent d'accueil ?",
                    "options": [
                        "Refuser l'accès tant qu'un accompagnant n'est pas présent avec la carte vitale.",
                        "Mettre la personne en sécurité dans l'espace d'attente visible, déclencher le repérage IOA/IDE de tri en priorité et créer un dossier provisoire sécurisé.",
                        "L'envoyer attendre dehors sur un des cailloux qui servent de banc : le froid, c'est revigorant !"
                    ],
                    "rep": "Mettre la personne en sécurité dans l'espace d'attente visible, déclencher le repérage IOA/IDE de tri en priorité et créer un dossier provisoire sécurisé."
                },
                {
                    "id": "ACC2",
                    "q": "Un proche inquiet se présente au guichet pour connaître la prescription médicale d'un patient vulnérable installé en zone de soins. Que fait l'agent d'accueil ?",
                    "options": [
                        "Orienter le proche ou transférer la demande vers l'IDE/Medecin de la zone concernée, en rappelant qu'aucune donnée thérapeutique n'est délivrée au guichet.",
                        "Lire la liste des médicaments affichée sur l'écran d'accueil.",
                        "Donner une réponse vague mais rassurante pour éviter que le proche ne pose de questions."
                    ],
                    "rep": "Orienter le proche ou transférer la demande vers l'IDE/Medecin de la zone concernée, en rappelant qu'aucune donnée thérapeutique n'est délivrée au guichet."
                },
                {
                    "id": "ACC3",
                    "q": "Comment l'agent d'accueil gère-t-il les effets personnels et objets de valeur d'un patient inconscient, ramenés plus tard par les pompiers car ils avaient été 'oubliés sur place' ?",
                    "options": [
                        "Appliquer la procédure de dépôt (inventaire contradictoire avec un soignant/agent, traçabilité et mise en coffre ou remise sécurisée).",
                        "Les laisser dans un sac plastique sur le comptoir.",
                        "Les donner au premier visiteur se réclamant de la famille."
                    ],
                    "rep": "Appliquer la procédure de dépôt (inventaire contradictoire avec un soignant/agent, traçabilité et mise en coffre ou remise sécurisée)."
                },
                {
                    "id": "ACC4",
                    "q": "Un patient vulnérable en salle d'attente exprime une aggravation de son inconfort (douleur, difficulté respiratoire). Que fait l'agent d'accueil ?",
                    "options": [
                        "Lui dire de patienter gentiment, et que son tour arrive.",
                        "Alerter l'IOA pour une réévaluation clinique.",
                        "Lui proposer un antalgique."
                    ],
                    "rep": "Alerter l'IOA pour une réévaluation clinique."
                },
                {
                    "id": "ACC5",
                    "q": "Face à la frustration d'une famille accompagnant un patient âgé vulnérable en attente de lit d'aval, quelle est la posture de l'agent d'accueil ?",
                    "options": [
                        "Expliquer que l'hôpital est en tension ces derniers temps et que venir faire part de son mécontentement ne changera rien.",
                        "Ignorer la famille en fermant le hygiaphone.",
                        "Réexpliquer avec empathie les étapes du parcours, le rôle de la régulation des lits et faire le lien avec l'équipe soignante de la zone."
                    ],
                    "rep": "Réexpliquer avec empathie les étapes du parcours, le rôle de la régulation des lits et faire le lien avec l'équipe soignante de la zone."
                }
            ],
            "Brancardier": [
                {
                    "id": "BRAN1",
                    "q": "Vous devez brancarder un patient très âgé, algique et anxieux vers le service de radiologie. Quelle précaution prenez-vous ?",
                    "options": [
                        "Transporter le patient rapidement pour gagner du temps.",
                        "Présenter le soin, vérifier l'installation (couverture, barrières de sécurité, cales), manipuler avec douceur et rassurer durant le trajet.",
                        "Proposer au patient de marcher si le brancard est inconfortable à ce point."
                    ],
                    "rep": "Présenter le soin, vérifier l'installation (couverture, barrières de sécurité, cales), manipuler avec douceur et rassurer durant le trajet."
                },
                {
                    "id": "BRAN2",
                    "q": "Transport d'un patient vulnérable sous O2 : quelle est la règle d'or de sécurité du brancardier ?",
                    "options": [
                        "Poser la bouteille d'oxygène entre les jambes du patient sur le brancard.",
                        "Couper l'oxygène pendant le transport.",
                        "Vérifier la charge de la bouteille avant le départ, la fixer sur le support homologué et s'assurer que le débit prescrit est actif."
                    ],
                    "rep": "Vérifier la charge de la bouteille avant le départ, la fixer sur le support homologué et s'assurer que le débit prescrit est actif."
                },
                {
                    "id": "BRAN3",
                    "q": "Durant le transfert d'un patient vulnérable, celui-ci présente un malaise avec altération de la conscience. Quelle est votre réaction ?",
                    "options": [
                        "Stopper immédiatement le brancard en zone sécurisée, appeler au secours l'équipe soignante la plus prochaine et rester auprès du patient.",
                        "Continuer le trajet jusqu'à destination en espérant que le service d'arrivée s'en occupe.",
                        "Le secouer énergiquement pour le faire réagir."
                    ],
                    "rep": "Stopper immédiatement le brancard en zone sécurisée, appeler au secours l'équipe soignante la plus prochaine et rester auprès du patient."
                },
                {
                    "id": "BRAN4",
                    "q": "Après avoir transporté un patient porteur d'une BMR ou en isolement protecteur, que faites-vous du brancard ?",
                    "options": [
                        "Le réutiliser immédiatement pour un autre patient vulnérable du couloir.",
                        "Le laisser dehors au soleil pendant quelques minutes.",
                        "Effectuer le bionettoyage/désinfection de contact des points d'appui avec le produit détergent-désinfectant homologué du service."
                    ],
                    "rep": "Effectuer le bionettoyage/désinfection de contact des points d'appui avec le produit détergent-désinfectant homologué du service."
                },
                {
                    "id": "BRAN5",
                    "q": "Comment le brancardier participe-t-il à la fluidité du circuit des urgences ?",
                    "options": [
                        "En informant l'IDE de zone dès que le transfert en service d'aval est effectif pour libérer le box au plus vite.",
                        "En décidant de l'ordre de passage des patients en radiologie.",
                        "En poussant vite les brancards dans les couloirs."
                    ],
                    "rep": "En informant l'IDE de zone dès que le transfert en service d'aval est effectif pour libérer le box au plus vite."
                }
            ],
            "Cadre": [
                {
                    "id": "CAD1",
                    "q": "Dans le cadre de la certification HAS 2027, comment le cadre de santé évalue-t-il la qualité de la prise en charge des publics vulnérables dans son unité ?",
                    "options": [
                        "En se fiant aux impressions orales lors des pauses café.",
                        "En réalisant des EPP et audits ciblés (traçabilité des repérages, audits de dossiers 'patient traceur', suivi des FEI) associés à des restitutions d'équipe.",
                        "En questionnant certains patients au quotidien."
                    ],
                    "rep": "En réalisant des EPP et audits ciblés (traçabilité des repérages, audits de dossiers 'patient traceur', suivi des FEI) associés à des restitutions d'équipe."
                },
                {
                    "id": "CAD2",
                    "q": "Tension majeure sur les lits d'aval et accumulation de patients vulnérables en brancard de couloir. Quelle est l'action prioritaire du cadre ?",
                    "options": [
                        "Déclencher et piloter la cellule de crise/gestion des lits, coordonner avec la direction des soins et réallouer les ressources pour sécuriser les zones saturées.",
                        "Aller voir les équipes pour leur demander d'augmenter la fluidité.",
                        "Aller chercher de nouveaux brancards, consigner la tension dans le cahier de garde et souhaiter bon courage aux équipes soignantes."
                    ],
                    "rep": "Déclencher et piloter la cellule de crise/gestion des lits, coordonner avec la direction des soins et réallouer les ressources pour sécuriser les zones saturées."
                },
                {
                    "id": "CAD3",
                    "q": "Un événement indésirable grave (EIG) survient chez un patient vulnérable (chute avec fracture sous contention non tracée). Que fait le cadre ?",
                    "options": [
                        "Modifier a posteriori le dossier de soins pour faire disparaître l'absence de prescription.",
                        "Rejeter la faute exclusive sur l'élève aide-soignant présent.",
                        "Organiser une RMM (Revue de Maîtrise des Risques / Mortalité-Morbide), déclarer l'EIG sur le portail dédié et mettre en place un plan d'action correctif avec l'équipe."
                    ],
                    "rep": "Organiser une RMM (Revue de Maîtrise des Risques / Mortalité-Morbide), déclarer l'EIG sur le portail dédié et mettre en place un plan d'action correctif avec l'équipe."
                },
                {
                    "id": "CAD4",
                    "q": "Comment le cadre garantit-il l'appropriation par l'équipe des protocoles de bientraitance et de repérage des maltraitances chez les sujets fragiles ?",
                    "options": [
                        "En intégrant des temps d'échange réguliers (briefings, réunions d'unité), en formant les agents et en facilitant l'accès aux fiches réflexes.",
                        "En envoyant un mail avec les protocoles en pièce-jointe.",
                        "En considérant que la formation initiale à l'école suffit pour toute la carrière."
                    ],
                    "rep": "En intégrant des temps d'échange réguliers (briefings, réunions d'unité), en formant les agents et en facilitant l'accès aux fiches réflexes."
                },
                {
                    "id": "CAD5",
                    "q": "Quel rôle joue le cadre dans le respect de l'organisation structurée du service ?",
                    "options": [
                        "Modifier les zones tous les jours sans concertation.",
                        "Veiller au respect de la sectorisation pour garantir la clarté des rôles, la traçabilité des soins et la sécurité des transmissions inter-métiers.",
                        "Supprimer les zones pour créer un espace unique sans référent soignant."
                    ],
                    "rep": "Veiller au respect de la sectorisation pour garantir la clarté des rôles, la traçabilité des soins et la sécurité des transmissions inter-métiers."
                }
            ]
        },
        "fiches_reflexes": {
            "IDE": {
                "class": "Mémo Box IDE - Parcours & Vulnérabilités (Semaine 4)",
                "slug": "ide",
                "points": [
                    "Sectorisation stricte : responsabilité directe de la gestion des soins et des risques sur sa zone de 6 box.",
                    "Repérage et traçabilité : cotation systématique des risques de vulnérabilité (chutes, escarres, dénutrition, troubles cognitifs) dès l'admission dans le DPI.",
                    "Surveillance des temps d'attente : traçabilité renforcée des patients en attente prolongée ou en brancard de couloir (hydratation, confort, réévaluations).",
                    "Sécurité des transmissions : relèves ciblées axées sur l'autonomie, les alertes thérapeutiques et le statut des lits d'aval."
                ]
            },
            "Medecin": {
                "class": "Mémo Box Medecin - Parcours & Vulnérabilités (Semaine 4)",
                "slug": "medecin",
                "points": [
                    "Pilotage sectoriel : responsabilité clinique de l'ensemble des 2 zones rattachées (gestion globale des flux et des priorités médicales).",
                    "Sécurisation thérapeutique : adaptation stricte des posologies aux fonctions d'élimination (DFG) chez le sujet âgé et traçabilité des conciliations médicamenteuses.",
                    "Cadre réglementaire des décisions lourdes : protocoles stricts de contention physique (prescription écrite, limitée, réévaluée) et recherche des directives anticipées.",
                    "Continuité des soins d'aval : validation systématique et transmission immédiate de la lettre de liaison de sortie pour garantir la fluidité du parcours patient."
                ]
            },
            "AS": {
                "class": "Mémo Box AS - Parcours & Vulnérabilités (Semaine 4)",
                "slug": "as",
                "points": [
                    "Prévention active : installation immédiate des supports anti-escarres et respect des postures de décharge pour les patients dépendants ou grabataires.",
                    "Sécurité alimentaire & hydrique : surveillance des apports, adaptation des textures (mixé, eau gélifiée) et prévention des fausses routes lors des repas en zone de soins.",
                    "Veille comportementale : repérage et signalement immédiat à l'IDE de tout changement d'état cutané, de conscience ou d'agitation à risque de chute.",
                    "Préservation de la dignité : utilisation systématique des paravents et respect de l'intimité malgré la forte affluence et la configuration ouverte des urgences."
                ]
            },
            "ARM (Assistant/e de Régulation Médicale)": {
                "class": "Mémo Box ARM - Régulation & Vulnérabilités (Semaine 4)",
                "slug": "arm",
                "points": [
                    "Qualification ciblée : repérage immédiat des situations d'isolement, de perte de contact ou de fragilité gérontologique dès le premier décroché au 15.",
                    "Traçabilité amont : consignation rigoureuse des antécédents lourds, des traitements et des statuts éthiques (directives anticipées) dans le DRM.",
                    "Interface sécurisée : transmission exclusive des éléments cliniques et logistiques au Medecin Régulateur des Urgences (MRU) pour arbitrage et engagement des secours adaptés.",
                    "Gestion des signalements : application stricte des consignes d'alerte en cas de suspicion de maltraitance transmise par un tiers."
                ]
            },
            "Accueil": {
                "class": "Mémo Box Accueil - Guichet & Vulnérabilités (Semaine 4)",
                "slug": "accueil",
                "points": [
                    "Accueil sécurisé 24h/24 : prise en charge immédiate et mise en sécurité des patients vulnérables isolés ou confus se présentant au comptoir.",
                    "Barrière du secret professionnel : interdiction absolue de divulguer des informations thérapeutiques au guichet ; orientation systématique vers l'IDE ou l'équipe médicale de la zone.",
                    "Gestion rigoureuse des valeurs : application stricte des procédures d'inventaire contradictoire et de mise en coffre des effets personnels des patients non conscients.",
                    "Veille visuale continue : repérage des signes d'aggravation en salle d'attente et alerte immédiate de l'équipe de tri."
                ]
            },
            "Brancardier": {
                "class": "Mémo Box Brancardier - Transport & Vulnérabilités (Semaine 4)",
                "slug": "brancardier",
                "points": [
                    "Confort et sécurité du transport : installation minutieuse du patient fragile (barrières relevées, protections thermiques, cales posturales) et vigilance permanente.",
                    "Sécurité des appareillages : vérification et fixation des obus d'oxygène et des dispositifs de perfusion avant tout départ de la zone de soins.",
                    "Réaction face à l'incident : arrêt immédiat du transfert en zone sécurisée et appel des soignants les plus proches en cas de modification de la conscience ou des constantes.",
                    "Hygiène et bionettoyage : désinfection systématique des points de contact du brancard avec les produits homologués après le transport de patients à risque (BMR/isolements)."
                ]
            },
            "Cadre": {
                "class": "Mémo Box Cadre - Management & Vulnérabilités (Semaine 4)",
                "slug": "cadre",
                "points": [
                    "Pilotage qualité & certification HAS 2027 : mise en place d'audits flash, d'EPP ciblées et de revues de dossiers sur le parcours des patients vulnérables.",
                    "Gestion opérationnelle des tensions : animation des cellules de flux, régulation des lits d'aval et réallocation des ressources en cas de saturation des zones (6 box/IDE).",
                    "Maîtrise des risques : pilotage des déclarations d'événements indésirables (FEI/EIG), animation des RMM et mise en place d'actions correctives pérennes.",
                    "Culture de service : accompagnement des équipes, diffusion des protocoles de bientraitance et maintien d'une sectorisation claire des rôles professionnels."
                ]
            }
        }
    },
        {
        "id": 5,
        "titre": "Semaine 5 - Gestion des Risques & Identitovigilance",
        "date_debut": datetime.date(2026, 11, 23),
        "date_fin": datetime.date(2026, 11, 29),
        "tronc_commun": [],
        "metiers": {
            "IDE": [
                {
                    "q": "1. [IDE] Un patient arrive aux urgences avec un bracelet d'identitovigilance comportant une inversion entre le nom de naissance et le nom d'usage. L'IDE doit administrer un traitement critique immédiat. Quelle est la règle HAS absolue ?",
                    "options": [
                        "Exiger la correction immédiate et la réédition du bracelet conforme (Triptyque : Nom de naissance, Prénom, Date de naissance) avant toute administration de soin à risque.",
                        "Administrer le traitement sous réserve de vérifier l'oralité avec le patient conscient.",
                        "Ne rien faire tant que le bureau des entrées n'a pas refait le bracelet complet, quitte à retarder le soin critique de 30 minutes."
                    ],
                    "rep": "Exiger la correction immédiate et la réédition du bracelet conforme (Triptyque : Nom de naissance, Prénom, Date de naissance) avant toute administration de soin à risque."
                },
                {
                    "q": "2. [IDE] Lors d'une double lecture pour l'administration de potassium IV direct en urgence absolue (erreur de prescription constatée au dernier moment), l'IDE évite de justesse l'accident. Que qualifie la HAS ?",
                    "options": [
                        "Un Événement Indésirable Grave (EIG) avec déclaration obligatoire sous 24h à l'ARS.",
                        "Une simple friction de service sans importance puisque l'erreur a été évitée in extremis.",
                        "Un quasi-événement (ou 'near-miss') qui doit impérativement faire l'objet d'une Fiche d'Événement Indésirable (FEI) pour analyse collective des causes."
                    ],
                    "rep": "Un quasi-événement (ou 'near-miss') qui doit impérativement faire l'objet d'une Fiche d'Événement Indésirable (FEI) pour analyse collective des causes."
                },
                {
                    "q": "3. [IDE] Un patient présente une allergie documentée aux pénicillines dans son dossier. Une prescription mentionne une amoxicilline-acide clavulanique sans alerte visuelle active sur le logiciel. Quelle est la conduite attendue ?",
                    "options": [
                        "Administrer une dose test réduite de moitié pour vérifier la tolérance clinique immédiate.",
                        "Surseoir à l'administration, alerter le prescripteur pour réévaluer la stratégie thérapeutique et tracer l'interception de l'erreur médicamenteuse.",
                        "Remplacer d'office la molécule par une céphalosporine de 3e génération sans avis médical."
                    ],
                    "rep": "Surseoir à l'administration, alerter le prescripteur pour réévaluer la stratégie thérapeutique et tracer l'interception de l'erreur médicamenteuse."
                },
                {
                    "q": "4. [IDE] En préparant un soluté en zone de soins, l'IDE est interrompu par un appel téléphonique urgent du SMUR. Le flacon reste sur le plan de travail sans étiquette nominative. Piège HAS :",
                    "options": [
                        "Tout médicament préparé et non administré immédiatement par le préparateur doit être détruit ou étiqueté selon les règles strictes de traçabilité pour éliminer tout risque de confusion.",
                        "Le flacon peut être utilisé si l'IDE se souvient parfaitement de ce qu'il a mis dedans.",
                        "Il suffit de demander à la collègue de valider la préparation à l'aveugle."
                    ],
                    "rep": "Tout médicament préparé et non administré immédiatement par le préparateur doit être détruit ou étiqueté selon les règles strictes de traçabilité pour éliminer tout risque de confusion."
                },
                {
                    "q": "5. [IDE] Comment l'IDE doit-il procéder lors d'un prélèvement sanguin complexe chez deux patients homonymes présents simultanément dans des box contigus ?",
                    "options": [
                        "Prélever les deux patients à la suite en gardant les tubes dans les mains pour aller plus vite au chariot.",
                        "Imprimer les étiquettes à l'avance au poste central pour gagner du temps en zone de soins.",
                        "Utiliser le principe du 'patient unique' : étiquetter les tubes au chevet du patient après l'avoir identifié formellement avec son bracelet, avant de passer au second patient."
                    ],
                    "rep": "Utiliser le principe du 'patient unique' : étiquetter les tubes au chevet du patient après l'avoir identifié formellement avec son bracelet, avant de passer au second patient."
                },
                {
                    "q": "6. [IDE] Lors d'une relève de poste, l'IDE sortant signale qu'une hémoculture a été prélevée 2 heures plus tôt mais que le bon de transport n'a pas été validé dans le logiciel. Quel est l'enjeu de sécurité ?",
                    "options": [
                        "Un simple retard administratif sans impact sur la fiabilité microbiologique.",
                        "Un risque de perte de traçabilité, de retard d'acheminement ou de fausse négativité/contamination, imposant une vérification immédiate du circuit et une régularisation tracée.",
                        "La nécessité de jeter le flacon et de ne pas prévenir le médecin."
                    ],
                    "rep": "Un risque de perte de traçabilité, de retard d'acheminement ou de fausse négativité/contamination, imposant une vérification immédiate du circuit et une régularisation tracée."
                },
                {
                    "q": "7. [IDE] Lors de la survenue d'un effet indésirable inattendu suite à l'injection d'un produit de contraste radiologique, l'IDE :",
                    "options": [
                        "Traite l'urgence, prévient le médecin sénior, trace l'événement dans le dossier et réalise une déclaration de matériovigilance/pharmacovigilance.",
                        "Se contente de le dire à l'oral au radiologue sans tracer dans le DPI.",
                        "Demande au manipulateur radio de faire la déclaration à sa place."
                    ],
                    "rep": "Traite l'urgence, prévient le médecin sénior, trace l'événement dans le dossier et réalise une déclaration de matériovigilance/pharmacovigilance."
                },
                {
                    "q": "8. [IDE] Quelle règle d'identitovigilance s'applique impérativement lors du transfert d'un patient des urgences vers le bloc opératoire ou la réanimation ?",
                    "options": [
                        "S'assurer que le dossier informatique est simplement fermé sur l'écran du box.",
                        "Donner les papiers d'identité en main propre au patient pour qu'il les tende au service d'accueil.",
                        "Vérification croisée verbale et physique de l'identité entre l'IDE des urgences et l'agent transporteur/receveur à partir du bracelet infalsifiable."
                    ],
                    "rep": "Vérification croisée verbale et physique de l'identité entre l'IDE des urgences et l'agent transporteur/receveur à partir du bracelet infalsifiable."
                },
                {
                    "q": "9. [IDE] Face à une prescription de chimiothérapie ou de produit hautement cytotoxique égarée ou ambiguë dans les urgences, l'IDE :",
                    "options": [
                        "Applique le principe de précaution en devinant la dose usuelle.",
                        "Refuse l'exécution, contacte immédiatement le prescripteur pour confirmation écrite explicite et alerte la pharmacie (PUI).",
                        "Demande à un collègue plus ancien de valider l'interprétation de la prescription."
                    ],
                    "rep": "Refuse l'exécution, contacte immédiatement le prescripteur pour confirmation écrite explicite et alerte la pharmacie (PUI)."
                },
                {
                    "q": "10. [IDE] En fin de prise en charge d'un patient quittant le service avec une ordonnance et des consignes de surveillance, quel point critique l'IDE vérifie-t-il avant le départ ?",
                    "options": [
                        "La compréhension effective des signes d'alerte justifiant un retour aux urgences et la concordance entre les consignes orales, l'ordonnance et l'identité du patient.",
                        "Uniquement que le brancard du box a été sorti dans le couloir.",
                        "Que le patient a bien réglé ses éventuels dépassements avant de lire l'ordonnance."
                    ],
                    "rep": "La compréhension effective des signes d'alerte justifiant un retour aux urgences et la concordance entre les consignes orales, l'ordonnance et l'identité du patient."
                }
            ],
            "Medecin": [
                {
                    "q": "1. [Medecin] Un patient en urgence absolue présente des troubles cognitifs majeurs sans aucun proche ni directives anticipées. Une intervention chirurgicale vitale immédiate s'impose. Quelle règle procédurale valide la décision ?",
                    "options": [
                        "Attendre 24 heures l'autorisation d'un juge des tutelles de permanence.",
                        "Demander l'avis téléphonique d'un voisin présent dans la salle d'attente.",
                        "Décision médicale collégiale d'urgence tracée dans le dossier (urgence vitale immédiate primant sur le consentement différé, avec recherche active de la personne de confiance)."
                    ],
                    "rep": "Décision médicale collégiale d'urgence tracée dans le dossier (urgence vitale immédiate primant sur le consentement différé, avec recherche active de la personne de confiance)."
                },
                {
                    "q": "2. [Medecin] Erreur de prescription de molécule par un interne sous votre responsabilité directe, interceptée par l'IDE avant administration. Quelle est l'exigence culturelle de sécurité HAS ?",
                    "options": [
                        "Analyser collectivement le contexte (fatigue, surcharge, ergonomie du logiciel de prescription) via une démarche d'équipe non punitive et déclarer le quasi-événement.",
                        "Sanctionner l'interne par un avertissement écrit dans son livret de stage pour l'exemple.",
                        "Ne rien faire puisque le patient n'a subi aucun dommage physique."
                    ],
                    "rep": "Analyser collectivement le contexte (fatigue, surcharge, ergonomie du logiciel de prescription) via une démarche d'équipe non punitive et déclarer le quasi-événement."
                },
                {
                    "q": "3. [Medecin] Lors de la validation de la sortie d'un patient fragile polymédiqué, vous omettez de signer la lettre de liaison de sortie obligatoire. Quel risque majeur pointe la certification HAS ?",
                    "options": [
                        "Un retard de facturation administrative pour le service financier de l'hôpital.",
                        "Une rupture majeure dans la continuité des soins de ville, favorisant la iatrogénie médicamenteuse et les réadmissions évitables.",
                        "Une simple anomalie statistique sans incidence sur la sécurité du patient."
                    ],
                    "rep": "Une rupture majeure dans la continuité des soins de ville, favorisant la iatrogénie médicamenteuse et les réadmissions évitables."
                },
                {
                    "q": "4. [Medecin] Un patient décède aux urgences dans un contexte d'Événement Indésirable Grave Associé aux Soins (EIGAS). Quelle est la chronologie réglementaire de déclaration imposée à l'établissement ?",
                    "options": [
                        "Déclaration sans délai sur le portail ministériel des signalements (par l'ARS/direction) et enclenchement immédiat d'une analyse des causes (RMM/CREX).",
                        "Attendre la fin du mois pour compiler tous les décès survenus aux urgences.",
                        "Informer uniquement la famille par téléphone sans formaliser de dossier de déclaration interne."
                    ],
                    "rep": "Déclaration sans délai sur le portail ministériel des signalements (par l'ARS/direction) et enclenchement immédiat d'une analyse des causes (RMM/CREX)."
                },
                {
                    "q": "5. [Medecin] Un patient présente une hémorragie digestive active nécessitant une transfusion en urgence. L'étiquette de groupage sanguin porte une mention 'détermination en cours - 1 seule détermination disponible'. Quelle règle transfusionnelle s'impose ?",
                    "options": [
                        "Transfuser des concentrés de globules rouges isogroupes sur la base d'une seule détermination si le patient n'est pas en arrêt cardiaque.",
                        "Respecter strictement les règles de sécurité transfusionnelle (O négatif/KEL- en urgence vitale immédiate selon protocole si pas de double détermination validée) et ne jamais valider une compatibilité sur une seule détermination hors urgence vitale non différable.",
                        "Demander à l'IDE de re-prélever le même tube et de le renvoyer sous le même nom."
                    ],
                    "rep": "Respecter strictement les règles de sécurité transfusionnelle (O négatif/KEL- en urgence vitale immédiate selon protocole si pas de double détermination validée) et ne jamais valider une compatibilité sur une seule détermination hors urgence vitale non différable."
                },
                {
                    "q": "6. [Medecin] Devant un afflux massif de résultats biologiques critiques non consultés dans les délais (en raison de la saturation du service), quelle est la responsabilité du médecin sénior référent de zone ?",
                    "options": [
                        "Considérer que le patient est parti donc le problème est réglé.",
                        "Mettre en place une organisation garantissant l'alerte et la levée des doutes sur les résultats anormaux avant la sortie définitive du patient.",
                        "Déléguer cette surveillance exclusivement aux secrétaires médicales."
                    ],
                    "rep": "Mettre en place une organisation garantissant l'alerte et la levée des doutes sur les résultats anormaux avant la sortie définitive du patient."
                },
                {
                    "q": "7. [Medecin] Comment traiter sur le plan de l'identitovigilance un patient inconscient, non identifié, amené par les secours sans le moindre document ?",
                    "options": [
                        "Créer un dossier d'urgence sous identité provisoire codifiée selon la charte d'identitovigilance institutionnelle, avec un bracelet de crise spécifique, enclenchant la recherche active d'identité.",
                        "L'appeler par un prénom inventé par l'interne de garde sur le tableau d'affichage.",
                        "Attendre qu'il se réveille pour lui demander son nom de naissance."
                    ],
                    "rep": "Créer un dossier d'urgence sous identité provisoire codifiée selon la charte d'identitovigilance institutionnelle, avec un bracelet de crise spécifique, enclenchant la recherche active d'identité."
                },
                {
                    "q": "8. [Medecin] Un patient refuse une hospitalisation en aval alors que son état somatique l'exige. Le médecin rédige la sortie contre avis médical :",
                    "options": [
                        "En lui faisant signer une décharge de responsabilité juridique absolue qui dédouane totalement l'hôpital.",
                        "En refusant de lui rendre ses effets personnels tant qu'il n'a pas accepté le transfert.",
                        "En s'assurant que le patient a reçu une information loyale et éclairée sur les risques encourus, en traçant cette information dans le DPI et en lui proposant des alternatives de suivi."
                    ],
                    "rep": "En s'assurant que le patient a reçu une information loyale et éclairée sur les risques encourus, en traçant cette information dans le DPI et en lui proposant des alternatives de suivi."
                },
                {
                    "q": "9. [Medecin] Lors de la réalisation d'un geste invasif à haut risque en urgence (ex: pose de voie centrale), le médecin :",
                    "options": [
                        "Peut s'affranchir des règles d'asepsie stricte si la situation est critique.",
                        "Applique les checklists de sécurité des soins, le marquage/contrôle d'identitovigilance et trace la réalisation ainsi que ses complications éventuelles.",
                        "Délègue l'intégralité de la traçabilité à l'étudiant en médecine présent."
                    ],
                    "rep": "Applique les checklists de sécurité des soins, le marquage/contrôle d'identitovigilance et trace la réalisation ainsi que ses complications éventuelles."
                },
                {
                    "q": "10. [Medecin] Quelle est la définition exacte du 'Patient Traceur' lors de la visite des experts-visiteurs de la HAS ?",
                    "options": [
                        "Un mode d'évaluation méthodologique où les experts analysent la qualité et la sécurité des soins en suivant pas à pas le dossier et le parcours réel d'un patient hospitalisé.",
                        "Un patient porteur d'une balise GPS pour suivre ses déplacements dans l'hôpital.",
                        "Un patient choisi au hasard pour tester la rapidité du laboratoire de biologie."
                    ],
                    "rep": "Un mode d'évaluation méthodologique où les experts analysent la qualité et la sécurité des soins en suivant pas à pas le dossier et le parcours réel d'un patient hospitalisé."
                }
            ],
            "AS": [
                {
                    "q": "1. [AS] Un patient confus est installé sur un brancard des urgences. L'AS remarque que le bracelet d'identification est absent du poignet et traîne sur le matelas. Que fait l'AS ?",
                    "options": [
                        "Le remet elle-même au poignet du patient en devinant l'emplacement.",
                        "Jette le bracelet à la poubelle pour éviter qu'il ne se perde.",
                        "Alerte immédiatement l'IDE pour qu'un contrôle formel d'identité soit opéré et qu'un nouveau bracelet certifié soit posé avant tout soin ou transport."
                    ],
                    "rep": "Alerte immédiatement l'IDE pour qu'un contrôle formel d'identité soit opéré et qu'un nouveau bracelet certifié soit posé avant tout soin ou transport."
                },
                {
                    "q": "2. [AS] Lors de l'installation d'un patient vulnérable en box, l'AS constate une lésion suspecte de maltraitance (ecchymoses d'âges différents sur le corps). Quelle est la conduite HAS ?",
                    "options": [
                        "Transmettre immédiatement et de façon confidentielle les observations factuelles à l'IDE et au médecin sénior, et consigner les faits dans le dossier de soins.",
                        "Interroger agressivement l'accompagnant dans le couloir pour obtenir des aveux.",
                        "Ne rien dire pour respecter le secret de la vie privée de la famille."
                    ],
                    "rep": "Transmettre immédiatement et de façon confidentielle les observations factuelles à l'IDE et au médecin sénior, et consigner les faits dans le dossier de soins."
                },
                {
                    "q": "3. [AS] En préparant un box pour un patient présentant une toux productive avec suspicion de tuberculose pulmonaire, quel équipement l'AS doit-il porter à l'entrée du box ?",
                    "options": [
                        "Un simple masque chirurgical porté uniquement par le patient si possible.",
                        "Un appareil de protection respiratoire de type masque FFP2 ajusté, dans le cadre des précautions complémentaires 'Air', et s'assurer de la porte fermée.",
                        "Une surblouse en tissu sans protection respiratoire."
                    ],
                    "rep": "Un appareil de protection respiratoire de type masque FFP2 ajusté, dans le cadre des précautions complémentaires 'Air', et s'assurer de la porte fermée."
                },
                {
                    "q": "4. [AS] En réalisant le bio-nettoyage d'un box, l'AS découvre un flacon ouvert contenant un produit chimique d'entretien sans étiquette. Piège sécurité :",
                    "options": [
                        "Ne jamais utiliser un produit non identifié, l'isoler et appliquer le protocole de signalisation des risques chimiques (produit non étiqueté = danger majeur).",
                        "L'utiliser pour finir le sol du box voisin.",
                        "Le transvaser dans une bouteille d'eau vide."
                    ],
                    "rep": "Ne jamais utiliser un produit non identifié, l'isoler et appliquer le protocole de signalisation des risques chimiques (produit non étiqueté = danger majeur)."
                },
                {
                    "q": "5. [AS] Quelle est la règle d'or de l'AS en matière d'identitovigilance lors du transport ou de l'accompagnement d'un patient vers l'imagerie ?",
                    "options": [
                        "Se fier au numéro du box indiqué sur la porte.",
                        "Laisser le patient donner lui-même son dossier au radiologue sans contrôle.",
                        "Demander au patient son prénom et vérifier la concordance avec le brancard et le dossier d'accompagnement."
                    ],
                    "rep": "Demander au patient son prénom et vérifier la concordance avec le brancard et le dossier d'accompagnement."
                },
                {
                    "q": "6. [AS] Lors d'une réfection de lit ou d'un change en box, l'AS constate qu'une sonde urinaire ou un drain est tiré ou coudé sous le drap. Quelle est la conduite attendue ?",
                    "options": [
                        "Tirer d'un coup sec pour remettre le dispositif en place et replier le drap dessus.",
                        "Prévenir immédiatement l'IDE sans forcer ni mobiliser abusivement le dispositif, afin d'éviter un traumatisme ou un arrachement accidentel.",
                        "Laisser le tuyau coincé sous le matelas jusqu'à la fin du poste."
                    ],
                    "rep": "Prévenir immédiatement l'IDE sans forcer ni mobiliser abusivement le dispositif, afin d'éviter un traumatisme ou un arrachement accidentel."
                },
                {
                    "q": "7. [AS] Un patient à jeun pour un examen ou un geste invasif demande un verre d'eau et un biscuit car il a faim. Quelle est la règle de sécurité ?",
                    "options": [
                        "Vérifier impérativement la consigne de jeûne avec l'IDE ou le médecin avant toute prise alimentaire ou hydrique, car une rupture de jeûne peut faire reporter ou annuler un acte urgent.",
                        "Lui donner un petit encas en cachette puisque ce n'est pas un vrai repas.",
                        "Lui dire de boire un grand verre d'eau du robinet pour patienter."
                    ],
                    "rep": "Vérifier impérativement la consigne de jeûne avec l'IDE ou le médecin avant toute prise alimentaire ou hydrique, car une rupture de jeûne peut faire reporter ou annuler un acte urgent."
                },
                {
                    "q": "8. [AS] Bientraitance et intimité : un box d'urgences n'a pas de porte pleine mais un simple rideau. Des passants discutent bruyamment dans le couloir. L'AS :",
                    "options": [
                        "Laisse le rideau entrouvert pour surveiller la luminosité.",
                        "Demande au patient de parler moins fort.",
                        "Ferme le rideau hermétiquement, ajuste les protections visuelles et veille à baisser la voix lors des échanges relatifs à l'intimité du patient."
                    ],
                    "rep": "Ferme le rideau hermétiquement, ajuste les protections visuelles et veille à baisser la voix lors des échanges relatifs à l'intimité du patient."
                },
                {
                    "q": "9. [AS] Lors de la remise d'un plateau-repas ou d'une collation en box, l'AS vérifie la présence d'un régime particulier ou d'une texture adaptée (ex: dysphagie / mixé / liquide épaissi). Pourquoi ?",
                    "options": [
                        "Uniquement pour respecter les préférences gustatives du patient.",
                        "Pour prévenir un risque grave de fausse route ou d'erreur diététique/allergique chez un patient fragile.",
                        "Parce que le service restauration impose de vérifier l'étiquette du plateau."
                    ],
                    "rep": "Pour prévenir un risque grave de fausse route ou d'erreur diététique/allergique chez un patient fragile."
                },
                {
                    "q": "10. [AS] Comment l'AS participe-t-elle activement à la démarche qualité HAS dans sa zone de travail ?",
                    "options": [
                        "En signalant les pannes, en participant aux remontées de fiches d'événements indésirables (FEI) et en appliquant rigoureusement les protocoles d'hygiène et de bientraitance.",
                        "En rangeant le placard à balais une fois par an.",
                        "En ne faisant remonter aucun incident pour ne pas surcharger la hiérarchie."
                    ],
                    "rep": "En signalant les pannes, en participant aux remontées de fiches d'événements indésirables (FEI) et en appliquant rigoureusement les protocoles d'hygiène et de bientraitance."
                }
            ],
            "ARM (Assistant/e de Régulation Médicale)": [
                {
                    "q": "1. [ARM] Un appel arrive au SAMU pour un patient dont l'identité est incertaine (témoin affolé qui raccroche vite). Quelle est la priorité absolue d'identitovigilance de l'ARM ?",
                    "options": [
                        "Clôturer l'appel sans suite pour ne pas encombrer la ligne.",
                        "Attendre que l'appelant rappelle par lui-même.",
                        "Tenter de rappeler immédiatement, géolocaliser l'appel, créer un dossier de crise sécurisé avec les indices disponibles et alerter le régulateur."
                    ],
                    "rep": "Tenter de rappeler immédiatement, géolocaliser l'appel, créer un dossier de crise sécurisé avec les indices disponibles et alerter le régulateur."
                },
                {
                    "q": "2. [ARM] Risque d'erreur d'aiguillage de moyen : un appelant signale une détresse respiratoire aiguë mais l'ARM sélectionne par erreur un vecteur de transport simple au lieu d'un SMUR. Piège de gestion des risques :",
                    "options": [
                        "Dès la prise de conscience, l'ARM applique la procédure d'alerte corrective immédiate en réajustant le vecteur et rédige une fiche d'événement indésirable (FEI) pour analyse systémique.",
                        "L'ARM doit masquer son erreur dans le dossier informatique pour éviter un blâme.",
                        "Laisser l'ambulance simple arriver sur les lieux pour voir."
                    ],
                    "rep": "Dès la prise de conscience, l'ARM applique la procédure d'alerte corrective immédiate en réajustant le vecteur et rédige une fiche d'événement indésirable (FEI) pour analyse systémique."
                },
                {
                    "q": "3. [ARM] Un tiers appelle en se faisant passer pour un proche pour obtenir des renseignements médicaux confidentiels sur une victime d'accident grave. L'ARM :",
                    "options": [
                        "Donne l'ensemble du bilan hémodynamique car l'appelant est insistant.",
                        "Applique strictement les règles du secret professionnel et de non-divulgation, et oriente vers la cellule d'information officielle ou le médecin régulateur.",
                        "Transmet le numéro de portable personnel du médecin urgentiste."
                    ],
                    "rep": "Applique strictement les règles du secret professionnel et de non-divulgation, et oriente vers la cellule d'information officielle ou le médecin régulateur."
                },
                {
                    "q": "4. [ARM] En mode dégradé informatique complet (panne du logiciel CENTAURE), comment l'ARM garantit-il la sécurité de la traçabilité des engagements de moyens ?",
                    "options": [
                        "En basculant immédiatement sur les mains courantes et fiches chronologiques papier de crise préétablies, avec double horodatage.",
                        "En mémorisant les interventions dans sa tête sans support écrit.",
                        "En arrêtant de prendre les appels d'urgence jusqu'au retour du réseau."
                    ],
                    "rep": "En basculant immédiatement sur les mains courantes et fiches chronologiques papier de crise préétablies, avec double horodatage."
                },
                {
                    "q": "5. [ARM] Homonymie en régulation : deux dossiers de patients portant exactement le même nom de naissance et prénom sont créés à 10 minutes d'intervalle. L'ARM :",
                    "options": [
                        "Fusionne les deux dossiers en un seul pour faire de la place.",
                        "Supprime le plus ancien des deux.",
                        "Vérifie les critères discriminants (date de naissance, adresse, numéro de téléphone, contexte) pour s'assurer de la stricte dissociation des dossiers et éviter la confusion de moyens."
                    ],
                    "rep": "Vérifie les critères discriminants (date de naissance, adresse, numéro de téléphone, contexte) pour s'assurer de la stricte dissociation des dossiers et éviter la confusion de moyens."
                },
                {
                    "q": "6. [ARM] Un appelant signale une situation de violence intrafamiliale menaçante. L'ARM :",
                    "options": [
                        "Conseille à la victime de changer de serrure.",
                        "Sécurise les données, évalue le degré d'urgence, transmet immédiatement au médecin régulateur et coordonne l'intervention des forces de l'ordre selon la doctrine de sécurité.",
                        "Transfère l'appel vers une ligne de loisirs."
                    ],
                    "rep": "Sécurise les données, évalue le degré d'urgence, transmet immédiatement au médecin régulateur et coordonne l'intervention des forces de l'ordre selon la doctrine de sécurité."
                },
                {
                    "q": "7. [ARM] Quelle est l'exigence de la HAS concernant l'enregistrement audio des appels au centre 15 et leur traçabilité informatique ?",
                    "options": [
                        "Conservation réglementaire des bandes et traçabilité inaltérable des actions de régulation dans les dossiers informatisés, opposables en cas de contentieux.",
                        "Les enregistrements peuvent être effacés au bout de 24 heures pour gagner de l'espace disque.",
                        "Aucun enregistrement n'est obligatoire."
                    ],
                    "rep": "Conservation réglementaire des bandes et traçabilité inaltérable des actions de régulation dans les dossiers informatisés, opposables en cas de contentieux."
                },
                {
                    "q": "8. [ARM] Lors d'un rappel d'un requérant pour un dossier déjà ouvert, l'ARM constate que l'adresse d'intervention saisie initialement comportait une erreur de rue. Quelle action est critique ?",
                    "options": [
                        "Corriger immédiatement la localisation dans le dossier, notifier le changement au régulateur et aux vecteurs déjà engagés, et tracer la rectification pour éviter un retard d'arrivée sur site.",
                        "Créer un deuxième dossier distinct sans fermer ni relier le premier.",
                        "Attendre que l'équipage sur place signale qu'il ne trouve pas l'adresse."
                    ],
                    "rep": "Corriger immédiatement la localisation dans le dossier, notifier le changement au régulateur et aux vecteurs déjà engagés, et tracer la rectification pour éviter un retard d'arrivée sur site."
                },
                {
                    "q": "9. [ARM] Transmission d'une alerte sanitaire grave (ex: intoxication collective) : l'ARM doit :",
                    "options": [
                        "Diffuser l'information sur ses réseaux sociaux personnels.",
                        "Alerter immédiatement le médecin régulateur chef de service et appliquer la procédure de signalement institutionnel de crise sanitaire.",
                        "Attendre la fin de sa semaine de travail pour en parler."
                    ],
                    "rep": "Alerter immédiatement le médecin régulateur chef de service et appliquer la procédure de signalement institutionnel de crise sanitaire."
                },
                {
                    "q": "10. [ARM] Rôle de l'ARM dans la culture de sécurité des soins du SAMU :",
                    "options": [
                        "Être le premier maillon de la barrière de sécurité, qualifiant rigoureusement le risque et participant activement aux retours d'expérience (REX).",
                        "Se contenter de décrocher le téléphone sans analyser les risques de l'appel.",
                        "Laisser l'ordinateur faire tout le travail de tri."
                    ],
                    "rep": "Être le premier maillon de la barrière de sécurité, qualifiant rigoureusement le risque et participant activement aux retours d'expérience (REX)."
                }
            ],
            "Accueil": [
                {
                    "q": "1. [Accueil] Un patient se présente au guichet avec une carte d'identité périmée mais un passeport valide et sa carte Vitale. Quel est le réflexe d'identitovigilance ?",
                    "options": [
                        "Refuser systématiquement l'enregistrement administratif et le renvoyer chez lui sans prévenir l'IOA.",
                        "Enregistrer l'identité à partir du justificatif valide le plus probant (passeport / CNI valide) en respectant la charte d'identitovigilance, sans inventer de donnée.",
                        "Saisir un prénom approximatif en attendant qu'il retrouve un autre papier."
                    ],
                    "rep": "Enregistrer l'identité à partir du justificatif valide le plus probant (passeport / CNI valide) en respectant la charte d'identitovigilance, sans inventer de donnée."
                },
                {
                    "q": "2. [Accueil] Erreur d'enregistrement d'identité au guichet : un agent sélectionne par erreur le mauvais homonyme dans la base de données administrative. Conséquence critique HAS :",
                    "options": [
                        "Risque majeur de télescopage des dossiers médicaux, d'erreurs d'examens et d'administration de traitements inadaptés. La vigilance à l'accueil est le premier rempart d'identitovigilance.",
                        "Aucun impact, c'est purement de la papeterie.",
                        "Le médecin rectifiera de lui-même sans aide."
                    ],
                    "rep": "Risque majeur de télescopage des dossiers médicaux, d'erreurs d'examens et d'administration de traitements inadaptés. La vigilance à l'accueil est le premier rempart d'identitovigilance."
                },
                {
                    "q": "3. [Accueil] Confidentialité au comptoir : un patient énonce sa pathologie intime à haute voix devant une file d'attente serrée. L'agent d'accueil :",
                    "options": [
                        "Laisse faire pour accélérer le flux.",
                        "Invite discrètement l'usager à respecter la ligne de discrétion, baisse la voix et adapte l'environnement pour préserver le secret médical.",
                        "Demande à la file d'attente de commenter le diagnostic."
                    ],
                    "rep": "Invite discrètement l'usager à respecter la ligne de discrétion, baisse la voix et adapte l'environnement pour préserver le secret médical."
                },
                {
                    "q": "4. [Accueil] Gestion des objets de valeur d'un patient pris en charge en urgence vitale et inconscient au déchocage :",
                    "options": [
                        "Réaliser un inventaire contradictoire formel avec un soignant, placer les valeurs dans un sac scellé sécurisé et les déposer au coffre de l'établissement.",
                        "Laisser les bijoux dans le blouson posé sur la chaise de la salle d'attente.",
                        "Les confier au premier passant se disant un ami de la famille."
                    ],
                    "rep": "Réaliser un inventaire contradictoire formel avec un soignant, placer les valeurs dans un sac scellé sécurisé et les déposer au coffre de l'établissement."
                },
                {
                    "q": "5. [Accueil] Un accompagnant demande au guichet à consulter le dossier médical complet de son conjoint majeur hospitalisé aux urgences, sans procuration ni statut de personne de confiance désignée. Quelle est la règle ?",
                    "options": [
                        "Imprimer l'intégralité des examens et les lui remettre immédiatement pour apaiser la famille.",
                        "Refuser la communication directe des éléments médicaux confidentiels à un tiers non habilité et orienter vers l'équipe médicale selon les règles du secret médical et de l'accès au dossier.",
                        "Lui dicter les conclusions diagnostiques à voix haute au guichet."
                    ],
                    "rep": "Refuser la communication directe des éléments médicaux confidentiels à un tiers non habilité et orienter vers l'équipe médicale selon les règles du secret médical et de l'accès au dossier."
                },
                {
                    "q": "6. [Accueil] En cas de panne informatique des admissions, l'agent d'accueil doit :",
                    "options": [
                        "Arrêter d'inscrire les patients et leur dire de revenir le lendemain.",
                        "Utiliser la papeterie de secours (fiches d'admission de crise) en s'assurant de recueillir rigoureusement le triptyque d'identitovigilance.",
                        "Noter les prénoms sur un bout de carton de récupération."
                    ],
                    "rep": "Utiliser la papeterie de secours (fiches d'admission de crise) en s'assurant de recueillir rigoureusement le triptyque d'identitovigilance."
                },
                {
                    "q": "7. [Accueil] Un journaliste se présente au guichet des urgences en demandant des détails sur une personnalité admise suite à un accident. L'agent d'accueil :",
                    "options": [
                        "Applique strictement la consigne de non-divulgation, refuse l'accès et oriente vers la direction de la communication / cellule officielle.",
                        "Lui vend l'information en échange d'un article positif.",
                        "Lui indique dans quel box est le patient."
                    ],
                    "rep": "Applique strictement la consigne de non-divulgation, refuse l'accès et oriente vers la direction de la communication / cellule officielle."
                },
                {
                    "q": "8. [Accueil] Quelle pièce justificative officielle est prioritairement exigée pour lever un doute sur l'identité d'un patient se présentant à l'accueil des urgences ?",
                    "options": [
                        "Une carte de fidélité de grande surface.",
                        "Une facture de téléphone fixe de moins de 3 mois.",
                        "Une pièce d'identité officielle avec photographie (CNI, passeport, titre de séjour) combinée à la carte Vitale."
                    ],
                    "rep": "Une pièce d'identité officielle avec photographie (CNI, passeport, titre de séjour) combinée à la carte Vitale."
                },
                {
                    "q": "9. [Accueil] Comment l'agent d'accueil gère-t-il l'attente prolongée des familles en période de forte tension aux urgences ?",
                    "options": [
                        "En leur raccrochant le guichet au nez pour être tranquille.",
                        "En faisant preuve d'empathie, en expliquant de manière transparente le mode de tri fondé sur la gravité (et non l'ordre d'arrivée) et en faisant le lien avec l'équipe soignante.",
                        "En leur promettant une heure de sortie précise et irréaliste."
                    ],
                    "rep": "En faisant preuve d'empathie, en expliquant de manière transparente le mode de tri fondé sur la gravité (et non l'ordre d'arrivée) et en faisant le lien avec l'équipe soignante."
                },
                {
                    "q": "10. [Accueil] Un patient mineur se présente seul au guichet pour des soins. Quel réflexe administratif et de sécurité est attendu à l'accueil ?",
                    "options": [
                        "Le renvoyer dehors sans prévenir l'équipe soignante.",
                        "Alerter immédiatement l'équipe soignante (IOA) et appliquer les procédures d'accueil/protection des mineurs ainsi que la recherche des titulaires de l'autorité parentale selon le contexte.",
                        "Lui faire signer lui-même une décharge financière et médicale."
                    ],
                    "rep": "Alerter immédiatement l'équipe soignante (IOA) et appliquer les procédures d'accueil/protection des mineurs ainsi que la recherche des titulaires de l'autorité parentale selon le contexte."
                }
            ],
            "Brancardier": [
                {
                    "q": "1. [Brancardier] Le brancardier vient chercher un patient en box pour l'imagerie. Le patient n'a pas de bracelet d'identitovigilance à son poignet. Que dit la règle HAS ?",
                    "options": [
                        "Emmener le patient quand même en lui demandant juste son nom à l'oral.",
                        "Inscrire le nom du patient au feutre sur sa main pour aller plus vite.",
                        "Refuser le départ du brancard, alerter l'IDE pour poser un bracelet conforme et certifié avant d'effectuer le moindre déplacement."
                    ],
                    "rep": "Refuser le départ du brancard, alerter l'IDE pour poser un bracelet conforme et certifié avant d'effectuer le moindre déplacement."
                },
                {
                    "q": "2. [Brancardier] Transport d'un patient sous oxygénothérapie : le brancardier oublie de fixer la bouteille d'oxygène dans son support, celle-ci roule au sol et la lyre se débranche. Analyse du risque :",
                    "options": [
                        "Un quasi-événement / risque critique de chute d'obus sous pression et de coupure d'oxygène pour un patient fragile, nécessitant une Fiche d'Événement Indésirable (FEI).",
                        "Un incident sans gravité, il suffit de la ramasser.",
                        "Une simple maladresse de manipulation sans traçabilité requise."
                    ],
                    "rep": "Un quasi-événement / risque critique de chute d'obus sous pression et de coupure d'oxygène pour un patient fragile, nécessitant une Fiche d'Événement Indésirable (FEI)."
                },
                {
                    "q": "3. [Brancardier] Au moment de quitter le service de radiologie avec un patient, le manipulateur remet au brancardier le dossier d'un autre patient portant un nom très proche. Quelle est la bonne réaction ?",
                    "options": [
                        "Prendre les deux dossiers ensemble et faire le tri dans le couloir.",
                        "Vérifier systématiquement la concordance entre le bracelet du patient et l'identité figurant sur les documents/examens avant de quitter le secteur, et faire corriger l'erreur immédiatement.",
                        "Laisser le dossier sur le comptoir de radiologie sans rien dire."
                    ],
                    "rep": "Vérifier systématiquement la concordance entre le bracelet du patient et l'identité figurant sur les documents/examens avant de quitter le secteur, et faire corriger l'erreur immédiatement."
                },
                {
                    "q": "4. [Brancardier] Hygiène hospitalière : après le transport d'un patient connu porteur d'une bactérie multirésistante (BMR), le brancardier doit :",
                    "options": [
                        "Réaliser un bio-nettoyage systématique et complet des surfaces de contact du brancard (matelas, ridelles, poignées) avec le produit détergent-désinfectant homologué.",
                        "Laisser le brancard tel quel pour le patient suivant.",
                        "Passer un coup de chiffon sec pour enlever la poussière."
                    ],
                    "rep": "Réaliser un bio-nettoyage systématique et complet des surfaces de contact du brancard (matelas, ridelles, poignées) avec le produit détergent-désinfectant homologué."
                },
                {
                    "q": "5. [Brancardier] Ergonomie et sécurité des manipulations : pour transférer un patient grabataire du lit au brancard, le brancardier :",
                    "options": [
                        "Tire le patient par les bras en force brute.",
                        "Demande au patient de sauter seul sur le brancard.",
                        "Utilise les équipements d'aide à la mobilisation (plan glissant, drap de transfert) en collaboration avec l'aide-soignant ou l'infirmier, en respectant les postures de sécurité."
                    ],
                    "rep": "Utilise les équipements d'aide à la mobilisation (plan glissant, drap de transfert) en collaboration avec l'aide-soignant ou l'infirmier, en respectant les postures de sécurité."
                },
                {
                    "q": "6. [Brancardier] Le brancardier est invité par un collègue à modifier les débits d'une seringue électrique de perfusion pendant le trajet en ascenseur. Il doit :",
                    "options": [
                        "Obtempérer pour aider l'équipe en tension.",
                        "Refuser formellement : le brancardier ne doit jamais manipuler les dispositifs médicaux actifs, les débits ou les pompes de perfusion.",
                        "Arrêter l'alarme de la machine en appuyant sur n'importe quel bouton."
                    ],
                    "rep": "Refuser formellement : le brancardier ne doit jamais manipuler les dispositifs médicaux actifs, les débits ou les pompes de perfusion."
                },
                {
                    "q": "7. [Brancardier] Sécurité des circulations : lors d'un Plan Blanc, le brancardier doit respecter :",
                    "options": [
                        "Les sens de circulation spécifiques et sectorisés (flux propres/contaminés) définis par la cellule logistique de crise.",
                        "Le chemin le plus court en traversant les zones confinées interdites.",
                        "Les couloirs réservés au public de l'hôpital."
                    ],
                    "rep": "Les sens de circulation spécifiques et sectorisés (flux propres/contaminés) définis par la cellule logistique de crise."
                },
                {
                    "q": "8. [Brancardier] Comment s'assure-t-on de la stabilité d'un patient positionné sur un brancard avant d'entamer le déplacement ?",
                    "options": [
                        "Demander au patient s'il a le vertige sans relever les barrières.",
                        "Courir directement dans le couloir pour tester l'équilibre.",
                        "Vérification du verrouillage complet et de la hauteur des ridelles de sécurité, calage correct du corps et des dispositifs associés."
                    ],
                    "rep": "Vérification du verrouillage complet et de la hauteur des ridelles de sécurité, calage correct du corps et des dispositifs associés."
                },
                {
                    "q": "9. [Brancardier] Lors de l'arrivée dans un service d'hospitalisation en aval, le lit prévu n'est pas prêt ou le service signale un problème d'accueil. Quelle est la conduite à tenir ?",
                    "options": [
                        "Laisser le patient seul dans le couloir du service d'aval et repartir à vide.",
                        "Ne pas abandonner le patient sans prise en charge sécurisée, prévenir le cadre/référent des urgences et suivre la procédure de gestion des transferts/lits tampons.",
                        "Ramener le patient au fond du parking des urgences."
                    ],
                    "rep": "Ne pas abandonner le patient sans prise en charge sécurisée, prévenir le cadre/référent des urgences et suivre la procédure de gestion des transferts/lits tampons."
                },
                {
                    "q": "10. [Brancardier] Rôle clé du brancardier dans la fluidité et la sécurité des urgences :",
                    "options": [
                        "Optimiser les délais de transport, relayer les informations de tension au personnel soignant et contribuer à la sécurité active des transferts.",
                        "Rester invisible et ne communiquer avec personne.",
                        "Décider de la priorité médicale des examens radiologiques."
                    ],
                    "rep": "Optimiser les délais de transport, relayer les informations de tension au personnel soignant et contribuer à la sécurité active des transferts."
                }
            ],
            "ASH": [
                {
                    "q": "1. [ASH] En effectuant le bio-nettoyage d'un box d'urgences, l'ASH trouve un flacon de traitement anticancéreux (cytotoxique) éliminé par erreur dans la poubelle noire classique (DAOM). Quelle est la conduite immédiate ?",
                    "options": [
                        "Le laisser dans la poubelle pour ne pas perturber le tri.",
                        "Le vider dans l'évier du box et jeter le flacon vide.",
                        "Alerter immédiatement l'équipe soignante et reconditionner le déchet dans la filière spécifique sécurisée appropriée (DASRI / cytotoxiques) pour prévenir un risque toxique majeur."
                    ],
                    "rep": "Alerter immédiatement l'équipe soignante et reconditionner le déchet dans la filière spécifique sécurisée appropriée (DASRI / cytotoxiques) pour prévenir un risque toxique majeur."
                },
                {
                    "q": "2. [ASH] L'ASH constate qu'une flaque de liquide biologique vient de tomber au sol dans un couloir de passage. Quelle est la méthode de sécurité avant de passer la lavette ?",
                    "options": [
                        "Essuyer rapidement sans balisage pendant que les brancards passent.",
                        "Baliser/sécuriser temporairement la zone si possible pour éviter les glissades, porter les gants adaptés et appliquer le protocole de traitement des souillures biologiques.",
                        "Saupoudrer du sel et laisser sécher."
                    ],
                    "rep": "Baliser/sécuriser temporairement la zone si possible pour éviter les glissades, porter les gants adaptés et appliquer le protocole de traitement des souillures biologiques."
                },
                {
                    "q": "3. [ASH] Manipulation des produits d'entretien : un agent ASH transvase du détergent-désinfectant concentré dans une bouteille de jus de fruit vide laissée sur un chariot. Analyse HAS de ce comportement :",
                    "options": [
                        "C'est une astuce pratique et économique courante.",
                        "C'est une infraction majeure et un danger mortel d'ingestion accidentelle par confusion (interdiction formelle de transvaser des produits chimiques dans des contenants alimentaires).",
                        "C'est toléré si une croix est dessinée au feutre sur la bouteille."
                    ],
                    "rep": "C'est une infraction majeure et un danger mortel d'ingestion accidentelle par confusion (interdiction formelle de transvaser des produits chimiques dans des contenants alimentaires)."
                },
                {
                    "q": "4. [ASH] Quelle est la règle absolue d'hygiène des mains à respecter par l'ASH lors de l'entretien des locaux de soins à haut risque ?",
                    "options": [
                        "Réaliser une friction hydro-alcoolique (PHA) des mains avant d'entrer, après chaque tâche à risque, et systématiquement après le retrait des gants de protection.",
                        "Garder la même paire de gants de ménage toute la journée sans friction.",
                        "Se rincer les mains à l'eau froide sans savon."
                    ],
                    "rep": "Réaliser une friction hydro-alcoolique (PHA) des mains avant d'entrer, après chaque tâche à risque, et systématiquement après le retrait des gants de protection."
                },
                {
                    "q": "5. [ASH] Bientraitance environnementale : l'ASH doit nettoyer un box occupé par un patient conscient, éveillé et anxieux. La bonne posture est de :",
                    "options": [
                        "Entrer en silence sans dire bonjour, pousser le lit et faire du bruit avec le seau.",
                        "Refuser de nettoyer le box tant que le patient y est.",
                        "Frapper à la porte, se présenter, expliquer poliment l'intervention de bio-nettoyage et veiller à respecter l'intimité et le repos du patient."
                    ],
                    "rep": "Frapper à la porte, se présenter, expliquer poliment l'intervention de bio-nettoyage et veiller à respecter l'intimité et le repos du patient."
                },
                {
                    "q": "6. [ASH] En période de risque épidémique ou de Plan Blanc, quelle méthode de bio-nettoyage des surfaces l'ASH doit-il renforcer ?",
                    "options": [
                        "Un simple dépoussiérage avec un chiffon sec non stérile.",
                        "L'application stricte du protocole de désinfection terminale avec des produits virucides/sporicides aux temps de contact requis, en portant les équipements de protection individuelle (EPI) complets.",
                        "Ne rien changer aux habitudes de nettoyage."
                    ],
                    "rep": "L'application stricte du protocole de désinfection terminale avec des produits virucides/sporicides aux temps de contact requis, en portant les équipements de protection individuelle (EPI) complets."
                },
                {
                    "q": "7. [ASH] Que doit faire l'ASH si le chariot de soins infirmiers se trouve au milieu du box pendant qu'elle souhaite nettoyer le sol sous ce chariot ?",
                    "options": [
                        "Demander impérativement la présence et l'accord de l'IDE pour déplacer tout plan de travail mobile ou chariot contenant des produits de santé (interdiction de manipuler les médicaments).",
                        "Déplacer seule les boîtes de médicaments et les seringues pour faire place nette.",
                        "Jeter le contenu du chariot dans la poubelle pour nettoyer."
                    ],
                    "rep": "Demander impérativement la présence et l'accord de l'IDE pour déplacer tout plan de travail mobile ou chariot contenant des produits de santé (interdiction de manipuler les médicaments)."
                },
                {
                    "q": "8. [ASH] Gestion des sacs DASRI : à quel niveau de remplissage maximal les sacs jaunes de déchets infectieux doivent-ils impérativement être fermés et évacués ?",
                    "options": [
                        "Quand le sac éclate sous la pression.",
                        "Une fois par semaine quel que soit le niveau.",
                        "Aux trois quarts de leur capacité maximale, avec une fermeture étanche définitive (lien tunique / colliers de serrage)."
                    ],
                    "rep": "Aux trois quarts de leur capacité maximale, avec une fermeture étanche définitive (lien tunique / colliers de serrage)."
                },
                {
                    "q": "9. [ASH] En rangeant le local de stockage des produits d'entretien, l'ASH constate une fuite sur un bidon de désinfectant et une absence de fiche de données de sécurité (FDS) accessible. Que fait-elle ?",
                    "options": [
                        "Laisser le bidon fuir dans le bac de rétention sans rien dire.",
                        "Sécuriser/isoler le contenant selon la procédure, signaler l'incident à l'encadrement et s'assurer de l'accessibilité des consignes/FDS du local.",
                        "Utiliser le bidon en premier pour le vider plus vite."
                    ],
                    "rep": "Sécuriser/isoler le contenant selon la procédure, signaler l'incident à l'encadrement et s'assurer de l'accessibilité des consignes/FDS du local."
                },
                {
                    "q": "10. [ASH] Rôle de l'ASH dans la prévention des infections nosocomiales :",
                    "options": [
                        "Un rôle de première ligne fondamental : la qualité du bio-nettoyage des surfaces et le respect des circuits de bionettoyage brisent la chaîne de transmission croisée.",
                        "Un rôle secondaire sans impact sur les patients.",
                        "Le nettoyage des sols n'a aucun lien avec la sécurité des soins."
                    ],
                    "rep": "Un rôle de première ligne fondamental : la qualité du bio-nettoyage des surfaces et le respect des circuits de bionettoyage brisent la chaîne de transmission croisée."
                }
            ],
            "Cadre": [
                {
                    "q": "1. [Cadre] Visite HAS 2027 : un Événement Indésirable Grave Associé aux Soins (EIGAS) est survenu dans l'unité deux mois plus tôt. Les experts-visiteurs consultent le dossier. Quelle attente managériale majeure ont-ils ?",
                    "options": [
                        "Vérifier que le nom du soignant responsable est affiché en salle de repos.",
                        "Constater que l'incident a été étouffé pour ne pas ternir la réputation du service.",
                        "Analyser la traçabilité de la déclaration, la mise en œuvre immédiate d'une analyse systémique des causes (RMM/CREX) et le suivi effectif du plan d'actions correctives."
                    ],
                    "rep": "Analyser la traçabilité de la déclaration, la mise en œuvre immédiate d'une analyse systémique des causes (RMM/CREX) et le suivi effectif du plan d'actions correctives."
                },
                {
                    "q": "2. [Cadre] Surcharge chronique et tensions majeures sur les flux aux urgences : le cadre constate que le double contrôle des Médicaments à Haut Risque (MHR) n'est plus fait par manque de temps. Son action corrective :",
                    "options": [
                        "Analyser les freins organisationnels, rappeler le caractère non négociable de cette barrière de sécurité et réorganiser les binômes soignants pour sanctuariser la pratique.",
                        "Supprimer officiellement la règle du double contrôle pour fluidifier les passages.",
                        "Faire un reproche individuel public aux infirmiers récalcitrants."
                    ],
                    "rep": "Analyser les freins organisationnels, rappeler le caractère non négociable de cette barrière de sécurité et réorganiser les binômes soignants pour sanctuariser la pratique."
                },
                {
                    "q": "3. [Cadre] Comment le cadre pilote-t-il concrètement l'évaluation des pratiques professionnelles (EPP) exigée par la certification HAS dans son service d'urgences ?",
                    "options": [
                        "En rédigeant des classeurs de protocoles poussiéreux rangés au fond d'un placard.",
                        "En organisant des audits flash réguliers et partagés (identitovigilance, traçabilité de la douleur, chariots d'urgence, dossiers 'patients traceurs') ancrés dans le quotidien des équipes.",
                        "En interdisant aux soignants de commettre des erreurs."
                    ],
                    "rep": "En organisant des audits flash réguliers et partagés (identitovigilance, traçabilité de la douleur, chariots d'urgence, dossiers 'patients traceurs') ancrés dans le quotidien des équipes."
                },
                {
                    "q": "4. [Cadre] Gestion des risques liés aux ressources humaines et à l'épuisement professionnel (burn-out) : quelle est la responsabilité managériale du cadre ?",
                    "options": [
                        "Surveiller les signaux faibles d'épuisement, veiller au respect strict des temps de pause, planifier des rotations équitables et favoriser un espace de parole sécure.",
                        "Ignorer la fatigue des agents tant que les indicateurs chiffrés de passage sont corrects.",
                        "Exiger des doubles postes continus en cas d'absentéisme."
                    ],
                    "rep": "Surveiller les signaux faibles d'épuisement, veiller au respect strict des temps de pause, planifier des rotations équitables et favoriser un espace de parole sécure."
                },
                {
                    "q": "5. [Cadre] Contrôle de la sécurité du chariot d'urgence de l'unité : quelle est la fréquence et la modalité de traçabilité exigée par la certification HAS ?",
                    "options": [
                        "Un contrôle visuel annuel aléatoire.",
                        "Une vérification réalisée uniquement par la pharmacie centrale.",
                        "Un contrôle quotidien formalisé de l'intégrité du scellé et une traçabilité rigoureuse des péremptions sur le registre dédié de l'unité."
                    ],
                    "rep": "Un contrôle quotidien formalisé de l'intégrité du scellé et une traçabilité rigoureuse des péremptions sur le registre dédié de l'unité."
                },
                {
                    "q": "6. [Cadre] Face à un signalement répété de quasi-erreurs informatiques liées à l'ergonomie d'un nouveau logiciel de prescription, le cadre :",
                    "options": [
                        "Demande aux soignants de faire plus attention sans rien remonter.",
                        "Coordonne la remontée institutionnelle des incidents via la matériovigilance/système d'information et met en place des barrières de sécurité palliatives sur le terrain.",
                        "Interdit l'utilisation de l'ordinateur."
                    ],
                    "rep": "Coordonne la remontée institutionnelle des incidents via la matériovigilance/système d'information et met en place des barrières de sécurité palliatives sur le terrain."
                },
                {
                    "q": "7. [Cadre] Quelle est l'attente de la HAS concernant la culture de sécurité des soins et la déclaration des événements indésirables (FEI) par les équipes ?",
                    "options": [
                        "Développer une culture juste (just culture) non punitive, encourageant la déclaration libérée des erreurs et quasi-erreurs pour transformer l'organisation.",
                        "Promouvoir une approche punitive pour responsabiliser individuellement chaque agent.",
                        "Limiter le nombre de déclarations mensuelles pour embellir les statistiques."
                    ],
                    "rep": "Développer une culture juste (just culture) non punitive, encourageant la déclaration libérée des erreurs et quasi-erreurs pour transformer l'organisation."
                },
                {
                    "q": "8. [Cadre] En situation de crise sanitaire (Plan Blanc) avec une saturation critique des box d'urgences, le cadre pilote la gestion des flux en :",
                    "options": [
                        "Fermant les portes du service pour refuser l'entrée de nouveaux patients.",
                        "Demandant à l'équipe de se débrouiller sans directive.",
                        "Coordonnant la cellule de crise locale, activant les lits tampons, fluidifiant l'aval et réallouant les ressources soignantes selon les priorités de criticité."
                    ],
                    "rep": "Coordonnant la cellule de crise locale, activant les lits tampons, fluidifiant l'aval et réallouant les ressources soignantes selon les priorités de criticité."
                },
                {
                    "q": "9. [Cadre] Lors d'un audit interne, le cadre constate que des protocoles de service sont périmés ou en double version sur le réseau intranet. Quelle est la bonne gouvernance documentaire ?",
                    "options": [
                        "Conserver les anciennes versions 'au cas où' sans mention de statut.",
                        "Retirer les versions obsolètes de la diffusion active, valider et diffuser la version unique à jour avec l'équipe, et tracer la mise à jour.",
                        "Demander à chaque agent d'imprimer sa propre version personnelle."
                    ],
                    "rep": "Retirer les versions obsolètes de la diffusion active, valider et diffuser la version unique à jour avec l'équipe, et tracer la mise à jour."
                },
                {
                    "q": "10. [Cadre] Rôle du cadre dans la préparation physique et psychologique de l'équipe à la visite des experts-visiteurs de la HAS :",
                    "options": [
                        "Impliquer les professionnels au quotidien dans la démarche qualité, rendre lisibles les protocoles et libérer la parole de l'équipe pour présenter la réalité des pratiques.",
                        "Faire du trucage de dossiers la veille de la visite pour masquer les non-conformités.",
                        "Interdire au personnel de parler aux experts."
                    ],
                    "rep": "Impliquer les professionnels au quotidien dans la démarche qualité, rendre lisibles les protocoles et libérer la parole de l'équipe pour présenter la réalité des pratiques."
                }
            ]
        },
        "fiches_reflexes": {
            "IDE": {
                "class": "memo-box-ide",
                "slug": "ide",
                "points": [
                    "**Identitovigilance Rigoureuse** : Exigence absolue du triptyque conforme (Nom de naissance, Prénom, Date de naissance) sur le bracelet avant tout soin critique.",
                    "**Déclaration des Quasi-Erreurs** : Systématisation des Fiches d'Événements Indésirables (FEI) pour tout 'near-miss' afin d'améliorer la barrière systémique.",
                    "**Sécurité Médicamenteuse & Allergies** : Vérification des antécédents/allergies, interdiction des préparations sans étiquetage nominatif immédiat et respect strict du patient unique.",
                    "**Traçabilité & Consignes de Sortie** : Régularisation rigoureuse des actes dans le DPI, sécurisation des prélèvements/examens et vérification de la compréhension des consignes."
                ]
            },
            "Medecin": {
                "class": "memo-box-med",
                "slug": "medecin",
                "points": [
                    "**Culture Juste & Analyse Systémique** : Implication active dans les RMM/CREX suite à un EIGAS, en bannissant la recherche de bouc émissaire individuel.",
                    "**Continuité des Soins & Sorties** : Signature et transmission immédiate de la lettre de liaison de sortie pour prévenir la iatrogénie post-urgences.",
                    "**Décisions Lourdes & Sécurité Transfusionnelle** : Formalisation des procédures collégiales d'urgence et respect strict des règles d'identitovigilance et de sécurité transfusionnelle.",
                    "**Méthodologie Patient Traceur** : Garantie d'une traçabilité irréprochable dans le DPI et suivi des résultats critiques pour répondre aux exigences d'audit de la HAS."
                ]
            },
            "AS": {
                "class": "memo-box-as",
                "slug": "as",
                "points": [
                    "**Vigie de l'Identité** : Contrôle systématique de la présence et de la conformité du bracelet d'identitovigilance au poignet des patients.",
                    "**Précautions d'Hygiène & Risques Cliniques** : Application des précautions complémentaires adaptées (ex: FFP2 si besoin), contrôle du jeûne et des régimes/textures avant remise alimentaire.",
                    "**Sécurité Environnementale & Produits** : Signalement immédiat des produits non étiquetés et alerte rapide de l'IDE en cas de mobilisation/coudure d'un dispositif.",
                    "**Signalement Précoce** : Remontée immédiate à l'IDE et au cadre de toute lésion suspecte, situation de maltraitance ou quasi-accident."
                ]
            },
            "ARM (Assistant/e de Régulation Médicale)": {
                "class": "memo-box-arm",
                "slug": "arm",
                "points": [
                    "**Premier Maillon de Sécurité** : Qualification rigoureuse du triptyque d'identitovigilance, de la localisation et des critères de gravité dès le premier décroché au SAMU 15.",
                    "**Gestion des Homonymies & Rectifications** : Traitement strict des dossiers multiples et mise à jour immédiate/tracée de toute erreur de localisation ou d'aiguillage.",
                    "**Traçabilité de Crise & Inaltérabilité** : Conservation des enregistrements audio et utilisation rigoureuse des mains courantes informatisées ou papiers en mode dégradé.",
                    "**Secret Professionnel & Confidentialité** : Refus absolu de divulgation d'informations nominatives aux tiers non habilités par téléphone."
                ]
            },
            "Accueil": {
                "class": "memo-box-acc",
                "slug": "accueil",
                "points": [
                    "**Barrière d'Accueil 24h/24** : Vérification de l'identité sur justificatifs valides pour éviter le télescopage de dossiers.",
                    "**Secret Médical & Situations Particulières** : Préservation de la confidentialité au guichet, non-divulgation aux tiers non habilités et vigilance particulière pour les mineurs.",
                    "**Protection des Valeurs & Sécurité** : Application stricte des inventaires contradictoires et alerte rapide face aux situations à risque.",
                    "**Veille & Communication** : Explication claire du tri par gravité aux familles et alerte immédiate de l'équipe soignante en cas de besoin clinique."
                ]
            },
            "Brancardier": {
                "class": "memo-box-branc",
                "slug": "brancardier",
                "points": [
                    "**Vérification Préalable Bracelet & Dossiers** : Contrôle de la présence du bracelet conforme et concordance de l'identité sur les documents/examens remis lors des transports.",
                    "**Sécurité des Dispositifs Associés** : Arrimage parfait et sécurisé des obus d'oxygène et respect absolu de la règle de non-manipulation des pompes/perfusions.",
                    "**Continuité & Sécurité du Transfert** : Ne jamais laisser un patient sans prise en charge sécurisée lors d'un transfert et vérifier le verrouillage des ridelles.",
                    "**Hygiène & Bio-nettoyage** : Désinfection systématique des points de contact du brancard entre chaque patient, particulièrement en cas de transport à risque (BMR)."
                ]
            },
            "ASH": {
                "class": "memo-box-ash",
                "slug": "ash",
                "points": [
                    "**Maîtrise des Filières de Déchets** : Distinction rigoureuse et tri strict entre les filières DAOM, DASRI et déchets cytotoxiques.",
                    "**Sécurité Chimique & Souillures** : Interdiction formelle de transvaser des produits d'entretien dans des contenants alimentaires, sécurisation des souillures et suivi des FDS/fuites.",
                    "**Hygiène des Mains & EPI** : Pratique systématique de la friction hydro-alcoolique et port des équipements de protection adaptés lors des bio-nettoyages terminaux.",
                    "**Respect du Matériel Soignant** : Interdiction absolue de manipuler ou déplacer les chariots et plans de travail mobiles de soins en l'absence des infirmiers."
                ]
            },
            "Cadre": {
                "class": "memo-box-cadre",
                "slug": "cadre",
                "points": [
                    "**Culture Juste & REX** : Animation des revues de mortalité/morbidité (RMM) et des CREX sans esprit de blâme individuel pour corriger les défaillances de système.",
                    "**Pilotage des Audits Flash & Documents** : Évaluation continue des pratiques (EPP) par audits ciblés et garantie d'une gestion documentaire à jour sans doublons périmés.",
                    "**Management de la Sécurité des Soins** : Sanctuarisation des barrières critiques incompressibles comme le double contrôle des MHR malgré les tensions de flux.",
                    "**Accompagnement & Tutorat** : Mise en place de parcours d'intégration sécurisés pour les nouveaux arrivants et veille attentive face à l'épuisement des équipes."
                ]
            }
        }
    },
        {
        "id": 6,
        "titre": "Semaine 6 - Qualité de Vie au Travail, Prévention des Violences & Culture d'Évaluation",
        "date_debut": datetime.date(2026, 11, 30),
        "date_fin": datetime.date(2026, 12, 6),
        "tronc_commun": [],
        "metiers": {},
        "fiches_reflexes": {}
        },
    {
        "id": 7,
        "titre": "Semaine 7 - Coordination Ville-Hôpital, Pertinence des Soins & Orientations",
        "date_debut": datetime.date(2026, 12, 7),
        "date_fin": datetime.date(2026, 12, 13),
        "tronc_commun": [],
        "metiers": {},
        "fiches_reflexes": {}
    },
    {
        "id": 8,
        "titre": "Semaine 8 - Éthique Clinique, Transparence & Mesures Restrictives",
        "date_debut": datetime.date(2026, 12, 14),
        "date_fin": datetime.date(2026, 12, 20),
        "tronc_commun": [],
        "metiers": {},
        "fiches_reflexes": {}
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
# 5. BANNIÈRE EN-TÊTE AVEC VOS LOGOS DUAL (logo & logo2)
# ------------------------------------------------------------------------------
col_logo_gauche, col_titre, col_logo_droite = st.columns([1, 4, 1])

# --- LOGO 1 (À GAUCHE) ---
with col_logo_gauche:
    try:
        st.markdown("<div class='service-logo' style='text-align: center;'>", unsafe_allow_html=True)
        fichier_logo1 = "logo.jpg" if os.path.exists("logo.jpg") else "logo.png"
        st.image(fichier_logo1, width=110)
        st.markdown("</div>", unsafe_allow_html=True)
    except Exception:
        st.caption("⚠️ Logo gauche introuvable")

# --- TITRE CENTRAL ---
with col_titre:
    st.markdown("<h1 class='main-title' style='text-align: center;'>🧠 Pause Révision HAS 2027</h1>", unsafe_allow_html=True)
    st.markdown("<h3 class='subtitle' style='text-align: center;'>Service des Urgences & SAMU — Mulhouse</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color:#64748b; margin-bottom:0; text-align: center;'>Plateforme ludo-pédagogique d'équipe pour la préparation à la certification</p>", unsafe_allow_html=True)
    st.markdown("<p style='color:#64748b; margin-bottom:0; text-align: center;'> ⚠️ ATTENTION : mettez l'affichage en 'Light' en haut à droite, sinon le texte sera blanc... sur blanc</p>", unsafe_allow_html=True)

# --- LOGO 2 (À DROITE) ---
with col_logo_droite:
    try:
        st.markdown("<div class='service-logo' style='text-align: center;'>", unsafe_allow_html=True)
        fichier_logo2 = "logo2.png" if os.path.exists("logo2.png") else "logo2.jpg"
        st.image(fichier_logo2, width=110)
        st.markdown("</div>", unsafe_allow_html=True)
    except Exception:
        st.caption("⚠️ Logo droit (logo2) introuvable")

st.divider()

# ------------------------------------------------------------------------------
# 6. ÉCRAN D'AUTHENTIFICATION (VIGNETTES ANIMALES & FILTRAGE STRICT)
# ------------------------------------------------------------------------------
if "user_pseudo" not in st.session_state:
    params = st.query_params
    if "pseudo" in params:
        st.session_state.user_pseudo = params["pseudo"]

if not st.session_state.user_pseudo:
    tab_login, tab_register = st.tabs(["🔑 Se connecter", "✨ Créer un compte (1ère visite)"])
    comptes_existants = charger_utilisateurs()

    # --- ONGLET 1 : CONNEXION PAR VIGNETTE ANIMAL + FILTRAGE PSEUDOS ---
    with tab_login:
        st.markdown("<div class='auth-card-header'><h3 style='color:#0f766e; margin:0;'>Connexion rapide à votre espace</h3><p style='color:#64748b; font-size:0.9rem; margin-top:5px;'>Sélectionnez votre animal pour retrouver votre profil créé lors de la première visite</p></div>", unsafe_allow_html=True)
        
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
                    st.warning(f"Aucun compte enregistré pour l'animal {animal_actif}. Créez-en un dans l'onglet 'Première visite' !")
                else:
                    pseudo_choisi = st.selectbox("Étape 2 : Choisissez votre Pseudo dans la liste :", options=pseudos_animal)
                    mdp_saisi = st.text_input("Étape 3 : Code secret / Mot de passe :", type="password", key="login_mdp")

                    if st.button("🚀 Me connecter", type="primary", use_container_width=True):
                        if mdp_saisi:
                            mdp_attendu = comptes_existants.get(pseudo_choisi)
                            if str(mdp_saisi) == str(mdp_attendu):
                                st.session_state.user_pseudo = pseudo_choisi
                                st.query_params["pseudo"] = pseudo_choisi
                                st.rerun()
                            else:
                                st.error("Mot de passe incorrect !")
                        else:
                            st.warning("Veuillez saisir votre mot de passe.")

    # --- ONGLET 2 : CRÉATION DE COMPTE (VIGNETTES ANIMALES + ADJECTIF) ---
    with tab_register:
        st.markdown("""
            <div class='auth-card-header'>
                <h3 style='color:#0f766e; margin:0;'>😷 Créez votre Avatar & Mot de passe</h3>
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
                            if ajouter_utilisateur(pseudo_cree, nouveau_mdp, animal_choisi):
                                st.session_state.user_pseudo = pseudo_cree
                                st.query_params["pseudo"] = pseudo_cree
                                st.success(f"Compte créé avec succès ! Bienvenue {pseudo_cree}.")
                                st.rerun()

    st.stop()
else:
    st.query_params["pseudo"] = st.session_state.user_pseudo

# ------------------------------------------------------------------------------
# 7. TABLEAU DE BORD CONNECTÉ
# ------------------------------------------------------------------------------
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
        st.session_state.pop("questions_courantes", None)
        st.rerun()

st.markdown("<h2 style='color:#0f766e; margin-top:15px;'>🗃️ Tableau de bord des Révisions</h2>", unsafe_allow_html=True)

tab_actuel, tab_progression, tab_historique, tab_avenir, tab_podium = st.tabs([
    "🤔❓ Semaine Actuelle", 
    "🥳 Ma Progression", 
    "🧐 Archives & Fiches Mémos", 
    "⌛ Semaines À Venir",
    "🏆 Podium"
])

# --- TAB 1 : QUIZ INTERACTIF (PARCOURS STRICT ET SÉQUENTIEL) ---
with tab_actuel:
    mes_notes_utilisateur = charger_notes_utilisateur(st.session_state.user_pseudo)
    semaines_validees = [str(item.get("Semaine_ID")) for item in mes_notes_utilisateur]

    sessions_ouvertes = sorted(
        [s for s in SESSIONS if obtenir_statut_session(s) in ["Actuelle", "Passee"] or s["id"] == 0],
        key=lambda x: x["id"]
    )

    # 🔒 PROTECTION : Si un quiz est déjà en cours dans le state et non validé, on le verrouille !
    active_id_en_cours = st.session_state.get("session_id_courante")
    session_active = None
    
    if active_id_en_cours is not None and str(active_id_en_cours) not in semaines_validees:
        session_active = next((s for s in sessions_ouvertes if s["id"] == active_id_en_cours), None)

    # Sinon, on détermine la première session non validée
    if session_active is None:
        for s in sessions_ouvertes:
            if str(s["id"]) not in semaines_validees:
                session_active = s
                break

    tous_les_quiz_faits = (session_active is None)
    if tous_les_quiz_faits and sessions_ouvertes:
        session_active = sessions_ouvertes[-1]

    if not sessions_ouvertes:
        st.info("🔒 Aucune session de quiz n'est ouverte aujourd'hui.")
    else:
        if tous_les_quiz_faits:
            st.success("🏆 Bravo ! Tu as validé tous les quiz disponibles jusqu'à présent dans l'ordre.")
            st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            f"<div class='card-actuelle'><h3 style='color:#0f766e;'>📝 {session_active['titre']}</h3><p style='color:#64748b; font-size:0.9rem;'>⚡ Parcours séquentiel guidé</p></div>",
            unsafe_allow_html=True
        )

        deja_fait = str(session_active["id"]) in semaines_validees

        if deja_fait and not st.session_state.get(f"force_recommencer_{session_active['id']}", False):
            st.success("🎉 Tu as déjà validé le quiz de cette session !")
            
            derniere_note = next((item for item in mes_notes_utilisateur if str(item.get("Semaine_ID")) == str(session_active["id"])), None)
            if derniere_note:
                st.metric("Ton score enregistré", f"{derniere_note.get('Score')} / {derniere_note.get('Total_Questions')}")

            st.markdown("<br>", unsafe_allow_html=True)
            if tous_les_quiz_faits:
                if st.button("🔄 Recommencer ce quiz pour le plaisir", type="primary", use_container_width=True):
                    st.session_state[f"force_recommencer_{session_active['id']}"] = True
                    st.session_state.current_q_index = 0
                    st.session_state.user_quiz_answers = {}
                    st.session_state.pop("questions_courantes", None)
                    st.rerun()
            else:
                st.info("👉 Passe à la session suivante ou attends l'ouverture de la prochaine.")
        else:
            if st.session_state.quiz_paused:
                st.warning(f"⏸️ **Quiz en pause !** Tu étais à la question {st.session_state.current_q_index + 1}.")
                c_rep, c_raz = st.columns([1, 1])
                with c_rep:
                    if st.button("▶️ Reprendre", type="primary", use_container_width=True):
                        st.session_state.quiz_paused = False
                        st.rerun()
                with c_raz:
                    if st.button("🔄 Recommencer", type="secondary", use_container_width=True):
                        st.session_state.current_q_index = 0
                        st.session_state.user_quiz_answers = {}
                        st.session_state.quiz_paused = False
                        st.session_state.pop("questions_courantes", None)
                        st.session_state.pop("session_id_courante", None)
                        st.session_state.pop(f"force_recommencer_{session_active['id']}", None)
                        st.rerun()
            else:
                metiers_tries_alphabetique = [
                    "-- Choisir ma fonction --",
                    "ARM (Assistant/e de Régulation Médicale)",
                    "AS (Aide-Soignant/e)",
                    "ASH (Agent de Service Hospitalier)",
                    "Brancardier",
                    "Cadre de Santé / Encadrement",
                    "Hôte / Hôtesse d'accueil & Admission",
                    "IDE (Infirmier/ère)",
                    "Medecin"
                ]

                role_soignant = st.selectbox(
                    "Sélectionnez votre fonction pour personnaliser votre parcours :",
                    options=metiers_tries_alphabetique,
                    key="select_role_soignant"
                )

                if role_soignant != "-- Choisir ma fonction --":
                    if "questions_courantes" not in st.session_state or st.session_state.get("role_actif") != role_soignant or st.session_state.get("session_id_courante") != session_active["id"]:
                        st.session_state.role_actif = role_soignant
                        st.session_state.session_id_courante = session_active["id"]
                        q_liste = list(session_active.get("tronc_commun", []))
                        
                        if "IDE" in role_soignant:
                            q_liste.extend(session_active["metiers"].get("IDE", []))
                        elif "AS (" in role_soignant:
                            q_liste.extend(session_active["metiers"].get("AS", []))
                        elif "Medecin" in role_soignant:
                            q_liste.extend(session_active["metiers"].get("Medecin", []))
                        elif "ARM (Assistant/e de Régulation Médicale)" in role_soignant:
                            q_liste.extend(session_active["metiers"].get("ARM (Assistant/e de Régulation Médicale)", []))
                        elif "accueil" in role_soignant:
                            q_liste.extend(session_active["metiers"].get("Accueil", []))
                        elif "Brancardier" in role_soignant:
                            q_liste.extend(session_active["metiers"].get("Brancardier", []))
                        elif "ASH" in role_soignant:
                            q_liste.extend(session_active["metiers"].get("ASH", []))
                        elif "Cadre" in role_soignant:
                            q_liste.extend(session_active["metiers"].get("Cadre", []))
                            
                        st.session_state.questions_courantes = q_liste
                        st.session_state.current_q_index = 0
                        st.session_state.user_quiz_answers = {}

                    questions_quiz = st.session_state.questions_courantes
                    total_q = len(questions_quiz)
                    current_idx = st.session_state.current_q_index

                    if current_idx < total_q:
                        q_data = questions_quiz[current_idx]
                        
                        col_prog, col_pause = st.columns([4, 1])
                        with col_prog:
                            st.progress((current_idx + 1) / total_q)
                            st.caption(f"Question {current_idx + 1} sur {total_q}")
                        with col_pause:
                            if st.button("⏸️ Pause", key=f"pause_btn_{current_idx}"):
                                st.session_state.quiz_paused = True
                                st.rerun()

                        st.markdown(f"""
                            <div class="question-card">
                                <span class="question-badge">{'Tronc Commun' if current_idx < 5 else 'Spécifique ' + role_soignant.split(' ')[0]}</span>
                                <div class="question-title">{q_data['q']}</div>
                            </div>
                        """, unsafe_allow_html=True)

                        existing_ans = st.session_state.user_quiz_answers.get(current_idx, None)
                        def_index = q_data["options"].index(existing_ans) if existing_ans in q_data["options"] else 0
                        
                        choix = st.radio(
                            "Sélectionnez votre réponse :", 
                            q_data["options"], 
                            index=def_index if existing_ans else None,
                            key=f"radio_q_{session_active['id']}_{current_idx}"
                        )

                        st.markdown("<br>", unsafe_allow_html=True)
                        col_prev, col_next = st.columns([1, 1])

                        with col_prev:
                            if current_idx > 0:
                                if st.button("⬅️ Précédent", key=f"prev_{current_idx}", use_container_width=True):
                                    if choix:
                                        st.session_state.user_quiz_answers[current_idx] = choix
                                    st.session_state.current_q_index -= 1
                                    st.rerun()

                        with col_next:
                            btn_label = "Suivant ➡️" if current_idx < total_q - 1 else "🏁 Terminer & Valider"
                            if st.button(btn_label, key=f"next_{current_idx}", type="primary", use_container_width=True):
                                if not choix and not existing_ans:
                                    st.warning("Veuillez sélectionner une réponse !")
                                else:
                                    st.session_state.user_quiz_answers[current_idx] = choix if choix else q_data["options"][0]
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

                        if enregistrer_reponse(st.session_state.user_pseudo, session_active["id"], score_obtenu, total_q, role=role_soignant):
                            st.success(f"Félicitations **{st.session_state.user_pseudo}** ! Vos résultats ont bien été enregistrés pour la session {session_active['titre']}.")

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
                                    {f'<div style="font-size:0.95rem; color:#15803d; font-weight:700;"><strong>Bonne réponse :</strong> {q["rep"]}</div>' if not est_correct else ''}
                                </div>
                            """, unsafe_allow_html=True)

                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("🔄 Recommencer", key="restart_quiz_btn", type="primary"):
                            st.session_state.current_q_index = 0
                            st.session_state.user_quiz_answers = {}
                            st.session_state.quiz_paused = False
                            st.session_state.pop("questions_courantes", None)
                            st.session_state.pop("session_id_courante", None)
                            st.session_state.pop(f"force_recommencer_{session_active['id']}", None)
                            st.rerun()
                            
# --- TAB 2 : MA PROGRESSION ---
with tab_progression:
    st.markdown("<div class='card-progression'>", unsafe_allow_html=True)
    st.markdown(f"### 📈 Progression de **{st.session_state.user_pseudo}**")
    
    mes_notes = charger_notes_utilisateur(st.session_state.user_pseudo)
    
    if not mes_notes:
        st.info("Tu n'as pas encore répondu à un quiz. Participe à la semaine actuelle pour voir apparaître tes statistiques !")
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

# --- TAB 3 : ARCHIVES & FICHES MÉMOS ---
with tab_historique:
    st.header("📜 Archives, Synthèses & Fiches Mémos")
    st.markdown("Retrouvez ici l'historique cumulé des synthèses ainsi que la bibliothèque des fiches mémos officielles.")
    
    sub_tab_synthese, sub_tab_fiches = st.tabs(["📚 Synthèse (Cumulée)", "📑 Fiches Mémos par Semaine"])
    
    sessions_passees = [s for s in SESSIONS if obtenir_statut_session(s) in ["Passee", "Actuelle"] or s["id"] == 0]
    
    with sub_tab_synthese:
        st.subheader("Rappels et Synthèses par Semaine (Cumulatif)")
        st.markdown("Au fil des clôtures de semaines, les points clés s'ajoutent ici pour constituer votre référentiel de révision. *(Note : La synthèse de la semaine en cours se débloque une fois le quiz validé !)*")
        
        if not sessions_passees:
            st.info("Aucune synthèse disponible pour le moment.")
        else:
            mes_notes_actuelles = charger_notes_utilisateur(st.session_state.user_pseudo)
            semaines_validees_ids = [str(item.get("Semaine_ID")) for item in mes_notes_actuelles]

            for s in sessions_passees:
                str_debut = s['date_debut'].strftime('%d/%m/%Y') if hasattr(s['date_debut'], 'strftime') else s['date_debut']
                str_fin = s['date_fin'].strftime('%d/%m/%Y') if hasattr(s['date_fin'], 'strftime') else s['date_fin']
                
                statut = obtenir_statut_session(s)
                est_valide = str(s["id"]) in semaines_validees_ids
                
                if statut == "Actuelle" and not est_valide and s["id"] != 0:
                    with st.expander(f"🔒 {s['titre']} (Verrouillé - Quiz en cours)"):
                        st.warning("⚠️ Cette synthèse se débloquera automatiquement ici dès que tu auras validé le quiz de cette semaine dans l'onglet 'Semaine Actuelle' !")
                else:
                    with st.expander(f"📌 {s['titre']} (Du {str_debut} au {str_fin})", expanded=(s["id"] == max([x["id"] for x in sessions_passees if obtenir_statut_session(x) == "Passee" or str(x["id"]) in semaines_validees_ids], default=0))):
                        if "fiches_reflexes" in s:
                            fiches = s["fiches_reflexes"]
                            if fiches:
                                onglets_metiers = list(fiches.keys())
                                tabs_m = st.tabs(onglets_metiers)
                                
                                for idx_m, nom_m in enumerate(onglets_metiers):
                                    fiche_info = fiches[nom_m]
                                    css_class = fiche_info.get("class", "memo-box-tc")
                                    points_list = fiche_info.get("points", [])
                                    
                                    with tabs_m[idx_m]:
                                        st.markdown(f"<div class='{css_class}'><div class='memo-title-text'>Synthèse HAS — {nom_m}</div>", unsafe_allow_html=True)
                                        for pt in points_list:
                                            st.markdown(f"• {pt}")
                                        st.markdown("</div>", unsafe_allow_html=True)
                            else:
                                st.info("Aucune synthèse spécifique pour cette session.")
                                

    with sub_tab_fiches:
        st.subheader("Consultation des Fiches Mémos PDF")
        st.markdown("Retrouve ici les fiches officielles. *(Note : La fiche de la semaine en cours se débloque une fois le quiz validé !)*")
        
        if not sessions_passees:
            st.info("Aucune fiche PDF disponible pour le moment.")
        else:
            mes_notes_actuelles = charger_notes_utilisateur(st.session_state.user_pseudo)
            semaines_validees_ids = [str(item.get("Semaine_ID")) for item in mes_notes_actuelles]

            sessions_fiches_disponibles = []
            for s in sessions_passees:
                statut = obtenir_statut_session(s)
                if statut == "Passee" or str(s["id"]) in semaines_validees_ids or s["id"] == 0:
                    sessions_fiches_disponibles.append(s)

            if not sessions_fiches_disponibles:
                st.warning("🔒 La fiche mémo de la semaine actuelle sera accessible ici dès que tu auras validé ton quiz !")
            else:
                col_s, col_m = st.columns(2)
                with col_s:
                    semaine_choisie = st.selectbox(
                        "Choisis la semaine :",
                        options=sessions_fiches_disponibles,
                        format_func=lambda x: x["titre"],
                        key="select_semaine_fiche_securise"
                    )
                with col_m:
                    fiches_dispo = semaine_choisie.get("fiches_reflexes", {})
                    liste_metiers_fiches = list(fiches_dispo.keys())
                    
                    metier_choisi_cle = st.selectbox(
                        "Choisis ton profil métier :",
                        options=liste_metiers_fiches,
                        key="select_metier_fiche_securise"
                    )
                
                st.markdown("---")
                
                if metier_choisi_cle in fiches_dispo:
                    slug_metier = fiches_dispo[metier_choisi_cle].get("slug", "tronc_commun")
                    
                    afficher_et_telecharger_pdf(
                        semaine_id=semaine_choisie["id"],
                        metier_slug=slug_metier,
                        nom_affichage=metier_choisi_cle
                    )

# --- TAB 4 : SEMAINES À VENIR ---
with tab_avenir:
    st.markdown("<h3 style='color:#0f766e;'>⌛ Prochaines Semaines de Révision</h3>", unsafe_allow_html=True)
    st.markdown("Découvre le calendrier des prochaines thématiques de révision pour la certification HAS 2027.")
    st.markdown("<br>", unsafe_allow_html=True)

    sessions_futures = [s for s in SESSIONS if obtenir_statut_session(s) == "A venir"]
    
    if not sessions_futures:
        st.info("🎯 Tu es actuellement à jour sur toutes les sessions publiées ! Les prochaines semaines de révision seront affichées ici dès leur programmation officielle.")
    else:
        for s in sessions_futures:
            str_debut = s['date_debut'].strftime('%d/%m/%Y') if hasattr(s['date_debut'], 'strftime') else s['date_debut']
            str_fin = s['date_fin'].strftime('%d/%m/%Y') if hasattr(s['date_fin'], 'strftime') else s['date_fin']
            
            st.markdown(
                f"<div class='card-avenir'><h4 style='color:#b45309;'>🔒 {s['titre']}</h4><p style='margin:0;'>📅 Ouverture prévue du <strong>{str_debut} au {str_fin}</strong></p></div>",
                unsafe_allow_html=True
            )
            
# --- TAB 5 : PODIUMS PAR MÉTIER & GÉNÉRAL ---
with tab_podium:
    st.markdown("<h3 style='color:#0f766e;'>🏆 Podiums & Classements de l'Équipe</h3>", unsafe_allow_html=True)
    st.markdown("*(Classements cumulatifs basés uniquement sur le score de la **première participation** de chaque semaine)*")
    st.markdown("<br>", unsafe_allow_html=True)

    podiums_data = calculer_scores_podium_par_metier()

    if not podiums_data:
        st.info("Aucun score enregistré pour l'instant. Soyez le premier à valider un quiz !")
    else:
        metiers_disponibles = sorted(list(podiums_data.keys()))
        tabs_podiums = st.tabs(["🌟 Général"] + [f"🩺 {m}" for m in metiers_disponibles])
        
        with tabs_podiums[0]:
            st.markdown("#### 🌟 Top 10 Général de l'Équipe")
            st.markdown("<br>", unsafe_allow_html=True)
            
            classement_general = calculer_scores_podium()
            if not classement_general:
                st.info("Aucun score général pour le moment.")
            else:
                for idx, user_data in enumerate(classement_general[:10]):
                    rang = idx + 1
                    if rang == 1:
                        medaille = "🥇"
                        card_bg = "background: linear-gradient(135deg, #fef08a 0%, #fde047 100%); border: 2px solid #eab308;"
                    elif rang == 2:
                        medaille = "🥈"
                        card_bg = "background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%); border: 2px solid #94a3b8;"
                    elif rang == 3:
                        medaille = "🥉"
                        card_bg = "background: linear-gradient(135deg, #fed7aa 0%, #fdba74 100%); border: 2px solid #f97316;"
                    else:
                        medaille = f"#{rang}"
                        card_bg = "background: #ffffff; border: 1px solid #cbd5e1;"

                    st.markdown(f"""
                        <div style="{card_bg} border-radius: 16px; padding: 15px 20px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 10px rgba(0,0,0,0.03);">
                            <div style="display: flex; align-items: center; gap: 15px;">
                                <span style="font-size: 1.5rem; font-weight: 800; min-width: 40px; text-align: center;">{medaille}</span>
                                <span style="font-size: 1.1rem; font-weight: 700; color: #1e293b;">{user_data['Pseudo']}</span>
                            </div>
                            <div style="text-align: right;">
                                <span style="font-size: 1.1rem; font-weight: 800; color: #0f766e;">{user_data['Total_Points']} pts</span>
                                <span style="display: block; font-size: 0.8rem; color: #64748b;">({user_data['Quiz_Completes']} quiz validés)</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

        for idx_m, metier in enumerate(metiers_disponibles):
            with tabs_podiums[idx_m + 1]:
                st.markdown(f"#### 🎯 Podium — {metier}")
                st.markdown("<br>", unsafe_allow_html=True)
                
                classement_metier = podiums_data.get(metier, [])
                
                if not classement_metier:
                    st.info("Aucun participant dans cette catégorie pour le moment.")
                else:
                    for idx, user_data in enumerate(classement_metier[:10]):
                        rang = idx + 1
                        if rang == 1:
        
                            medaille = "🥇"
                            card_bg = "background: linear-gradient(135deg, #fef08a 0%, #fde047 100%); border: 2px solid #eab308;"
                        elif rang == 2:
                            medaille = "🥈"
                            card_bg = "background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%); border: 2px solid #94a3b8;"
                        elif rang == 3:
                            medaille = "🥉"
                            card_bg = "background: linear-gradient(135deg, #fed7aa 0%, #fdba74 100%); border: 2px solid #f97316;"
                        else:
                            medaille = f"#{rang}"
                            card_bg = "background: #ffffff; border: 1px solid #cbd5e1;"

                        st.markdown(f"""
                            <div style="{card_bg} border-radius: 16px; padding: 15px 20px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 10px rgba(0,0,0,0.03);">
                                <div style="display: flex; align-items: center; gap: 15px;">
                                    <span style="font-size: 1.5rem; font-weight: 800; min-width: 40px; text-align: center;">{medaille}</span>
                                    <span style="font-size: 1.1rem; font-weight: 700; color: #1e293b;">{user_data['Pseudo']}</span>
                                </div>
                                <div style="text-align: right;">
                                    <span style="font-size: 1.1rem; font-weight: 800; color: #0f766e;">{user_data['Total_Points']} pts</span>
                                    <span style="display: block; font-size: 0.8rem; color: #64748b;">({user_data['Quiz_Completes']} quiz validés)</span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
