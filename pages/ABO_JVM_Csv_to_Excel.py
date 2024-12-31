import streamlit as st
import pandas as pd
from datetime import datetime

import pandas as pd
from datetime import datetime

def process_csv(csv_file):
    # 1. Lire le fichier CSV avec toutes les colonnes
    df = pd.read_csv(csv_file)

    # 2. Analyser les valeurs invalides dans 'Next order date'
    try:
        # Tenter de convertir 'Next order date' en datetime
        df['Next order date'] = pd.to_datetime(df['Next order date'], errors='coerce')

        # Trouver les lignes avec des valeurs invalides
        invalid_dates = df[df['Next order date'].isnull()]
        print(f"Nombre total de valeurs invalides : {len(invalid_dates)}")

        if not invalid_dates.empty:
            print("Lignes avec des valeurs invalides dans 'Next order date' :")
            print(invalid_dates[['Next order date', 'Status', 'Customer name', 'ID']])

            print("Valeurs brutes non valides dans 'Next order date' :")
            print(invalid_dates['Next order date'].unique())
    except Exception as e:
        print(f"Erreur lors de l'analyse des valeurs invalides : {e}")

    # Continuez avec le reste du traitement (comme avant)
    # ...

    return df




# Interface principale Streamlit
st.title("Debugging : Problèmes de type avec les dates")
uploaded_file = st.file_uploader("Téléversez le fichier CSV", type="csv")

if uploaded_file:
    df_processed = process_csv(uploaded_file)
    st.write("Aperçu des données après traitement :", df_processed.head())
