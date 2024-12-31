import streamlit as st
import pandas as pd
from datetime import datetime

def process_csv(csv_file):
    # Lire le fichier CSV
    df = pd.read_csv(csv_file)

    # Conversion de 'Next order date' en datetime
    df['Next order date'] = pd.to_datetime(df['Next order date'], errors='coerce')

    # Calcul de start_date en datetime
    today = datetime.today()
    start_date = today.replace(day=5, hour=0, minute=0, second=0, microsecond=0)
    start_date = pd.Timestamp(start_date)  # Assurez-vous que c'est un Timestamp Pandas

    # Afficher pour debug
    print(f"Start date type: {type(start_date)} | Value: {start_date}")
    print(f"Next order date sample: {df['Next order date'].head()}")

    # Filtrage des abonnements annulés avec Next order date avant start_date
    cancelled_filter = (df['Status'] == 'CANCELLED')
    df = df[~(cancelled_filter & (df['Next order date'] < start_date))]

    return df


# Interface principale Streamlit
st.title("Debugging : Problèmes de type avec les dates")
uploaded_file = st.file_uploader("Téléversez le fichier CSV", type="csv")

if uploaded_file:
    df_processed = process_csv(uploaded_file)
    st.write("Aperçu des données après traitement :", df_processed.head())
