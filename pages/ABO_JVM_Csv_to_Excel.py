import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def process_csv(csv_file):
    # 1. Lire le fichier CSV avec toutes les colonnes
    df = pd.read_csv(csv_file)

    # 2. Mettre toutes les valeurs en majuscules
    df = df.applymap(lambda x: x.upper() if isinstance(x, str) else x)

    # 3. Déterminer la plage de dates pour la validation
    today = datetime.today()
    start_date = today.replace(day=5)  # 5 du mois en cours
    end_date = (start_date + timedelta(days=31)).replace(day=4)  # 4 du mois suivant

    # 4. Convertir la colonne "Next order date" en datetime
    if 'Next order date' in df.columns:
        # Tenter de convertir en datetime
        df['Next order date'] = pd.to_datetime(df['Next order date'], errors='coerce')

        # Afficher un aperçu des valeurs non valides
        invalid_dates = df[df['Next order date'].isnull() & df['Next order date'].notna()]
        if not invalid_dates.empty:
            st.warning("Certaines valeurs de 'Next order date' n'ont pas pu être converties en datetime.")

        # Filtrer en excluant les lignes annulées avec une Next Order Date trop ancienne
        df = df[~((df['Status'] == 'CANCELLED') & (df['Next order date'].notnull()) & (df['Next order date'] < start_date))]
    else:
        st.error("Le fichier CSV ne contient pas de colonne 'Next order date'.")

    # 5. Filtrer les lignes avec des dates 'Created at' <= date limite
    date_limite = f"{today.year}-{today.month:02d}-04T23:59:59"
    if 'Created at' in df.columns:
        df['Created at'] = pd.to_datetime(df['Created at'], errors='coerce')
        df = df[df['Created at'] <= pd.to_datetime(date_limite, errors='coerce')]
        # Supprimer la colonne 'Created at' après le filtrage
        df = df.drop(columns=['Created at'], errors='ignore')
    else:
        st.error("Le fichier CSV ne contient pas de colonne 'Created at'.")

    # 6. Garder uniquement les colonnes spécifiées
    columns_to_keep = ["ID", "Customer name", "Delivery address 1", "Delivery address 2", 
                       "Delivery zip", "Delivery city", "Delivery province code", 
                       "Delivery country code", "Billing country", "Delivery interval count"]
    df = df[columns_to_keep]

    # 7. Corriger la colonne 'Billing country' directement si vide ou manquante
    df['Billing country'] = df.apply(
        lambda row: "FRANCE" if (pd.isnull(row['Billing country']) or row['Billing country'].strip() == "") 
        and row['Delivery country code'] == "FR" else row['Billing country'],
        axis=1
    )

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
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # Sauvegarder le fichier pour le reste du monde
        df_rest_of_world.to_excel(rest_of_world_file_name, index=False)
        with open(rest_of_world_file_name, "rb") as file:
            st.download_button(
                label="Télécharger le fichier Étranger",
                data=file,
                file_name=rest_of_world_file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
