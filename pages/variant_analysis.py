import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io
from collections import defaultdict
import re

def analyze_file_structure(df):
    """Analyse automatique de la structure du fichier pour détecter les colonnes importantes"""
    
    # Dictionnaire de mapping pour les colonnes courantes
    column_mappings = {
        'email': ['customer: email', 'email', 'customer_email', 'user_email'],
        'country': ['shipping: country', 'country', 'shipping_country', 'billing_country'],
        'country_code': ['shipping: country code', 'country_code', 'shipping_country_code'],
        'product_name': ['line: name', 'product_name', 'item_name', 'line_name'],
        'quantity': ['line: quantity', 'quantity', 'qty', 'line_quantity'],
        'line_type': ['line: type', 'type', 'line_type', 'item_type'],
        'payment_status': ['payment: status', 'status', 'payment_status', 'order_status'],
        'order_id': ['id', 'order_id', 'order_number', 'name']
    }
    
    detected_columns = {}
    available_columns = [col.lower() for col in df.columns]
    
    for field, possible_names in column_mappings.items():
        for possible_name in possible_names:
            if possible_name in available_columns:
                # Retrouver le nom original de la colonne
                original_name = next(col for col in df.columns if col.lower() == possible_name)
                detected_columns[field] = original_name
                break
    
    return detected_columns, available_columns

def clean_and_filter_data(df, detected_columns, selected_statuses, selected_line_types):
    """Nettoie et filtre les données selon les critères choisis"""
    
    # Créer une copie pour éviter les modifications
    df_clean = df.copy()
    
    # Filtrer par statut de paiement si disponible
    if 'payment_status' in detected_columns and selected_statuses:
        status_col = detected_columns['payment_status']
        df_clean = df_clean[df_clean[status_col].isin(selected_statuses)]
    
    # Filtrer par type de ligne si disponible
    if 'line_type' in detected_columns and selected_line_types:
        line_type_col = detected_columns['line_type']
        df_clean = df_clean[df_clean[line_type_col].isin(selected_line_types)]
    
    # Supprimer les lignes avec des valeurs manquantes dans les colonnes critiques
    critical_columns = ['email', 'country', 'product_name']
    for col_key in critical_columns:
        if col_key in detected_columns:
            col_name = detected_columns[col_key]
            df_clean = df_clean.dropna(subset=[col_name])
    
    return df_clean

def create_user_variants(df, detected_columns):
    """Crée les variants pour chaque utilisateur en regroupant par email"""
    
    email_col = detected_columns['email']
    country_col = detected_columns['country']
    product_col = detected_columns['product_name']
    quantity_col = detected_columns.get('quantity')
    
    # Regrouper par utilisateur
    user_variants = {}
    
    for email, user_orders in df.groupby(email_col):
        # Obtenir le pays (prendre le premier si plusieurs)
        country = user_orders[country_col].iloc[0]
        
        # Calculer les produits et quantités
        product_counts = defaultdict(int)
        
        for _, order in user_orders.iterrows():
            product = order[product_col]
            
            # Gérer la quantité
            if quantity_col and pd.notna(order[quantity_col]):
                qty = int(order[quantity_col])
            else:
                qty = 1
            
            product_counts[product] += qty
        
        # Créer le variant (format: "1x Produit1 + 2x Produit2")
        variant_parts = []
        for product, qty in sorted(product_counts.items()):
            variant_parts.append(f"{qty}x {product}")
        
        variant = " + ".join(variant_parts)
        
        user_variants[email] = {
            'variant': variant,
            'country': country,
            'products': dict(product_counts)
        }
    
    return user_variants

def analyze_variants_by_country(user_variants):
    """Analyse les variants par pays"""
    
    # Structure: variant -> country -> count
    variant_country_stats = defaultdict(lambda: defaultdict(int))
    
    for user_data in user_variants.values():
        variant = user_data['variant']
        country = user_data['country']
        variant_country_stats[variant][country] += 1
    
    return variant_country_stats

def extract_unique_products(user_variants):
    """Extrait tous les produits uniques des variants"""
    all_products = set()
    
    for user_data in user_variants.values():
        all_products.update(user_data['products'].keys())
    
    return sorted(list(all_products))

def organize_variants_by_user_config(variant_country_stats, ordered_products):
    """Organise les variants selon la configuration utilisateur, sans doublons"""
    
    variant_groups = {}
    assigned_variants = set()  # Pour éviter les doublons
    
    # Pour chaque produit dans l'ordre choisi par l'utilisateur
    for product in ordered_products:
        group_name = product
        variants_for_product = []
        
        # Parcourir tous les variants pour trouver ceux qui contiennent ce produit
        for variant, country_stats in variant_country_stats.items():
            # Vérifier si ce variant n'a pas déjà été assigné
            if variant in assigned_variants:
                continue
                
            # Vérifier si ce produit est dans le variant
            if product in variant:
                variants_for_product.append((variant, country_stats))
                assigned_variants.add(variant)
        
        # Ajouter le groupe seulement s'il y a des variants
        if variants_for_product:
            variant_groups[group_name] = variants_for_product
    
    # Ajouter les variants restants dans "Autres combinaisons"
    remaining_variants = []
    for variant, country_stats in variant_country_stats.items():
        if variant not in assigned_variants:
            remaining_variants.append((variant, country_stats))
    
    if remaining_variants:
        variant_groups["Autres combinaisons"] = remaining_variants
    
    return variant_groups

def create_organized_results_dataframe(variant_country_stats, ordered_products):
    """Crée le DataFrame final organisé selon la configuration utilisateur"""
    
    # Obtenir tous les pays uniques
    all_countries = set()
    for country_stats in variant_country_stats.values():
        all_countries.update(country_stats.keys())
    
    all_countries = sorted(all_countries)
    
    # Organiser les variants par groupes selon la configuration utilisateur
    variant_groups = organize_variants_by_user_config(variant_country_stats, ordered_products)
    
    # Créer le DataFrame organisé
    results = []
    
    # Parcourir dans l'ordre configuré par l'utilisateur
    for product in ordered_products:
        if product not in variant_groups:
            continue
            
        # Ajouter une ligne de titre de section
        section_title = f"=== {product.upper()} ==="
        group_row = {'Variant': section_title, 'Total utilisateurs': ''}
        for country in all_countries:
            group_row[country] = ''
        results.append(group_row)
        
        # Trier les variants du groupe par popularité
        group_variants = sorted(variant_groups[product], 
                              key=lambda x: sum(x[1].values()), reverse=True)
        
        # Ajouter les variants du groupe
        for variant, country_stats in group_variants:
            total = sum(country_stats.values())
            
            # Nettoyer le nom du variant pour une meilleure lisibilité
            clean_variant = variant.replace('x ', '× ').replace(' + ', ' + ')
            
            row = {
                'Variant': clean_variant,
                'Total utilisateurs': total
            }
            
            # Ajouter chaque pays
            for country in all_countries:
                row[country] = country_stats.get(country, 0)
            
            results.append(row)
        
        # Ajouter une ligne vide entre les sections
        empty_row = {'Variant': '', 'Total utilisateurs': ''}
        for country in all_countries:
            empty_row[country] = ''
        results.append(empty_row)
    
    # Ajouter la section "Autres combinaisons" si elle existe
    if "Autres combinaisons" in variant_groups:
        # Titre de section
        section_title = "=== AUTRES COMBINAISONS ==="
        group_row = {'Variant': section_title, 'Total utilisateurs': ''}
        for country in all_countries:
            group_row[country] = ''
        results.append(group_row)
        
        # Variants de la section
        other_variants = sorted(variant_groups["Autres combinaisons"], 
                              key=lambda x: sum(x[1].values()), reverse=True)
        
        for variant, country_stats in other_variants:
            total = sum(country_stats.values())
            clean_variant = variant.replace('x ', '× ').replace(' + ', ' + ')
            
            row = {
                'Variant': clean_variant,
                'Total utilisateurs': total
            }
            
            for country in all_countries:
                row[country] = country_stats.get(country, 0)
            
            results.append(row)
    
    # Convertir en DataFrame
    df_results = pd.DataFrame(results)
    
    return df_results

def create_summary_stats(variant_groups, all_countries):
    """Crée un DataFrame avec les statistiques par groupe"""
    
    summary_data = []
    
    for group_name, variants in variant_groups.items():
        total_users = sum(sum(country_stats.values()) for _, country_stats in variants)
        total_variants = len(variants)
        
        # Calculer le top pays pour ce groupe
        country_totals = {}
        for _, country_stats in variants:
            for country, count in country_stats.items():
                country_totals[country] = country_totals.get(country, 0) + count
        
        top_country = max(country_totals.items(), key=lambda x: x[1]) if country_totals else ("N/A", 0)
        
        summary_data.append({
            'Produit/Groupe': group_name,
            'Nombre de variants': total_variants,
            'Total utilisateurs': total_users,
            'Pays principal': f"{top_country[0]} ({top_country[1]})"
        })
    
    return pd.DataFrame(summary_data)

# Interface Streamlit
st.title("🔍 Analyseur de Variants de Commandes")
st.write("Analysez automatiquement les combinaisons de produits achetés par vos clients et organisez-les selon vos préférences.")

# Upload du fichier
uploaded_file = st.file_uploader(
    "📁 Téléversez votre fichier Excel d'export des commandes", 
    type=['xlsx', 'xls']
)

if uploaded_file:
    with st.spinner("📊 Chargement et analyse du fichier..."):
        try:
            # Lire le fichier Excel
            df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ Fichier chargé avec succès ! {len(df)} lignes trouvées.")
        
        except Exception as e:
            st.error(f"❌ Erreur lors du chargement du fichier: {str(e)}")
            st.write("Veuillez vérifier que le fichier est un export Excel valide.")
            st.stop()
            
            # Analyse automatique de la structure
            st.write("## 🔍 Analyse automatique de la structure")
            
            detected_columns, available_columns = analyze_file_structure(df)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("### Colonnes détectées automatiquement")
                for field, column in detected_columns.items():
                    st.write(f"- **{field.replace('_', ' ').title()}**: `{column}`")
            
            with col2:
                st.write("### Toutes les colonnes disponibles")
                st.write(df.columns.tolist())
            
            # Vérification des colonnes critiques
            critical_fields = ['email', 'country', 'product_name']
            missing_critical = [field for field in critical_fields if field not in detected_columns]
            
            if missing_critical:
                st.error(f"❌ Colonnes critiques manquantes: {', '.join(missing_critical)}")
                st.write("**Aide à la configuration:**")
                st.write("- Email client: colonne contenant l'adresse email")
                st.write("- Pays: colonne contenant le pays de livraison")
                st.write("- Nom produit: colonne contenant le nom des produits")
                st.stop()
            
            # Configuration des filtres
            st.write("## ⚙️ Configuration des filtres")
            
            # Filtre par statut de paiement
            if 'payment_status' in detected_columns:
                status_col = detected_columns['payment_status']
                unique_statuses = df[status_col].dropna().unique().tolist()
                
                selected_statuses = st.multiselect(
                    f"Statuts de paiement à inclure (colonne: {status_col})",
                    options=unique_statuses,
                    default=['paid'] if 'paid' in unique_statuses else unique_statuses
                )
            else:
                selected_statuses = []
                st.info("ℹ️ Aucune colonne de statut de paiement détectée.")
            
            # Filtre par type de ligne
            if 'line_type' in detected_columns:
                line_type_col = detected_columns['line_type']
                unique_line_types = df[line_type_col].dropna().unique().tolist()
                
                selected_line_types = st.multiselect(
                    f"Types de ligne à inclure (colonne: {line_type_col})",
                    options=unique_line_types,
                    default=['Line Item'] if 'Line Item' in unique_line_types else unique_line_types
                )
            else:
                selected_line_types = []
                st.info("ℹ️ Aucune colonne de type de ligne détectée.")
            
            # Bouton d'analyse préliminaire
            if st.button("🔎 Analyser les produits disponibles", type="secondary"):
                with st.spinner("🔄 Analyse des produits..."):
                    
                    # Nettoyer et filtrer les données
                    df_clean = clean_and_filter_data(df, detected_columns, selected_statuses, selected_line_types)
                    
                    if len(df_clean) == 0:
                        st.error("❌ Aucune donnée ne correspond aux filtres sélectionnés.")
                        st.stop()
                    
                    st.info(f"📊 {len(df_clean)} lignes retenues après filtrage")
                    
                    # Créer les variants par utilisateur
                    user_variants = create_user_variants(df_clean, detected_columns)
                    
                    # Extraire tous les produits uniques
                    unique_products = extract_unique_products(user_variants)
                    
                    # Stocker dans session state pour utilisation ultérieure
                    st.session_state['df_clean'] = df_clean
                    st.session_state['detected_columns'] = detected_columns
                    st.session_state['user_variants'] = user_variants
                    st.session_state['unique_products'] = unique_products
                    
                    st.success("✅ Analyse terminée ! Configurez l'ordre des produits ci-dessous.")

# Configuration des produits (seulement si l'analyse a été faite)
if 'unique_products' in st.session_state:
    st.write("## 🎯 Configuration de l'organisation des variants")
    
    unique_products = st.session_state['unique_products']
    
    st.write("### Produits détectés automatiquement")
    st.write("Sélectionnez les produits principaux et définissez leur ordre d'affichage :")
    
    # Interface de sélection et d'ordonnancement
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write("**Produits disponibles :**")
        for i, product in enumerate(unique_products):
            st.write(f"{i+1}. {product}")
    
    with col2:
        st.write("**Configuration :**")
        st.info("""
        **Instructions :**
        1. Sélectionnez les produits principaux
        2. L'ordre de sélection = ordre d'affichage
        3. Les variants seront organisés sans doublons
        """)
    
    # Sélection multiple avec ordre
    selected_products = st.multiselect(
        "Sélectionnez les produits principaux dans l'ordre souhaité d'affichage :",
        options=unique_products,
        help="L'ordre de sélection détermine l'ordre d'affichage dans le rapport final"
    )
    
    # Aperçu de l'organisation
    if selected_products:
        st.write("### 📋 Aperçu de l'organisation")
        st.write("**Sections qui seront créées :**")
        
        for i, product in enumerate(selected_products, 1):
            st.write(f"{i}. **{product}** - Tous les variants contenant ce produit")
        
        if len(selected_products) < len(unique_products):
            st.write(f"{len(selected_products) + 1}. **Autres combinaisons** - Variants des autres produits")
    
    # Bouton de génération finale
    if selected_products:
        if st.button("🚀 Générer le rapport final", type="primary"):
            with st.spinner("🔄 Génération du rapport..."):
                
                # Récupérer les données depuis session state
                df_clean = st.session_state['df_clean']
                detected_columns = st.session_state['detected_columns']
                user_variants = st.session_state['user_variants']
                
                # Analyser les variants par pays
                variant_stats = analyze_variants_by_country(user_variants)
                
                # Organiser selon la configuration utilisateur
                variant_groups = organize_variants_by_user_config(variant_stats, selected_products)
                
                # Créer le DataFrame de résultats organisé
                results_df = create_organized_results_dataframe(variant_stats, selected_products)
                
                # Créer les statistiques par groupe
                all_countries = sorted(set(country for user_data in user_variants.values() for country in [user_data['country']]))
                summary_df = create_summary_stats(variant_groups, all_countries)
                
                # Afficher les statistiques générales
                st.write("## 📈 Statistiques générales")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Utilisateurs uniques", len(user_variants))
                with col2:
                    st.metric("Variants différents", len(variant_stats))
                with col3:
                    st.metric("Sections créées", len(selected_products) + (1 if len(selected_products) < len(unique_products) else 0))
                with col4:
                    st.metric("Pays différents", len(all_countries))
                
                # Afficher le résumé par section
                st.write("## 📊 Résumé par section")
                st.dataframe(summary_df, use_container_width=True)
                
                # Afficher les groupes principaux
                st.write("## 🏆 Aperçu des sections principales")
                
                for product in selected_products[:3]:  # Top 3 sections
                    if product in variant_groups:
                        variants = variant_groups[product]
                        total_users = sum(sum(country_stats.values()) for _, country_stats in variants)
                        
                        with st.expander(f"📦 {product} ({total_users} utilisateurs - {len(variants)} variants)"):
                            
                            # Trier par popularité
                            sorted_variants = sorted(variants, key=lambda x: sum(x[1].values()), reverse=True)
                            
                            for variant, country_stats in sorted_variants[:5]:  # Top 5 du groupe
                                total = sum(country_stats.values())
                                st.write(f"**{variant}** ({total} utilisateurs)")
                                
                                # Afficher les pays principaux
                                top_countries = sorted(country_stats.items(), key=lambda x: x[1], reverse=True)[:3]
                                country_text = ", ".join([f"{country}: {count}" for country, count in top_countries if count > 0])
                                if country_text:
                                    st.write(f"└─ {country_text}")
                                st.write("")
                
                # Option d'affichage du tableau complet
                st.write("## 📋 Tableau complet organisé")
                
                if st.checkbox("Afficher le tableau complet (peut être long à charger)"):
                    st.dataframe(results_df, use_container_width=True)
                else:
                    st.info("📊 Cochez la case ci-dessus pour afficher le tableau complet, ou téléchargez directement le fichier Excel.")
                
                # Export
                st.write("## 💾 Export des résultats")
                
                # Préparer le fichier Excel avec plusieurs feuilles
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    
                    # Feuille principale organisée
                    results_df.to_excel(writer, sheet_name='Variants organisés', index=False)
                    
                    # Feuille avec résumé par sections
                    summary_df.to_excel(writer, sheet_name='Résumé par sections', index=False)
                    
                    # Feuille avec les statistiques générales
                    stats_data = {
                        'Statistique': ['Utilisateurs uniques', 'Variants différents', 'Sections créées', 'Pays différents', 'Lignes traitées'],
                        'Valeur': [len(user_variants), len(variant_stats), len(selected_products) + (1 if len(selected_products) < len(unique_products) else 0),
                                 len(all_countries), len(df_clean)]
                    }
                    stats_df = pd.DataFrame(stats_data)
                    stats_df.to_excel(writer, sheet_name='Statistiques générales', index=False)
                    
                    # Feuille avec configuration utilisée
                    config_data = {
                        'Ordre d\'affichage': range(1, len(selected_products) + 1),
                        'Produit principal': selected_products
                    }
                    config_df = pd.DataFrame(config_data)
                    config_df.to_excel(writer, sheet_name='Configuration utilisée', index=False)
                
                buffer.seek(0)
                
                # Nom du fichier avec timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"analyse_variants_organisee_{timestamp}.xlsx"
                
                st.download_button(
                    label="📥 Télécharger l'analyse complète (Excel)",
                    data=buffer,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                st.success("✅ Rapport généré avec succès selon votre configuration !")

else:
    st.info("👆 Téléversez un fichier Excel et cliquez sur 'Analyser les produits disponibles' pour commencer.")
    
    # Section d'aide
    with st.expander("ℹ️ Comment utiliser cet outil"):
        st.write("""
        **Cet outil analyse vos exports de commandes et organise les variants selon vos préférences.**
        
        **Nouveau : Configuration personnalisée !**
        - L'outil détecte automatiquement tous les produits
        - Vous choisissez lesquels sont "principaux" 
        - Vous définissez l'ordre d'affichage
        - Aucun doublon : chaque variant n'apparaît qu'une fois
        
        **Format de fichier attendu:**
        - Fichier Excel (.xlsx ou .xls)
        - Une ligne par produit commandé
        - Colonnes requises : Email client, Pays, Nom du produit
        - Colonnes optionnelles : Quantité, Statut de paiement, Type de ligne
        
        **Étapes:**
        1. Téléversez votre fichier d'export
        2. Configurez les filtres de données
        3. Analysez les produits disponibles
        4. Sélectionnez et ordonnez vos produits principaux
        5. Générez le rapport personnalisé
        6. Téléchargez les résultats au format Excel
        
        **Logique anti-doublon:**
        Si un variant contient plusieurs produits principaux, il sera placé dans la première section selon votre ordre de priorité.
        
        **Exemple:** Si vous choisissez l'ordre "Super Smash Pack, Packman", alors le variant "1× Super Smash Pack + 1× Packman" sera dans la section Super Smash Pack uniquement.
        """)