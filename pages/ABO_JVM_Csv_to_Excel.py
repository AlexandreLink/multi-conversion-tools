import streamlit as st
import pandas as pd
from datetime import datetime

def process_csv(csv_file):
    # Charger le fichier CSV
    df = pd.read_csv(csv_file)

    # Étape 1 : Nettoyer les données avant conversion
    df['Next order date'] = df['Next order date'].str.strip()  # Supprimer les espaces superflus
    df['Next order date'] = df['Next order date'].replace('', pd.NA)  # Remplacer les chaînes vides par NaN

    # Étape 2 : Conversion en datetime
    try:
        df['Next order date'] = pd.to_datetime(df['Next order date'], errors='coerce')
        st.write("Types de données après conversion :", df['Next order date'].dtype)
    except Exception as e:
        st.error(f"Erreur lors de la conversion en datetime : {e}")
        return None

    # Étape 3 : Identifier et afficher les valeurs invalides
    invalid_dates = df[df['Next order date'].isna()]
    if not invalid_dates.empty:
        st.write("Valeurs non valides dans 'Next order date' :")
        st.dataframe(invalid_dates)
        st.stop()  # Arrêter le processus si des valeurs invalides existent
    else:
        st.write("Toutes les valeurs de 'Next order date' sont valides.")

    # Étape 4 : Supprimer les fuseaux horaires si présents
    try:
        df['Next order date'] = df['Next order date'].dt.tz_localize(None)
    except Exception as e:
        st.error(f"Erreur lors de la suppression des fuseaux horaires : {e}")
        return None

    # Étape 5 : Créer la date limite pour filtrage
    start_date = datetime.now().replace(day=5, hour=0, minute=0, second=0, microsecond=0)
    st.write("Date limite pour filtrage (start_date) :", start_date)

    # Étape 6 : Filtrer les abonnements annulés avec une `Next order date` antérieure
    try:
        cancelled_filter = df['Status'] == 'CANCELLED'
        df = df[~(cancelled_filter & (df['Next order date'] < start_date))]
        st.write("Filtrage effectué avec succès.")
    except Exception as e:
        st.error(f"Erreur lors du filtrage des données : {e}")
        return None

    # Retourner le DataFrame filtré
    return df



# Interface Streamlit
st.title("Debugging : Problèmes de type avec les dates")

# Téléversement du fichier CSV
uploaded_file = st.file_uploader("Téléversez le fichier CSV", type="csv")

if uploaded_file:
    # Traiter le fichier CSV
    df_processed = process_csv(uploaded_file)

    if df_processed is not None:
        # Afficher un aperçu des données traitées
        st.write("Aperçu des données après traitement :")
        st.dataframe(df_processed.head())
