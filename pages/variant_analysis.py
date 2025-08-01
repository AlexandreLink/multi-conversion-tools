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
                section_variants.append((variant, countries))
                used_variants.add(variant)
        
        if section_variants:
            # Trier par popularité
            section_variants.sort(key=lambda x: sum(x[1].values()), reverse=True)
            sections[product] = section_variants
    
    # Ajouter les variants restants
    remaining = []
    for variant, countries in variant_stats.items():
        if variant not in used_variants:
            remaining.append((variant, countries))
    
    if remaining:
        remaining.sort(key=lambda x: sum(x[1].values()), reverse=True)
        sections["Autres combinaisons"] = remaining
    
    return sections

def create_final_dataframe(sections):
    """Crée le DataFrame final organisé"""
    
    # Obtenir tous les pays
    all_countries = set()
    for section_variants in sections.values():
        for _, countries in section_variants:
            all_countries.update(countries.keys())
    all_countries = sorted(all_countries)
    
    # Construire le DataFrame
    rows = []
    
    for section_name, variants in sections.items():
        # Titre de section
        title_row = {'Variant': f"=== {section_name.upper()} ===", 'Total utilisateurs': ''}
        for country in all_countries:
            title_row[country] = ''
        rows.append(title_row)
        
        # Variants de la section
        for variant, countries in variants:
            total = sum(countries.values())
            row = {
                'Variant': variant.replace('x ', '× '),
                'Total utilisateurs': total
            }
            for country in all_countries:
                row[country] = countries.get(country, 0)
            rows.append(row)
        
        # Ligne vide
        empty_row = {'Variant': '', 'Total utilisateurs': ''}
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
        unique_products, df_filtered = extract_products_from_orders(df, columns)
        user_data = create_variants_by_user(df_filtered, columns)
    
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
    
    # Étape 4: Configuration utilisateur
    st.write("## ⚙️ Configuration de l'organisation")
    
    selected_products = st.multiselect(
        "Choisissez les produits principaux (dans l'ordre d'affichage souhaité) :",
        options=unique_products,
        help="L'ordre de sélection = ordre des sections dans le rapport final"
    )
    
    if selected_products:
        st.write("### 📋 Aperçu de l'organisation")
        for i, product in enumerate(selected_products, 1):
            st.write(f"**{i}. {product}** → Tous les variants contenant ce produit")
        
        if len(selected_products) < len(unique_products):
            st.write(f"**{len(selected_products) + 1}. Autres combinaisons** → Variants restants")
        
        # Étape 5: Génération
        if st.button("🚀 Générer le rapport personnalisé", type="primary"):
            with st.spinner("🔄 Génération en cours..."):
                
                # Organiser selon la configuration
                sections = organize_by_user_order(user_data, selected_products)
                
                # Créer le DataFrame final
                final_df = create_final_dataframe(sections)
                
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
                        if isinstance(row['Variant'], str) and row['Variant'].startswith('==='):
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