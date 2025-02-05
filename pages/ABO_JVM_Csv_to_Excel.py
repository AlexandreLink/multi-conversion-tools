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

    # Vérifier si la colonne "Status" existe
    if 'Status' not in df.columns:
        st.error("La colonne 'Status' est introuvable dans les fichiers CSV.")
        return None, None
    df['Status'] = df['Status'].str.upper()

    # Vérifier si la colonne "Created at" existe
    if 'Created at' in df.columns:
        st.write(f"📅 **Vérification des abonnements créés après le 5 du mois en cours...**")

        # Conversion de "Created at" en datetime
        df['Created at'] = pd.to_datetime(df['Created at'], errors='coerce')

        # Déterminer la date limite (5 du mois en cours)
        today = datetime.today()
        limit_date = datetime(today.year, today.month, 5)

        # Afficher le nombre total avant suppression
        st.write(f"🔍 **Nombre total d'abonnements avant filtrage : {len(df)}**")

        # Supprimer les abonnements créés après le 5 du mois
        df = df[df['Created at'] < limit_date]

        # Afficher le nombre après suppression
        st.write(f"❌ **Abonnements après exclusion des créés après le 5 du mois : {len(df)}**")
    else:
        st.write("⚠️ **La colonne 'Created at' n'existe pas dans les fichiers fournis.**")

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


def ask_openai_for_filtering(cancelled_df):
    """Envoie les données des abonnements annulés à OpenAI et récupère la liste des ID à réintégrer."""
    if cancelled_df.empty:
        return pd.DataFrame()

    today = datetime.today()
    start_date = datetime(today.year, today.month, 5).strftime('%Y-%m-%d')

    # Conversion de 'Next order date' en datetime pour éviter les erreurs
    cancelled_df['Next order date'] = pd.to_datetime(cancelled_df['Next order date'], errors='coerce')

    # Afficher la liste des abonnements annulés envoyés à OpenAI
    st.write(f"📝 **Liste des abonnements annulés envoyés à OpenAI : {len(cancelled_df)}**")
    st.dataframe(cancelled_df[['ID', 'Customer name', 'Next order date']])

    # Vérifier si la colonne "Cancellation note" existe
    if 'Cancellation note' in cancelled_df.columns:
        # Filtrer pour supprimer les clients ayant "Remboursement" dans Cancellation note
        cancelled_df = cancelled_df[~cancelled_df['Cancellation note'].str.contains("Remboursement", case=False, na=False)]

        # Afficher le nombre d'abonnements après suppression des remboursements
        st.write(f"❌ **Abonnements après exclusion des remboursements : {len(cancelled_df)}**")
    else:
        st.write("⚠️ **La colonne 'Cancellation note' n'existe pas dans les fichiers fournis.**")


    # Supprimer les doublons basés sur le Customer name (conserver le premier)
    cancelled_df = cancelled_df.drop_duplicates(subset=['Customer name'], keep='first')

    # Construire une requête textuelle pour OpenAI
    prompt = f"""
    Tu es un assistant chargé de filtrer les abonnements annulés.
    Ta seule tâche est d'extraire les ID des abonnements dont la 'Next Order Date' est **après** le 5 du mois en cours ({start_date}).

    🔹 **Format de réponse attendu :** Une simple liste d'ID séparés par des virgules **et RIEN D'AUTRE**.
    🔹 **Exemple de réponse correcte :** `12345,67890,54321`
    🔹 **Interdictions :** Ne pas expliquer, ne pas formater autrement. Juste la liste brute des ID.

    Voici la liste des abonnements annulés :
    """

    for index, row in cancelled_df.iterrows():
        prompt += f"{row['ID']} ({row['Next order date'].strftime('%Y-%m-%d')})\n"

    prompt += "\n🔹 Maintenant, donne-moi UNIQUEMENT la liste des ID, sans aucun texte supplémentaire."


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

    # Extraction des ID retournés par OpenAI
    output = response.choices[0].message.content.strip()
    selected_ids = re.findall(r'\d+', output)  # Extraction des nombres
    selected_ids = [int(id_) for id_ in selected_ids]

    # Filtrer les abonnements annulés sélectionnés
    selected_cancelled_df = cancelled_df[cancelled_df['ID'].isin(selected_ids)]

    # Afficher la liste des abonnements annulés sélectionnés
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
uploaded_files = st.file_uploader("Téléversez les fichiers CSV des abonnements", type="csv", accept_multiple_files=True)

if uploaded_files:
    active_df, cancelled_df = process_csv(uploaded_files)

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
