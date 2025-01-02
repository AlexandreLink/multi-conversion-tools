import streamlit as st
import pandas as pd
from datetime import datetime

def process_csv(csv_file):
    # Charger le fichier CSV
    df = pd.read_csv(csv_file)

    # Étape 1 : Sélection automatique des abonnements actifs
    active_df = df[df['Status'] == 'ACTIVE']

    # Étape 2 : Interface pour sélectionner les abonnements annulés
    cancelled_df = df[df['Status'] == 'CANCELLED']
    st.write("### Liste des abonnements annulés (`CANCELLED`) :")
    selected_indices = []
    for i, row in cancelled_df.iterrows():
        keep = st.checkbox(f"ID: {row['ID']} | Name: {row['Customer name']} | Next Order: {row['Next order date']}", key=f"cancelled_{i}")
        if keep:
            selected_indices.append(i)

    # Garder uniquement les `CANCELLED` sélectionnés
    selected_cancelled_df = cancelled_df.loc[selected_indices]

    # Étape 3 : Fusion des `ACTIVE` et `CANCELLED` sélectionnés
    final_df = pd.concat([active_df, selected_cancelled_df])

    # Étape 4 : Traitement des colonnes et renommage
    columns_to_keep = [
        "ID", "Customer name", "Delivery address 1", "Delivery address 2",
        "Delivery zip", "Delivery city", "Delivery province code",
        "Delivery country code", "Billing country", "Delivery interval count"
    ]
    final_df = final_df[columns_to_keep]

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
    final_df = final_df.rename(columns=column_mapping)

    # Étape 5 : Séparation entre France et Reste du Monde
    france_df = final_df[final_df['Delivery country code'] == 'FR']
    rest_of_world_df = final_df[final_df['Delivery country code'] != 'FR']

    # Afficher un aperçu des données traitées
    st.write("### Aperçu des données finales pour la France :")
    st.dataframe(france_df)
    st.write("### Aperçu des données finales pour le reste du monde :")
    st.dataframe(rest_of_world_df)

    return france_df, rest_of_world_df

# Interface principale
st.title("Gestion des abonnements avec séparation France / Reste du Monde")

# Téléversement du fichier CSV
uploaded_file = st.file_uploader("Téléversez le fichier CSV", type="csv")

if uploaded_file:
    # Étape principale
    france_df, rest_of_world_df = process_csv(uploaded_file)

    if not france_df.empty or not rest_of_world_df.empty:
        # Sauvegarder les données dans des fichiers CSV
        france_file = "subscriptions_france.csv"
        rest_of_world_file = "subscriptions_rest_of_world.csv"

        france_df.to_csv(france_file, index=False)
        rest_of_world_df.to_csv(rest_of_world_file, index=False)

        # Boutons de téléchargement
        with open(france_file, "rb") as file:
            st.download_button(
                label="Télécharger le fichier France",
                data=file,
                file_name=france_file,
                mime="text/csv"
            )

        with open(rest_of_world_file, "rb") as file:
            st.download_button(
                label="Télécharger le fichier Reste du Monde",
                data=file,
                file_name=rest_of_world_file,
                mime="text/csv"
            )
