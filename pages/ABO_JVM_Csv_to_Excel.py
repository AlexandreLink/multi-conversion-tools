import streamlit as st
import pandas as pd
from datetime import datetime

def process_csv(csv_file):
    # Lire le fichier CSV
    df = pd.read_csv(csv_file)

    # Vérification : les colonnes nécessaires sont-elles présentes ?
    required_columns = ['Created at', 'Next order date', 'Status', 'Billing country', 'Delivery country code']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"La colonne obligatoire '{col}' est absente.")

    # Conversion sécurisée des colonnes date
    for date_col in ['Created at', 'Next order date']:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        if df[date_col].isnull().all():
            raise ValueError(f"Toutes les valeurs dans '{date_col}' sont invalides après conversion.")

    # Supprimer les lignes avec 'Created at' ou 'Next order date' invalides
    initial_rows = len(df)
    df = df[df['Created at'].notnull() & df['Next order date'].notnull()]
    remaining_rows = len(df)
    print(f"Lignes initiales : {initial_rows}, après suppression des NaT : {remaining_rows}")

    # Définir les limites de date pour la comparaison
    today = datetime.today()
    date_limite = today.replace(day=4, hour=23, minute=59, second=59, microsecond=0)
    start_date = today.replace(day=5, hour=0, minute=0, second=0, microsecond=0)

    # Filtrer selon 'Created at'
    df = df[df['Created at'] <= date_limite]

    # Gestion des abonnements annulés
    cancelled_filter = (df['Status'] == 'CANCELLED') & (df['Next order date'].notnull())
    df = df[~(cancelled_filter & (df['Next order date'] < start_date))]

    # Gestion des champs vides dans "Billing country"
    df['Billing country'] = df.apply(
        lambda row: "FRANCE" if (pd.isnull(row['Billing country']) or row['Billing country'].strip() == "") 
        and row['Delivery country code'] == "FR" else row['Billing country'],
        axis=1
    )

    # Garder uniquement les colonnes spécifiées
    columns_to_keep = [
        "ID", "Customer name", "Delivery address 1", "Delivery address 2", 
        "Delivery zip", "Delivery city", "Delivery province code", 
        "Delivery country code", "Billing country", "Delivery interval count"
    ]
    df = df[columns_to_keep]

    # Renommer les colonnes
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

    # Réorganiser les colonnes
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
