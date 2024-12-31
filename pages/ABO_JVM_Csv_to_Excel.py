import streamlit as st
import pandas as pd
from datetime import datetime

import pandas as pd
from datetime import datetime

def process_csv(csv_file):
    # Lire le fichier CSV
    df = pd.read_csv(csv_file)

    # Conversion explicite de 'Next order date' en datetime
    df['Next order date'] = pd.to_datetime(df['Next order date'], errors='coerce')

    # Identifier et afficher les valeurs non valides pour débogage
    invalid_dates = df[df['Next order date'].isnull()]
    if not invalid_dates.empty:
        print("Lignes avec des valeurs invalides dans 'Next order date' :")
        print(invalid_dates[['Next order date', 'Status', 'Customer name', 'ID']])  # Ajoutez d'autres colonnes si nécessaire

    # Normaliser les fuseaux horaires uniquement pour les valeurs valides
    df['Next order date'] = df['Next order date'].apply(
        lambda x: x.tz_localize(None) if pd.notnull(x) else x
    )

    # Définir la date limite
    today = datetime.today()
    start_date = pd.Timestamp(today.replace(day=5, hour=0, minute=0, second=0, microsecond=0))

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
