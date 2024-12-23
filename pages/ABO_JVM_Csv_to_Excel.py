import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def process_csv(csv_file):
    # 1. Lire le fichier CSV avec toutes les colonnes
    df = pd.read_csv(csv_file)

    # 2. Mettre toutes les valeurs en majuscules
    df = df.applymap(lambda x: x.upper() if isinstance(x, str) else x)

    # 3. Créer la date limite au format du CSV (ex. "2024-11-04T23:59:59+01:00")
    today = datetime.today()
    date_limite = datetime(today.year, today.month, 4, 23, 59, 59)  # Objet datetime pour comparaison

    # 4. Filtrer les lignes avec des dates 'Created at' <= date_limite
    if 'Created at' in df.columns:
        df['Created at'] = pd.to_datetime(df['Created at'], errors='coerce')
        df = df[df['Created at'] <= date_limite]
        # Supprimer la colonne 'Created at' après le filtrage
        df = df.drop(columns=['Created at'], errors='ignore')
    else:
        st.error("Le fichier CSV ne contient pas de colonne 'Created at' pour les dates de commande.")

    # 5. Corriger la colonne 'Billing country' directement si vide ou manquante
    df['Billing country'] = df.apply(
        lambda row: "FRANCE" if (pd.isnull(row['Billing country']) or row['Billing country'].strip() == "") 
        and row['Delivery country code'] == "FR" else row['Billing country'],
        axis=1
    )

    # 6. Gestion des abonnements annulés basés sur "Next Order"
    if 'Next Order' in df.columns:
        df['Next Order'] = pd.to_datetime(df['Next Order'], errors='coerce')
        start_date = today.replace(day=5)
        end_date = (start_date + pd.offsets.MonthEnd(1)).replace(day=4)
        df = df[(df['Next Order'] >= start_date) | (df['Next Order'].isnull())]

    # 7. Garder uniquement les colonnes spécifiées
    columns_to_keep = ["ID", "Customer name", "Delivery address 1", "Delivery address 2", 
                       "Delivery zip", "Delivery city", "Delivery province code", 
                       "Delivery country code", "Billing country", "Delivery interval count"]
    df = df[columns_to_keep]

    # 8. Supprimer les doublons
    df = df.drop_duplicates()

    # 9. Renommer les colonnes pour correspondre aux noms finaux et ordonner
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
    final_columns = ["Customer ID", "Delivery name", "Delivery address 1", "Delivery address 2", 
                     "Delivery zip", "Delivery city", "Delivery province code", 
                     "Delivery country code", "Billing country", "Quantity"]
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
