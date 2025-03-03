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
        
        # Récupération des utilisateurs avec uniquement les nouveaux champs
        users = list(collection.find({}, {
            "_id": 0,  # Exclusion de l'ID MongoDB
            "customerID": 1,
            "deliveryName": 1,
            "deliveryAddress1": 1, 
            "deliveryAddress2": 1,
            "deliveryZip": 1,
            "deliveryCity": 1,
            "deliveryProvinceCode": 1,
            "deliveryCountryCode": 1,
            "billingCountry": 1,
            "quantity": 1,
            "discordId": 1,
            "username": 1
        }))
        
        if not users:
            st.warning("Aucun abonné YouTube trouvé dans MongoDB.")
            return pd.DataFrame()
        
        # Conversion en DataFrame pandas
        df_youtube = pd.DataFrame(users)
        
        # Filtrer les entrées de test Brice N Guessan dès le chargement
        if 'deliveryName' in df_youtube.columns:
            name_pattern = r"Brice N'?Guessan"
            name_mask = df_youtube['deliveryName'].str.contains(name_pattern, case=False, na=False, regex=True)
            
            # Vérification pour l'email si présent
            email_mask = pd.Series(False, index=df_youtube.index)
            if 'username' in df_youtube.columns:
                email_mask = df_youtube['username'].str.contains('bnguessan@linkdigitalspirit.com', case=False, na=False)
            
            # Combiner les masques
            test_mask = name_mask | email_mask
            test_count = test_mask.sum()
            
            if test_count > 0:
                st.warning(f"⚠️ Suppression de {test_count} entrées de test (Brice N Guessan) des données YouTube.")
                df_youtube = df_youtube[~test_mask]
            
        # Uniformiser les noms de colonnes pour le format final attendu par les transporteurs
        column_mapping = {
            "customerID": "ID",
            "deliveryName": "Customer name",
            "deliveryAddress1": "Delivery address 1",
            "deliveryAddress2": "Delivery address 2",
            "deliveryZip": "Delivery zip",
            "deliveryCity": "Delivery city",
            "deliveryProvinceCode": "Delivery province code",
            "deliveryCountryCode": "Delivery country code",
            "billingCountry": "Billing country",
            "quantity": "Delivery interval count"
        }
        
        # Renommer les colonnes pour correspondre au format attendu
        df_youtube = df_youtube.rename(columns=column_mapping)
        
        # Ajouter les colonnes manquantes pour la compatibilité
        for col in column_mapping.values():
            if col not in df_youtube.columns:
                df_youtube[col] = None
        
        # Ajouter la colonne Source pour distinguer ces entrées
        df_youtube['Source'] = 'YouTube'
        df_youtube['Status'] = 'ACTIVE'  # Tous les abonnés YouTube sont considérés comme actifs
        df_youtube['Created at'] = datetime.now()  # Date actuelle comme date de création
        
        st.success(f"✅ **{len(df_youtube)} abonnés YouTube récupérés avec succès !**")
        return df_youtube
        
    except Exception as e:
        st.error(f"Erreur lors de la connexion à MongoDB: {e}")
        return pd.DataFrame()

# Fonction dédiée à la suppression des entrées de test
def remove_test_entries(df):
    """Supprime toutes les entrées liées à Brice N Guessan et son email"""
    if df.empty:
        return df
    
    initial_count = len(df)
    
    # Pattern pour le nom
    name_pattern = r"Brice N'?Guessan"
    name_mask = df['Customer name'].str.contains(name_pattern, case=False, na=False, regex=True)
    
    # Pattern pour l'email - vérifier si la colonne existe
    email_mask = pd.Series(False, index=df.index)
    email_columns = ['Email', 'Customer email', 'email']
    for email_col in email_columns:
        if email_col in df.columns:
            col_mask = df[email_col].str.contains('bnguessan@linkdigitalspirit.com', case=False, na=False)
            email_mask = email_mask | col_mask
    
    # Combiner les masques
    test_mask = name_mask | email_mask
    test_count = test_mask.sum()
    
    if test_count > 0:
        # Supprimer les entrées de test sans afficher de détails
        df = df[~test_mask]
        st.info(f"ℹ️ {test_count} entrées de test ont été supprimées.")
    
    return df

def process_csv(uploaded_files, include_youtube=False):
    """Lit et traite plusieurs fichiers CSV, avec option d'inclure les abonnés YouTube."""
    all_dataframes = []

    for csv_file in uploaded_files:
        try:
            df = pd.read_csv(csv_file)
            st.write(f"✅ Fichier {csv_file.name} chargé : {len(df)} lignes")
            
            # Supprimer les entrées de test immédiatement après le chargement
            df = remove_test_entries(df)
            
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

    # Vérifier les colonnes requises
    required_columns = ['ID', 'Created at', 'Status', 'Next order date', 'Customer name']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"Colonnes manquantes dans les fichiers CSV: {', '.join(missing_columns)}")
        return None, None
    
    # Utiliser notre fonction robuste de conversion de dates
    original_count = len(df)
    df['Created at'] = robust_date_conversion(df['Created at'])
    
    # Supprimer les lignes avec des dates invalides
    df = df.dropna(subset=['Created at'])
    if len(df) < original_count:
        st.warning(f"⚠️ {original_count - len(df)} lignes avec des dates invalides ont été supprimées.")

    # 🚀 Filtrage : Suppression des abonnements créés après le 5 du mois
    today = datetime.today()
    start_date = datetime(today.year, today.month, 5)

    df_before_filtering = len(df)

    # Calculer quels abonnements seront supprimés sans les afficher
    df_to_be_removed = df[df['Created at'] >= start_date].copy()
    removed_count = len(df_to_be_removed)

    # Créer le bouton de téléchargement pour les abonnements supprimés si nécessaire
    if not df_to_be_removed.empty:
        removed_csv = df_to_be_removed.to_csv(index=False)
        st.download_button(
            label="📥 Télécharger la liste des abonnements supprimés",
            data=removed_csv,
            file_name="abonnements_supprimes.csv",
            mime="text/csv",
            help="Télécharger la liste des abonnements créés après le 5 du mois"
        )

    # Continuer avec le filtrage normal
    df = df[df['Created at'] < start_date]
    df_after_filtering = len(df)

    st.write(f"✅ **Abonnements après filtrage : {df_after_filtering} (supprimés : {df_before_filtering - df_after_filtering})**")

    # Standardisation de la colonne 'Status'
    df['Status'] = df['Status'].str.upper()

    # Ajout de la colonne 'Source' pour Shopify
    df['Source'] = 'Shopify'

    # Séparation initiale des abonnements par statut
    active_df = df[df['Status'] == 'ACTIVE']
    paused_df = df[df['Status'] == 'PAUSED']
    cancelled_df = df[df['Status'] == 'CANCELLED']

    # Vérifier à nouveau pour les entrées de test à chaque étape
    active_df = remove_test_entries(active_df)
    cancelled_df = remove_test_entries(cancelled_df)

    # Filtrage spécifique pour les abonnements annulés
    # D'abord, exclure les abonnements remboursés
    if 'Cancellation note' in cancelled_df.columns:
        # Compter les abonnements remboursés
        refund_mask = cancelled_df['Cancellation note'].str.contains('Remboursement', case=False, na=False)
        refund_count = refund_mask.sum()
        
        if refund_count > 0:
            # Filtrer pour ne garder que les abonnements non remboursés
            cancelled_df = cancelled_df[~refund_mask]
            st.info(f"ℹ️ {refund_count} abonnements remboursés ont été exclus.")
    
    # Ensuite, continuer avec le filtrage par date
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
        valid_cancelled_df = cancelled_df[cancelled_df['Next order date'] > cutoff_date]
        
        excluded_count = len(cancelled_df) - len(valid_cancelled_df)
        if excluded_count > 0:
            st.info(f"ℹ️ {excluded_count} abonnements annulés ont été exclus car leur prochaine date de commande est avant le 5 du mois.")
        
    except Exception as e:
        st.error(f"Erreur lors de l'analyse des dates de commande: {e}")
        valid_cancelled_df = cancelled_df.copy()  # En cas d'erreur, garder tous les abonnements annulés par précaution
    
    # Vérifier à nouveau pour les entrées de test dans les cancelled valides
    valid_cancelled_df = remove_test_entries(valid_cancelled_df)

    # Intégrer les abonnés YouTube si demandé
    if include_youtube:
        youtube_df = load_from_mongodb()
        if not youtube_df.empty:
            # Ajouter les abonnés YouTube aux abonnés actifs
            active_df = pd.concat([active_df, youtube_df], ignore_index=True)
            
            # Vérifier une dernière fois après la fusion
            active_df = remove_test_entries(active_df)
            
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
            # S'assurer que valid_cancelled_df existe
            if 'valid_cancelled_df' not in locals() and 'valid_cancelled_df' not in globals():
                valid_cancelled_df = cancelled_df
    
            # Combiner actifs et annulés
            all_df = pd.concat([active_df, valid_cancelled_df], ignore_index=True)
            
            # Vérification finale pour les entrées de test
            all_df = remove_test_entries(all_df)
            
            # Préparer le format final
            all_df = prepare_final_files(all_df)

            # Vérification ultime des entrées de test
            name_pattern = r"Brice N'?Guessan"
            mask = all_df['Delivery name'].str.contains(name_pattern, case=False, na=False, regex=True)
            test_count = mask.sum()
            if test_count > 0:
                # Les supprimer
                all_df = all_df[~mask]
                st.info(f"ℹ️ {test_count} entrées de test supplémentaires ont été éliminées.")
            
            # Séparer par pays
            france_df = all_df[all_df.apply(is_france, axis=1)]
            etranger_df = all_df[~all_df.apply(is_france, axis=1)]
            
            st.write(f"📊 **Répartition des abonnements :**")
            st.write(f"- France : {len(france_df)} abonnements")
            st.write(f"- Étranger : {len(etranger_df)} abonnements")
            
            # Afficher un aperçu
            st.write(f"📌 **Données finales pour la France :**")
            st.dataframe(france_df)

            st.write(f"📌 **Données finales pour l'étranger :**")
            st.dataframe(etranger_df)

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