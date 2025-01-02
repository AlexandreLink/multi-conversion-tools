import streamlit as st
import pandas as pd


st.set_page_config(
    layout="wide",  # Augmente la largeur de la page
    page_title="Gestion des abonnements",  # Titre de la page
    page_icon="📄"  # Icône
)

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
    st.write("Aperçu brut des abonnements annulés (avant transformation) :")
    st.dataframe(cancelled_df)

    if cancelled_df.empty:
        st.error("Aucun abonnement annulé (CANCELLED) trouvé dans les données.")
    else:
        st.success(f"{len(cancelled_df)} abonnements annulés trouvés.")

    # Filtrer les abonnements actifs
    active_df = df[df['Status'] == 'ACTIVE']

    return active_df, cancelled_df


# Interface utilisateur Streamlit
st.title("Gestion des abonnements annulés et actifs")

# Upload du fichier CSV
uploaded_file = st.file_uploader("Téléversez le fichier CSV des abonnements", type="csv")

if uploaded_file:
    active_df, cancelled_df = process_csv(uploaded_file)

    if active_df is not None and cancelled_df is not None:
        # Affichage des abonnements actifs
        st.write("Aperçu des abonnements actifs (ACTIVE) :")
        st.dataframe(active_df)

        # Sélection des abonnements annulés à inclure
        st.write("Liste des abonnements annulés (CANCELLED) :")
        selected_indices = []
        for idx, row in cancelled_df.iterrows():
            # Ajouter des informations supplémentaires dans chaque ligne de sélection
            checkbox_label = (
                f"ID: {row['ID']} | Nom: {row['Customer name']} | "
                f"Email: {row['Customer email']} | Next Order Date: {row['Next order date']}"
            )
            if st.checkbox(checkbox_label, key=f"cancelled_{idx}"):
                selected_indices.append(idx)

        # Filtrer les abonnements annulés sélectionnés
        selected_cancelled_df = cancelled_df.loc[selected_indices]

        # Fusionner les actifs et les annulés sélectionnés
        final_df = pd.concat([active_df, selected_cancelled_df])

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
        rest_of_world_file.to_excel(rest_of_world_file, index=False)

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
