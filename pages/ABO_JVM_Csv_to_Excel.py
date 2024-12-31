import streamlit as st
import pandas as pd
from datetime import datetime

def process_csv(csv_file):
    # Charger le fichier CSV
    df = pd.read_csv(csv_file)

    # Conversion explicite de 'Next order date'
    df['Next order date (converted)'] = pd.to_datetime(df['Next order date'], errors='coerce')

    # Identifier les dates invalides
    df['Invalid Dates'] = df['Next order date (converted)'].isna()
    st.write("Lignes avec des dates invalides dans 'Next order date' :")
    st.dataframe(df[df['Invalid Dates']])

    # Remplacer les valeurs invalides ou les gérer
    valid_dates_df = df[~df['Invalid Dates']].copy()  # Garder uniquement les lignes valides
    invalid_dates_df = df[df['Invalid Dates']]       # Sauvegarder les lignes invalides si nécessaire

    # Comparer uniquement sur les dates valides
    start_date = datetime.now().replace(day=5, hour=0, minute=0, second=0, microsecond=0)
    st.write("Date limite pour filtrage (start_date) :", start_date)

    # Filtrage des abonnements annulés
    cancelled_filter = valid_dates_df['Status'] == 'CANCELLED'
    valid_dates_df = valid_dates_df[~(cancelled_filter & (valid_dates_df['Next order date (converted)'] < start_date))]

    # Réunir les données valides et invalides (si nécessaire)
    final_df = pd.concat([valid_dates_df, invalid_dates_df], ignore_index=True)

    st.write("Aperçu des données après traitement :")
    st.dataframe(final_df)

    return final_df

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
