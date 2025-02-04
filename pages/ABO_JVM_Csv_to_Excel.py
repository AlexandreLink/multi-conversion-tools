import streamlit as st
import pandas as pd
import openai
from datetime import datetime
import os
import json


# Configuration de l'API OpenAI (utilisation de st.secrets pour la clé API sur Streamlit Cloud)
openai.api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")

def process_csv(csv_file):
    """Lit et traite le fichier CSV."""
    df = pd.read_csv(csv_file)

    # Vérification de la colonne 'Status'
    if 'Status' not in df.columns:
        st.error("La colonne 'Status' est introuvable dans le fichier CSV.")
        return None, None
    df['Status'] = df['Status'].str.upper()

    # Vérification de la colonne 'Next order date'
    if 'Next order date' not in df.columns:
        st.error("La colonne 'Next order date' est introuvable dans le fichier CSV.")
        return None, None

    # Filtrage des abonnements actifs et annulés
    active_df = df[df['Status'] == 'ACTIVE']
    cancelled_df = df[df['Status'] == 'CANCELLED']

    # Exclure Brice N'Guessan des abonnements annulés
    cancelled_df = cancelled_df[~cancelled_df['Customer name'].str.contains("Brice N Guessan", case=False, na=False)]

    return active_df, cancelled_df

def ask_openai_for_filtering(cancelled_df):
    """Envoie les données des abonnements annulés à OpenAI et récupère la liste des ID à réintégrer."""
    if cancelled_df.empty:
        return pd.DataFrame()

    today = datetime.today()
    start_date = datetime(today.year, today.month, 5).strftime('%Y-%m-%d')

    # Afficher la liste des abonnements annulés envoyés à OpenAI avec nombre de lignes
    st.write(f"📋 **Liste des abonnements annulés envoyés à OpenAI ({len(cancelled_df)} lignes) :**")
    st.dataframe(cancelled_df[['ID', 'Customer name', 'Next order date']])

    # Construire une requête textuelle pour OpenAI
    prompt = f"""
    Tu es un assistant spécialisé en traitement de données. 

    Voici une liste d'abonnements annulés avec leur 'Next order date'.
    Filtre uniquement ceux dont 'Next order date' est **après** le 5 du mois en cours ({start_date}).
    Retourne **uniquement** un JSON valide contenant un tableau d'IDs.

    EXEMPLE DE RÉPONSE ATTENDUE :
    ```json
    {{ "selected_ids": [20338901319, 20037239111, 20511621447] }}
    N'inclus aucun autre texte en dehors du JSON. N'écris pas de phrase explicative, uniquement le JSON. Voici les abonnements :
    """

    for index, row in cancelled_df.iterrows():
        prompt += f"ID: {row['ID']}, Next Order Date: {row['Next order date']}\n"

    client = openai.OpenAI(api_key=openai.api_key)  # Crée un client OpenAI

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "Tu es un assistant de filtrage de données."},
            {"role": "user", "content": prompt}
        ]
    )

    # Affichage de la réponse brute d'OpenAI
    st.write("🔍 **Réponse brute d'OpenAI :**", response)

    # Extraire et analyser correctement le JSON retourné par GPT
    try:
        json_response = json.loads(response.choices[0].message.content)
        selected_ids = json_response.get("selected_ids", [])
    except json.JSONDecodeError:
        st.error("❌ Erreur : OpenAI n'a pas retourné un JSON valide.")
        selected_ids = []

    # Filtrer les abonnements annulés sélectionnés
    selected_cancelled_df = cancelled_df[cancelled_df['ID'].isin(selected_ids)]


    # Exclure Brice N'Guessan après la réponse d'OpenAI (par sécurité)
    selected_cancelled_df = selected_cancelled_df[~selected_cancelled_df['Customer name'].str.contains("Brice N Guessan", case=False, na=False)]


    # Afficher la liste des abonnements annulés sélectionnés avec nombre de lignes
    st.write(f"✅ **Abonnements annulés sélectionnés par OpenAI ({len(selected_cancelled_df)} lignes) :**")
    st.dataframe(selected_cancelled_df[['ID', 'Next order date']])

    return selected_cancelled_df


def prepare_final_files(df):
    """Prépare le fichier final avec les colonnes nécessaires et renommées."""
    column_mapping = {
        "ID": "Customer ID",
        "Customer name": "Delivery name",
        "Delivery address 1": "Delivery address 1",
        "Delivery address 2": "Delivery address 2",
        "Delivery zip": "Delivery zip",
        "Delivery city": "Delivery city",
        "Delivery province code": "Delivery province code",
        "Delivery country code": "Delivery country code",
        "Billing country": "Billing country",
        "Delivery interval count": "Quantity"
    }

    df = df[list(column_mapping.keys())].rename(columns=column_mapping)

    df['Billing country'] = df.apply(
        lambda row: "FRANCE" if pd.isnull(row['Billing country']) and row['Delivery country code'] == "FR" else row['Billing country'],
        axis=1
    )

    final_columns = [
        "Customer ID", "Delivery name", "Delivery address 1", "Delivery address 2",
        "Delivery zip", "Delivery city", "Delivery province code",
        "Delivery country code", "Billing country", "Quantity"
    ]
    return df[final_columns]

# Interface utilisateur Streamlit
st.title("Gestion des abonnements annulés et actifs")
file_prefix = st.text_input("Entrez le préfixe pour les fichiers finaux :", "")
uploaded_file = st.file_uploader("Téléversez le fichier CSV des abonnements", type="csv")

if uploaded_file:
    active_df, cancelled_df = process_csv(uploaded_file)

    if active_df is not None and cancelled_df is not None:
        selected_cancelled_df = ask_openai_for_filtering(cancelled_df)

        final_df = pd.concat([active_df, selected_cancelled_df])
        final_df = prepare_final_files(final_df)

        france_df = final_df[final_df['Delivery country code'] == 'FR']
        foreign_df = final_df[final_df['Delivery country code'] != 'FR']

        st.write(f"📌 **Aperçu des données finales pour la France ({len(france_df)} lignes) :**")
        st.dataframe(france_df)

        st.write(f"📌 **Aperçu des données finales pour l'étranger ({len(foreign_df)} lignes) :**")
        st.dataframe(foreign_df)

        if file_prefix.strip():
            france_file = f"{file_prefix}_France.xlsx"
            foreign_file = f"{file_prefix}_Etranger.xlsx"

            france_df.to_excel(france_file, index=False)
            foreign_df.to_excel(foreign_file, index=False)

            st.download_button(
                label="📥 Télécharger les données France",
                data=open(france_file, "rb"),
                file_name=france_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            st.download_button(
                label="📥 Télécharger les données Étranger",
                data=open(foreign_file, "rb"),
                file_name=foreign_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.warning("⚠️ Veuillez entrer un préfixe pour les fichiers finaux avant de télécharger.")
