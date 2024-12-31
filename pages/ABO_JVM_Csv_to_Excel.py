import streamlit as st
import pandas as pd
from datetime import datetime

def process_csv(csv_file):
    # Charger le fichier CSV
    df = pd.read_csv(csv_file)

    # Conversion initiale de 'Next order date' en datetime, avec gestion des erreurs
    df['Next order date'] = pd.to_datetime(df['Next order date'], errors='coerce')

    # Identifier les valeurs non interprétées comme dates (valeurs NaT)
    invalid_dates = df[df['Next order date'].isna()]
    if not invalid_dates.empty:
        st.write("Valeurs non valides dans 'Next order date' :")
        st.dataframe(invalid_dates)
    else:
        st.write("Toutes les valeurs de 'Next order date' sont valides.")

    # Supprimer les fuseaux horaires pour 'Next order date' uniquement si les valeurs sont valides
    df['Next order date'] = df['Next order date'].dt.tz_localize(None)

    # Créer la date limite de filtrage au format tz-naive
    start_date = datetime.now().replace(tzinfo=None)

    # Afficher les informations pour vérification
    st.write("Valeurs dans 'Next order date' après conversion :")
    st.dataframe(df['Next order date'].head(10))
    st.write("Start date pour comparaison :", start_date)

    # Appliquer les filtres pour retirer les entrées annulées avec des dates trop anciennes
    cancelled_filter = df['Status'] == 'CANCELLED'

    # Comparaison des valeurs
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
