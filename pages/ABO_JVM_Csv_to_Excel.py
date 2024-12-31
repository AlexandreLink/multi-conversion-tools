import streamlit as st
import pandas as pd
from datetime import datetime

def process_csv(csv_file):
    # Charger le fichier CSV
    df = pd.read_csv(csv_file)

    # Étape 1 : Conversion initiale en datetime
    df['Next order date'] = pd.to_datetime(df['Next order date'], errors='coerce')

    # Vérifier les types pour s'assurer qu'il n'y a que des datetime
    st.write("Types de données après conversion :")
    st.write(df['Next order date'].dtype)

    # Étape 2 : Identifier les valeurs invalides
    invalid_dates = df[df['Next order date'].isna()]
    if not invalid_dates.empty:
        st.write("Valeurs non valides dans 'Next order date' :")
        st.dataframe(invalid_dates)
    else:
        st.write("Toutes les valeurs de 'Next order date' sont valides.")

    # Étape 3 : Forcer la suppression des fuseaux horaires
    try:
        df['Next order date'] = df['Next order date'].apply(lambda x: x.tz_localize(None) if pd.notnull(x) else x)
    except Exception as e:
        st.error(f"Erreur lors de la suppression des fuseaux horaires : {e}")
        return df  # Retourne le DataFrame actuel pour déboguer

    # Étape 4 : Créer la date limite pour filtrer
    start_date = datetime.now().replace(day=5, hour=0, minute=0, second=0, microsecond=0)
    st.write("Date limite pour filtrage (start_date) :", start_date)

    # Étape 5 : Appliquer le filtre
    cancelled_filter = df['Status'] == 'CANCELLED'
    try:
        df = df[~(cancelled_filter & (df['Next order date'] < start_date))]
        st.write("Filtrage effectué avec succès.")
    except Exception as e:
        st.error(f"Erreur lors de la comparaison : {e}")

    # Retourner le DataFrame filtré
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
