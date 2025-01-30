import streamlit as st
import pandas as pd
from datetime import datetime

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

    # Vérifier la colonne 'Next order date' et convertir en datetime
    if 'Next order date' in df.columns:
        df['Next order date'] = pd.to_datetime(df['Next order date'], errors='coerce', utc=True).dt.tz_localize(None)
    else:
        st.error("La colonne 'Next order date' est introuvable dans le fichier CSV.")
        return None, None

    # Date limite : 5 du mois en cours
    today = datetime.today()
    start_date = datetime(today.year, today.month, 5)

    # Filtrage automatique des abonnements annulés
    cancelled = df[(df['Status'] == 'CANCELLED') & (df['Next order date'] >= start_date)]
    
    # Filtrage des abonnements actifs
    active = df[df['Status'] == 'ACTIVE']

    return active, cancelled

# Interface Streamlit
st.title("Gestion des abonnements Appstle")

# Champ obligatoire pour nommer les fichiers
file_prefix = st.text_input("Nom du fichier final (obligatoire) :", value="")

# Téléversement du fichier CSV
uploaded_file = st.file_uploader("Téléversez le fichier CSV", type="csv")

if uploaded_file:
    active_df, cancelled_df = process_csv(uploaded_file)

    if active_df is not None and cancelled_df is not None:
        # Affichage des abonnements annulés après filtrage automatique
        st.subheader("Abonnements annulés filtrés automatiquement :")
        if cancelled_df.empty:
            st.info("Aucun abonnement annulé pertinent trouvé après filtrage.")
        else:
            st.success(f"{len(cancelled_df)} abonnements annulés ajoutés automatiquement.")
            st.dataframe(cancelled_df[['ID', 'Customer name', 'Customer email', 'Next order date']])

        # Fusionner les actifs et les annulés sélectionnés
        final_df = pd.concat([active_df, cancelled_df])

        # Séparation des données en France et Étranger
        france_df = final_df[final_df['Delivery country code'] == 'FR']
        etranger_df = final_df[final_df['Delivery country code'] != 'FR']

        # Afficher les données finales
        st.subheader("Aperçu des données finales pour la France :")
        st.dataframe(france_df[['ID', 'Customer name', 'Delivery address 1', 'Delivery city', 'Delivery zip']].reset_index(drop=True))

        st.subheader("Aperçu des données finales pour l’étranger :")
        st.dataframe(etranger_df[['ID', 'Customer name', 'Delivery address 1', 'Delivery city', 'Delivery zip']].reset_index(drop=True))

        # Vérifier que le nom du fichier est rempli avant d'autoriser le téléchargement
        if file_prefix.strip():
            # Téléchargement des fichiers finaux
            france_file = f"{file_prefix}_France.xlsx"
            etranger_file = f"{file_prefix}_Etranger.xlsx"

            france_df.to_excel(france_file, index=False)
            etranger_df.to_excel(etranger_file, index=False)

            with open(france_file, "rb") as file:
                st.download_button(
                    label="Télécharger le fichier pour la France",
                    data=file,
                    file_name=france_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            with open(etranger_file, "rb") as file:
                st.download_button(
                    label="Télécharger le fichier pour l’étranger",
                    data=file,
                    file_name=etranger_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.error("Veuillez entrer un nom de fichier pour activer les téléchargements.")
