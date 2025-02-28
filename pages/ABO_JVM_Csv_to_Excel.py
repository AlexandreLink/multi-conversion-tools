import streamlit as st
import pandas as pd
import pymongo
from datetime import datetime
import os
import re
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Récupération des clés d'API et connexion MongoDB depuis les variables d'environnement
mongo_uri = os.getenv("MONGODB_URI") or st.secrets.get("MONGODB_URI")

def robust_date_conversion(date_series):
    """Fonction améliorée pour la conversion des dates avec gestion de multiples formats"""
    # Copie des données pour préserver l'original
    cleaned_dates = date_series.astype(str).str.strip()
    
    # Liste des formats à essayer (du plus spécifique au plus général)
    date_formats = [
        '%Y-%m-%dT%H:%M:%S%z',  # Format ISO avec fuseau horaire
        '%Y-%m-%dT%H:%M:%S',     # Format ISO sans fuseau horaire
        '%Y-%m-%d %H:%M:%S%z',   # Format standard avec fuseau horaire
        '%Y-%m-%d %H:%M:%S',     # Format standard sans fuseau horaire
        '%Y-%m-%d',              # Date simple
        '%d/%m/%Y %H:%M:%S',     # Format européen avec heure
        '%d/%m/%Y',              # Format européen simple
        '%m/%d/%Y %H:%M:%S',     # Format US avec heure
        '%m/%d/%Y',              # Format US simple
    ]
    
    # Convertir les dates en utilisant pandas
    result = pd.to_datetime(cleaned_dates, errors='coerce', utc=True)
    
    # Pour les dates qui n'ont pas été converties, essayons les formats spécifiques
    mask = result.isna()
    if mask.any():
        problematic_dates = cleaned_dates[mask]
        st.write("⚠️ **Formats de dates problématiques détectés :**", problematic_dates.unique())
        
        # Essayer chaque format pour les dates problématiques
        for date_format in date_formats:
            try:
                # Convertir uniquement les dates problématiques restantes
                still_na = result.isna()
                temp_result = pd.to_datetime(cleaned_dates[still_na], format=date_format, errors='coerce')
                # Mettre à jour seulement les valeurs qui ont été converties
                result[still_na] = temp_result
                # Si toutes les dates sont converties, sortir de la boucle
                if not result.isna().any():
                    break
            except Exception as e:
                continue
    
    # Supprimer les fuseaux horaires pour uniformisation
    if result.dt.tz is not None:
        result = result.dt.tz_localize(None)
    
    return result

def load_from_mongodb():
    """Charge les données des abonnés YouTube depuis MongoDB"""
    if not mongo_uri:
        st.error("L'URI MongoDB n'est pas configuré. Veuillez vérifier vos variables d'environnement.")
        return pd.DataFrame()
    
    try:
        # Connexion à MongoDB
        client = pymongo.MongoClient(mongo_uri)
        db = client.get_database()
        collection = db.users  # Assurez-vous que c'est le bon nom de collection
        
        # Récupération des utilisateurs
        users = list(collection.find({}, {
            "_id": 0,  # Exclusion de l'ID MongoDB
            "name": 1,
            "address": 1,
            "city": 1,
            "postalCode": 1,
            "country": 1,
            "discordId": 1,
            "username": 1
        }))
        
        if not users:
            st.warning("Aucun abonné YouTube trouvé dans MongoDB.")
            return pd.DataFrame()
        
        # Conversion en DataFrame pandas
        df_youtube = pd.DataFrame(users)
        
        # Ajouter et renommer les colonnes pour correspondre au format attendu
        df_youtube['ID'] = df_youtube['discordId']  # Utiliser discordId comme identifiant unique
        df_youtube['Customer name'] = df_youtube['name']
        df_youtube['Delivery address 1'] = df_youtube['address']
        df_youtube['Delivery address 2'] = ""  # Colonne vide par défaut
        df_youtube['Delivery city'] = df_youtube['city']
        df_youtube['Delivery zip'] = df_youtube['postalCode']
        df_youtube['Delivery country code'] = df_youtube.apply(
            lambda row: "FR" if row.get('country', "").upper() == "FRANCE" else row.get('country', ""), 
            axis=1
        )
        df_youtube['Delivery province code'] = ""  # Colonne vide par défaut
        df_youtube['Billing country'] = df_youtube.apply(
            lambda row: "FRANCE" if row.get('country', "").upper() == "FRANCE" else row.get('country', ""),
            axis=1
        )
        df_youtube['Delivery interval count'] = 1  # Par défaut, 1 exemplaire par abonné
        df_youtube['Status'] = 'ACTIVE'  # Tous les abonnés YouTube sont considérés comme actifs
        df_youtube['Source'] = 'YouTube'  # Marquer la source
        df_youtube['Created at'] = datetime.now()  # Date actuelle comme date de création
        
        # Créer une colonne d'adresse complète pour affichage uniquement
        df_youtube['Shipping address'] = df_youtube.apply(
            lambda row: f"{row.get('address', '')}, {row.get('city', '')}, {row.get('postalCode', '')}, {row.get('country', '')}",
            axis=1
        )
        
        st.success(f"✅ **{len(df_youtube)} abonnés YouTube récupérés avec succès !**")
        return df_youtube
        
    except Exception as e:
        st.error(f"Erreur lors de la connexion à MongoDB: {e}")
        return pd.DataFrame()

def process_csv(uploaded_files, include_youtube=False):
    """Lit et traite plusieurs fichiers CSV, avec option d'inclure les abonnés YouTube."""
    all_dataframes = []

    for csv_file in uploaded_files:
        try:
            df = pd.read_csv(csv_file)
            st.write(f"✅ Fichier {csv_file.name} chargé : {len(df)} lignes")
            all_dataframes.append(df)
        except Exception as e:
            st.error(f"❌ Erreur lors du chargement de {csv_file.name}: {e}")
    
    if not all_dataframes:
        st.error("Aucun fichier CSV n'a pu être chargé.")
        return None, None

    # Fusionner tous les fichiers en un seul DataFrame
    df = pd.concat(all_dataframes, ignore_index=True)

    # Vérifier tous les statuts uniques présents
    unique_statuses = df['Status'].unique()
    st.write(f"📊 **Statuts d'abonnement trouvés :** {', '.join(unique_statuses)}")

    # Compter les abonnements par statut
    status_counts = df['Status'].value_counts()
    st.write("📊 **Nombre d'abonnements par statut avant filtrage :**")
    for status, count in status_counts.items():
        st.write(f"- {status}: {count}")

    # Vérifier les colonnes requises
    required_columns = ['ID', 'Created at', 'Status', 'Next order date', 'Customer name']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"Colonnes manquantes dans les fichiers CSV: {', '.join(missing_columns)}")
        return None, None

    # 🔍 Afficher un aperçu des données brutes
    st.write("🔍 **Aperçu des données brutes :**")
    st.dataframe(df.head(5))

    # 🧹 Nettoyage et conversion des dates
    st.write("🧹 **Nettoyage et conversion des dates...**")
    
    # Utiliser notre fonction robuste de conversion de dates
    original_count = len(df)
    df['Created at'] = robust_date_conversion(df['Created at'])
    
    # Supprimer les lignes avec des dates invalides
    df = df.dropna(subset=['Created at'])
    if len(df) < original_count:
        st.warning(f"⚠️ {original_count - len(df)} lignes avec des dates invalides ont été supprimées.")

    # 🔎 Afficher un aperçu après conversion
    st.write("🔎 **Aperçu après conversion des dates :**")
    st.dataframe(df[['ID', 'Created at']].head(5))

    # 🚀 Filtrage : Suppression des abonnements créés après le 5 du mois
    today = datetime.today()
    start_date = datetime(today.year, today.month, 5)

    df_before_filtering = len(df)

    # Ajoutez ce code pour capturer les abonnements qui vont être supprimés
    df_to_be_removed = df[df['Created at'] >= start_date].copy()
    st.write(f"🔍 **Analyse des {len(df_to_be_removed)} abonnements qui seront supprimés :**")

    # Afficher un échantillon de ces abonnements pour analyse
    if not df_to_be_removed.empty:
        # Afficher les statistiques sur les statuts
        status_counts = df_to_be_removed['Status'].value_counts()
        st.write("Répartition par statut :")
        for status, count in status_counts.items():
            st.write(f"- {status}: {count}")
        
        # Afficher les premières lignes pour inspection
        st.write("Échantillon des abonnements supprimés :")
        st.dataframe(df_to_be_removed[['ID', 'Status', 'Created at', 'Customer name']].head(10))
        
        # Option pour télécharger le fichier complet des supprimés
        removed_csv = df_to_be_removed.to_csv(index=False)
        st.download_button(
            label="📥 Télécharger la liste des abonnements supprimés",
            data=removed_csv,
            file_name="abonnements_supprimes.csv",
            mime="text/csv"
        )

    # Continuer avec le filtrage normal
    df = df[df['Created at'] < start_date]
    df_after_filtering = len(df)

    st.write(f"🚀 **Avant le filtrage : {df_before_filtering} abonnements**")
    st.write(f"✅ **Après le filtrage : {df_after_filtering} abonnements (supprimés : {df_before_filtering - df_after_filtering})**")

    # Standardisation de la colonne 'Status'
    df['Status'] = df['Status'].str.upper()

    # Ajout de la colonne 'Source' pour Shopify
    df['Source'] = 'Shopify'

    # Séparation initiale des abonnements par statut
    active_df = df[df['Status'] == 'ACTIVE']
    paused_df = df[df['Status'] == 'PAUSED']
    cancelled_df = df[df['Status'] == 'CANCELLED']

    # Afficher le nombre d'abonnements par statut
    st.write("📊 **Détail des abonnements par statut :**")
    st.write(f"- ACTIVE: {len(active_df)}")
    st.write(f"- PAUSED: {len(paused_df)}")
    st.write(f"- CANCELLED: {len(cancelled_df)}")

    # Filtrage spécifique pour les abonnements annulés
    # Conversion de "Next order date" en datetime avec gestion des erreurs
    try:
        # Convertir la colonne Next order date sans fuseau horaire
        cancelled_df['Next order date'] = pd.to_datetime(cancelled_df['Next order date'], errors='coerce', utc=True)
        
        # S'assurer que les dates n'ont pas de fuseau horaire
        if cancelled_df['Next order date'].dt.tz is not None:
            cancelled_df['Next order date'] = cancelled_df['Next order date'].dt.tz_localize(None)
        
        # Déterminer le 5 du mois actuel
        today = datetime.today()
        cutoff_date = datetime(today.year, today.month, 5)
        
        # Filtrer les abonnements annulés qui ont une date de prochaine commande après le 5 du mois
        # OU qui ont une date de prochaine commande nulle/invalide (les garder par précaution)
        valid_cancelled_df = cancelled_df[cancelled_df['Next order date'] > cutoff_date]
        
        excluded_count = len(cancelled_df) - len(valid_cancelled_df)
        if excluded_count > 0:
            st.info(f"ℹ️ {excluded_count} abonnements annulés ont été exclus car leur prochaine date de commande est avant le 5 du mois.")
        
        st.write(f"ℹ️ Sur {len(cancelled_df)} abonnements annulés, {len(valid_cancelled_df)} ont une date de commande postérieure au 5 du mois et sont conservés.")
    except Exception as e:
        st.error(f"Erreur lors de l'analyse des dates de commande: {e}")
        valid_cancelled_df = cancelled_df.copy()  # En cas d'erreur, garder tous les abonnements annulés par précaution
    
    # Supprimer les abonnements test (Brice N Guessan / Brice N'Guessan)
    pattern = r"Brice N'?Guessan"
    mask = valid_cancelled_df['Customer name'].str.contains(pattern, case=False, na=False, regex=True)
    test_count = mask.sum()
    if test_count > 0:
        valid_cancelled_df = valid_cancelled_df[~mask]
        st.info(f"ℹ️ {test_count} abonnements de test ont été supprimés.")

    # Intégrer les abonnés YouTube si demandé
    if include_youtube:
        youtube_df = load_from_mongodb()
        if not youtube_df.empty:
            # Sélectionner uniquement les colonnes nécessaires pour la fusion
            youtube_columns = [
                'ID', 'Customer name', 'Shipping address', 'Status', 
                'Created at', 'Source'
            ]
            youtube_df_filtered = youtube_df[youtube_columns]
            
            # Ajouter les abonnés YouTube aux abonnés actifs
            active_df = pd.concat([active_df, youtube_df_filtered], ignore_index=True)
            
            st.success(f"✅ **{len(youtube_df)} abonnés YouTube ajoutés aux abonnés actifs !**")

    return active_df, valid_cancelled_df

# Interface utilisateur Streamlit
st.title("Gestion des abonnements JV Magazine")
st.write("👋 Cet outil permet de traiter les abonnements Shopify et d'intégrer les abonnés YouTube Discord.")

# Option pour inclure les abonnés YouTube
include_youtube = st.checkbox("Inclure les abonnés YouTube depuis MongoDB", value=False)

file_prefix = st.text_input("Entrez le préfixe pour les fichiers finaux :", "")
uploaded_files = st.file_uploader("Téléversez les fichiers CSV des abonnements", type="csv", accept_multiple_files=True)

if uploaded_files:
    with st.spinner("Traitement des données en cours..."):
        active_df, cancelled_df = process_csv(uploaded_files, include_youtube)

    if active_df is not None and cancelled_df is not None:
        # Afficher les statistiques
        st.write("## 📊 Statistiques")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Abonnements actifs", len(active_df))
            if include_youtube:
                youtube_count = sum(active_df['Source'] == 'YouTube')
                shopify_count = sum(active_df['Source'] == 'Shopify')
                st.write(f"- Shopify: {shopify_count}")
                st.write(f"- YouTube: {youtube_count}")
        
        with col2:
            st.metric("Abonnements annulés", len(cancelled_df))
        
        # Afficher les aperçus
        st.write("## 📋 Aperçu des données")
        
        st.write(f"📌 **Abonnements actifs ({len(active_df)} lignes) :**")
        st.dataframe(active_df)

        st.write(f"📌 **Abonnements annulés ({len(cancelled_df)} lignes) :**")
        st.dataframe(cancelled_df)
        
        # Option d'exportation
        st.write("## 💾 Exportation des données")

        # Fonction pour déterminer si une adresse est en France
        def is_france(row):
            # Vérifier d'abord le pays de livraison s'il existe
            if 'Delivery country code' in row and pd.notna(row['Delivery country code']):
                return row['Delivery country code'].upper() == 'FR'
            
            # Vérifier le pays de livraison s'il existe
            if 'Delivery country' in row and pd.notna(row['Delivery country']):
                return 'FRANCE' in row['Delivery country'].upper()
            
            # Vérifier la méthode de livraison s'il existe
            if 'Delivery Method' in row and pd.notna(row['Delivery Method']):
                return 'FR' in row['Delivery Method'].upper()
            
            # Par défaut, considérer comme étranger si on ne peut pas déterminer
            return False

        # Fonction pour préparer le format final
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
            
            # S'assurer que toutes les colonnes nécessaires existent
            for col in column_mapping.keys():
                if col not in df.columns:
                    df[col] = None  # Ajouter une colonne vide si elle n'existe pas
            
            # Sélectionner et renommer les colonnes
            df = df[list(column_mapping.keys())].rename(columns=column_mapping)
            
            # Remplir la colonne Billing country pour la France si elle est vide
            df['Billing country'] = df.apply(
                lambda row: "FRANCE" if pd.isnull(row['Billing country']) and row['Delivery country code'] == "FR" else row['Billing country'],
                axis=1
            )
            
            final_columns = [
                "Customer ID", "Delivery name", "Delivery address 1", "Delivery address 2",
                "Delivery zip", "Delivery city", "Delivery province code",
                "Delivery country code", "Billing country", "Quantity"
            ]
            return df[final_columns]

        # Créer les dataframes séparés pour France et Étranger
        if active_df is not None and cancelled_df is not None:
            # Combiner actifs et annulés
            all_df = pd.concat([active_df, cancelled_df], ignore_index=True)
            
            # Préparer le format final
            all_df = prepare_final_files(all_df)
            
            # Séparer par pays
            france_df = all_df[all_df.apply(is_france, axis=1)]
            etranger_df = all_df[~all_df.apply(is_france, axis=1)]
            
            st.write(f"📊 **Répartition des abonnements :**")
            st.write(f"- France : {len(france_df)} abonnements")
            st.write(f"- Étranger : {len(etranger_df)} abonnements")
            
            # Afficher un aperçu
            st.write(f"📌 **Aperçu des données finales pour la France :**")
            st.dataframe(france_df.head(5))
            
            st.write(f"📌 **Aperçu des données finales pour l'étranger :**")
            st.dataframe(etranger_df.head(5))

        # Colonnes d'export 
        col1, col2 = st.columns(2)

        with col1:
            st.write("### 🇫🇷 Abonnements France")
            if st.button("Exporter le fichier France"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Définir le nom du fichier
                fr_filename = f"{file_prefix}_france_{timestamp}.csv" if file_prefix else f"france_{timestamp}.csv"
                
                # Convertir le DataFrame en CSV
                fr_csv = france_df.to_csv(index=False)
                
                # Proposer le téléchargement
                st.download_button(
                    label="📥 Télécharger les abonnements France",
                    data=fr_csv,
                    file_name=fr_filename,
                    mime="text/csv"
                )
                
                st.success(f"✅ Fichier France prêt à être téléchargé ({len(france_df)} abonnements)")

        with col2:
            st.write("### 🌍 Abonnements Étranger")
            if st.button("Exporter le fichier Étranger"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Définir le nom du fichier
                int_filename = f"{file_prefix}_etranger_{timestamp}.csv" if file_prefix else f"etranger_{timestamp}.csv"
                
                # Convertir le DataFrame en CSV
                int_csv = etranger_df.to_csv(index=False)
                
                # Proposer le téléchargement
                st.download_button(
                    label="📥 Télécharger les abonnements Étranger",
                    data=int_csv,
                    file_name=int_filename,
                    mime="text/csv"
                )
                
                st.success(f"✅ Fichier Étranger prêt à être téléchargé ({len(etranger_df)} abonnements)")