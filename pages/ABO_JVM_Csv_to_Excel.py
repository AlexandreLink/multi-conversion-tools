import streamlit as st
import pandas as pd
from datetime import datetime

def process_csv(csv_file):
    # Lire le fichier CSV
    df = pd.read_csv(csv_file)

    # Définir les limites de date pour la comparaison
    today = datetime.today()
    date_limite = today.replace(day=4, hour=23, minute=59, second=59, microsecond=0)
    start_date = today.replace(day=5, hour=0, minute=0, second=0, microsecond=0)

    # Debugging : Affichez les dates limites
    print("Date limite :", date_limite, "Type :", type(date_limite))
    print("Start date :", start_date, "Type :", type(start_date))

    # Conversion sécurisée de 'Next order date'
    df['Next order date'] = pd.to_datetime(df['Next order date'], errors='coerce')
    
    # Debugging : Afficher les valeurs de 'Next order date' et leurs types
    print("Valeurs de 'Next order date' après conversion :")
    print(df['Next order date'].head())
    print("Type de données :", df['Next order date'].dtype)

    # Debugging : Vérifier les valeurs problématiques
    invalid_dates = df[df['Next order date'].isnull()]
    print("Lignes avec 'Next order date' non valide :", invalid_dates)

    # Filtrer les abonnements annulés
    cancelled_filter = (df['Status'] == 'CANCELLED')
    filtered_rows = df[cancelled_filter & (df['Next order date'] < start_date)]

    # Debugging : Afficher les lignes qui correspondent au filtre problématique
    print("Lignes annulées avec 'Next order date' avant start_date :")
    print(filtered_rows)

    # Appliquer le filtre
    df = df[~(cancelled_filter & (df['Next order date'] < start_date))]

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
