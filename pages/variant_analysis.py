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

def identify_base_products(user_variants):
    """Identifie automatiquement les produits de base en analysant les patterns de commandes"""
    
    all_products = set()
    product_popularity = {}
    product_combinations = {}
    
    for user_data in user_variants.values():
        products = user_data['products']
        all_products.update(products.keys())
        
        # Compter la popularité de chaque produit
        for product in products.keys():
            product_popularity[product] = product_popularity.get(product, 0) + 1
        
        # Analyser les combinaisons (quels produits apparaissent ensemble)
        product_list = list(products.keys())
        if len(product_list) > 1:
            for i, product1 in enumerate(product_list):
                for product2 in product_list[i+1:]:
                    combo = tuple(sorted([product1, product2]))
                    product_combinations[combo] = product_combinations.get(combo, 0) + 1
    
    # Stratégie 1: Les produits les plus populaires (achetés seuls fréquemment)
    solo_purchases = {}
    for user_data in user_variants.values():
        products = user_data['products']
        if len(products) == 1:  # Achat d'un seul produit
            product = list(products.keys())[0]
            solo_purchases[product] = solo_purchases.get(product, 0) + 1
    
    # Stratégie 2: Identifier les produits qui apparaissent dans beaucoup de variants
    product_in_variants = {}
    for user_data in user_variants.values():
        for product in user_data['products'].keys():
            product_in_variants[product] = product_in_variants.get(product, 0) + 1
    
    # Calculer un score pour déterminer les produits de base
    base_product_scores = {}
    
    for product in all_products:
        score = 0
        
        # Plus un produit est acheté seul, plus il est probablement un produit de base
        solo_count = solo_purchases.get(product, 0)
        total_appearances = product_in_variants.get(product, 0)
        
        if total_appearances > 0:
            solo_ratio = solo_count / total_appearances
            score += solo_ratio * 100  # Poids fort pour les achats seuls
        
        # Plus un produit est populaire globalement, plus il peut être un produit de base
        popularity_score = product_popularity.get(product, 0)
        score += popularity_score * 0.1  # Poids faible pour la popularité générale
        
        base_product_scores[product] = score
    
    # Trier par score décroissant
    sorted_products = sorted(base_product_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Seuil automatique : prendre les produits avec un score significatif
    # ou au minimum les 3 produits les plus probables d'être des produits de base
    threshold = max(10, sorted_products[0][1] * 0.1) if sorted_products else 10
    
    base_products = []
    other_products = []
    
    for product, score in sorted_products:
        if score >= threshold or len(base_products) < 3:
            base_products.append(product)
        else:
            other_products.append(product)
    
    return base_products, other_products

def get_product_group_name(variant, base_products):
    """Détermine le nom du groupe pour un variant donné"""
    
    # Extraire les produits du variant
    variant_products = []
    parts = variant.split(' + ')
    for part in parts:
        # Extraire le nom du produit (après "1x ", "2x ", etc.)
        if '× ' in part:
            product_name = part.split('× ', 1)[1]
        elif 'x ' in part:
            product_name = part.split('x ', 1)[1]
        else:
            product_name = part
        variant_products.append(product_name.strip())
    
    # Trouver quel produit de base est dans ce variant
    main_base_product = None
    for product in variant_products:
        if product in base_products:
            if main_base_product is None:
                main_base_product = product
            # Si plusieurs produits de base, prendre le plus populaire (premier dans la liste)
            elif base_products.index(product) < base_products.index(main_base_product):
                main_base_product = product
    
    if main_base_product:
        # Vérifier si c'est juste le produit seul
        if len(variant_products) == 1 and variant_products[0] == main_base_product:
            return f"{main_base_product} (seul)", main_base_product
        else:
            return f"{main_base_product} + Add-ons", main_base_product
    else:
        return "Autres combinaisons", None

def organize_variants_by_groups(variant_country_stats, user_variants):
    """Organise les variants par groupes logiques de façon automatique"""
    
    base_products, other_products = identify_base_products(user_variants)
    
    # Créer des groupes de variants
    variant_groups = {}
    
    for variant, country_stats in variant_country_stats.items():
        # Déterminer à quel groupe appartient ce variant
        group_name, main_product = get_product_group_name(variant, base_products)
        
        if group_name not in variant_groups:
            variant_groups[group_name] = []
        
        variant_groups[group_name].append((variant, country_stats))
    
    return variant_groups, base_products

def create_organized_results_dataframe(variant_country_stats, user_variants):
    """Crée le DataFrame final organisé par groupes automatiquement détectés"""
    
    # Obtenir tous les pays uniques
    all_countries = set()
    for country_stats in variant_country_stats.values():
        all_countries.update(country_stats.keys())
    
    all_countries = sorted(all_countries)
    
    # Organiser les variants par groupes
    variant_groups, base_products = organize_variants_by_groups(variant_country_stats, user_variants)
    
    # Créer le DataFrame organisé
    results = []
    
    # Ordre de priorité pour les groupes (basé sur les produits de base détectés automatiquement)
    group_priority = []
    
    # D'abord les produits seuls (dans l'ordre de leur importance détectée)
    for base_product in base_products:
        group_name = f"{base_product} (seul)"
        if group_name in variant_groups:
            group_priority.append(group_name)
    
    # Puis les variants de chaque produit (dans l'ordre de leur importance)
    for base_product in base_products:
        group_name = f"{base_product} + Add-ons"
        if group_name in variant_groups:
            group_priority.append(group_name)
    
    # Enfin les autres
    if "Autres combinaisons" in variant_groups:
        group_priority.append("Autres combinaisons")
    
    # Construire le DataFrame
    for group_name in group_priority:
        if group_name not in variant_groups:
            continue
            
        # Ajouter une ligne de séparation/titre de groupe
        group_row = {'Variant': f"=== {group_name.upper()} ===", 'Total utilisateurs': ''}
        for country in all_countries:
            group_row[country] = ''
        results.append(group_row)
        
        # Trier les variants du groupe par popularité
        group_variants = sorted(variant_groups[group_name], 
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
        
        # Ajouter une ligne vide entre les groupes
        empty_row = {'Variant': '', 'Total utilisateurs': ''}
        for country in all_countries:
            empty_row[country] = ''
        results.append(empty_row)
    
    # Convertir en DataFrame
    df_results = pd.DataFrame(results)
    
    return df_results

def create_summary_stats(variant_groups, all_countries):
    """Crée un DataFrame avec les statistiques par groupe"""
    
    summary_data = []
    
    for group_name, variants in variant_groups.items():
        if "===" in group_name:  # Ignorer les lignes de titre
            continue
            
        total_users = sum(sum(country_stats.values()) for _, country_stats in variants)
        total_variants = len(variants)
        
        # Calculer le top pays pour ce groupe
        country_totals = {}
        for _, country_stats in variants:
            for country, count in country_stats.items():
                country_totals[country] = country_totals.get(country, 0) + count
        
        top_country = max(country_totals.items(), key=lambda x: x[1]) if country_totals else ("N/A", 0)
        
        summary_data.append({
            'Groupe': group_name,
            'Nombre de variants': total_variants,
            'Total utilisateurs': total_users,
            'Pays principal': f"{top_country[0]} ({top_country[1]})"
        })
    
    return pd.DataFrame(summary_data)

# Interface Streamlit
st.title("🔍 Analyseur de Variants de Commandes")
st.write("Analysez automatiquement les combinaisons de produits achetés par vos clients et leur répartition géographique.")

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
            
            # Bouton d'analyse
            if st.button("🚀 Lancer l'analyse des variants", type="primary"):
                with st.spinner("🔄 Traitement en cours..."):
                    
                    # Nettoyer et filtrer les données
                    df_clean = clean_and_filter_data(df, detected_columns, selected_statuses, selected_line_types)
                    
                    if len(df_clean) == 0:
                        st.error("❌ Aucune donnée ne correspond aux filtres sélectionnés.")
                        st.stop()
                    
                    st.info(f"📊 {len(df_clean)} lignes retenues après filtrage")
                    
                    # Créer les variants par utilisateur
                    user_variants = create_user_variants(df_clean, detected_columns)
                    
                    # Analyser les variants par pays
                    variant_stats = analyze_variants_by_country(user_variants)
                    
                    # Organiser les variants par groupes
                    variant_groups, base_products = organize_variants_by_groups(variant_stats, user_variants)
                    
                    # Afficher l'analyse automatique des produits de base
                    st.write("## 🤖 Analyse automatique des produits")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("### Produits de base détectés")
                        for i, product in enumerate(base_products, 1):
                            st.write(f"{i}. **{product}**")
                    
                    with col2:
                        st.write("### Logique de détection")
                        st.info("""
                        **Critères automatiques :**
                        - Fréquence d'achat seul
                        - Popularité générale 
                        - Présence dans les variants
                        
                        Les produits sont classés automatiquement sans liste prédéfinie !
                        """)
                    
                    # Créer le DataFrame de résultats organisé
                    results_df = create_organized_results_dataframe(variant_stats, user_variants)
                    summary_df = create_summary_stats(variant_groups, list(set(country for user_data in user_variants.values() for country in [user_data['country']])))
                    
                    # Afficher les statistiques générales
                    st.write("## 📈 Statistiques générales")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Utilisateurs uniques", len(user_variants))
                    with col2:
                        st.metric("Variants différents", len(variant_stats))
                    with col3:
                        st.metric("Groupes de produits", len(variant_groups))
                    with col4:
                        st.metric("Pays différents", len(set(country for user_data in user_variants.values() for country in [user_data['country']])))
                    
                    # Afficher le résumé par groupe
                    st.write("## 📊 Résumé par groupe de produits")
                    st.dataframe(summary_df, use_container_width=True)
                    
                    # Afficher les groupes principaux
                    st.write("## 🏆 Analyse par groupes de produits")
                    
                    # Filtrer et afficher seulement les groupes principaux (pas les lignes vides)
                    display_groups = {k: v for k, v in variant_groups.items() if not k.startswith("===")}
                    
                    for group_name, variants in list(display_groups.items())[:5]:  # Top 5 groupes
                        total_group_users = sum(sum(country_stats.values()) for _, country_stats in variants)
                        
                        with st.expander(f"📦 {group_name} ({total_group_users} utilisateurs - {len(variants)} variants)"):
                            
                            # Trier les variants du groupe par popularité
                            sorted_variants = sorted(variants, key=lambda x: sum(x[1].values()), reverse=True)
                            
                            for variant, country_stats in sorted_variants[:10]:  # Top 10 du groupe
                                total = sum(country_stats.values())
                                st.write(f"**{variant}** ({total} utilisateurs)")
                                
                                # Afficher seulement les pays avec des commandes
                                active_countries = {k: v for k, v in country_stats.items() if v > 0}
                                if active_countries:
                                    country_text = ", ".join([f"{country}: {count}" for country, count in 
                                                            sorted(active_countries.items(), key=lambda x: x[1], reverse=True)])
                                    st.write(f"└─ {country_text}")
                                st.write("")  # Ligne vide
                    
                    # Afficher le tableau complet organisé
                    st.write("## 📋 Tableau complet organisé par groupes")
                    
                    # Option pour télécharger un aperçu
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
                        
                        # Obtenir le workbook et worksheet pour le formatage
                        workbook = writer.book
                        worksheet = writer.sheets['Variants organisés']
                        
                        # Format pour les titres de groupes
                        group_format = workbook.add_format({
                            'bold': True,
                            'font_size': 12,
                            'bg_color': '#D3D3D3',
                            'align': 'center'
                        })
                        
                        # Appliquer le formatage aux lignes de titre de groupe
                        for row_num, (_, row) in enumerate(results_df.iterrows(), start=1):
                            if isinstance(row['Variant'], str) and row['Variant'].startswith('==='):
                                worksheet.set_row(row_num, None, group_format)
                        
                        # Feuille avec résumé par groupes
                        summary_df.to_excel(writer, sheet_name='Résumé par groupes', index=False)
                        
                        # Feuille avec les statistiques générales
                        stats_data = {
                            'Statistique': ['Utilisateurs uniques', 'Variants différents', 'Groupes de produits', 'Pays différents', 'Lignes traitées'],
                            'Valeur': [len(user_variants), len(variant_stats), len(variant_groups),
                                     len(set(country for user_data in user_variants.values() for country in [user_data['country']])),
                                     len(df_clean)]
                        }
                        stats_df = pd.DataFrame(stats_data)
                        stats_df.to_excel(writer, sheet_name='Statistiques générales', index=False)
                        
                        # Feuille avec les détails des groupes
                        group_details = []
                        for group_name, variants in variant_groups.items():
                            if group_name.startswith("==="):
                                continue
                            group_details.append({'Groupe': group_name, 'Variant': '', 'Total utilisateurs': ''})
                            
                            # Trier par popularité
                            sorted_variants = sorted(variants, key=lambda x: sum(x[1].values()), reverse=True)
                            
                            for variant, country_stats in sorted_variants:
                                total = sum(country_stats.values())
                                group_details.append({
                                    'Groupe': '',
                                    'Variant': variant,
                                    'Total utilisateurs': total
                                })
                        
                        if group_details:
                            group_details_df = pd.DataFrame(group_details)
                            group_details_df.to_excel(writer, sheet_name='Détails par groupes', index=False)
                    
                    buffer.seek(0)
                    
                    # Nom du fichier avec timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"analyse_variants_{timestamp}.xlsx"
                    
                    st.download_button(
                        label="📥 Télécharger l'analyse complète (Excel)",
                        data=buffer,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    st.success("✅ Analyse terminée avec succès !")
        
        except Exception as e:
            st.error(f"❌ Erreur lors du traitement du fichier: {str(e)}")
            st.write("Veuillez vérifier que le fichier est un export Excel valide.")

else:
    st.info("👆 Téléversez un fichier Excel pour commencer l'analyse.")
    
    # Section d'aide
    with st.expander("ℹ️ Comment utiliser cet outil"):
        st.write("""
        **Cet outil analyse automatiquement vos exports de commandes pour identifier les variants (combinaisons de produits) achetés par vos clients.**
        
        **Format de fichier attendu:**
        - Fichier Excel (.xlsx ou .xls)
        - Une ligne par produit commandé
        - Colonnes requises : Email client, Pays, Nom du produit
        - Colonnes optionnelles : Quantité, Statut de paiement, Type de ligne
        
        **Étapes:**
        1. Téléversez votre fichier d'export
        2. L'outil détecte automatiquement la structure
        3. Configurez les filtres (statuts de paiement, types de ligne)
        4. Lancez l'analyse
        5. Téléchargez les résultats au format Excel
        
        **Résultats obtenus:**
        - Liste de tous les variants (combinaisons de produits)
        - Nombre d'utilisateurs par variant
        - Répartition géographique pour chaque variant
        - Statistiques générales
        
        **Exemple de variant:** "1x Packman + 2x Pack 5 boosters" signifie qu'un utilisateur a acheté 1 Packman et 2 packs de boosters.
        """)