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
        border-radius
