import streamlit as st
import pandas as pd
import openai
from datetime import datetime
import os
import re

# Configuration de l'API OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")

def process_csv(uploaded_files):
    """Lit et traite plusieurs fichiers CSV."""
    all_dataframes = []

    for csv_file in uploaded_files:
        df = pd.read_csv(csv_file)
        all_dataframes.append(df)

    # Fusionner tous les fichiers en un seul DataFrame
    df = pd.concat(all_dataframes, ignore_index=True)

    # Vérifier la colonne 'Created at'
    if 'Created at' not in df.columns:
        st.error("La colonne 'Created at' est introuvable dans les fichiers CSV.")
        return None, None

    # 🎯 **Étape 1 : Afficher les valeurs brutes**
    st.write("🔍 **Extrait brut de la colonne 'Created at' avant conversion :**")
    st.dataframe(df[['ID', 'Created at']].head(20))  # Afficher les 20 premières lignes

    # 🎯 **Étape 2 : Essai de conversion avec détection des erreurs**
    try:
        df['Created at'] = pd.to_datetime(df['Created at'], errors='coerce')
    except Exception as e:
        st.write("❌ **Erreur lors de la conversion de 'Created at' en datetime :**", e)

    # 🎯 **Étape 3 : Identifier les valeurs invalides**
    invalid_dates = df[df['Created at'].isna()][['ID', 'Created at']]
    if not invalid_dates.empty:
        st.write("⚠️ **Valeurs impossibles à convertir en datetime :**")
        st.dataframe(invalid_dates)

    # 🎯 **Étape 4 : Correction automatique des formats**
    df['Created at'] = df['Created at'].astype(str).str.strip()  # Supprimer les espaces
    df['Created at'] = df['Created at'].str.replace('T', ' ')  # Remplacer 'T' par un espace (format ISO)
    # Conversion de "Created at" en datetime
    df['Created at'] = pd.to_datetime(df['Created at'], errors='coerce')

    # Vérifier si certaines valeurs sont NaT après conversion
    invalid_dates = df[df['Created at'].isna()]
    if not invalid_dates.empty:
        st.write("⚠️ **Certaines dates n'ont pas pu être converties en datetime :**")
        st.dataframe(invalid_dates[['ID', 'Created at']])

    # Normalisation des fuseaux horaires : Convertir toutes les dates en UTC
    df['Created at'] = df['Created at'].dt.tz_convert(None)  # Supprime les informations de fuseau horaire

    # 🚀 Filtrage : Suppression des abonnements créés après le 5 du mois
    today = datetime.today()
    start_date = datetime(today.year, today.month, 5)  # Cette date est sans fuseau horaire

    df_before_filtering = len(df)
    df = df[df['Created at'] < start_date]  # Comparaison entre dates maintenant uniformisées
    df_after_filtering = len(df)

    st.write(f"🚀 **Avant le filtrage : {df_before_filtering} abonnements**")
    st.write(f"✅ **Après le filtrage : {df_after_filtering} abonnements (supprimés : {df_before_filtering - df_after_filtering})**")
    


    # 🎯 **Étape 5 : Vérifier après correction**
    invalid_dates_after_correction = df[df['Created at'].isna()][['ID', 'Created at']]
    if not invalid_dates_after_correction.empty:
        st.write("⚠️ **Valeurs toujours impossibles à convertir après correction :**")
        st.dataframe(invalid_dates_after_correction)

    # Vérification de la colonne 'Status'
    if 'Status' not in df.columns:
        st.error("La colonne 'Status' est introuvable dans les fichiers CSV.")
        return None, None

    df['Status'] = df['Status'].str.upper()

    # Vérification de la colonne 'Next order date'
    if 'Next order date' not in df.columns:
        st.error("La colonne 'Next order date' est introuvable dans les fichiers CSV.")
        return None, None

    # Filtrage des abonnements actifs et annulés
    active_df = df[df['Status'] == 'ACTIVE']
    cancelled_df = df[df['Status'] == 'CANCELLED']

    # Supprimer les abonnements test (Brice N Guessan / Brice N'Guessan)
    cancelled_df = cancelled_df[~cancelled_df['Customer name'].str.contains(r"Brice N'?Guessan", case=False, na=False, regex=True)]

    return active_df, cancelled_df

# Interface utilisateur Streamlit
st.title("Gestion des abonnements annulés et actifs")
file_prefix = st.text_input("Entrez le préfixe pour les fichiers finaux :", "")
uploaded_files = st.file_uploader("Téléversez les fichiers CSV des abonnements", type="csv", accept_multiple_files=True)

if uploaded_files:
    active_df, cancelled_df = process_csv(uploaded_files)

    if active_df is not None and cancelled_df is not None:
        st.write(f"📌 **Aperçu des données finales pour les abonnements actifs ({len(active_df)} lignes) :**")
        st.dataframe(active_df)

        st.write(f"📌 **Aperçu des données finales pour les abonnements annulés ({len(cancelled_df)} lignes) :**")
        st.dataframe(cancelled_df)
