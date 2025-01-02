import streamlit as st
import pandas as pd

# Configuration de la page
st.set_page_config(
    layout="wide",  # Largeur étendue
    page_title="Gestion des abonnements",  # Titre de la page
    page_icon="📄"  # Icône
)

# Fonction pour traiter le fichier CSV
def process_csv(csv_file):
    df = pd.read_csv(csv_file)

    # Vérifier si la colonne 'Status' existe
    if 'Status' in df.columns:
        df['Status'] = df['Status'].str.upper()  # Normaliser en majuscules
    else:
        st.error("La colonne 'Status' est introuvable dans le fichier CSV.")
        return None, None

    # Diviser les abonnements en actifs et annulés
    active = df[df['Status'] == 'ACTIVE']
    cancelled = df[df['Status'] == 'CANCELLED']

    return active, cancelled

# Interface Streamlit
st.title("Gestion des abonnements Appstle")

# Téléversement du fichier CSV
uploaded_file = st.file_uploader("Téléversez le fichier CSV", type="csv")

if uploaded_file:
    active_df, cancelled_df = process_csv(uploaded_file)

    if active_df is not None and cancelled_df is not None:
        # Afficher les abonnements annulés dans un tableau
        st.subheader("Liste des abonnements annulés (CANCELLED) :")
        if cancelled_df.empty:
            st.info("Aucun abonnement annulé trouvé.")
        else:
            st.success(f"{len(cancelled_df)} abonnements annulés trouvés.")
            # Créer un tableau avec des checkboxes
            selected_indices = []
            cancelled_df = cancelled_df[['ID', 'Customer name', 'Customer email', 'Next order date']]
            for idx, row in cancelled_df.iterrows():
                checkbox_label = (
                    f"ID: {row['ID']} | Nom: {row['Customer name']} | "
                    f"Email: {row['Customer email']} | Next Order Date: {row['Next order date']}"
                )
                if st.checkbox(checkbox_label, key=f"cancelled_{idx}"):
                    selected_indices.append(idx)

            # Filtrer les abonnements annulés sélectionnés
            selected_cancelled_df = cancelled_df.loc[selected_indices]

        # Afficher les abonnements actifs
        st.subheader("Aperçu des abonnements actifs (ACTIVE) :")
        if active_df.empty:
            st.info("Aucun abonnement actif trouvé.")
        else:
            st.dataframe(active_df[['ID', 'Customer name', 'Customer email', 'Next order date']].reset_index(drop=True))

        # Fusionner les actifs et les annulés sélectionnés
        final_df = pd.concat([active_df, selected_cancelled_df]) if not selected_cancelled_df.empty else active_df

        # Séparation des données en France et Reste du Monde
        france_df = final_df[final_df['Delivery country code'] == 'FR']
        rest_of_world_df = final_df[final_df['Delivery country code'] != 'FR']

        # Afficher les données finales
        st.subheader("Aperçu des données finales pour la France :")
        st.dataframe(france_df[['ID', 'Customer name', 'Delivery address 1', 'Delivery city', 'Delivery zip']].reset_index(drop=True))

        st.subheader("Aperçu des données finales pour le reste du monde :")
        st.dataframe(rest_of_world_df[['ID', 'Customer name', 'Delivery address 1', 'Delivery city', 'Delivery zip']].reset_index(drop=True))

        # Téléchargement des fichiers finaux
        france_file = "final_france.xlsx"
        rest_of_world_file = "final_rest_of_world.xlsx"

        france_df.to_excel(france_file, index=False)
        rest_of_world_df.to_excel(rest_of_world_file, index=False)

        st.download_button(
            label="Télécharger les données France",
            data=open(france_file, "rb"),
            file_name=france_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.download_button(
            label="Télécharger les données Reste du Monde",
            data=open(rest_of_world_file, "rb"),
            file_name=rest_of_world_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
