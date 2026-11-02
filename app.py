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

def charger_utilisateurs():
    try:
        sheet = get_sheet().worksheet("Utilisateurs")
        records = sheet.get_all_records()
        return {str(r["Pseudo"]): str(r.get("Mot_De_Passe", "")) for r in records if "Pseudo" in r and r["Pseudo"]}
    except Exception:
        return {}

def ajouter_utilisateur(pseudo, mdp, animal=""):
    try:
        sheet = get_sheet().worksheet("Utilisateurs")
        date_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        sheet.append_row([date_str, str(pseudo), str(mdp), str(animal)])
        return True
    except Exception as e:
        st.error(f"Erreur d'enregistrement Google Sheets : {e}")
        return False

@st.cache_data(ttl=60)
def charger_notes_utilisateur_cached(pseudo):
    try:
        sheet = get_sheet().worksheet("Reponses")
        records = sheet.get_all_records()
        return [r for r in records if str(r.get("Pseudo")) == str(pseudo)]
    except Exception:
        return []

def charger_notes_utilisateur(pseudo):
    return charger_notes_utilisateur_cached(pseudo)

def enregistrer_reponse(pseudo, semaine_id, score, total, role=""):
    try:
        sheet = get_sheet().worksheet("Reponses")
        date_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        sheet.append_row([date_str, str(pseudo), int(semaine_id), int(score), int(total), str(role)])
        return True
    except Exception as e:
        st.error(f"Erreur de sauvegarde : {e}")
        return False

def charger_top10_semaine(semaine_id):
    try:
        sheet = get_sheet().worksheet("Reponses")
        records = sheet.get_all_records()
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
        sheet = get_sheet().worksheet("Reponses")
        records = sheet.get_all_records()
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
        sheet = get_sheet().worksheet("Reponses")
        records = sheet.get_all_records()
        scores_par_metier = {}
        
        for r in records:
            pseudo = str(r.get("Pseudo"))
            semaine_id = str(r.get("Semaine_ID"))
            metier = str(r.get("Role", r.get("Metier", "Autre"))).strip()
            if not metier or metier == "":
                metier = "Général / Non renseigné"
                
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
                {"q": "9. [Module Médecin] Quelle information minimale doit obligatoirement être tracée dans le Dossier Patient Informatisé lors d'une sortie contre avis médical ?", "options": ["L'information claire délivrée sur les risques vitaux encourus, la proposition d'alternatives et la signature du formulaire dédié", "La mention 'Patient parti' sans autre précision", "Le règlement des frais de séjour"], "rep": "L'information claire délivrée sur les risques vitaux encourus, la proposition d'alternatives et la signature du formulaire dédié"},
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
    },
     {
        "id": 2,
        "titre": "Semaine 2 - Situations Sanitaires Exceptionnelles (SSE) & Mode Dégradé",
        "date_debut": datetime.date(2026, 11, 2),
        "date_fin": datetime.date(2026, 11, 15),
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
                        "Sur décision de l'IDE en accord avec les agents de sécurité de l'hôpital et du médecin."
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
            "Médecin": [
                {
                    "q": "6. [Module Médecin] En situation de saturation aiguë des urgences (Plan Blanc), quel critère médico-légal valide la décision de sortie précoce ou d'orientation directe vers l'aval ?",
                    "options": [
                        "L'absence de réclamation du patient après quatre heures d'attente dans les couloirs.",
                        "La formalisation d'une évaluation médicale de sécurité, la validation des critères de stabilité et la transmission des consignes écrites au médecin traitant.",
                        "L'accord tacite du médecin, qui sera tracé plus tard."
                    ],
                    "rep": "La formalisation d'une évaluation médicale de sécurité, la validation des critères de stabilité et la transmission des consignes écrites au médecin traitant."
                },
                {
                    "q": "7. [Module Médecin] Lors d'un afflux massif de victimes (AMV), sur quoi se fonde la doctrine de triage médico-chirurgical (PMA / Accueil des urgences) ?",
                    "options": [
                        "L'ordre d'arrivée chronologique des patients sur le site des urgences.",
                        "La hiérarchisation rapide de la criticité (urgences absolues U1 vs relatives U2/U3) pour optimiser l'allocation immédiate des ressources vitales.",
                        "La réalisation systématique d'un examen clinique médical complet avant l'orientation."
                    ],
                    "rep": "La hiérarchisation rapide de la criticité (urgences absolues U1 vs relatives U2/U3) pour optimiser l'allocation immédiate des ressources vitales."
                },
                {
                    "q": "8. [Module Médecin] En mode dégradé informatique, quelles mentions obligatoires doivent impérativement figurer sur une prescription médicale d'urgence rédigée sur papier ?",
                    "options": [
                        "Le tampon de l'hôpital, la signature et les initiales du médecin.",
                        "L'identification nominative du prescripteur, sa signature manuscrite, la date et l'horodatage de manière lisible.",
                        "La transcription ultérieure par le secrétariat sans contre-signature du médecin prescripteur."
                    ],
                    "rep": "L'identification nominative du prescripteur, sa signature manuscrite, la date et l'horodatage de manière lisible."
                },
                {
                    "q": "9. [Module Médecin] En contexte de tension extrême aux urgences, quelle règle encadre la prise de décision collégiale de limitation ou d'arrêt de traitement (LAT) ?",
                    "options": [
                        "La décision du médecin s'occupant du patient suffit.",
                        "Malgré la situation, il faut respecter la procédure collégiale, la consultation des directives anticipées ou de la personne de confiance, et la traçabilité formelle de la discussion.",
                        "Le report de la discussion au-delà de la fin de la vague épidémique ou de la crise est possible."
                    ],
                    "rep": "Malgré la situation, il faut respecter la procédure collégiale, la consultation des directives anticipées ou de la personne de confiance, et la traçabilité formelle de la discussion."
                },
                {
                    "q": "10. [Module Médecin] Quelle est l'attente majeure de la HAS concernant l'organisation du retour d'expérience (REX) après une séquence de crise SSE ?",
                    "options": [
                        "La constitution d'un rapport de synthèse anonyme classé immédiatement dans les archives de l'hôpital.",
                        "La mise en place d'une analyse systémique non punitive (CREX) des dysfonctionnements pour transformer les retours de terrain en plans d'actions correctives.",
                        "La recherche individuelle d'un responsable à sanctionner en cas de dépassement des délais de prise en charge."
                    ],
                    "rep": "La mise en place d'une analyse systémique non punitive (CREX) des dysfonctionnements pour transformer les retours de terrain en plans d'actions correctives."
                }
            ],
            "ARM": [
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
                        "Respecter strictement le plan de circulation sectorisé et les sens unidirectionnels (séparation des flux entrants/sortants et propres/contaminés) définis par la logistique de crise.",
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
            "Médecin": {
                "class": "memo-box-med",
                "slug": "medecin",
                "points": [
                    "**Régulation & Coordination Interne** : Supervision médicale du tri, arbitrage des priorités d'examens et pilotage des sorties directes vers l'aval.",
                    "**Validation des Prescriptions de Crise** : Traçabilité formalisée des décisions d'urgence sous contrainte de plateau technique dégradé.",
                    "**Commandement Médical & Triage** : Rôle du médecin chef de triage et coordination étroite avec le SAMU-Centre 15.",
                    "**Traçabilité Allégée de Crise** : Conservation des informations cliniques essentielles sur support papier de crise."
                ]
            },
            "ARM": {
                "class": "memo-box-arm",
                "slug": "arm",
                "points": [
                    "**Qualification de l'EIMV** : Recueil normé du triptyque d'alerte (Cinétique, Nombre d'impliqués, Gravité potentielle) pour le médecin régulateur.",
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
        "date_debut": datetime.date(2026, 11, 16),
        "date_fin": datetime.date(2026, 11, 29),
        "tronc_commun": [],
        "metiers": {},
        "fiches_reflexes": {}
    },
    {
        "id": 4,
        "titre": "Semaine 4 - Parcours patient, Fluidité & Sujets vulnérables",
        "date_debut": datetime.date(2026, 11, 30),
        "date_fin": datetime.date(2026, 12, 13),
        "tronc_commun": [],
        "metiers": {},
        "fiches_reflexes": {}
    },
    {
        "id": 5,
        "titre": "Semaine 5 - Gestion des Risques & Identitovigilance",
        "date_debut": datetime.date(2026, 12, 14),
        "date_fin": datetime.date(2026, 12, 31),
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
                    "Médecin"
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
                        elif "Médecin" in role_soignant:
                            q_liste.extend(session_active["metiers"].get("Médecin", []))
                        elif "ARM" in role_soignant:
                            q_liste.extend(session_active["metiers"].get("ARM", []))
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
                            charger_notes_utilisateur_cached.clear()

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
            # Récupération des semaines déjà validées par l'utilisateur
            mes_notes_actuelles = charger_notes_utilisateur(st.session_state.user_pseudo)
            semaines_validees_ids = [str(item.get("Semaine_ID")) for item in mes_notes_actuelles]

            for s in sessions_passees:
                str_debut = s['date_debut'].strftime('%d/%m/%Y') if hasattr(s['date_debut'], 'strftime') else s['date_debut']
                str_fin = s['date_fin'].strftime('%d/%m/%Y') if hasattr(s['date_fin'], 'strftime') else s['date_fin']
                
                statut = obtenir_statut_session(s)
                est_valide = str(s["id"]) in semaines_validees_ids
                
                # Si c'est la semaine actuelle et qu'elle n'est pas encore validée (et pas la démo semaine 0)
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
            # Récupération des semaines déjà validées par l'utilisateur
            mes_notes_actuelles = charger_notes_utilisateur(st.session_state.user_pseudo)
            semaines_validees_ids = [str(item.get("Semaine_ID")) for item in mes_notes_actuelles]

            # Filtrage : on autorise les semaines passées ou celles dont le quiz a déjà été validé
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
        
        # 1. Sous-onglet Général
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

        # 2. Sous-onglets par Métier
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
