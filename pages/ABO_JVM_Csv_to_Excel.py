import streamlit as st
import pandas as pd

# Fonction pour reformater la date pour les abonnements annulés
def format_date(date_str):
    """ Reformate une date ISO en JJ/MM/AAAA. """
    if isinstance(date_str, str) and "T" in date_str:
        try:
            parts = date_str.split("T")[0].split("-")  # Extraire AAAA-MM-JJ
            return f"{parts[2]}/{parts[1]}/{parts[0]}"  # Reformater en JJ/MM/AAAA
        except Exception:
            return date_str  # Si erreur, conserver tel quel
    return date_str

def process_csv(csv_file):
    """Lit et traite le fichier CSV."""
    df = pd.read_csv(csv_file)

    # Vérifier si la colonne 'Next order date' est bien présente
    if 'Next order date' not in df.columns:
        st.error("La colonne 'Next order date' est introuvable dans le fichier CSV.")
        return None, None

    # Appliquer le formatage UNIQUEMENT sur les abonnements annulés
    df.loc[df['Status'] == 'CANCELLED', 'Next order date'] = df['Next order date'].apply(format_date)

    # Filtrer les abonnements actifs et annulés
    active_df = df[df['Status'] == 'ACTIVE']
    cancelled_df = df[df['Status'] == 'CANCELLED']

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
        st.success(f"{len(cancelled_df)} abonnements annulés sélectionnés automatiquement.")

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
