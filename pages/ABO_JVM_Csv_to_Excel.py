import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil import parser


def convert_to_datetime(date_str):
    """Convertit une date ISO avec fuseau horaire en datetime sans timezone."""
    try:
        return parser.isoparse(date_str).replace(tzinfo=None)
    except Exception:
        return None  # Retourne None si la conversion échoue


def process_csv(csv_file):
    """Lit et traite le fichier CSV."""
    df = pd.read_csv(csv_file)

    # Vérifier si les colonnes essentielles sont présentes
    required_columns = {'Status', 'Next order date'}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        st.error(f"Colonnes manquantes dans le fichier CSV : {', '.join(missing_columns)}")
        return None, None

    # Normaliser la colonne 'Status' en majuscules
    df['Status'] = df['Status'].str.upper()
    
    # Conversion en datetime avec gestion des erreurs
    df['Next order date'] = df['Next order date'].astype(str).apply(convert_to_datetime)
    df = df[df['Next order date'].notna()].copy()  # Supprime les valeurs invalides

    # Définition de la date limite (5 du mois en cours)
    today = datetime.today()
    start_date = datetime(today.year, today.month, 5)

    # Filtrage automatique des abonnements annulés dont la Next Order Date >= 5 du mois
    cancelled_df = df[(df['Status'] == 'CANCELLED') & (df['Next order date'] >= start_date)]
    
    # Filtrage des abonnements actifs
    active_df = df[df['Status'] == 'ACTIVE']

    return active_df, cancelled_df


def prepare_final_files(df):
    """Prépare le fichier final avec les colonnes nécessaires et renommées."""
    column_mapping = {
        "ID": "Customer ID",
        "Customer name": "Delivery name",
        "Delivery address 1": "Delivery address 1",
        "Delivery address 2": "Delivery address 2",
        "Delivery zip": "Delivery zip",
        "Delivery city": "Delivery city",
        "Delivery province code": "Delivery province code",
        "Delivery country code": "Delivery country code",
        "Billing country": "Billing country",
        "Delivery interval count": "Quantity"
    }

    # Garder et renommer uniquement les colonnes nécessaires
    df = df[list(column_mapping.keys())].rename(columns=column_mapping)

    # Compléter les valeurs manquantes dans "Billing country"
    df['Billing country'] = df.apply(
        lambda row: "FRANCE" if pd.isnull(row['Billing country']) and row['Delivery country code'] == "FR" else row['Billing country'],
        axis=1
    )

    # Réorganiser les colonnes dans l'ordre final
    final_columns = [
        "Customer ID", "Delivery name", "Delivery address 1", "Delivery address 2", 
        "Delivery zip", "Delivery city", "Delivery province code", 
        "Delivery country code", "Billing country", "Quantity"
    ]
    return df[final_columns]


# Interface utilisateur Streamlit
st.title("Gestion des abonnements annulés et actifs")

# Champ pour personnaliser le préfixe des fichiers
file_prefix = st.text_input("Entrez le préfixe pour les fichiers finaux :", "")

# Upload du fichier CSV
uploaded_file = st.file_uploader("Téléversez le fichier CSV des abonnements", type="csv")

if uploaded_file:
    active_df, cancelled_df = process_csv(uploaded_file)

    if active_df is not None and cancelled_df is not None:
        # Vérification et message de confirmation du filtrage automatique
        st.success(f"{len(cancelled_df)} abonnements annulés sélectionnés automatiquement avec une Next Order Date >= {datetime.today().strftime('%Y-%m-05')}")

        # Fusionner les actifs et les abonnements annulés sélectionnés
        final_df = pd.concat([active_df, cancelled_df])

        # Préparer les fichiers finaux
        final_df = prepare_final_files(final_df)

        # Séparation des données en France et Étranger
        france_df = final_df[final_df['Delivery country code'] == 'FR']
        foreign_df = final_df[final_df['Delivery country code'] != 'FR']

        # Afficher les résultats finaux
        st.write("Aperçu des données finales pour la France :")
        st.dataframe(france_df)

        st.write("Aperçu des données finales pour l'étranger :")
        st.dataframe(foreign_df)

        # Vérification si le champ de préfixe est rempli
        if file_prefix.strip():
            # Téléchargement des fichiers finaux
            france_file = f"{file_prefix}_France.xlsx"
            foreign_file = f"{file_prefix}_Etranger.xlsx"

            france_df.to_excel(france_file, index=False)
            foreign_df.to_excel(foreign_file, index=False)

            st.download_button(
                label="Télécharger les données France",
                data=open(france_file, "rb"),
                file_name=france_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            st.download_button(
                label="Télécharger les données Étranger",
                data=open(foreign_file, "rb"),
                file_name=foreign_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.warning("Veuillez entrer un préfixe pour les fichiers finaux avant de télécharger.")
