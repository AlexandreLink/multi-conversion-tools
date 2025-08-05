import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io
from collections import defaultdict

def detect_columns(df):
    """Détecte automatiquement les colonnes importantes"""
    columns = {}
    df_cols = [col.lower() for col in df.columns]
    
    # Email
    for col in ['customer: email', 'email', 'customer_email']:
        if col in df_cols:
            columns['email'] = df.columns[df_cols.index(col)]
            break
    
    # Pays
    for col in ['shipping: country', 'country', 'shipping_country']:
        if col in df_cols:
            columns['country'] = df.columns[df_cols.index(col)]
            break
    
    # Produit
    for col in ['line: name', 'product_name', 'item_name']:
        if col in df_cols:
            columns['product'] = df.columns[df_cols.index(col)]
            break
    
    # Quantité (optionnel)
    for col in ['line: quantity', 'quantity', 'qty']:
        if col in df_cols:
            columns['quantity'] = df.columns[df_cols.index(col)]
            break
    
    # Statut (optionnel)
    for col in ['payment: status', 'status', 'payment_status']:
        if col in df_cols:
            columns['status'] = df.columns[df_cols.index(col)]
            break
    
    # Type de ligne (optionnel)
    for col in ['line: type', 'type', 'line_type']:
        if col in df_cols:
            columns['line_type'] = df.columns[df_cols.index(col)]
            break
    
    return columns

def extract_products_from_orders(df, columns):
    """Extrait tous les produits uniques des commandes"""
    
    # Filtrer les données
    df_filtered = df.copy()
    
    # Filtrer par statut si disponible
    if 'status' in columns:
        status_col = columns['status']
        if 'paid' in df_filtered[status_col].str.lower().values:
            df_filtered = df_filtered[df_filtered[status_col].str.lower() == 'paid']
    
    # Filtrer par type de ligne si disponible
    if 'line_type' in columns:
        line_type_col = columns['line_type']
        if 'line item' in df_filtered[line_type_col].str.lower().values:
            df_filtered = df_filtered[df_filtered[line_type_col].str.lower() == 'line item']
    
    # Extraire les produits uniques
    product_col = columns['product']
    unique_products = sorted(df_filtered[product_col].dropna().unique().tolist())
    
    return unique_products, df_filtered

def translate_countries(countries):
    """Traduit les noms de pays en français"""
    translation = {
        'France': 'France',
        'Belgium': 'Belgique', 
        'Switzerland': 'Suisse',
        'Canada': 'Canada',
        'United States': 'États-Unis',
        'Germany': 'Allemagne',
        'Spain': 'Espagne',
        'Italy': 'Italie',
        'Netherlands': 'Pays-Bas',
        'United Kingdom': 'Royaume-Uni',
        'Luxembourg': 'Luxembourg',
        'Austria': 'Autriche',
        'Portugal': 'Portugal',
        'Denmark': 'Danemark',
        'Finland': 'Finlande',
        'Sweden': 'Suède',
        'Norway': 'Norvège',
        'Ireland': 'Irlande',
        'Poland': 'Pologne',
        'Czech Republic': 'République tchèque',
        'Hungary': 'Hongrie',
        'Greece': 'Grèce',
        'Reunion': 'La Réunion',
        'Guadeloupe': 'Guadeloupe',
        'Martinique': 'Martinique',
        'French Guiana': 'Guyane française',
        'New Caledonia': 'Nouvelle-Calédonie',
        'French Polynesia': 'Polynésie française',
        'Monaco': 'Monaco',
        'Mayotte': 'Mayotte',
        'Saint Pierre and Miquelon': 'Saint-Pierre-et-Miquelon'
    }
    return [translation.get(country, country) for country in countries]

def reorder_variant_with_main_product_first(variant, main_product):
    """Réorganise le variant pour mettre le produit principal en premier"""
    
    # Séparer les parties du variant
    parts = variant.split(' + ')
    main_part = None
    other_parts = []
    
    for part in parts:
        # Extraire le nom du produit (après "1x ", "2x ", etc.)
        if '× ' in part:
            product_name = part.split('× ', 1)[1]
        elif 'x ' in part:
            product_name = part.split('x ', 1)[1]
        else:
            product_name = part
        
        if product_name.strip() == main_product:
            main_part = part
        else:
            other_parts.append(part)
    
    # Reconstruire avec le produit principal en premier
    if main_part:
        reordered_parts = [main_part] + sorted(other_parts)
        return ' + '.join(reordered_parts)
    else:
        return variant  # Si pas trouvé, retourner l'original

def calculate_weight_and_foreign(variants, user_data, product_weights):
    """Calcule le poids estimé et le nombre d'utilisateurs à l'étranger"""
    
    results = {}
    
    for variant, countries in variants:
        # Calculer le poids estimé
        total_weight = 0.0
        parts = variant.split(' + ')
        
        for part in parts:
            # Extraire quantité et produit
            if '× ' in part:
                qty_str, product = part.split('× ', 1)
            elif 'x ' in part:
                qty_str, product = part.split('x ', 1)
            else:
                qty_str, product = '1', part
            
            try:
                qty = int(qty_str)
            except:
                qty = 1
            
            weight = product_weights.get(product.strip(), 0.0)  # Utiliser le poids configuré
            total_weight += qty * weight
        
        # Calculer les utilisateurs à l'étranger (non-France)
        total_users = sum(countries.values())
        france_users = countries.get('France', 0)
        foreign_users = total_users - france_users
        
        results[variant] = {
            'weight': f"{total_weight:.3f}kg",
            'total': total_users,
            'foreign': foreign_users
        }
    
    return results
    """Crée les variants en regroupant par utilisateur"""
    
    email_col = columns['email']
    country_col = columns['country']
    product_col = columns['product']
    quantity_col = columns.get('quantity')
    
    user_data = {}
    
    # Regrouper par email
    for email, user_orders in df_filtered.groupby(email_col):
        country = user_orders[country_col].iloc[0]
        
        # Calculer les produits et quantités pour cet utilisateur
        products = defaultdict(int)
        for _, row in user_orders.iterrows():
            product = row[product_col]
            qty = int(row[quantity_col]) if quantity_col and pd.notna(row[quantity_col]) else 1
            products[product] += qty
        
        # Créer le variant
        variant_parts = []
        for product, qty in sorted(products.items()):
            variant_parts.append(f"{qty}x {product}")
        variant = " + ".join(variant_parts)
        
        user_data[email] = {
            'variant': variant,
            'country': country,
            'products': dict(products)
        }
    
    return user_data

def organize_by_user_order(user_data, ordered_products):
    """Organise les variants selon l'ordre choisi par l'utilisateur"""
    
    # Analyser les variants par pays
    variant_stats = defaultdict(lambda: defaultdict(int))
    for data in user_data.values():
        variant_stats[data['variant']][data['country']] += 1
    
    # Organiser par sections selon l'ordre utilisateur
    sections = {}
    used_variants = set()
    
    # Traiter chaque produit dans l'ordre choisi
    for product in ordered_products:
        section_variants = []
        
        for variant, countries in variant_stats.items():
            if variant in used_variants:
                continue
            
            # Ce variant contient-il ce produit ?
            if product in variant:
                # Réorganiser le variant avec le produit principal en premier
                reordered_variant = reorder_variant_with_main_product_first(variant, product)
                section_variants.append((reordered_variant, countries))
                used_variants.add(variant)
        
        if section_variants:
            # Trier par ordre alphabétique au lieu de popularité
            section_variants.sort(key=lambda x: x[0])
            sections[product] = section_variants
    
    # Ajouter les variants restants
    remaining = []
    for variant, countries in variant_stats.items():
        if variant not in used_variants:
            remaining.append((variant, countries))
    
    if remaining:
        remaining.sort(key=lambda x: x[0])  # Alphabétique aussi
        sections["Autres combinaisons"] = remaining
    
    return sections

def create_final_dataframe(sections, user_data, product_weights):
    """Crée le DataFrame final organisé avec colonnes poids et étranger"""
    
    # Obtenir tous les pays et les traduire
    all_countries = set()
    for section_variants in sections.values():
        for _, countries in section_variants:
            all_countries.update(countries.keys())
    
    all_countries = sorted(translate_countries(list(all_countries)))
    
    # Construire le DataFrame
    rows = []
    
    for section_name, variants in sections.items():
        # Titre de section
        title_row = {
            'Variant': f"--- {section_name.upper()} ---", 
            'Poids des packs': '',
            'Nombre de packs': '',
            'Packs en livraison à l\'étranger': ''
        }
        for country in all_countries:
            title_row[country] = ''
        rows.append(title_row)
        
        # Calculer poids et étranger pour cette section
        variant_stats = calculate_weight_and_foreign(variants, user_data, product_weights)
        
        # Variants de la section
        for variant, countries in variants:
            stats = variant_stats[variant]
            
            # Traduire les noms de pays dans les données
            translated_countries = {}
            country_translation = {
                'France': 'France',
                'Belgium': 'Belgique', 
                'Switzerland': 'Suisse',
                'Canada': 'Canada',
                'United States': 'États-Unis',
                'Germany': 'Allemagne',
                'Spain': 'Espagne',
                'Italy': 'Italie',
                'Netherlands': 'Pays-Bas',
                'United Kingdom': 'Royaume-Uni',
                'Luxembourg': 'Luxembourg',
                'Austria': 'Autriche',
                'Portugal': 'Portugal',
                'Denmark': 'Danemark',
                'Finland': 'Finlande',
                'Sweden': 'Suède',
                'Norway': 'Norvège',
                'Ireland': 'Irlande',
                'Poland': 'Pologne',
                'Czech Republic': 'République tchèque',
                'Hungary': 'Hongrie',
                'Greece': 'Grèce',
                'Reunion': 'La Réunion',
                'Guadeloupe': 'Guadeloupe',
                'Martinique': 'Martinique',
                'French Guiana': 'Guyane française',
                'New Caledonia': 'Nouvelle-Calédonie',
                'French Polynesia': 'Polynésie française',
                'Monaco': 'Monaco',
                'Mayotte': 'Mayotte',
                'Saint Pierre and Miquelon': 'Saint-Pierre-et-Miquelon'
            }
            
            for original_country, count in countries.items():
                french_country = country_translation.get(original_country, original_country)
                translated_countries[french_country] = count
            
            row = {
                'Variant': variant.replace('x ', '× '),
                'Poids des packs': stats['weight'],
                'Nombre de packs': stats['total'],
                'Packs en livraison à l\'étranger': stats['foreign']
            }
            
            for country in all_countries:
                row[country] = translated_countries.get(country, 0)
            
            rows.append(row)
        
        # Ligne vide
        empty_row = {
            'Variant': '', 
            'Poids des packs': '',
            'Nombre de packs': '',
            'Packs en livraison à l\'étranger': ''
        }
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
                st.write("**Utilisez la configuration manuelle ci-dessus pour spécifier les colonnes.**")
            else:
                st.success("✅ Toutes les colonnes critiques ont été détectées !")
                
                # Configuration des filtres (seulement si les colonnes critiques sont OK)
                st.write("## ⚙️ Configuration des filtres")
                
                # Filtre par statut de paiement
                if 'payment_status' in detected_columns:
                    try:
                        status_col = detected_columns['payment_status']
                        unique_statuses = df[status_col].dropna().unique().tolist()
                        
                        selected_statuses = st.multiselect(
                            f"Statuts de paiement à inclure (colonne: {status_col})",
                            options=unique_statuses,
                            default=['paid'] if 'paid' in unique_statuses else unique_statuses[:1] if unique_statuses else []
                        )
                    except Exception as e:
                        st.warning(f"Problème avec la colonne statut: {e}")
                        selected_statuses = []
                else:
                    selected_statuses = []
                    st.info("ℹ️ Aucune colonne de statut de paiement détectée.")
                
                # Filtre par type de ligne
                if 'line_type' in detected_columns:
                    try:
                        line_type_col = detected_columns['line_type']
                        unique_line_types = df[line_type_col].dropna().unique().tolist()
                        
                        selected_line_types = st.multiselect(
                            f"Types de ligne à inclure (colonne: {line_type_col})",
                            options=unique_line_types,
                            default=['Line Item'] if 'Line Item' in unique_line_types else unique_line_types[:1] if unique_line_types else []
                        )
                    except Exception as e:
                        st.warning(f"Problème avec la colonne type de ligne: {e}")
                        selected_line_types = []
                else:
                    selected_line_types = []
                    st.info("ℹ️ Aucune colonne de type de ligne détectée.")
                
                # Bouton d'analyse préliminaire
                if st.button("🔎 Analyser les produits disponibles", type="secondary"):
                    with st.spinner("🔄 Analyse des produits..."):
                        try:
                            # Nettoyer et filtrer les données
                            df_clean = clean_and_filter_data(df, detected_columns, selected_statuses, selected_line_types)
                            
                            if len(df_clean) == 0:
                                st.error("❌ Aucune donnée ne correspond aux filtres sélectionnés.")
                                st.write("Essayez d'ajuster les filtres ou vérifiez le contenu du fichier.")
                            else:
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
                        
                        except Exception as e:
                            st.error(f"Erreur lors de l'analyse: {str(e)}")
                            st.write("Détails de l'erreur pour le débogage :")
                            st.write(f"Type d'erreur: {type(e).__name__}")
                            st.write(f"Message: {str(e)}")

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
        for i, product in enumerate(unique_products, 1):
            st.write(f"{i}. {product}")
    
    with col2:
        st.info("""
        **Instructions :**
        
        Sélectionnez les produits que vous voulez comme "sections principales" et définissez leur ordre d'affichage.
        """)
    
    # Étape 4: Configuration des poids
    if selected_products:
        st.write("## ⚖️ Configuration des poids des produits")
        
        st.write("Renseignez le poids de chaque produit pour calculer automatiquement le poids des variants :")
        
        product_weights = {}
        
        # Interface pour saisir les poids
        cols = st.columns(2)
        
        for i, product in enumerate(unique_products):
            col_index = i % 2
            with cols[col_index]:
                weight = st.number_input(
                    f"Poids de **{product}** (kg)",
                    min_value=0.0,
                    max_value=50.0,
                    value=1.0,
                    step=0.1,
                    format="%.3f",
                    key=f"weight_{i}"
                )
                product_weights[product] = weight
        
        # Étape 5: Configuration de l'organisation
        st.write("## ⚙️ Configuration de l'organisation")
        
        selected_products = st.multiselect(
            "Choisissez les produits principaux (dans l'ordre d'affichage souhaité) :",
            options=unique_products,
            help="L'ordre de sélection = ordre des sections dans le rapport final"
        )
        
        if selected_products:
            st.write("### 📋 Aperçu de l'organisation")
            for i, product in enumerate(selected_products, 1):
                weight = product_weights.get(product, 0.0)
                st.write(f"**{i}. {product}** ({weight:.3f}kg) → Tous les variants contenant ce produit")
            
            if len(selected_products) < len(unique_products):
                st.write(f"**{len(selected_products) + 1}. Autres combinaisons** → Variants restants")
            
            # Étape 6: Génération
            if st.button("🚀 Générer le rapport personnalisé", type="primary"):
                with st.spinner("🔄 Génération en cours..."):
                    
                    # Organiser selon la configuration
                    sections = organize_by_user_order(user_data, selected_products)
                    
                    # Créer le DataFrame final avec les poids configurés
                    final_df = create_final_dataframe(sections, user_data, product_weights)
                
                # Statistiques
                st.write("## 📈 Résultats")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Utilisateurs", len(user_data))
                with col2:
                    st.metric("Sections créées", len(sections))
                with col3:
                    st.metric("Variants uniques", len(set(data['variant'] for data in user_data.values())))
                
                # Aperçu
                st.write("### 👀 Aperçu du tableau")
                st.dataframe(final_df.head(20), use_container_width=True)
                
                # Export
                st.write("### 💾 Téléchargement")
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    final_df.to_excel(writer, sheet_name='Variants organisés', index=False)
                    
                    # Formatage des titres
                    workbook = writer.book
                    worksheet = writer.sheets['Variants organisés']
                    
                    title_format = workbook.add_format({
                        'bold': True,
                        'bg_color': '#D3D3D3',
                        'align': 'center',
                        'font_size': 12
                    })
                    
                    for row_num, (_, row) in enumerate(final_df.iterrows(), start=1):
                        if isinstance(row['Variant'], str) and row['Variant'].startswith('---'):
                            worksheet.set_row(row_num, None, title_format)
                
                buffer.seek(0)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"variants_personnalises_{timestamp}.xlsx"
                
                st.download_button(
                    label="📥 Télécharger le rapport Excel",
                    data=buffer,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                st.success("✅ Rapport généré avec votre configuration personnalisée !")
    
    else:
        st.warning("⚠️ Sélectionnez au moins un produit pour continuer.")

else:
    st.info("👆 Commencez par téléverser votre fichier Excel d'export.")
    
    with st.expander("ℹ️ Format de fichier attendu"):
        st.write("""
        **Colonnes requises :**
        - Email client (ex: "Customer: Email", "email")
        - Pays (ex: "Shipping: Country", "country") 
        - Nom du produit (ex: "Line: Name", "product_name")
        
        **Colonnes optionnelles :**
        - Quantité (ex: "Line: Quantity", "quantity")
        - Statut de paiement (ex: "Payment: Status", "status")
        - Type de ligne (ex: "Line: Type", "type")
        
        **Logique :**
        1. Regroupe les commandes par utilisateur (email)
        2. Crée des "variants" = combinaisons de produits achetés
        3. Organise selon votre ordre de priorité
        4. Évite les doublons automatiquement
        """)