import streamlit as st
import pandas as pd
from datetime import datetime

def process_csv(csv_file):
    # Lire le fichier CSV
    df = pd.read_csv(csv_file)

    # Définir les limites de date
    today = datetime.today()
    date_limite = today.replace(day=4, hour=23, minute=59, second=59, microsecond=0)
    start_date = today.replace(day=5, hour=0, minute=0, second=0, microsecond=0)

    # Affichage de start_date et date_limite
    st.write("Date limite :", date_limite, "Type :", type(date_limite))
    st.write("Start date :", start_date, "Type :", type(start_date))

    # Convertir la colonne 'Next order date' en datetime
    df['Next order date'] = pd.to_datetime(df['Next order date'], errors='coerce')

    # Afficher les types des colonnes pour vérification
    st.write("Types des colonnes :", df.dtypes)

    # Afficher les premières lignes de 'Next order date' pour analyse
    st.write("Valeurs de 'Next order date' :", df['Next order date'].head())

    # Vérifier les lignes où 'Next order date' est null
    null_dates = df[df['Next order date'].isnull()]
    st.write("Lignes avec 'Next order date' non valide :", null_dates)

    # Filtrer les abonnements annulés avec la condition sur 'Next order date'
    cancelled_filter = (df['Status'] == 'CANCELLED')
    try:
        filtered_rows = df[cancelled_filter & (df['Next order date'] < start_date)]
        st.write("Lignes annulées avec 'Next order date' avant start_date :", filtered_rows)
    except Exception as e:
        st.error(f"Erreur lors de l'application du filtre : {e}")

    # Appliquer le filtre
    df = df[~(cancelled_filter & (df['Next order date'] < start_date))]

    return df

# Interface principale Streamlit
st.title("Debugging : Problèmes de type avec les dates")
uploaded_file = st.file_uploader("Téléversez le fichier CSV", type="csv")

if uploaded_file:
    df_processed = process_csv(uploaded_file)
    st.write("Aperçu des données après traitement :", df_processed.head())
