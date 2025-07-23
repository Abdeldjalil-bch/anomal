import streamlit as st
import pandas as pd
import plotly.express as px
from plotly import colors as px_colors
import zipfile
import io
from datetime import datetime

# Vérification et installation des dépendances si nécessaire
try:
    import openpyxl
except ImportError:
    st.error("La bibliothèque 'openpyxl' n'est pas installée. Veuillez l'installer avec: pip install openpyxl")
    st.stop()

# Configuration de la page
st.set_page_config(
    page_title="Analyseur d'Anomalies de Données",
    page_icon="🔍",
    layout="wide"
)

# Title
st.title("🔍 Analyseur d'Anomalies de Données")
st.markdown("Uploadez votre fichier Excel ou CSV pour analyser les anomalies et détecter les doublons")

# File uploader
uploaded_file = st.file_uploader("Choisissez un fichier Excel (.xlsx) ou CSV (.csv)", type=["xlsx", "csv"])

def load_data(uploaded_file):
    """Charge les données depuis le fichier uploadé"""
    try:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        if file_extension == "xlsx":
            df = pd.read_excel(uploaded_file)
        elif file_extension == "csv":
            df = pd.read_csv(uploaded_file, encoding='utf-8')
        return df, None
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(uploaded_file, encoding='latin-1')
            return df, None
        except Exception as e:
            return None, f"Erreur d'encodage: {e}"
    except Exception as e:
        return None, f"Erreur lors du chargement: {e}"

def data_overview(df):
    """Affiche un aperçu général des données"""
    st.header("📊 Aperçu des Données")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Nombre de lignes", df.shape[0])
    with col2:
        st.metric("Nombre de colonnes", df.shape[1])
    with col3:
        st.metric("Valeurs manquantes", df.isna().sum().sum())
    with col4:
        st.metric("Lignes dupliquées", df.duplicated().sum())

    # Aperçu des données
    st.subheader("Aperçu des premières lignes")
    st.dataframe(df.head(10), use_container_width=True)

    # Informations sur les colonnes
    st.subheader("Informations sur les colonnes")
    col_info = pd.DataFrame({
        'Nom de la colonne': df.columns,
        'Type de données': df.dtypes.values,
        'Valeurs non-nulles': df.count().values,
        'Valeurs manquantes': df.isna().sum().values,
        'Valeurs uniques': [df[col].nunique() for col in df.columns],
        '% de valeurs manquantes': [round((df[col].isna().sum() / len(df)) * 100, 2) for col in df.columns]
    })
    st.dataframe(col_info, use_container_width=True)

def anomaly_analysis(df):
    """Analyse les anomalies dans les données"""
    st.header("🚨 Analyse des Anomalies")
    
    # Analyse des valeurs manquantes
    st.subheader("Valeurs manquantes par colonne")
    missing_data = df.isnull().sum()
    missing_data = missing_data[missing_data > 0].sort_values(ascending=False)
    
    if len(missing_data) > 0:
        col1, col2 = st.columns([2, 1])
        with col1:
            fig = px.bar(
                x=missing_data.values, 
                y=missing_data.index,
                orientation='h',
                title="Nombre de valeurs manquantes par colonne",
                labels={'x': 'Nombre de valeurs manquantes', 'y': 'Colonnes'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.write("**Détails des valeurs manquantes:**")
            for col, count in missing_data.items():
                percentage = (count / len(df)) * 100
                st.write(f"• **{col}**: {count} ({percentage:.1f}%)")
    else:
        st.success("✅ Aucune valeur manquante détectée!")

    # Analyse des doublons
    st.subheader("Analyse des doublons")
    total_duplicates = df.duplicated().sum()
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.metric("Nombre total de doublons", total_duplicates)
        if total_duplicates > 0:
            st.warning(f"⚠️ {total_duplicates} lignes dupliquées détectées")
        else:
            st.success("✅ Aucun doublon détecté!")
    
    with col2:
        if total_duplicates > 0:
            percentage = (total_duplicates / len(df)) * 100
            st.metric("Pourcentage de doublons", f"{percentage:.2f}%")

def duplicate_analysis(df):
    """Analyse détaillée des combinaisons de colonnes"""
    st.header("🔄 Analyse des Combinaisons de Colonnes")
    
    # Sélection des colonnes pour l'analyse
    st.subheader("Sélection des colonnes à analyser")
    selected_cols = st.multiselect(
        "Sélectionnez les colonnes pour analyser les combinaisons uniques/dupliquées:",
        options=df.columns.tolist(),
        default=[],  # Pas de sélection automatique
        help="Sélectionnez les colonnes dont vous voulez analyser les combinaisons"
    )
    
    if not selected_cols:
        st.warning("⚠️ Veuillez sélectionner au moins une colonne.")
        return None, None, False
    
    # Configuration des noms de fichiers
    st.subheader("Configuration des fichiers de sortie")
    col1, col2 = st.columns(2)
    
    with col1:
        unique_filename = st.text_input(
            "Nom du fichier des lignes uniques:",
            value="lignes_uniques",
            help="Nom du fichier Excel contenant les lignes avec combinaisons uniques"
        )
    
    with col2:
        duplicate_filename = st.text_input(
            "Nom du fichier des lignes dupliquées:",
            value="lignes_dupliquees",
            help="Nom du fichier Excel contenant les lignes avec combinaisons dupliquées"
        )
    
    # Bouton d'exécution
    if st.button("🚀 Exécuter l'analyse", type="primary", use_container_width=True):
        # Créer un sous-dataframe avec les colonnes sélectionnées pour l'analyse
        df_selected = df[selected_cols].copy()
        
        # Analyser les combinaisons
        st.subheader("Résultats de l'analyse")
        
        # Identifier les lignes avec combinaisons uniques et dupliquées
        # Garder toutes les colonnes originales mais identifier basé sur les colonnes sélectionnées
        is_duplicate = df[selected_cols].duplicated(keep=False)
        unique_rows = df[~is_duplicate].copy()  # Toutes les colonnes pour les lignes uniques
        duplicate_rows = df[is_duplicate].copy()  # Toutes les colonnes pour les lignes dupliquées
        
        # Statistiques
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total des lignes", len(df))
        with col2:
            st.metric("Lignes avec combinaisons uniques", len(unique_rows))
        with col3:
            st.metric("Lignes avec combinaisons dupliquées", len(duplicate_rows))
        
        # Affichage des résultats
        if len(unique_rows) > 0:
            st.subheader("✅ Lignes avec combinaisons uniques")
            st.write(f"**Analyse basée sur les colonnes:** {', '.join(selected_cols)}")
            st.dataframe(unique_rows.head(100), use_container_width=True)  # Limiter l'affichage
            if len(unique_rows) > 100:
                st.info(f"Affichage des 100 premières lignes sur {len(unique_rows)} au total")
        
        if len(duplicate_rows) > 0:
            st.subheader("🔄 Lignes avec combinaisons dupliquées")
            st.write(f"**Analyse basée sur les colonnes:** {', '.join(selected_cols)}")
            st.dataframe(duplicate_rows.head(100), use_container_width=True)  # Limiter l'affichage
            if len(duplicate_rows) > 100:
                st.info(f"Affichage des 100 premières lignes sur {len(duplicate_rows)} au total")
            
            # Analyse des groupes de doublons
            st.subheader("Analyse des groupes de doublons")
            duplicate_groups = df[is_duplicate][selected_cols].groupby(selected_cols).size().reset_index(name='count')
            duplicate_groups = duplicate_groups.sort_values('count', ascending=False)
            
            st.write("**Top 10 des combinaisons les plus dupliquées:**")
            st.dataframe(duplicate_groups.head(10), use_container_width=True)
            
            # Graphique des doublons
            if len(duplicate_groups) > 0:
                fig = px.histogram(
                    duplicate_groups, 
                    x='count',
                    title="Distribution du nombre de doublons par combinaison",
                    labels={'count': 'Nombre de doublons', 'count_of_count': 'Fréquence'}
                )
                st.plotly_chart(fig, use_container_width=True)
        
        return unique_rows, duplicate_rows, True, unique_filename, duplicate_filename
    
    return None, None, False, None, None

def create_download_zip(unique_df, duplicate_df, unique_filename="lignes_uniques", duplicate_filename="lignes_dupliquees"):
    """Crée un fichier ZIP contenant les deux fichiers Excel"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Fichier des lignes uniques
        if unique_df is not None and not unique_df.empty:
            unique_buffer = io.BytesIO()
            with pd.ExcelWriter(unique_buffer, engine='openpyxl') as writer:
                unique_df.to_excel(writer, index=False, sheet_name='Lignes_Uniques')
            unique_buffer.seek(0)
            zip_file.writestr(f"{unique_filename}.xlsx", unique_buffer.getvalue())
        
        # Fichier des lignes dupliquées
        if duplicate_df is not None and not duplicate_df.empty:
            duplicate_buffer = io.BytesIO()
            with pd.ExcelWriter(duplicate_buffer, engine='openpyxl') as writer:
                duplicate_df.to_excel(writer, index=False, sheet_name='Lignes_Dupliquees')
            duplicate_buffer.seek(0)
            zip_file.writestr(f"{duplicate_filename}.xlsx", duplicate_buffer.getvalue())
    
    zip_buffer.seek(0)
    return zip_buffer

def visualizations(df):
    """Fonction pour créer différents types de visualisations"""
    st.header("📈 Visualisations")

    if df.empty:
        st.warning("Le DataFrame est vide. Aucune visualisation disponible.")
        return

    # Palette de couleurs prédéfinies
    color_palettes = {
        'Défaut': ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F'],
        'Viridis': px.colors.sequential.Viridis,
        'Plasma': px.colors.sequential.Plasma,
        'Blues': px.colors.sequential.Blues,
        'Reds': px.colors.sequential.Reds,
        'Greens': px.colors.sequential.Greens,
        'Pastel': px.colors.qualitative.Pastel,
        'Set1': px.colors.qualitative.Set1,
        'Set2': px.colors.qualitative.Set2,
        'Set3': px.colors.qualitative.Set3,
        'Dark2': px.colors.qualitative.Dark2,
        'Océan': ['#006994', '#13A5B7', '#26C9DE', '#B8E6F0'],
        'Sunset': ['#FF6B35', '#F7931E', '#FFD23F', '#06FFA5'],
        'Forest': ['#2D5016', '#4F7942', '#74A478', '#A8DADC']
    }

    # Correspondance pour les colorscales (graphiques continus)
    colorscale_mapping = {
        'Défaut': 'viridis',
        'Viridis': 'viridis',
        'Plasma': 'plasma',
        'Blues': 'blues',
        'Reds': 'reds',
        'Greens': 'greens',
        'Pastel': 'viridis',
        'Set1': 'viridis', 
        'Set2': 'viridis',
        'Set3': 'viridis',
        'Dark2': 'viridis',
        'Océan': 'teal',
        'Sunset': 'sunset',
        'Forest': 'greens'
    }

    # Section 1: Graphiques individuels
    st.subheader("Graphiques individuels")

    # Conteneurs pour organiser les contrôles
    col1, col2 = st.columns([2, 1])

    with col1:
        selected_col = st.selectbox("Sélectionnez une colonne à visualiser:", options=df.columns)

    with col2:
        # Options de personnalisation dans un expander
        with st.expander("🎨 Personnalisation"):
            custom_title = st.text_input("Titre personnalisé (optionnel):", 
                                    placeholder=f"Graphique de {selected_col if selected_col else '...'}")
            color_palette = st.selectbox("Palette de couleurs:", options=list(color_palettes.keys()))
            custom_color = st.color_picker("Couleur personnalisée:", value="#FF6B6B")
            use_custom_color = st.checkbox("Utiliser couleur personnalisée")

    if selected_col and not df.empty:
        is_numeric = df[selected_col].dtype in ['int64', 'float64'] and df[selected_col].nunique() > 10
        unique_count = df[selected_col].nunique()
        
        # Déterminer les couleurs à utiliser
        if use_custom_color:
            colors = [custom_color]
        else:
            colors = color_palettes[color_palette]

        if is_numeric:  # Variable numérique continue
            graph_type = st.selectbox(
                "Type de graphique pour variable numérique:",
                options=["Histogramme", "Box Plot", "Violin Plot"],
                key="num_graph_type"
            )
            
            # Titre par défaut ou personnalisé
            default_title = f"Histogramme de {selected_col}" if graph_type == "Histogramme" else f"{graph_type} de {selected_col}"
            title = custom_title if custom_title else default_title

            if graph_type == "Histogramme":
                nbins = st.slider("Nombre de bins:", min_value=5, max_value=100, value=20)
                fig = px.histogram(df, x=selected_col, nbins=nbins,
                                title=title,
                                color_discrete_sequence=colors,
                                template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)

            elif graph_type == "Box Plot":
                fig = px.box(df, x=selected_col, title=title, 
                            points='all', color_discrete_sequence=colors,
                            template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)

            elif graph_type == "Violin Plot":
                fig = px.violin(df, y=selected_col, box=True, points='all',
                                title=title,
                                color_discrete_sequence=colors,
                                template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)

        else:  # Variable catégorielle
            graph_type = st.selectbox(
                "Type de graphique pour variable catégorielle:",
                options=["Bar Chart", "Pie Chart"],
                key="cat_graph_type"
            )
            
            # Titre par défaut ou personnalisé
            default_title = f"{graph_type} de {selected_col}"
            title = custom_title if custom_title else default_title

            value_counts = df[selected_col].value_counts()

            if graph_type == "Bar Chart":
                fig = px.bar(x=value_counts.index, y=value_counts.values,
                            title=title,
                            labels={'x': selected_col, 'y': 'Count'},
                            color_discrete_sequence=colors,
                            template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)

            elif graph_type == "Pie Chart":
                if len(value_counts) > 10:
                    st.warning(f"La colonne a {len(value_counts)} valeurs uniques. Affichage limité aux 10 plus fréquentes.")
                    value_counts = value_counts.nlargest(10)

                fig = px.pie(values=value_counts.values, names=value_counts.index,
                            title=title,
                            color_discrete_sequence=colors,
                            template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)

        # Statistiques descriptives
        with st.expander("📊 Statistiques descriptives"):
            if is_numeric:
                st.write(df[selected_col].describe())
            else:
                st.write(f"**Nombre de valeurs uniques:** {df[selected_col].nunique()}")
                st.write("**Distribution des valeurs:**")
                st.write(df[selected_col].value_counts())

# Fonction principale
def main():
    if uploaded_file is not None:
        # Charger les données
        df, error = load_data(uploaded_file)
        
        if error:
            st.error(f"Erreur lors du chargement du fichier: {error}")
            return
        
        if df is not None:
            st.success("✅ Fichier chargé avec succès!")
            
            # Créer des onglets pour organiser l'interface
            tab1, tab2, tab3, tab4 = st.tabs(["📊 Aperçu", "🚨 Anomalies", "🔄 Combinaisons", "📈 Visualisations"])
            
            with tab1:
                data_overview(df)
            
            with tab2:
                anomaly_analysis(df)
            
            with tab3:
                result = duplicate_analysis(df)
                
                # Vérifier si l'analyse a été exécutée et si des résultats sont disponibles
                if len(result) == 5:  # Nouvelle version avec noms de fichiers
                    unique_rows, duplicate_rows, analysis_executed, unique_filename, duplicate_filename = result
                    
                    # Bouton de téléchargement (affiché seulement si l'analyse a été exécutée)
                    if analysis_executed and (unique_rows is not None or duplicate_rows is not None):
                        st.subheader("📥 Téléchargement des résultats")
                        
                        # Informations sur les fichiers à télécharger
                        col1, col2 = st.columns(2)
                        with col1:
                            if unique_rows is not None and not unique_rows.empty:
                                st.write(f"✅ **{unique_filename}.xlsx:** {len(unique_rows)} lignes (toutes colonnes)")
                            else:
                                st.write("❌ **Aucune ligne avec combinaison unique**")
                        
                        with col2:
                            if duplicate_rows is not None and not duplicate_rows.empty:
                                st.write(f"🔄 **{duplicate_filename}.xlsx:** {len(duplicate_rows)} lignes (toutes colonnes)")
                            else:
                                st.write("❌ **Aucune ligne avec combinaison dupliquée**")
                        
                        # Préparer le fichier ZIP
                        zip_buffer = create_download_zip(unique_rows, duplicate_rows, unique_filename, duplicate_filename)
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        zip_filename = f"analyse_lignes_{timestamp}.zip"
                        
                        # Bouton de téléchargement direct
                        st.download_button(
                            label="📦 Télécharger les fichiers Excel (ZIP)",
                            data=zip_buffer.getvalue(),
                            file_name=zip_filename,
                            mime="application/zip",
                            type="primary",
                            use_container_width=True,
                            key="download_excel_zip"
                        )
                        
                        # Informations supplémentaires
                        st.info("""
                        **Contenu des fichiers:**
                        - Chaque fichier Excel contient TOUTES les colonnes du dataset original
                        - La classification unique/dupliquée est basée sur les colonnes sélectionnées
                        - Format: Excel (.xlsx) pour une meilleure compatibilité
                        """)
                else:
                    # Ancienne version pour compatibilité
                    unique_combinations, duplicate_combinations = result
                    
                    # Bouton de téléchargement
                    if unique_combinations is not None or duplicate_combinations is not None:
                        st.subheader("📥 Téléchargement des résultats")
                        
                        # Informations sur les fichiers à télécharger
                        col1, col2 = st.columns(2)
                        with col1:
                            if unique_combinations is not None and not unique_combinations.empty:
                                st.write(f"✅ **Fichier des combinaisons uniques:** {len(unique_combinations)} lignes")
                            else:
                                st.write("❌ **Aucune combinaison unique**")
                        
                        with col2:
                            if duplicate_combinations is not None and not duplicate_combinations.empty:
                                st.write(f"🔄 **Fichier des combinaisons dupliquées:** {len(duplicate_combinations)} lignes")
                            else:
                                st.write("❌ **Aucune combinaison dupliquée**")
                        
                        # Créer le fichier ZIP
                        if st.button("📦 Télécharger les fichiers (ZIP)", type="primary"):
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename_prefix = f"analyse_anomalies_{timestamp}"
                            
                            zip_buffer = create_download_zip(unique_combinations, duplicate_combinations, filename_prefix)
                            
                            st.download_button(
                                label="⬇️ Cliquez ici pour télécharger le ZIP",
                                data=zip_buffer.getvalue(),
                                file_name=f"{filename_prefix}.zip",
                                mime="application/zip"
                            )
                            
                            st.success("✅ Fichiers préparés pour le téléchargement!")
            
            with tab4:
                visualizations(df)
    
    else:
        st.info("📁 Veuillez uploader un fichier Excel (.xlsx) ou CSV (.csv) pour commencer l'analyse.")

# Exécuter l'application
if __name__ == "__main__":
    main()
