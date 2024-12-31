import streamlit as st
import pandas as pd
from datetime import datetime

def process_csv(csv_file):
    # Lire le fichier CSV avec toutes les colonnes
    df = pd.read_csv(csv_file)

    # Afficher les types de données initiaux pour débogage
    st.write("Types initiaux des colonnes :", df.dtypes)

    # Afficher toutes les valeurs dans 'Next order date' avant conversion
    st.write("Valeurs brutes dans 'Next order date' avant conversion :")
    st.dataframe(df['Next order date'])

    # Convertir la colonne 'Next order date' en datetime
    df['Next order date'] = pd.to_datetime(df['Next order date'], errors='coerce')

    # Afficher les valeurs après conversion
    st.write("Valeurs dans 'Next order date' après conversion :")
    st.dataframe(df['Next order date'])

    # Vérifier si des valeurs sont invalides après conversion
    invalid_dates = df[df['Next order date'].isnull()]
    st.write(f"Nombre total de valeurs invalides après conversion : {len(invalid_dates)}")
    if not invalid_dates.empty:
        st.write("Lignes avec des dates invalides après conversion :")
        st.dataframe(invalid_dates)

    # Filtrer les lignes avec des valeurs valides
    df = df[df['Next order date'].notnull()]

    # Définir start_date comme un objet datetime
    today = datetime.today()
    start_date = pd.Timestamp(today.replace(day=5))

    # Afficher start_date pour vérification
    st.write("Start date pour comparaison :", start_date)

    # Appliquer le filtre pour les abonnements annulés
    cancelled_filter = (df['Status'] == 'CANCELLED')
    try:
        df = df[~(cancelled_filter & (df['Next order date'] < start_date))]
    except Exception as e:
        st.error(f"Erreur lors de la comparaison : {e}")
        st.stop()

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
