import streamlit as st
import pandas as pd

# Fonction pour traiter le fichier CSV
def process_csv(csv_file):
    df = pd.read_csv(csv_file)

    # Diviser les abonnements en actifs et annulés
    active = df[df['Status'] == 'ACTIVE']
    cancelled = df[df['Status'] == 'CANCELLED']

    return active, cancelled

# Interface Streamlit
st.set_page_config(layout="wide")
st.title("Gestion des abonnements Appstle")

# Téléversement du fichier CSV
uploaded_file = st.file_uploader("Téléversez le fichier CSV", type="csv")

if uploaded_file:
    active, cancelled = process_csv(uploaded_file)

    # Affichage des abonnements annulés
    st.subheader("Liste des abonnements annulés (CANCELLED) :")
    cancelled['Display'] = cancelled.apply(
        lambda row: f"ID: {row['ID']} | Nom: {row['Customer name']} | Email: {row['Customer email']} | Next Order Date: {row['Next order date']}",
        axis=1,
    )
    selected_cancelled = st.multiselect(
        "Sélectionnez les abonnements annulés à inclure dans le fichier final :",
        options=cancelled['Display'].tolist(),
    )

    # Filtrer les abonnements annulés sélectionnés
    selected_rows = cancelled[cancelled['Display'].isin(selected_cancelled)]

    # Affichage des abonnements actifs
    st.subheader("Aperçu des abonnements actifs (ACTIVE) :")
    st.dataframe(active[['ID', 'Customer name', 'Customer email', 'Next order date']].reset_index(drop=True))

    # Combiner les actifs et les annulés sélectionnés
    final_df = pd.concat([active, selected_rows])

    # Séparer les abonnements entre France et reste du monde
    france_df = final_df[final_df['Delivery country code'] == 'FR']
    rest_of_world_df = final_df[final_df['Delivery country code'] != 'FR']

    # Affichage des données finales pour la France
    st.subheader("Aperçu des données finales pour la France :")
    st.dataframe(france_df[['ID', 'Customer name', 'Delivery address 1', 'Delivery city', 'Delivery zip']].reset_index(drop=True))

    # Affichage des données finales pour le reste du monde
    st.subheader("Aperçu des données finales pour le reste du monde :")
    st.dataframe(rest_of_world_df[['ID', 'Customer name', 'Delivery address 1', 'Delivery city', 'Delivery zip']].reset_index(drop=True))

    # Boutons de téléchargement des fichiers
    france_file_name = "abonnements_france.xlsx"
    rest_of_world_file_name = "abonnements_reste_du_monde.xlsx"

    france_df.to_excel(france_file_name, index=False)
    rest_of_world_df.to_excel(rest_of_world_file_name, index=False)

    with open(france_file_name, "rb") as file:
        st.download_button(
            label="Télécharger le fichier pour la France",
            data=file,
            file_name=france_file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with open(rest_of_world_file_name, "rb") as file:
        st.download_button(
            label="Télécharger le fichier pour le reste du monde",
            data=file,
            file_name=rest_of_world_file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
