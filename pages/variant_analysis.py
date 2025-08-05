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

def create_variants_by_user(df_filtered, columns):
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
        rows.append(empty_row)
    
    return pd.DataFrame(rows)

# Interface Streamlit
st.title("🔍 Analyseur de Variants - Configuration Personnalisée")
st.write("Analysez vos commandes et organisez les variants selon vos préférences.")

# Étape 1: Upload
uploaded_file = st.file_uploader("📁 Téléversez votre export Excel", type=['xlsx', 'xls'])

if uploaded_file:
    # Charger le fichier
    with st.spinner("📊 Chargement du fichier..."):
        df = pd.read_excel(uploaded_file)
        st.success(f"✅ Fichier chargé ! {len(df)} lignes trouvées.")
    
    # Étape 2: Détection des colonnes
    st.write("## 🔍 Détection des colonnes")
    columns = detect_columns(df)
    
    if len(columns) >= 3:  # Au minimum email, pays, produit
        st.success("✅ Colonnes détectées automatiquement")
        for field, col_name in columns.items():
            st.write(f"- **{field.title()}**: `{col_name}`")
    else:
        st.error("❌ Colonnes manquantes. Vérifiez votre fichier.")
        st.stop()
    
    # Étape 3: Extraction des produits
    st.write("## 🎯 Produits détectés")
    with st.spinner("🔄 Analyse des produits..."):
        try:
            unique_products, df_filtered = extract_products_from_orders(df, columns)
            st.write(f"Debug - Lignes après filtrage: {len(df_filtered)}")
            st.write(f"Debug - Colonnes utilisées: {columns}")
            
            user_data = create_variants_by_user(df_filtered, columns)
        except Exception as e:
            st.error(f"Erreur lors de l'analyse des produits: {str(e)}")
            st.write(f"Colonnes détectées: {columns}")
            st.write(f"Taille du DataFrame: {len(df)}")
            st.write(f"Premières lignes du DataFrame:")
            st.write(df.head())
            st.stop()
    
    st.success(f"✅ {len(unique_products)} produits trouvés | {len(user_data)} utilisateurs analysés")
    
    # Afficher les produits
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
    
    st.success(f"✅ {len(unique_products)} produits trouvés | {len(user_data)} utilisateurs analysés")
    
    # Afficher les produits
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