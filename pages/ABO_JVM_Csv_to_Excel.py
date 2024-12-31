import streamlit as st
import pandas as pd
from datetime import datetime

def process_csv(csv_file):
    # 1. Lire le fichier CSV avec toutes les colonnes
    df = pd.read_csv(csv_file)

    # 2. Mettre toutes les valeurs en majuscules (facultatif si non nécessaire pour les dates)
    df = df.applymap(lambda x: x.upper() if isinstance(x, str) else x)

    # 3. Convertir la colonne "Next order date" en type datetime
    try:
        df['Next order date'] = pd.to_datetime(df['Next order date'], errors='coerce')
    except Exception as e:
        st.error(f"Erreur lors de la conversion des dates : {e}")
        return None

    # 4. Identifier les lignes avec des valeurs invalides dans "Next order date"
    invalid_dates = df[df['Next order date'].isnull()]
    st.write(f"Nombre total de valeurs invalides : {len(invalid_dates)}")

    # 5. Afficher les lignes invalides
    if not invalid_dates.empty:
        st.write("Voici toutes les lignes avec des valeurs invalides :")
        st.dataframe(invalid_dates)

        # Exporter les lignes invalides vers un fichier CSV
        invalid_dates_file = "invalid_dates.csv"
        invalid_dates.to_csv(invalid_dates_file, index=False)

        # Bouton de téléchargement pour le fichier des données invalides
        with open(invalid_dates_file, "rb") as file:
            st.download_button(
                label="Télécharger les données invalides",
                data=file,
                file_name=invalid_dates_file,
                mime="text/csv"
            )
    else:
        st.success("Aucune valeur invalide détectée dans 'Next order date'.")

    # 6. Continuer avec le traitement normal (filtrage, tri, etc.)
    today = datetime.today()
    start_date = today.replace(day=5)

    # Filtrer les abonnements annulés avec une date avant 'start_date'
    cancelled_filter = (df['Status'] == 'CANCELLED')
    if 'Next order date' in df.columns:
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

        # Exporter les données finales
        output_file = "processed_data.csv"
        df_processed.to_csv(output_file, index=False)

        # Bouton de téléchargement pour les données traitées
        with open(output_file, "rb") as file:
            st.download_button(
                label="Télécharger le fichier traité",
                data=file,
                file_name=output_file,
                mime="text/csv"
            )
