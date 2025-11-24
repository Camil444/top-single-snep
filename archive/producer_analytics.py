"""
Analyseur de données pour les producteurs musicaux
Génère des statistiques sur la popularité des producteurs
"""

import pandas as pd
import numpy as np
from collections import Counter, defaultdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ProducerAnalytics:
    """Analyseur de données pour les producteurs musicaux"""
    
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.df_dict = self.load_all_data()
        
    def load_all_data(self):
        """Charge toutes les données disponibles"""
        df_dict = {}
        
        for year in range(2020, 2026):
            file_path = self.data_dir / f"top_singles_{year}.csv"
            if file_path.exists():
                df_dict[str(year)] = pd.read_csv(file_path)
                
        return df_dict
    
    def get_all_producers(self, df):
        """Extrait tous les producteurs d'un DataFrame"""
        producers = []
        for _, row in df.iterrows():
            if pd.notna(row.get('producer_1')):
                producers.append(row['producer_1'])
            if pd.notna(row.get('producer_2')):
                producers.append(row['producer_2'])
        return producers
    
    def get_unique_songs_by_producer(self, df):
        """Compte les titres uniques par producteur (pas les semaines)"""
        producer_songs = defaultdict(set)
        
        for _, row in df.iterrows():
            song_key = f"{row['titre']}|{row['artiste']}"
            
            if pd.notna(row.get('producer_1')):
                producer_songs[row['producer_1']].add(song_key)
            if pd.notna(row.get('producer_2')):
                producer_songs[row['producer_2']].add(song_key)
        
        # Convertir en nombre de titres uniques
        return {producer: len(songs) for producer, songs in producer_songs.items()}
    
    def get_producer_song_sets(self, df):
        """Retourne les sets de chansons par producteur"""
        producer_songs = defaultdict(set)
        
        for _, row in df.iterrows():
            song_key = f"{row['titre']}|{row['artiste']}"
            
            if pd.notna(row.get('producer_1')):
                producer_songs[row['producer_1']].add(song_key)
            if pd.notna(row.get('producer_2')):
                producer_songs[row['producer_2']].add(song_key)
        
        return producer_songs
    
    def analyze_top_producers(self, limit=50):
        """Analyse les producteurs les plus populaires par période"""
        current_year = max([int(year) for year in self.df_dict.keys()])
        
        results = {}
        
        # Top 50 de l'année courante (titres uniques)
        if str(current_year) in self.df_dict:
            df_current = self.df_dict[str(current_year)]
            top_50_current = df_current[df_current['classement'] <= 50]
            producer_counts = self.get_unique_songs_by_producer(top_50_current)
            results['top_50_current_year'] = sorted(producer_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Top 200 de l'année courante (titres uniques)
        if str(current_year) in self.df_dict:
            top_200_current = df_current[df_current['classement'] <= 200]
            producer_counts = self.get_unique_songs_by_producer(top_200_current)
            results['top_200_current_year'] = sorted(producer_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        
        # Toute l'année courante (titres uniques)
        if str(current_year) in self.df_dict:
            producer_counts = self.get_unique_songs_by_producer(df_current)
            results['all_current_year'] = sorted(producer_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Année précédente (titres uniques)
        prev_year = current_year - 1
        if str(prev_year) in self.df_dict:
            df_prev = self.df_dict[str(prev_year)]
            producer_counts = self.get_unique_songs_by_producer(df_prev)
            results['previous_year'] = sorted(producer_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Depuis 2020 (titres uniques toutes années confondues)
        all_producer_songs = defaultdict(set)
        for year_str, df in self.df_dict.items():
            if int(year_str) >= 2020:
                for _, row in df.iterrows():
                    song_key = f"{row['titre']}|{row['artiste']}"
                    
                    if pd.notna(row.get('producer_1')):
                        all_producer_songs[row['producer_1']].add(song_key)
                    if pd.notna(row.get('producer_2')):
                        all_producer_songs[row['producer_2']].add(song_key)
        
        producer_unique_totals = {producer: len(songs) for producer, songs in all_producer_songs.items()}
        results['since_2020'] = sorted(producer_unique_totals.items(), key=lambda x: x[1], reverse=True)[:25]
        
        # Producteurs les plus constants (présents sur plusieurs années)
        producer_years = defaultdict(set)
        for year_str, df in self.df_dict.items():
            unique_producers = set()
            for _, row in df.iterrows():
                if pd.notna(row.get('producer_1')):
                    unique_producers.add(row['producer_1'])
                if pd.notna(row.get('producer_2')):
                    unique_producers.add(row['producer_2'])
            
            for producer in unique_producers:
                producer_years[producer].add(year_str)
        
        consistent_producers = [(prod, len(years)) for prod, years in producer_years.items() if len(years) >= 3]
        consistent_producers.sort(key=lambda x: x[1], reverse=True)
        results['most_consistent'] = consistent_producers[:15]
        
        return results
    
    def get_producer_evolution(self, producer_name):
        """Suit l'évolution d'un producteur au fil des années"""
        evolution = {}
        
        for year_str, df in self.df_dict.items():
            producer_songs = df[
                (df['producer_1'] == producer_name) | 
                (df['producer_2'] == producer_name)
            ]
            
            if len(producer_songs) > 0:
                evolution[year_str] = {
                    'total_songs': len(producer_songs),
                    'best_position': producer_songs['classement'].min(),
                    'avg_position': producer_songs['classement'].mean(),
                    'top_50_count': len(producer_songs[producer_songs['classement'] <= 50]),
                    'songs': producer_songs[['titre', 'artiste', 'classement']].to_dict('records')
                }
        
        return evolution
    
    def generate_summary_report(self):
        """Génère un rapport de synthèse"""
        analysis = self.analyze_top_producers()
        
        report = {
            'generation_date': pd.Timestamp.now().isoformat(),
            'data_coverage': {year: len(df) for year, df in self.df_dict.items()},
            'producer_rankings': analysis,
            'total_unique_producers': len(set([
                prod for df in self.df_dict.values() 
                for prod in self.get_all_producers(df)
            ]))
        }
        
        return report

if __name__ == "__main__":
    analyzer = ProducerAnalytics()
    report = analyzer.generate_summary_report()
    
    # Sauvegarder le rapport
    with open('producer_analysis_report.json', 'w', encoding='utf-8') as f:
        import json
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    
    print("📊 Rapport d'analyse généré: producer_analysis_report.json")