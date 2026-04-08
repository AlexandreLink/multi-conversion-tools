import streamlit as st
import pandas as pd
import pymongo
from datetime import datetime
import os
import re
from dotenv import load_dotenv
import io
from dateutil.relativedelta import relativedelta

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
        
        # Ajouter Line title pour les abonnés YouTube (par défaut Abo 1 an)
        df_youtube['Line title'] = 'Abonnement Extra - Engagement minimum de 12 mois'
        
        # Ajouter Next order date pour les abonnés YouTube (dans 12 mois)
        df_youtube['Next order date'] = datetime.now() + relativedelta(months=12)
        
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

def calculate_remaining_magazines(df):
    """Calcule le nombre de magazines restants pour chaque abonné basé sur Next order date"""
    
    # Vérifier que les colonnes nécessaires existent
    if 'Line title' not in df.columns:
        st.warning("⚠️ Colonne 'Line title' manquante. Calcul des magazines restants impossible.")
        df['Magazines Restants'] = None
        return df
    
    # Déterminer le type d'abonnement et le nombre total de magazines
    def get_total_magazines(line_title):
        if pd.isna(line_title):
            return 0
        line_title = str(line_title).lower()
        if 'flex' in line_title:
            return 1  # Sans engagement
        elif 'extra' in line_title or '1 an' in line_title or '12 mois' in line_title:
            return 12  # Engagement 12 numéros
        else:
            return 0  # Type inconnu
    
    today = datetime.now()
    
    def calculate_sent_magazines(row):
        try:
            total_magazines = get_total_magazines(row['Line title'])
            
            # Pour les abonnements Flex, utiliser Created at
            if total_magazines == 1:
                if 'Created at' in row and pd.notna(row['Created at']):
                    created_date = pd.to_datetime(row['Created at'])
                    
                    # Déterminer la date du premier envoi
                    if created_date.day < 5:
                        first_delivery = datetime(created_date.year, created_date.month, 5)
                    else:
                        if created_date.month == 12:
                            first_delivery = datetime(created_date.year + 1, 1, 5)
                        else:
                            first_delivery = datetime(created_date.year, created_date.month + 1, 5)
                    
                    # Si le premier envoi n'a pas encore eu lieu
                    if first_delivery > today:
                        return 0
                    else:
                        return 1  # Flex = 1 seul magazine
                else:
                    return 0
            
            # Pour les abonnements 12 mois (Extra et 1 an), utiliser Next order date
            elif total_magazines == 12:
                if 'Next order date' not in row or pd.isna(row['Next order date']):
                    # Si pas de Next order date, utiliser Created at comme fallback
                    if 'Created at' in row and pd.notna(row['Created at']):
                        created_date = pd.to_datetime(row['Created at'])
                        cycle_start = created_date
                    else:
                        return 0
                else:
                    # Convertir Next order date
                    next_order_date = pd.to_datetime(row['Next order date'])
                    
                    # Calculer le début du cycle actuel (12 mois avant next_order_date)
                    cycle_start = next_order_date - relativedelta(months=12)
                
                # Déterminer la date du premier envoi du cycle actuel
                if cycle_start.day < 5:
                    first_delivery = datetime(cycle_start.year, cycle_start.month, 5)
                else:
                    # Mois suivant
                    if cycle_start.month == 12:
                        first_delivery = datetime(cycle_start.year + 1, 1, 5)
                    else:
                        first_delivery = datetime(cycle_start.year, cycle_start.month + 1, 5)
                
                # Si le premier envoi n'a pas encore eu lieu
                if first_delivery > today:
                    return 0
                
                # Compter le nombre d'envois depuis le premier envoi du cycle actuel
                months_diff = (today.year - first_delivery.year) * 12 + (today.month - first_delivery.month)
                
                # Si on est après le 5 du mois actuel
                if today.day >= 5:
                    magazines_sent = months_diff + 1
                else:
                    magazines_sent = months_diff
                
                # Limiter au nombre total de magazines du cycle
                magazines_sent = min(magazines_sent, total_magazines)
                
                return magazines_sent
            
            else:
                return 0
                
        except Exception as e:
            st.warning(f"Erreur lors du calcul pour une ligne : {e}")
            return 0
    
    # Appliquer les calculs
    df['Total magazines'] = df['Line title'].apply(get_total_magazines)
    df['Magazines envoyés'] = df.apply(calculate_sent_magazines, axis=1)
    df['Magazines Restants'] = df['Total magazines'] - df['Magazines envoyés']
    
    # S'assurer que le nombre restant n'est jamais négatif
    df['Magazines Restants'] = df['Magazines Restants'].apply(lambda x: max(0, x))
    
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
    
    # Convertir aussi Next order date
    df['Next order date'] = robust_date_conversion(df['Next order date'])
    
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

    st.write(f"✅ **Abonnements après filtrage : {df_after_filtering} (Nombres d'abonnements crées après le 5 du mois : {df_before_filtering - df_after_filtering})**")

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
    # Exclure les abonnements avec motifs d'annulation spécifiques
    if 'Cancellation note' in cancelled_df.columns:
        # Liste des motifs d'annulation à exclure
        exclusion_patterns = [
            'Remboursement',
            'Arrêt abonnement',
            'Arrêt d\'abonnement',
            'Arret abonnement',
            'changer d\'abonnement',
            'Erreur du client',
            'résilier son abonnement',
            'annuler son abonnement',
            'pris deux fois',
            'déjà un autre abonnement',
            'demande du client',
            'commande frauduleuse',
            'Test',
            'opté pour un abonnement',
            'ne pas renouveler',
            'souscrit deux fois',
            'Abonnement en double'
        ]
        
        # Créer le pattern regex (| = OU)
        pattern = '|'.join(exclusion_patterns)
        
        # Filtrer avec case=False pour ignorer majuscules/minuscules
        exclusion_mask = cancelled_df['Cancellation note'].str.contains(pattern, case=False, na=False, regex=True)
        exclusion_count = exclusion_mask.sum()
        
        if exclusion_count > 0:
            # Filtrer pour ne garder que les abonnements sans motif d'exclusion
            cancelled_df = cancelled_df[~exclusion_mask]
            st.info(f"ℹ️ {exclusion_count} abonnements annulés ont été exclus (motifs d'annulation).")
    
    # Ensuite, continuer avec le filtrage par date
    try:
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
        
        # Section spéciale pour les abonnements 1 an
        st.write("## 📦 Analyse Abonnements 1 an")
        
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
        
        # Fonction pour déterminer si une adresse est en Europe (hors France)
        def is_europe(row):
            if is_france(row):
                return False
            
            # Liste des codes pays européens (hors France)
            european_countries = [
                'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'DE', 
                'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 
                'PT', 'RO', 'SK', 'SI', 'ES', 'SE', 'GB', 'CH', 'NO', 'IS'
            ]
            
            if 'Delivery country code' in row and pd.notna(row['Delivery country code']):
                return row['Delivery country code'].upper() in european_countries
            
            return False
        
        # S'assurer que valid_cancelled_df existe
        if 'valid_cancelled_df' not in locals() and 'valid_cancelled_df' not in globals():
            valid_cancelled_df = cancelled_df
        
        # Combiner actifs et annulés
        all_subs = pd.concat([active_df, valid_cancelled_df], ignore_index=True)
        
        # Calculer les magazines restants
        all_subs = calculate_remaining_magazines(all_subs)
        
        # Filtrer uniquement les abonnements "1 an"
        if 'Line title' in all_subs.columns:
            abo_1an_mask = all_subs['Line title'].str.contains('1 an', case=False, na=False, regex=True)
            abo_1an = all_subs[abo_1an_mask]
            
            if not abo_1an.empty:
                # Répartition géographique
                abo_1an_france = abo_1an[abo_1an.apply(is_france, axis=1)]
                abo_1an_europe = abo_1an[abo_1an.apply(is_europe, axis=1)]
                abo_1an_monde = abo_1an[~abo_1an.apply(is_france, axis=1) & ~abo_1an.apply(is_europe, axis=1)]
                
                # Calcul des magazines restants par zone
                magazines_france = int(abo_1an_france['Magazines Restants'].sum())
                magazines_europe = int(abo_1an_europe['Magazines Restants'].sum())
                magazines_monde = int(abo_1an_monde['Magazines Restants'].sum())
                
                # Prix par magazine selon la zone
                prix_magazine_france = 54.96 / 12  # 4.58€ par magazine
                prix_magazine_europe = 78.96 / 12  # 6.58€ par magazine
                prix_magazine_monde = 114.96 / 12  # 9.58€ par magazine
                
                # Calcul des dettes par zone
                dette_france = magazines_france * prix_magazine_france
                dette_europe = magazines_europe * prix_magazine_europe
                dette_monde = magazines_monde * prix_magazine_monde
                dette_totale = dette_france + dette_europe + dette_monde
                
                # Affichage des statistiques globales
                total_magazines_1an = magazines_france + magazines_europe + magazines_monde
                nombre_abonnes_1an = len(abo_1an)
                
                st.write("### 📊 Vue d'ensemble")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("👥 Nombre d'abonnés 1 an", nombre_abonnes_1an)
                with col2:
                    st.metric("📚 Total magazines à envoyer", total_magazines_1an)
                with col3:
                    st.metric("💰 Dette totale estimée", f"{dette_totale:.2f} €")
                
                # Répartition détaillée par zone
                st.write("### 🌍 Répartition géographique et calcul de dette")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write("#### 🇫🇷 France")
                    st.metric("Abonnés", len(abo_1an_france))
                    st.metric("Magazines restants", magazines_france)
                    st.write(f"**Prix abo 1 an :** 54.96 €")
                    st.write(f"**Prix/magazine :** {prix_magazine_france:.2f} €")
                    st.write(f"**Calcul :** {magazines_france} × {prix_magazine_france:.2f} €")
                    st.success(f"**Dette France : {dette_france:.2f} €**")
                
                with col2:
                    st.write("#### 🇪🇺 Europe")
                    st.metric("Abonnés", len(abo_1an_europe))
                    st.metric("Magazines restants", magazines_europe)
                    st.write(f"**Prix abo 1 an :** 78.96 €")
                    st.write(f"**Prix/magazine :** {prix_magazine_europe:.2f} €")
                    st.write(f"**Calcul :** {magazines_europe} × {prix_magazine_europe:.2f} €")
                    st.success(f"**Dette Europe : {dette_europe:.2f} €**")
                
                with col3:
                    st.write("#### 🌍 Monde")
                    st.metric("Abonnés", len(abo_1an_monde))
                    st.metric("Magazines restants", magazines_monde)
                    st.write(f"**Prix abo 1 an :** 114.96 €")
                    st.write(f"**Prix/magazine :** {prix_magazine_monde:.2f} €")
                    st.write(f"**Calcul :** {magazines_monde} × {prix_magazine_monde:.2f} €")
                    st.success(f"**Dette Monde : {dette_monde:.2f} €**")
                
                # Résumé final
                st.write("---")
                st.write("### 💼 Résumé financier")
                summary_col1, summary_col2 = st.columns(2)
                with summary_col1:
                    st.info(f"""
                    **Détail des dettes :**
                    - France : {dette_france:.2f} €
                    - Europe : {dette_europe:.2f} €
                    - Monde : {dette_monde:.2f} €
                    """)
                with summary_col2:
                    st.error(f"""
                    **DETTE TOTALE**  
                    ## {dette_totale:.2f} €
                    """)
                
            else:
                st.info("ℹ️ Aucun abonnement 1 an trouvé dans les données.")
        else:
            st.warning("⚠️ Colonne 'Line title' manquante. Impossible d'analyser les abonnements 1 an.")
        
        # Option d'exportation
        st.write("## 💾 Exportation des données")

        # Fonction pour préparer le format final (SANS Type d'abonnement et Magazines Restants)
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
            
            # Calculer les magazines restants AVANT de préparer les fichiers finaux
            all_df = calculate_remaining_magazines(all_df)
            
            # Vérification finale pour les entrées de test
            all_df = remove_test_entries(all_df)
            
            # Créer le fichier spécial pour les abonnements 1 an avec calcul de dette
            if 'Line title' in all_df.columns:
                # Filtrer uniquement les abonnements 1 an
                abo_1an_mask = all_df['Line title'].str.contains('1 an', case=False, na=False, regex=True)
                debt_df = all_df[abo_1an_mask].copy()
                
                if not debt_df.empty:
                    # Fonction pour déterminer le prix selon la zone
                    def get_price_info(row):
                        if is_france(row):
                            return 54.96, 54.96 / 12, 'France'
                        elif is_europe(row):
                            return 78.96, 78.96 / 12, 'Europe'
                        else:
                            return 114.96, 114.96 / 12, 'Monde'
                    
                    # Calculer les prix et la dette pour chaque ligne
                    debt_df[['Prix abo 1 an', 'Prix par magazine', 'Zone']] = debt_df.apply(
                        lambda row: pd.Series(get_price_info(row)), axis=1
                    )
                    
                    # Calculer la dette individuelle
                    debt_df['Dette (Magazine × Prix)'] = debt_df['Magazines Restants'] * debt_df['Prix par magazine']
                    
                    # Calculer les totaux pour les colonnes de synthèse
                    total_dette_france = debt_df[debt_df['Zone'] == 'France']['Dette (Magazine × Prix)'].sum()
                    total_dette_europe = debt_df[debt_df['Zone'] == 'Europe']['Dette (Magazine × Prix)'].sum()
                    total_dette_monde = debt_df[debt_df['Zone'] == 'Monde']['Dette (Magazine × Prix)'].sum()
                    total_dette_globale = total_dette_france + total_dette_europe + total_dette_monde
                    
                    # Sélectionner et réorganiser les colonnes pour le fichier final
                    debt_report = debt_df[[
                        'Customer name',
                        'Zone',
                        'Magazines Restants',
                        'Prix abo 1 an',
                        'Prix par magazine',
                        'Dette (Magazine × Prix)'
                    ]].copy()
                    
                    # Renommer pour plus de clarté
                    debt_report.columns = [
                        'Nom Prénom',
                        'Zone',
                        'Magazines Restants',
                        'Prix Abonnement 1 an (€)',
                        'Prix par Magazine (€)',
                        'Dette Totale (€)'
                    ]
                    
                    # Ajouter les colonnes de synthèse (vides sauf première ligne)
                    debt_report['Dette France (€)'] = None
                    debt_report['Dette Europe (€)'] = None
                    debt_report['Dette Monde (€)'] = None
                    debt_report['Dette Totale Globale (€)'] = None
                    
                    # Remplir uniquement la première ligne avec les totaux
                    debt_report.iloc[0, debt_report.columns.get_loc('Dette France (€)')] = round(total_dette_france, 2)
                    debt_report.iloc[0, debt_report.columns.get_loc('Dette Europe (€)')] = round(total_dette_europe, 2)
                    debt_report.iloc[0, debt_report.columns.get_loc('Dette Monde (€)')] = round(total_dette_monde, 2)
                    debt_report.iloc[0, debt_report.columns.get_loc('Dette Totale Globale (€)')] = round(total_dette_globale, 2)
                    
                    # Arrondir les prix à 2 décimales
                    debt_report['Prix Abonnement 1 an (€)'] = debt_report['Prix Abonnement 1 an (€)'].round(2)
                    debt_report['Prix par Magazine (€)'] = debt_report['Prix par Magazine (€)'].round(2)
                    debt_report['Dette Totale (€)'] = debt_report['Dette Totale (€)'].round(2)
                    
                    # Afficher un aperçu
                    st.write("## 💰 Rapport de Dette - Abonnements 1 an")
                    st.write(f"📊 **{len(debt_report)} abonnés 1 an avec dette calculée**")
                    st.dataframe(debt_report)
                    
                    # Statistiques rapides
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Dette totale", f"{total_dette_globale:.2f} €")
                    with col2:
                        st.metric("Dette moyenne", f"{debt_report['Dette Totale (€)'].mean():.2f} €")
                    with col3:
                        st.metric("Total magazines", int(debt_report['Magazines Restants'].sum()))
            
            # Préparer le format final (sans Type d'abonnement et Magazines Restants)
            all_df_export = prepare_final_files(all_df)

            # Vérification ultime des entrées de test
            name_pattern = r"Brice N'?Guessan"
            mask = all_df_export['Delivery name'].str.contains(name_pattern, case=False, na=False, regex=True)
            test_count = mask.sum()
            if test_count > 0:
                # Les supprimer
                all_df_export = all_df_export[~mask]
                st.info(f"ℹ️ {test_count} entrées de test supplémentaires ont été éliminées.")
            
            # Séparer par pays
            france_df = all_df_export[all_df_export.apply(is_france, axis=1)].copy()
            etranger_df = all_df_export[~all_df_export.apply(is_france, axis=1)].copy()
            
            st.write(f"📊 **Répartition des abonnements (tous types) :**")
            st.write(f"- France : {len(france_df)} abonnements")
            st.write(f"- Étranger : {len(etranger_df)} abonnements")
            
            # Afficher un aperçu
            st.write(f"📌 **Données finales pour la France :**")
            st.dataframe(france_df)

            st.write(f"📌 **Données finales pour l'étranger :**")
            st.dataframe(etranger_df)

        # Colonnes d'export (3 colonnes maintenant)
        col1, col2, col3 = st.columns(3)

        with col1:
            st.write("### 🇫🇷 Abonnements France")
            if st.button("Exporter le fichier France"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Définir le nom du fichier
                fr_filename = f"{file_prefix}_france_{timestamp}.xlsx" if file_prefix else f"france_{timestamp}.xlsx"
                
                # Créer un buffer pour stocker le fichier Excel
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    france_df.to_excel(writer, index=False, sheet_name='Abonnements France')
                buffer.seek(0)
                
                # Proposer le téléchargement
                st.download_button(
                    label="📥 Télécharger les abonnements France",
                    data=buffer,
                    file_name=fr_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                st.success(f"✅ Fichier France prêt à être téléchargé ({len(france_df)} abonnements)")

        with col2:
            st.write("### 🌍 Abonnements Étranger")
            if st.button("Exporter le fichier Étranger"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Définir le nom du fichier
                int_filename = f"{file_prefix}_etranger_{timestamp}.xlsx" if file_prefix else f"etranger_{timestamp}.xlsx"
                
                # Créer un buffer pour stocker le fichier Excel
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    etranger_df.to_excel(writer, index=False, sheet_name='Abonnements Etranger')
                buffer.seek(0)
                
                # Proposer le téléchargement
                st.download_button(
                    label="📥 Télécharger les abonnements Étranger",
                    data=buffer,
                    file_name=int_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                st.success(f"✅ Fichier Étranger prêt à être téléchargé ({len(etranger_df)} abonnements)")

        with col3:
            st.write("### 💰 Rapport Dette 1 an")
            if 'debt_report' in locals():
                if st.button("Exporter le rapport de dette"):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # Définir le nom du fichier
                    debt_filename = f"{file_prefix}_dette_1an_{timestamp}.xlsx" if file_prefix else f"dette_1an_{timestamp}.xlsx"
                    
                    # Créer un buffer pour stocker le fichier Excel
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        debt_report.to_excel(writer, index=False, sheet_name='Dette Abonnements 1 an')
                    buffer.seek(0)
                    
                    # Proposer le téléchargement
                    st.download_button(
                        label="📥 Télécharger le rapport de dette",
                        data=buffer,
                        file_name=debt_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    st.success(f"✅ Rapport de dette prêt ({len(debt_report)} abonnés)")
            else:
                st.info("ℹ️ Aucun abonnement 1 an trouvé pour le rapport de dette")
