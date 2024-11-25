import streamlit as st
import pandas as pd
from io import BytesIO
from docx import Document

# Titre de l'application
st.title("Fusion de Noms pour Remerciements")

# Champ pour entrer le nom du fichier Word à télécharger
file_name = st.text_input("Entrez le nom du fichier Word à télécharger (sans extension) :")

# Téléversement des fichiers Excel
file_rem = st.file_uploader("Téléversez le fichier des remerciements (Excel)", type=["xls", "xlsx"])
file_changes = st.file_uploader("Téléversez le fichier des changements de noms (Excel)", type=["xls", "xlsx"])

if file_rem and file_changes and file_name:
    # Charger les fichiers Excel
    df_rem = pd.read_excel(file_rem)
    df_changes = pd.read_excel(file_changes)

    # Vérifier les colonnes nécessaires
    if 'Reference' not in df_rem.columns or 'Commande' not in df_changes.columns:
        st.error("Le fichier des remerciements doit contenir la colonne 'Reference' et le fichier des changements doit contenir la colonne 'Commande'.")
    elif 'A supprimer des pages Remerciements' not in df_changes.columns or 'A faire apparaitre sur les pages Remerciements' not in df_changes.columns:
        st.error("Le fichier des changements doit contenir les colonnes 'A supprimer des pages Remerciements' et 'A faire apparaitre sur les pages Remerciements'.")
    else:
        # Supprimer le symbole "#" dans la colonne 'Commande'
        df_changes['Commande'] = df_changes['Commande'].str.replace('#', '')

        # Créer un dictionnaire des remplacements
        replacements = df_changes.set_index('Commande')['A faire apparaitre sur les pages Remerciements'].to_dict()

        # Appliquer les remplacements sur la colonne 'Reference' dans df_rem
        df_rem['Nom Complet'] = df_rem.apply(
            lambda row: replacements.get(row['Reference'], f"{row['Prénom']} {row['Nom']}"), axis=1
        )

        # Trier les noms par ordre alphabétique (basé sur le **nom de famille complet**)
        # Extraction des noms de famille pour assurer un tri précis
        df_rem['Nom de Famille'] = df_rem['Nom'].str.strip()
        df_rem = df_rem.sort_values(by='Nom de Famille')

        # Fusionner les noms et prénoms dans l'ordre alphabétique
        sorted_names = df_rem['Nom Complet'].unique()

        # Nettoyer les espaces superflus
        sorted_names = [name.strip() for name in sorted_names]

        # Créer un document Word avec les noms triés
        doc = Document()
        doc.add_heading("Remerciements", level=0)
        doc.add_paragraph(", ".join(sorted_names))

        # Enregistrer dans un buffer mémoire pour téléchargement
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        # Générer un bouton de téléchargement pour le fichier Word
        word_file_name = f"{file_name}.docx"  # Nom personnalisé avec extension .docx
        st.download_button(
            label="Télécharger le fichier de remerciements (Word)",
            data=buffer,
            file_name=word_file_name,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
