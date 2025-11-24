"""
Dashboard interactif pour analyser la popularité des producteurs musicaux
Lancement: streamlit run frontend_dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from producer_analytics import ProducerAnalytics
import json
from pathlib import Path

# Configuration de la page
st.set_page_config(
    page_title="🎵 Analyse des Producteurs Musicaux",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_analytics():
    """Charge l'analyseur de données avec cache"""
    return ProducerAnalytics()

@st.cache_data
def get_producer_analysis(_analyzer):
    """Génère l'analyse des producteurs avec cache"""
    return _analyzer.analyze_top_producers()

def main():
    st.title("🎵 Dashboard des Producteurs Musicaux")
    st.markdown("*Analyse de la popularité des producteurs dans les tops musicaux*")
    
    # Chargement des données
    try:
        analyzer = load_analytics()
        analysis = get_producer_analysis(analyzer)
    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {e}")
        return
    
    # Sidebar pour la navigation
    st.sidebar.title("📊 Navigation")
    view = st.sidebar.selectbox(
        "Choisir une vue",
        ["Vue d'ensemble", "Top 50 Année Courante", "Top 200 Année Courante", 
         "Année Précédente", "Depuis 2020", "Producteurs Constants", "Analyse Détaillée"]
    )
    
    if view == "Vue d'ensemble":
        show_overview(analysis, analyzer)
    elif view == "Top 50 Année Courante":
        show_ranking(analysis.get('top_50_current_year', []), "Top 50 - Année Courante", "🏆")
    elif view == "Top 200 Année Courante":
        show_ranking(analysis.get('top_200_current_year', []), "Top 200 - Année Courante", "📈")
    elif view == "Année Précédente":
        show_ranking(analysis.get('previous_year', []), "Année Précédente", "📅")
    elif view == "Depuis 2020":
        show_ranking(analysis.get('since_2020', []), "Depuis 2020", "🎯")
    elif view == "Producteurs Constants":
        show_consistent_producers(analysis.get('most_consistent', []))
    elif view == "Analyse Détaillée":
        show_detailed_analysis(analyzer)

def show_overview(analysis, analyzer):
    """Affiche la vue d'ensemble"""
    st.header("📊 Vue d'ensemble")
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_songs = sum(len(df) for df in analyzer.df_dict.values())
        st.metric("Total chansons", f"{total_songs:,}")
    
    with col2:
        years_covered = len(analyzer.df_dict)
        st.metric("Années couvertes", years_covered)
    
    with col3:
        if 'since_2020' in analysis:
            unique_producers = len(set([item[0] for item in analysis['since_2020']]))
            st.metric("Producteurs uniques", unique_producers)
    
    with col4:
        if 'most_consistent' in analysis:
            consistent_count = len([p for p in analysis['most_consistent'] if p[1] >= 4])
            st.metric("Producteurs 4+ années", consistent_count)
    
    # Graphiques de comparaison
    col1, col2 = st.columns(2)
    
    with col1:
        if 'top_50_current_year' in analysis and 'previous_year' in analysis:
            fig = create_comparison_chart(
                analysis['top_50_current_year'][:10],
                analysis['previous_year'][:10],
                "Top 10 Producteurs - Comparaison Années"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'since_2020' in analysis:
            fig = create_producer_pie_chart(analysis['since_2020'][:8])
            st.plotly_chart(fig, use_container_width=True)

def show_ranking(data, title, icon):
    """Affiche un classement de producteurs"""
    st.header(f"{icon} {title}")
    
    if not data:
        st.warning("Aucune donnée disponible pour cette période")
        return
    
    # Tableau interactif
    df_ranking = pd.DataFrame(data, columns=['Producteur', 'Nombre de chansons'])
    df_ranking.index = df_ranking.index + 1
    
    st.dataframe(
        df_ranking,
        use_container_width=True,
        height=400
    )
    
    # Graphique en barres
    if len(data) > 0:
        fig = px.bar(
            x=[item[1] for item in data],
            y=[item[0] for item in data],
            orientation='h',
            title=f"Distribution - {title}",
            labels={'x': 'Nombre de chansons', 'y': 'Producteur'}
        )
        fig.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

def show_consistent_producers(data):
    """Affiche les producteurs les plus constants"""
    st.header("🔥 Producteurs les Plus Constants")
    st.markdown("*Producteurs présents sur plusieurs années*")
    
    if not data:
        st.warning("Aucune donnée disponible")
        return
    
    df_consistent = pd.DataFrame(data, columns=['Producteur', 'Années de présence'])
    df_consistent.index = df_consistent.index + 1
    
    # Métriques
    col1, col2, col3 = st.columns(3)
    with col1:
        max_years = max([item[1] for item in data]) if data else 0
        st.metric("Maximum d'années", max_years)
    with col2:
        avg_years = np.mean([item[1] for item in data]) if data else 0
        st.metric("Moyenne d'années", f"{avg_years:.1f}")
    with col3:
        top_consistent = len([p for p in data if p[1] >= 5])
        st.metric("5+ années", top_consistent)
    
    # Tableau et graphique
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.dataframe(df_consistent, use_container_width=True, height=400)
    
    with col2:
        fig = px.bar(
            x=[item[1] for item in data[:15]],
            y=[item[0] for item in data[:15]],
            orientation='h',
            title="Constance des Producteurs",
            labels={'x': 'Années de présence', 'y': 'Producteur'},
            color=[item[1] for item in data[:15]],
            color_continuous_scale='viridis'
        )
        fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

def show_detailed_analysis(analyzer):
    """Analyse détaillée d'un producteur spécifique"""
    st.header("🔍 Analyse Détaillée")
    
    # Sélection du producteur
    all_producers = set()
    for df in analyzer.df_dict.values():
        all_producers.update(analyzer.get_all_producers(df))
    
    selected_producer = st.selectbox(
        "Choisir un producteur",
        sorted(list(all_producers))
    )
    
    if selected_producer:
        evolution = analyzer.get_producer_evolution(selected_producer)
        
        if evolution:
            # Métriques
            col1, col2, col3, col4 = st.columns(4)
            
            total_songs = sum(data['total_songs'] for data in evolution.values())
            best_pos = min(data['best_position'] for data in evolution.values())
            years_active = len(evolution)
            top_50_total = sum(data['top_50_count'] for data in evolution.values())
            
            with col1:
                st.metric("Total chansons", total_songs)
            with col2:
                st.metric("Meilleure position", best_pos)
            with col3:
                st.metric("Années actives", years_active)
            with col4:
                st.metric("Total Top 50", top_50_total)
            
            # Évolution temporelle
            years = list(evolution.keys())
            song_counts = [evolution[year]['total_songs'] for year in years]
            avg_positions = [evolution[year]['avg_position'] for year in years]
            
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Nombre de chansons par année', 'Position moyenne par année'),
                specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
            )
            
            fig.add_trace(
                go.Bar(x=years, y=song_counts, name="Nombre de chansons"),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(x=years, y=avg_positions, mode='lines+markers', name="Position moyenne"),
                row=2, col=1
            )
            
            fig.update_layout(height=500, title=f"Évolution de {selected_producer}")
            st.plotly_chart(fig, use_container_width=True)
            
            # Détails par année
            st.subheader("📋 Détails par année")
            for year in sorted(years, reverse=True):
                with st.expander(f"Année {year} - {evolution[year]['total_songs']} chansons"):
                    df_songs = pd.DataFrame(evolution[year]['songs'])
                    st.dataframe(df_songs, use_container_width=True)

def create_comparison_chart(current_data, previous_data, title):
    """Crée un graphique de comparaison entre deux années"""
    current_producers = [item[0] for item in current_data]
    current_counts = [item[1] for item in current_data]
    
    previous_dict = {item[0]: item[1] for item in previous_data}
    previous_counts = [previous_dict.get(prod, 0) for prod in current_producers]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Année courante',
        x=current_producers,
        y=current_counts,
        marker_color='#1f77b4'
    ))
    
    fig.add_trace(go.Bar(
        name='Année précédente',
        x=current_producers,
        y=previous_counts,
        marker_color='#ff7f0e'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Producteurs",
        yaxis_title="Nombre de chansons",
        barmode='group',
        height=400
    )
    
    return fig

def create_producer_pie_chart(data):
    """Crée un graphique en secteurs pour les producteurs"""
    producers = [item[0] for item in data]
    counts = [item[1] for item in data]
    
    fig = px.pie(
        values=counts,
        names=producers,
        title="Répartition des Producteurs les Plus Populaires"
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)
    
    return fig

# Interface principale
if __name__ == "__main__":
    main()