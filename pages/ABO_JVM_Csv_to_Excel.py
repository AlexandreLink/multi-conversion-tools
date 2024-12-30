import streamlit as st
import pandas as pd
from datetime import datetime

def process_csv(csv_file):
    # 1. Lire le fichier CSV
    df = pd.read_csv(csv_file)

    # 2. Conversion de toutes les colonnes en majuscules (optionnel selon besoin)
    df = df.applymap(lambda x: x.upper() if isinstance(x, str) else x)

    # 3. Gestion de la colonne "Next order date" - Conversion en datetime
    if 'Next order date' in df.columns:
        # Conversion en datetime avec gestion des erreurs
        df['Next order date'] = pd.to_datetime(df['Next order date'], errors='coerce')

        # Supprimer les fuseaux horaires si présents
        if pd.api.types.is_datetime64_any_dtype(df['Next order date']):
            df['Next order date'] = df['Next order date'].dt.tz_localize(None)
    else:
        raise ValueError("La colonne 'Next order date' est absente dans le fichier.")

    # 4. Gestion de la colonne "Created at" - Filtrer selon la date limite
    if 'Created at' in df.columns:
        df['Created at'] = pd.to_datetime(df['Created at'], errors='coerce')
        today = datetime.today()
        date_limite = today.replace(day=4, hour=23, minute=59, second=59)
        df = df[df['Created at'] <= date_limite]
    else:
        raise ValueError("La colonne 'Created at' est absente dans le fichier.")

    # 5. Gestion des abonnements annulés avec "Next order date"
    today = datetime.today()
    start_date = today.replace(day=5, hour=0, minute=0, second=0, microsecond=0)
    cancelled_filter = (df['Status'] == 'CANCELLED') & df['Next order date'].notnull()
    df = df[~(cancelled_filter & (df['Next order date'] < start_date))]

    # 6. Gestion des colonnes "Billing country" pour les champs vides
    if 'Billing country' in df.columns and 'Delivery country code' in df.columns:
        df['Billing country'] = df.apply(
            lambda row: "FRANCE" if (pd.isnull(row['Billing country']) or row['Billing country'].strip() == "") 
            and row['Delivery country code'] == "FR" else row['Billing country'],
            axis=1
        )

    # 7. Garder uniquement les colonnes spécifiées
    columns_to_keep = [
        "ID", "Customer name", "Delivery address 1", "Delivery address 2", 
        "Delivery zip", "Delivery city", "Delivery province code", 
        "Delivery country code", "Billing country", "Delivery interval count"
    ]
    df = df[columns_to_keep]

    # 8. Renommer les colonnes pour correspondre aux noms finaux et ordonner
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
    df = df.rename(columns=column_mapping)

    # Réorganiser les colonnes pour correspondre à l'ordre final souhaité
    final_columns = [
        "Customer ID", "Delivery name", "Delivery address 1", "Delivery address 2", 
        "Delivery zip", "Delivery city", "Delivery province code", 
        "Delivery country code", "Billing country", "Quantity"
    ]
    df = df[final_columns]

    return df


# Interface Streamlit
st.title("Convertisseur CSV vers Excel et Traitement des Données")

# Demander le nom de fichier à l'utilisateur
file_name = st.text_input("Entrez le nom du fichier Excel à télécharger (sans extension) :")

# Upload du fichier CSV
uploaded_file = st.file_uploader("Téléversez le fichier CSV", type="csv")

if uploaded_file and file_name:
    # Traiter le fichier CSV
    df_processed = process_csv(uploaded_file)
    
    if df_processed is not None:
        # Afficher un aperçu du DataFrame
        st.write("Aperçu des données après traitement :")
        st.dataframe(df_processed.head())

        # Séparer les données en deux groupes : France et Reste du Monde
        df_france = df_processed[df_processed['Delivery country code'] == "FR"]
        df_rest_of_world = df_processed[df_processed['Delivery country code'] != "FR"]

        # Enregistrer les fichiers avec les noms personnalisés
        france_file_name = f"{file_name}_FRANCE.xlsx"
        rest_of_world_file_name = f"{file_name}_ETRANGER.xlsx"

        # Sauvegarder le fichier pour la France
        df_france.to_excel(france_file_name, index=False)
        with open(france_file_name, "rb") as file:
            st.download_button(
                label="Télécharger le fichier France",
                data=file,
                file_name=france_file_name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

        # Sauvegarder le fichier pour le reste du monde
        df_rest_of_world.to_excel(rest_of_world_file_name, index=False)
        with open(rest_of_world_file_name, "rb") as file:
            st.download_button(
                label="Télécharger le fichier Étranger",
                data=file,
                file_name=rest_of_world_file_name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
