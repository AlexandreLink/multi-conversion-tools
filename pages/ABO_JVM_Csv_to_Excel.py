import streamlit as st
import pandas as pd
from datetime import datetime

def process_csv(csv_file):
    # Lire le fichier CSV
    df = pd.read_csv(csv_file)

    # Conversion de 'Next order date' en datetime
    df['Next order date'] = pd.to_datetime(df['Next order date'], errors='coerce')
    
    # Vérification des valeurs non valides dans 'Next order date'
    if df['Next order date'].isnull().any():
        print("Certaines valeurs dans 'Next order date' n'ont pas pu être converties en datetime.")
        print(df[df['Next order date'].isnull()])  # Debug : Afficher les lignes problématiques

    # Normaliser la colonne pour retirer les fuseaux horaires (si présents)
    df['Next order date'] = df['Next order date'].dt.tz_localize(None)

    # Calcul de start_date au format datetime
    today = datetime.today()
    start_date = today.replace(day=5, hour=0, minute=0, second=0, microsecond=0)
    start_date = pd.Timestamp(start_date)  # Convertir en Pandas Timestamp
    
    # Debugging : Afficher les types et exemples pour validation
    print(f"Start date: {start_date} | Type: {type(start_date)}")
    print(df[['Next order date']].head())

    # Filtrer les abonnements annulés avant la date limite
    cancelled_filter = df['Status'].str.upper() == 'CANCELLED'
    df = df[~(cancelled_filter & (df['Next order date'] < start_date))]

    return df


# Interface principale Streamlit
st.title("Debugging : Problèmes de type avec les dates")
uploaded_file = st.file_uploader("Téléversez le fichier CSV", type="csv")

if uploaded_file:
    df_processed = process_csv(uploaded_file)
    st.write("Aperçu des données après traitement :", df_processed.head())
