import streamlit as st
import pandas as pd
import openai
from datetime import datetime
import os
import re

# Configuration de l'API OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")

def filter_new_subscriptions(df):
    """Filtrer les abonnements créés après le 5 du mois en demandant à OpenAI."""
    if df.empty:
        return df, pd.DataFrame()

    today = datetime.today()
    start_date = datetime(today.year, today.month, 5).strftime('%Y-%m-%d')

    # Construire un prompt ultra-simple en n'envoyant QUE `ID` et `Created at`
    prompt = f"""
    Tu es un assistant chargé de filtrer les abonnements.
    Ta seule tâche est de **supprimer toutes les lignes où 'Created at' est postérieur au {start_date}.**

    🔹 **Format de réponse attendu :**
    - `KEEP: id1, id2, id3` (IDs à garder)
    - `REMOVE: id4, id5, id6` (IDs à supprimer)

    **Exemple :**
    ```
    KEEP: 12345,67890,54321
    REMOVE: 98765,56789,43210
    ```

    Voici les abonnements :
    """

    # **N'envoyer que l'ID et la date** pour réduire la taille des données
    for _, row in df[['ID', 'Created at']].dropna().iterrows():
        prompt += f"{row['ID']} | Created at: {row['Created at']}\n"

    prompt += "\n🔹 Maintenant, donne-moi UNIQUEMENT la liste des IDs KEEP et REMOVE."

    # **Envoyer à OpenAI**
    client = openai.OpenAI(api_key=openai.api_key)
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "Tu es un assistant de filtrage de données."},
                  {"role": "user", "content": prompt}]
    )

    # **Afficher la réponse brute d'OpenAI**
    st.write("🔍 **Réponse brute d'OpenAI (Filtrage 'Created at') :**", response)

    # **Extraire les IDs avec une regex efficace**
    output = response.choices[0].message.content.strip()

    keep_match = re.search(r'KEEP: ([\d, ]+)', output)
    remove_match = re.search(r'REMOVE: ([\d, ]+)', output)

    selected_ids = [int(id_) for id_ in keep_match.group(1).split(',')] if keep_match else []
    removed_ids = [int(id_) for id_ in remove_match.group(1).split(',')] if remove_match else []

    # **Créer les DataFrames filtrés**
    kept_df = df[df['ID'].isin(selected_ids)]
    removed_df = df[df['ID'].isin(removed_ids)]

    # **Afficher les abonnements supprimés**
    st.write(f"❌ **Abonnements supprimés (créés après le 5 du mois) : {len(removed_df)}**")
    st.dataframe(removed_df[['ID', 'Customer name', 'Created at']])

    return kept_df, removed_df


def process_csv(uploaded_files):
    """Lire et traiter plusieurs fichiers CSV."""
    all_dataframes = []

    for csv_file in uploaded_files:
        df = pd.read_csv(csv_file)
        all_dataframes.append(df)

    # **Fusionner les fichiers CSV**
    df = pd.concat(all_dataframes, ignore_index=True)

    # **Vérifier la colonne 'Created at'**
    if 'Created at' not in df.columns:
        st.error("La colonne 'Created at' est introuvable dans les fichiers CSV.")
        return None, None

    # 🎯 **Filtrer les abonnements créés après le 5 du mois AVEC OpenAI**
    df, removed_df = filter_new_subscriptions(df)

    # **Vérifier la colonne 'Status'**
    if 'Status' not in df.columns:
        st.error("La colonne 'Status' est introuvable dans les fichiers CSV.")
        return None, None

    df['Status'] = df['Status'].str.upper()

    # **Vérifier la colonne 'Next order date'**
    if 'Next order date' not in df.columns:
        st.error("La colonne 'Next order date' est introuvable dans les fichiers CSV.")
        return None, None

    # **Séparer les abonnements actifs et annulés**
    active_df = df[df['Status'] == 'ACTIVE']
    cancelled_df = df[df['Status'] == 'CANCELLED']

    # **Supprimer Brice N Guessan & Brice N'Guessan**
    cancelled_df = cancelled_df[~cancelled_df['Customer name'].str.contains(r"Brice N'?Guessan", case=False, na=False, regex=True)]

    return active_df, cancelled_df


def ask_openai_for_filtering(cancelled_df):
    """Filtrer les abonnements annulés via OpenAI pour réintégrer ceux valides."""
    if cancelled_df.empty:
        return pd.DataFrame()

    today = datetime.today()
    start_date = datetime(today.year, today.month, 5).strftime('%Y-%m-%d')

    # Conversion de 'Next order date' en datetime
    cancelled_df['Next order date'] = pd.to_datetime(cancelled_df['Next order date'], errors='coerce')

    # Afficher les abonnements annulés envoyés à OpenAI
    st.write(f"📝 **Liste des abonnements annulés envoyés à OpenAI : {len(cancelled_df)}**")
    st.dataframe(cancelled_df[['ID', 'Customer name', 'Next order date']])

    # Vérifier la colonne "Cancellation note" et supprimer les remboursements localement
    if 'Cancellation note' in cancelled_df.columns:
        cancelled_df = cancelled_df[~cancelled_df['Cancellation note'].str.contains("Remboursement", case=False, na=False)]
        st.write(f"❌ **Abonnements après suppression des remboursements : {len(cancelled_df)}**")

    # Supprimer les doublons basés sur le Customer name (conserver le premier)
    cancelled_df = cancelled_df.drop_duplicates(subset=['Customer name'], keep='first')

    # Construire la requête pour OpenAI
    prompt = f"""
    Tu es un assistant de filtrage des abonnements annulés.
    Ta seule tâche est de **conserver uniquement les ID des abonnements ayant une 'Next Order Date' après le 5 du mois en cours ({start_date}).**

    🔹 **Format de réponse attendu :** Une simple liste d'ID séparés par des virgules **et RIEN D'AUTRE**.
    🔹 **Exemple de réponse correcte :** `12345,67890,54321`

    Voici la liste des abonnements annulés :
    """

    for index, row in cancelled_df.iterrows():
        prompt += f"{row['ID']} ({row['Next order date'].strftime('%Y-%m-%d')})\n"

    prompt += "\n🔹 Maintenant, donne-moi UNIQUEMENT la liste des ID, sans autre texte."

    client = openai.OpenAI(api_key=openai.api_key)

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "Tu es un assistant de filtrage de données."},
                  {"role": "user", "content": prompt}]
    )

    st.write("🔍 **Réponse brute d'OpenAI :**", response)

    # Extraction des ID retournés par OpenAI
    output = response.choices[0].message.content.strip()
    selected_ids = [int(id_) for id_ in re.findall(r'\d+', output)]

    # Filtrer les abonnements annulés sélectionnés
    selected_cancelled_df = cancelled_df[cancelled_df['ID'].isin(selected_ids)]

    st.write(f"✅ **Abonnements annulés sélectionnés par OpenAI ({len(selected_cancelled_df)} lignes) :**")
    st.dataframe(selected_cancelled_df[['ID', 'Next order date']])

    return selected_cancelled_df

def prepare_final_files(df):
    """Préparer le fichier final avec les colonnes nécessaires et renommées."""
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

    return df

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

        st.write(f"📌 **Aperçu des données finales ({len(final_df)} lignes) :**")
        st.dataframe(final_df)
