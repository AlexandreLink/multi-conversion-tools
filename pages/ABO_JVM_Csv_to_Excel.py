import streamlit as st
import pandas as pd
from datetime import datetime

def process_csv(csv_file):
    # Charger le fichier CSV
    df = pd.read_csv(csv_file)

    # Conversion explicite de 'Next order date' en datetime
    df['Next order date (converted)'] = pd.to_datetime(df['Next order date'], errors='coerce')

    # Supprimer les fuseaux horaires des dates converties
    try:
        df['Next order date (converted)'] = df['Next order date (converted)'].dt.tz_localize(None)
    except Exception as e:
        st.error(f"Erreur lors de la suppression des fuseaux horaires : {e}")
        return

    # Identifier les dates invalides
    df['Invalid Dates'] = df['Next order date (converted)'].isna()
    st.write("Lignes avec des dates invalides dans 'Next order date' :")
    st.dataframe(df[df['Invalid Dates']])

    # Filtrer uniquement les dates valides
    valid_dates_df = df[~df['Invalid Dates']].copy()

    # Comparer avec une date limite (start_date) sans fuseau horaire
    start_date = datetime.now().replace(day=5, hour=0, minute=0, second=0, microsecond=0)
    start_date = pd.Timestamp(start_date).tz_localize(None)  # Supprimer les fuseaux horaires
    st.write("Date limite pour filtrage (start_date) :", start_date)

    # Appliquer le filtre pour les abonnements annulés
    cancelled_filter = valid_dates_df['Status'] == 'CANCELLED'
    valid_dates_df = valid_dates_df[~(cancelled_filter & (valid_dates_df['Next order date (converted)'] < start_date))]

    # Afficher les données après traitement
    st.write("Aperçu des données après traitement :")
    st.dataframe(valid_dates_df)

    return valid_dates_df

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
