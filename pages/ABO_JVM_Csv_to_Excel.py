import streamlit as st
import pandas as pd
from datetime import datetime

def process_csv(csv_file):
    # Charger le fichier CSV
    df = pd.read_csv(csv_file)

    # Normaliser les fuseaux horaires pour 'Next order date'
    df['Next order date'] = pd.to_datetime(df['Next order date'], errors='coerce').dt.tz_localize(None)

    # Créer la date limite de filtrage au format tz-naive
    start_date = datetime.now().replace(tzinfo=None)

    # Afficher les informations de debug pour vérifier les valeurs
    st.write("Valeurs dans 'Next order date' après conversion :")
    st.dataframe(df['Next order date'].head(10))
    st.write("Start date pour comparaison :", start_date)

    # Appliquer les filtres pour retirer les entrées annulées avec des dates trop anciennes
    cancelled_filter = df['Status'] == 'CANCELLED'

    # Comparaison des valeurs en s'assurant que les formats sont compatibles
    try:
        df = df[~(cancelled_filter & (df['Next order date'] < start_date))]
        st.write("Filtrage effectué avec succès.")
    except Exception as e:
        st.error(f"Erreur lors de la comparaison : {e}")

    # Retourner le dataframe filtré
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
