import streamlit as st
import pandas as pd
import openai
from datetime import datetime
import os

# ✅ Initialisation sécurisée de l'API OpenAI
api_key = os.getenv("OPENAI_API_KEY", st.secrets.get("OPENAI_API_KEY", None))
if not api_key:
    st.error("❌ Clé API OpenAI manquante. Assurez-vous de la configurer dans les secrets Streamlit.")
else:
    client = openai.OpenAI(api_key=api_key)  # ✅ Nouvelle syntaxe

def process_csv(csv_file):
    """Lit et traite le fichier CSV."""
    df = pd.read_csv(csv_file)

    # Vérification des colonnes essentielles
    required_columns = ['Status', 'Next order date', 'ID']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"❌ Colonnes manquantes dans le fichier CSV : {', '.join(missing_columns)}")
        return None, None
    df['Status'] = df['Status'].str.upper()

    # Vérification de la colonne 'Next order date'
    if 'Next order date' not in df.columns:
        st.error("La colonne 'Next order date' est introuvable dans le fichier CSV.")
        return None, None

    df['Status'] = df['Status'].str.upper()

    # Filtrage des abonnements actifs et annulés
    active_df = df[df['Status'] == 'ACTIVE']
    cancelled_df = df[df['Status'] == 'CANCELLED']

    return active_df, cancelled_df

def ask_openai_for_filtering(cancelled_df):
    """Envoie les abonnements annulés à OpenAI et récupère les ID à réintégrer."""
    if cancelled_df.empty:
        return pd.DataFrame()

    today = datetime.today()
    start_date = datetime(today.year, today.month, 5).strftime('%Y-%m-%d')

    # ✅ Construction d'une requête claire pour OpenAI
    prompt = f"""
    Voici une liste d'abonnements annulés avec leur 'Next order date'.
    Filtre uniquement ceux dont 'Next order date' est **avant** le 5 du mois en cours ({start_date}).
    Retourne uniquement les ID des abonnements à conserver sous forme de liste JSON.
    
    Exemple :
    Entrée : 
    ID: 12345, Next Order Date: 2024-04-02
    ID: 67890, Next Order Date: 2024-04-06

    Sortie attendue :
    ["12345"]
    """

    for index, row in cancelled_df.iterrows():
        prompt += f"ID: {row['ID']}, Next Order Date: {row['Next order date']}\n"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Tu es un assistant de filtrage de données."},
            {"role": "user", "content": prompt}
        ]
    )

    # ✅ Vérification et extraction des ID
    try:
        output = response.choices[0].message.content.strip()
        selected_ids = eval(output)  # Convertir la réponse en liste Python
        selected_ids = [str(s).strip() for s in selected_ids if str(s).strip().isdigit()]
        return cancelled_df[cancelled_df['ID'].astype(str).isin(selected_ids)]
    except Exception as e:
        st.error(f"⚠️ Erreur lors du traitement des données OpenAI : {e}")
        return pd.DataFrame()

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

# ✅ Interface utilisateur Streamlit
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

        st.write("Aperçu des données finales pour la France :")
        st.dataframe(france_df)
        st.write("Aperçu des données finales pour l'étranger :")
        st.dataframe(foreign_df)

        if file_prefix.strip():
            france_file = f"{file_prefix}_France.xlsx"
            foreign_file = f"{file_prefix}_Etranger.xlsx"
            
            france_df.to_excel(france_file, index=False)
            foreign_df.to_excel(foreign_file, index=False)
            
            st.download_button(
                label="Télécharger les données France",
                data=open(france_file, "rb"),
                file_name=france_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            
            st.download_button(
                label="Télécharger les données Étranger",
                data=open(foreign_file, "rb"),
                file_name=foreign_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.warning("Veuillez entrer un préfixe pour les fichiers finaux avant de télécharger.")
