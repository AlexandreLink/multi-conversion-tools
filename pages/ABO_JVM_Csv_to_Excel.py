import streamlit as st
import pandas as pd
from datetime import datetime

def process_csv(csv_file):
    # Lire le fichier CSV avec toutes les colonnes
    df = pd.read_csv(csv_file)

    # Convertir la colonne 'Next order date' en datetime
    df['Next order date'] = pd.to_datetime(df['Next order date'], errors='coerce')

    # Vérifier si 'Next order date' contient des valeurs invalides
    invalid_dates = df[df['Next order date'].isnull()]
    st.write(f"Nombre total de valeurs invalides : {len(invalid_dates)}")
    if not invalid_dates.empty:
        st.write("Lignes avec des dates invalides :")
        st.dataframe(invalid_dates)

    # Filtrer les valeurs invalides avant de continuer
    df = df[df['Next order date'].notnull()]

    # Définir la date de début comme datetime
    today = datetime.today()
    start_date = pd.Timestamp(today.replace(day=5))

    # Appliquer le filtre pour les abonnements annulés
    cancelled_filter = (df['Status'] == 'CANCELLED')
    df = df[~(cancelled_filter & (df['Next order date'] < start_date))]

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
