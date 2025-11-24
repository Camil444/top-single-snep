#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scraper pour récupérer les données du Top Singles de SNEP Musique
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import os
from urllib.parse import urljoin
import logging
from datetime import datetime
import re
import urllib3

# Désactiver les avertissements SSL non sécurisés
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Fonctions utilitaires de parsing (extraites pour modularité et tests) ---

def parse_artists_in_feat(artistes_text):
    """
    Parse les artistes dans un feat. (peut contenir &, virgules, etc.)
    """
    if not artistes_text:
        return []
    
    # Séparer par & et virgules
    artistes = re.split(r'\s*[&,]\s*', artistes_text)
    return [a.strip() for a in artistes if a.strip()]

def handle_x_separator(text):
    """
    Gère intelligemment le X comme séparateur d'artistes
    """
    # Pattern pour détecter un X entouré d'espaces entre des mots qui ressemblent à des noms
    # On cherche : [Mot(s)] X [Mot(s)] où les mots commencent par une majuscule
    x_pattern = r'\b([A-Z][A-Za-z\s]+?)\s+X\s+([A-Z][A-Za-z\s]+?)\b'
    
    def replace_x(match):
        artist1 = match.group(1).strip()
        artist2 = match.group(2).strip()
        
        # Vérifications supplémentaires pour s'assurer que c'est bien des noms d'artistes
        # On évite de remplacer si les mots sont trop courts ou contiennent des caractères suspects
        if (len(artist1) >= 2 and len(artist2) >= 2 and 
            not re.search(r'\d{3,}', artist1 + artist2) and  # Éviter les nombres longs
            not re.search(r'\b(THE|AND|OF|FOR|WITH|IN|ON|AT)\b', artist1 + " " + artist2, re.IGNORECASE)):
            return f"{artist1}|SEPARATOR|{artist2}"
        else:
            # Retourner le texte original si ça ne ressemble pas à des noms d'artistes
            return match.group(0)
    
    return re.sub(x_pattern, replace_x, text)

def parse_artists(artiste_string):
    """
    Sépare les artistes multiples selon les délimiteurs : virgule, FEAT., &, X (intelligent)
    
    Args:
        artiste_string: String contenant potentiellement plusieurs artistes
        
    Returns:
        Dict avec artiste, artiste_2, artiste_3, artiste_4
    """
    result = {
        'artiste': '',
        'artiste_2': '',
        'artiste_3': '',
        'artiste_4': ''
    }
    
    if not artiste_string or artiste_string.strip() == '':
        return result
    
    # Nettoyer la chaîne
    cleaned_string = artiste_string.strip()
    
    # Remplacer les différents séparateurs par un séparateur uniforme
    # On utilise |SEPARATOR| comme délimiteur temporaire unique
    separators = [
        (' FT. ', '|SEPARATOR|')
        (' FT ', '|SEPARATOR|'),
        (' ft ', '|SEPARATOR|'),
        ('FEAT.', '|SEPARATOR|'),
        ('FEAT', '|SEPARATOR|'),
        ('feat.', '|SEPARATOR|'),
        ('feat', '|SEPARATOR|'),
        ('Feat.', '|SEPARATOR|'),
        ('Feat', '|SEPARATOR|'),
        ('&', '|SEPARATOR|'),
        (',', '|SEPARATOR|')
    ]
    
    for old, new in separators:
        cleaned_string = cleaned_string.replace(old, new)
    
    # Gestion intelligente du X comme séparateur
    cleaned_string = handle_x_separator(cleaned_string)
    
    # Séparer selon le délimiteur uniforme
    artists = [artist.strip() for artist in cleaned_string.split('|SEPARATOR|') if artist.strip()]
    
    # Assigner aux colonnes
    keys = ['artiste', 'artiste_2', 'artiste_3', 'artiste_4']
    for i, artist in enumerate(artists[:4]):  # Maximum 4 artistes
        if i < len(keys):
            result[keys[i]] = artist
    
    return result

def clean_title_and_extract_feat(titre):
    """
    Nettoie le titre en supprimant les parenthèses et extrait les artistes en feat.
    
    Args:
        titre: Titre original
        
    Returns:
        Tuple (titre_propre, liste_artistes_feat)
    """
    if not titre:
        return titre, []
    
    titre_propre = titre.strip()
    artistes_feat = []
    
    # Chercher les contenus entre parenthèses
    parentheses_pattern = r'\(([^)]+)\)'
    matches = re.findall(parentheses_pattern, titre_propre)
    
    for match in matches:
        # Vérifier si c'est un feat.
        if re.search(r'\b(feat\.?|ft\.?|featuring)\b', match, re.IGNORECASE):
            # Extraire les artistes après feat.
            feat_pattern = r'\b(?:feat\.?|ft\.?|featuring)\s+(.+)'
            feat_match = re.search(feat_pattern, match, re.IGNORECASE)
            if feat_match:
                artistes_text = feat_match.group(1).strip()
                # Séparer les artistes dans le feat.
                artistes_dans_feat = parse_artists_in_feat(artistes_text)
                artistes_feat.extend(artistes_dans_feat)
    
    # Supprimer toutes les parenthèses du titre
    titre_propre = re.sub(r'\s*\([^)]*\)\s*', ' ', titre_propre)
    titre_propre = re.sub(r'\s+', ' ', titre_propre).strip()
    
    return titre_propre, artistes_feat

def merge_artists(artists_data, feat_artists):
    """
    Fusionne les artistes principaux avec les artistes feat. sans doublon
    """
    # Collecter tous les artistes existants
    existing_artists = []
    for key in ['artiste', 'artiste_2', 'artiste_3', 'artiste_4']:
        if artists_data[key]:
            existing_artists.append(artists_data[key].upper())
    
    # Ajouter les artistes feat. s'ils ne sont pas déjà présents
    keys = ['artiste', 'artiste_2', 'artiste_3', 'artiste_4']
    for feat_artist in feat_artists:
        if feat_artist.upper() not in existing_artists:
            # Trouver la prochaine colonne vide
            for key in keys:
                if not artists_data[key]:
                    artists_data[key] = feat_artist
                    existing_artists.append(feat_artist.upper())
                    break
    
    return artists_data

# --- Fin des fonctions utilitaires ---

class SNEPScraper:
    def __init__(self, delay_between_requests=1.5):
        """
        Initialise le scraper SNEP
        
        Args:
            delay_between_requests: Délai en secondes entre chaque requête
        """
        self.base_url = "https://snepmusique.com/les-tops/le-top-de-la-semaine/top-albums/"
        self.delay = delay_between_requests
        self.session = requests.Session()
        # Désactiver la vérification SSL pour éviter les erreurs de certificats locaux
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Créer le dossier data s'il n'existe pas
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            logger.info(f"Dossier '{self.data_dir}' créé")
    
    def clean_title_and_extract_feat(self, titre):
        return clean_title_and_extract_feat(titre)
    
    def parse_artists_in_feat(self, artistes_text):
        return parse_artists_in_feat(artistes_text)
    
    def parse_artists(self, artiste_string):
        return parse_artists(artiste_string)
    
    def handle_x_separator(self, text):
        return handle_x_separator(text)
    
    def merge_artists(self, artists_data, feat_artists):
        return merge_artists(artists_data, feat_artists)
    
    def get_page_content(self, semaine, annee):
        """
        Récupère le contenu HTML d'une page pour une semaine donnée
        
        Args:
            semaine: Numéro de la semaine
            annee: Année
            
        Returns:
            BeautifulSoup object ou None si erreur
        """
        params = {
            'categorie': 'Top Singles',
            'semaine': str(semaine),
            'annee': str(annee)
        }
        
        try:
            logger.info(f"Récupération des données : Année {annee}, Semaine {semaine}")
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la récupération de la page (Année {annee}, Semaine {semaine}): {e}")
            return None
    
    def extract_data_from_page(self, soup, semaine, annee):
        """
        Extrait les données de la page
        
        Args:
            soup: BeautifulSoup object
            semaine: Numéro de la semaine
            annee: Année
            
        Returns:
            Liste de dictionnaires contenant les données
        """
        data = []
        
        if not soup:
            return data
        
        try:
            # Chercher le conteneur principal avec les articles
            # Les données peuvent être dans des articles ou des divs avec la classe 'item'
            items = soup.find_all('article', class_='classement-item')
            
            if not items:
                # Alternative : chercher des divs avec classe item
                items = soup.find_all('div', class_='item')
            
            if not items:
                # Autre alternative : chercher dans la structure div.items
                items_container = soup.find('div', class_='items')
                if items_container:
                    items = items_container.find_all(['article', 'div'], recursive=False)
            
            if not items:
                # Dernière tentative : chercher toutes les structures qui ressemblent à des items de classement
                main_content = soup.find(['main', 'div'], id=['primary', 'content', 'main-content'])
                if main_content:
                    # Chercher les blocs de données
                    items = []
                    
                    # Pattern pour identifier les blocs de classement
                    classement_blocks = main_content.find_all(['div', 'article'], 
                                                             class_=re.compile(r'(item|single|track|classement)', re.I))
                    
                    for block in classement_blocks:
                        # Vérifier si c'est bien un item du classement
                        if block.find(text=re.compile(r'^\d+$|^\d+e?La Semaine', re.I)):
                            items.append(block)
            
            logger.info(f"Nombre d'items trouvés : {len(items)}")
            
            for item in items:
                try:
                    item_data = {}
                    
                    # Extraire le classement (nombre au début ou dans une balise spécifique)
                    classement = None
                    
                    # PRIORITÉ 1: Chercher spécifiquement la classe "rang" (SNEP standard)
                    # On exclut explicitement "rang_precedent"
                    classement_elem = item.find('div', class_='rang')
                    if classement_elem:
                        classement_text = classement_elem.get_text(strip=True)
                        match = re.search(r'(\d+)', classement_text)
                        if match:
                            classement = match.group(1)

                    # PRIORITÉ 2: Si pas trouvé, chercher avec des regex mais en excluant "precedent"
                    if not classement:
                        # On cherche les classes qui matchent rank/position/etc...
                        candidates = item.find_all(['span', 'div', 'strong'], class_=re.compile(r'(rank|position|classement|number)', re.I))
                        
                        for candidate in candidates:
                            # Vérifier que la classe ne contient pas "precedent" ou "previous"
                            classes = candidate.get('class', [])
                            class_str = " ".join(classes).lower()
                            
                            if 'precedent' in class_str or 'previous' in class_str or 'last' in class_str:
                                continue
                                
                            classement_text = candidate.get_text(strip=True)
                            match = re.search(r'(\d+)', classement_text)
                            if match:
                                classement = match.group(1)
                                break
                    
                    if not classement:
                        # Chercher dans le texte de l'item (fallback)
                        text = item.get_text(strip=True)
                        match = re.match(r'^(\d+)', text)
                        if match:
                            classement = match.group(1)
                    
                    
                    # Extraire le titre, l'artiste et l'éditeur
                    # Ces informations peuvent être dans différentes balises
                    
                    # Méthode 1: Chercher des balises spécifiques
                    titre_elem = item.find(['h2', 'h3', 'h4', 'h5', 'span', 'div'], 
                                          class_=re.compile(r'(title|titre|song|track)', re.I))
                    artiste_elem = item.find(['span', 'div', 'p'], 
                                            class_=re.compile(r'(artist|artiste|performer)', re.I))
                    editeur_elem = item.find(['span', 'div', 'p'], 
                                            class_=re.compile(r'(label|editeur|publisher|producer)', re.I))
                    
                    titre = titre_elem.get_text(strip=True) if titre_elem else None
                    artiste = artiste_elem.get_text(strip=True) if artiste_elem else None
                    editeur = editeur_elem.get_text(strip=True) if editeur_elem else None
                    
                    # Méthode 2: Si pas trouvé, essayer d'analyser le texte complet
                    if not all([titre, artiste, editeur]):
                        # Obtenir tout le texte et le diviser intelligemment
                        lines = []
                        for elem in item.find_all(text=True):
                            text = elem.strip()
                            if text and not re.match(r'^(\d+e?La Semaine|Nouveau)', text, re.I):
                                lines.append(text)
                        
                        # Filtrer les lignes pour enlever le classement et les infos de semaine
                        filtered_lines = []
                        for line in lines:
                            if not re.match(r'^\d+$', line) and len(line) > 2:
                                filtered_lines.append(line)
                        
                        # Généralement : Titre, Artiste, Éditeur
                        if len(filtered_lines) >= 3:
                            titre = titre or filtered_lines[0]
                            artiste = artiste or filtered_lines[1]
                            editeur = editeur or filtered_lines[2]
                        elif len(filtered_lines) == 2:
                            titre = titre or filtered_lines[0]
                            artiste = artiste or filtered_lines[1]
                        elif len(filtered_lines) == 1:
                            titre = titre or filtered_lines[0]
                    
                    # Si on a au moins le classement et le titre, ajouter l'entrée
                    if classement and titre:
                        # Nettoyer le titre et extraire les feat.
                        titre_propre, feat_artists = self.clean_title_and_extract_feat(titre)
                        
                        # Parser les artistes multiples
                        artists_data = self.parse_artists(artiste or '')
                        
                        # Fusionner avec les artistes feat.
                        artists_data = self.merge_artists(artists_data, feat_artists)
                        
                        entry = {
                            'classement': classement,
                            'artiste': artists_data['artiste'],
                            'artiste_2': artists_data['artiste_2'],
                            'artiste_3': artists_data['artiste_3'],
                            'artiste_4': artists_data['artiste_4'],
                            'titre': titre_propre,
                            'editeur': editeur or '',
                            'annee': annee,
                            'semaine': semaine
                        }
                        data.append(entry)
                        logger.debug(f"Entrée ajoutée : {entry}")
                    
                except Exception as e:
                    logger.error(f"Erreur lors de l'extraction d'un item : {e}")
                    continue
            
            # Si aucun item n'a été trouvé avec la méthode structurée,
            # essayer une extraction basée sur le texte
            if len(data) == 0:
                logger.info("Tentative d'extraction alternative basée sur le texte...")
                data = self.extract_data_from_text(soup, semaine, annee)
            
            logger.info(f"Nombre d'entrées extraites : {len(data)}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des données : {e}")
        
        return data
    
    def extract_data_from_text(self, soup, semaine, annee):
        """
        Méthode alternative pour extraire les données basée sur l'analyse du texte
        """
        data = []
        
        try:
            # Obtenir tout le texte de la page
            text_content = soup.get_text()
            
            # Diviser en lignes et nettoyer
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
            
            # Pattern pour identifier un numéro de classement
            classement_pattern = re.compile(r'^(\d{1,3})$')
            
            i = 0
            while i < len(lines):
                # Chercher un numéro de classement
                if classement_pattern.match(lines[i]):
                    classement = lines[i]
                    
                    # Les lignes suivantes devraient être titre, artiste, éditeur
                    titre = None
                    artiste = None
                    editeur = None
                    
                    j = i + 1
                    collected_lines = []
                    
                    # Collecter les prochaines lignes jusqu'au prochain classement ou indicateur
                    while j < len(lines) and not classement_pattern.match(lines[j]):
                        line = lines[j]
                        # Ignorer les lignes de navigation et métadonnées
                        if not any(skip in line.lower() for skip in ['semaine', 'nouveau', 'télécharger', 'pdf', 'précédente', 'suivante']):
                            # Ignorer aussi les positions de la semaine dernière
                            if not re.match(r'^\d+e?La Semaine', line, re.I):
                                collected_lines.append(line)
                        j += 1
                    
                    # Assigner les lignes collectées
                    if len(collected_lines) >= 1:
                        titre = collected_lines[0]
                    if len(collected_lines) >= 2:
                        artiste = collected_lines[1]
                    if len(collected_lines) >= 3:
                        editeur = collected_lines[2]
                    
                    # Ajouter l'entrée si on a au moins un titre
                    if titre:
                        # Nettoyer le titre et extraire les feat.
                        titre_propre, feat_artists = self.clean_title_and_extract_feat(titre)
                        
                        # Parser les artistes multiples
                        artists_data = self.parse_artists(artiste or '')
                        
                        # Fusionner avec les artistes feat.
                        artists_data = self.merge_artists(artists_data, feat_artists)
                        
                        entry = {
                            'classement': classement,
                            'artiste': artists_data['artiste'],
                            'artiste_2': artists_data['artiste_2'],
                            'artiste_3': artists_data['artiste_3'],
                            'artiste_4': artists_data['artiste_4'],
                            'titre': titre_propre,
                            'editeur': editeur or '',
                            'annee': annee,
                            'semaine': semaine
                        }
                        data.append(entry)
                    
                    i = j
                else:
                    i += 1
        
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction alternative : {e}")
        
        return data
    
    def save_to_csv(self, data, annee):
        """
        Sauvegarde les données dans un fichier CSV
        
        Args:
            data: Liste de dictionnaires contenant les données
            annee: Année pour le nom du fichier
        """
        if not data:
            logger.warning(f"Aucune donnée à sauvegarder pour l'année {annee}")
            return
        
        filename = os.path.join(self.data_dir, f"top_singles_{annee}.csv")
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['classement', 'artiste', 'artiste_2', 'artiste_3', 'artiste_4', 'titre', 'editeur', 'annee', 'semaine']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for row in data:
                    writer.writerow(row)
            
            logger.info(f"Données sauvegardées dans {filename} ({len(data)} entrées)")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du CSV : {e}")
    
    def scrape_week(self, annee, semaine):
        """
        Scrape une semaine spécifique et retourne les données (sans sauvegarder en CSV)
        
        Args:
            annee: Année à scraper
            semaine: Semaine à scraper
            
        Returns:
            Liste de dictionnaires contenant les données
        """
        logger.info(f"Récupération des données : Année {annee}, Semaine {semaine}")
        
        soup = self.get_page_content(semaine, annee)
        if not soup:
            logger.warning(f"✗ Année {annee}, Semaine {semaine} : Aucune donnée trouvée (Erreur requête)")
            return []
            
        data = self.extract_data_from_page(soup, semaine, annee)
        
        if data:
            logger.info(f"✓ Année {annee}, Semaine {semaine} : {len(data)} entrées récupérées")
            return data
        else:
            logger.warning(f"✗ Année {annee}, Semaine {semaine} : Aucune donnée trouvée")
            return []

    def scrape_year(self, annee, semaine_debut, semaine_fin):
        """
        Scrape toutes les semaines d'une année
        
        Args:
            annee: Année à scraper
            semaine_debut: Première semaine à scraper
            semaine_fin: Dernière semaine à scraper
        """
        logger.info(f"Début du scraping pour l'année {annee} (semaines {semaine_debut} à {semaine_fin})")
        all_data = []
        semaines_manquantes = []
        
        for semaine in range(semaine_debut, semaine_fin + 1):
            data = self.scrape_week(annee, semaine)
            
            if data:
                all_data.extend(data)
            else:
                semaines_manquantes.append(semaine)
            
            # Pause entre les requêtes
            time.sleep(self.delay)
        
        # Sauvegarder toutes les données de l'année
        if all_data:
            self.save_to_csv(all_data, annee)
        
        # Log des semaines manquantes
        if semaines_manquantes:
            logger.warning(f"Semaines manquantes pour {annee}: {semaines_manquantes}")
        
        return all_data
    
    def clean_existing_csv_files(self):
        """
        Supprime les fichiers CSV existants pour les régénérer
        """
        years = [2020, 2021, 2022, 2023, 2024, 2025]
        deleted_files = []
        
        for year in years:
            filename = os.path.join(self.data_dir, f"top_singles_{year}.csv")
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                    deleted_files.append(filename)
                    logger.info(f"Fichier supprimé : {filename}")
                except Exception as e:
                    logger.error(f"Erreur lors de la suppression de {filename} : {e}")
        
        if deleted_files:
            logger.info(f"Suppression terminée : {len(deleted_files)} fichiers supprimés")
        else:
            logger.info("Aucun fichier CSV existant à supprimer")
    
    def run(self):
        """
        Lance le scraping complet
        """
        logger.info("=" * 50)
        logger.info("Démarrage du scraper SNEP")
        logger.info("=" * 50)
        
        # NOTE: Suppression automatique désactivée pour éviter la perte de données
        # self.clean_existing_csv_files()
        
        # Calcul dynamique de la semaine actuelle
        now = datetime.now()
        current_year = now.year
        current_week = now.isocalendar()[1]
        
        # Scraper l'année en cours (2025)
        if current_year == 2025:
            # On va jusqu'à la semaine précédente pour être sûr que les données sont publiées
            # Ou jusqu'à la semaine actuelle si on veut tenter
            limit_week = current_week - 1 if current_week > 1 else 1
            
            # Pour le test demandé, on force jusqu'à 45 si on est au-delà, ou on utilise la logique dynamique
            # Ici je respecte la demande explicite de l'utilisateur d'aller jusqu'à 45 pour le test
            limit_week = 45 
            
            logger.info(f"Scraping de l'année en cours {current_year} jusqu'à la semaine {limit_week}")
            data_2025 = self.scrape_year(2025, 1, limit_week)
            logger.info(f"Total 2025 : {len(data_2025)} entrées")
        
        # Scraper les années précédentes seulement si nécessaire
        for year in range(2024, 2019, -1):
            # On force le scraping même si le fichier existe car on veut corriger les classements
            logger.info(f"Lancement du scraping pour {year}...")
            data_year = self.scrape_year(year, 1, 52)
            logger.info(f"Total {year} : {len(data_year)} entrées")
        
        logger.info("=" * 50)
        logger.info("Scraping terminé !")
        logger.info("=" * 50)


def main():
    """
    Fonction principale
    """
    print("""
    ╔══════════════════════════════════════════╗
    ║     SNEP Top Singles Scraper            ║
    ║     Récupération des données en cours... ║
    ╚══════════════════════════════════════════╝
    """)
    
    # Créer et lancer le scraper
    scraper = SNEPScraper(delay_between_requests=1.5)
    
    try:
        scraper.run()
        print("\n✅ Scraping terminé avec succès !")
        print("📁 Les fichiers CSV ont été sauvegardés dans le dossier 'data'")
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur lors du scraping : {e}")
        logger.error(f"Erreur fatale : {e}", exc_info=True)


if __name__ == "__main__":
    main()