import streamlit as st
import pandas as pd

def process_csv(csv_file):
    # Lecture du fichier CSV
    df = pd.read_csv(csv_file)

    # Normaliser la colonne 'Status' en majuscules (si elle existe)
    if 'Status' in df.columns:
        df['Status'] = df['Status'].str.upper()
    else:
        st.error("La colonne 'Status' est introuvable dans le fichier CSV.")
        return None, None

    # Filtrage des abonnements annulés
    cancelled_df = df[df['Status'] == 'CANCELLED']

    # Diagnostic : Vérifier si des abonnements annulés existent
    if cancelled_df.empty:
        st.error("Aucun abonnement annulé (CANCELLED) trouvé dans les données.")
    else:
        st.success(f"{len(cancelled_df)} abonnements annulés trouvés.")

    # Filtrer les abonnements actifs
    active_df = df[df['Status'] == 'ACTIVE']

    return active_df, cancelled_df

def prepare_final_files(df):
    # Renommer les colonnes pour correspondre aux exigences finales
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

# Upload du fichier CSV
uploaded_file = st.file_uploader("Téléversez le fichier CSV des abonnements", type="csv")

if uploaded_file:
    active_df, cancelled_df = process_csv(uploaded_file)

    if active_df is not None and cancelled_df is not None:
        # Sélection des abonnements annulés à inclure
        st.write("Liste des abonnements annulés (CANCELLED) :")
        selected_rows = st.multiselect(
            "Sélectionnez les abonnements annulés à inclure dans le fichier final :",
            cancelled_df.index.tolist(),
            format_func=lambda x: f"ID: {cancelled_df.loc[x, 'ID']}, {cancelled_df.loc[x, 'Customer name']}, Next Order Date: {cancelled_df.loc[x, 'Next order date']}"
        )

        if selected_rows:
            selected_cancelled_df = cancelled_df.loc[selected_rows]
        else:
            selected_cancelled_df = pd.DataFrame()

        # Fusionner les actifs et les annulés sélectionnés
        final_df = pd.concat([active_df, selected_cancelled_df])

        # Préparer les fichiers finaux
        final_df = prepare_final_files(final_df)

        # Séparation des données en France et Reste du Monde
        france_df = final_df[final_df['Delivery country code'] == 'FR']
        rest_of_world_df = final_df[final_df['Delivery country code'] != 'FR']

        # Afficher les résultats finaux
        st.write("Aperçu des données finales pour la France :")
        st.dataframe(france_df)

        st.write("Aperçu des données finales pour le reste du monde :")
        st.dataframe(rest_of_world_df)

        # Téléchargement des fichiers finaux
        france_file = "final_france.xlsx"
        rest_of_world_file = "final_rest_of_world.xlsx"

        france_df.to_excel(france_file, index=False)
        rest_of_world_df.to_excel(rest_of_world_file, index=False)

        st.download_button(
            label="Télécharger les données France",
            data=open(france_file, "rb"),
            file_name=france_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.download_button(
            label="Télécharger les données Reste du Monde",
            data=open(rest_of_world_file, "rb"),
            file_name=rest_of_world_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
