import requests
from bs4 import BeautifulSoup
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS
import json
import re
from pathlib import Path
import time

AUTO = Namespace("http://www.univ-projet.fr/ontologies/autosemantic#")

class OllamaKGBuilder:
    def __init__(self, ontology_path="../autosemantic.ttl", model="phi3"):
        
        self.graph = Graph()
        if Path(ontology_path).exists():
            self.graph.parse(ontology_path, format="turtle")
        self.graph.bind("auto", AUTO)
        
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = model
        
        # Vérifier qu'Ollama est accessible
        self._check_ollama()
    
    def _check_ollama(self):
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                print(f"Ollama connecté - {len(models)} modèles disponibles")
                if not any(m['name'].startswith(self.model) for m in models):
                    print(f"Modèle {self.model} non trouvé. Téléchargez-le avec:")
                    print(f"  ollama pull {self.model}")
            else:
                print("Ollama ne répond pas correctement")
        except requests.exceptions.ConnectionError:
            print("Ollama ne fonctionne pas correctement")
            raise
    
    def get_manufacturers(self) -> list:
        """Collecter toutes les marques depuis UltimateSpecs"""
        print("\nCollecte des marques...")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            response = requests.get("https://www.ultimatespecs.com/car-specs", headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            manufacturers = []
            # Trouver tous les liens vers les marques
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/car-specs/' in href and '-models' in href:
                    manufacturer_name = link.get_text().strip()
                    manufacturer_url = f"https://www.ultimatespecs.com{href}" if href.startswith('/') else href
                    manufacturers.append({
                        'name': manufacturer_name,
                        'url': manufacturer_url
                    })
            
            # Déduplication
            seen = set()
            unique_manufacturers = []
            for m in manufacturers:
                if m['url'] not in seen:
                    seen.add(m['url'])
                    unique_manufacturers.append(m)
            
            print(f"  {len(unique_manufacturers)} marques trouvées")
            return unique_manufacturers
            
        except Exception as e:
            print(f"  Erreur collecte marques: {e}")
            return []
    
    def get_models_from_manufacturer(self, manufacturer_url: str) -> list:
        """Collecter tous les modèles d'une marque"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            response = requests.get(manufacturer_url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            models = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Format: /car-specs/Marque/Modele
                if href.count('/') >= 3 and '/car-specs/' in href and '.html' not in href:
                    model_url = f"https://www.ultimatespecs.com{href}" if href.startswith('/') else href
                    models.append(model_url)
            
            # Déduplication
            return list(set(models))
            
        except Exception as e:
            print(f"  Erreur collecte modèles: {e}")
            return []
    
    def get_specs_from_model(self, model_url: str) -> list:
        """Collecter toutes les versions/specs d'un modèle"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            response = requests.get(model_url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            spec_urls = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Format: /car-specs/Marque/123456/Marque-Modele-Details.html
                if '.html' in href and '/car-specs/' in href:
                    spec_url = f"https://www.ultimatespecs.com{href}" if href.startswith('/') else href
                    spec_urls.append(spec_url)
            
            return list(set(spec_urls))
            
        except Exception as e:
            return []
    
    def collect_all_urls(self, max_manufacturers=None, max_models_per_manufacturer=None):
        """Collecter toutes les URLs de spécifications depuis UltimateSpecs"""
        print("\n" + "="*60)
        print("COLLECTE AUTOMATIQUE DES URLS")
        print("="*60)
        
        all_spec_urls = []
        
        # Étape 1: Collecter les marques
        manufacturers = self.get_manufacturers()
        if max_manufacturers:
            manufacturers = manufacturers[:max_manufacturers]
            print(f"  (Limitation à {max_manufacturers} marques pour test)")
        
        # Étape 2: Pour chaque marque, collecter les modèles
        for i, manufacturer in enumerate(manufacturers):
            print(f"\n[{i+1}/{len(manufacturers)}] {manufacturer['name']}")
            
            models = self.get_models_from_manufacturer(manufacturer['url'])
            if max_models_per_manufacturer:
                models = models[:max_models_per_manufacturer]
            
            print(f"  -> {len(models)} modèles trouvés")
            
            # Étape 3: Pour chaque modèle, collecter les specs
            for j, model_url in enumerate(models):
                spec_urls = self.get_specs_from_model(model_url)
                all_spec_urls.extend(spec_urls)
                
                if (j + 1) % 5 == 0:
                    print(f"    {j+1}/{len(models)} modèles traités...")
                
                time.sleep(0.5)  # Pause pour ne pas surcharger le serveur
            
            time.sleep(1)  # Pause entre marques
        
        # Déduplication finale
        all_spec_urls = list(set(all_spec_urls))
        
        print(f"\nTOTAL: {len(all_spec_urls)} URLs de spécifications collectées")
        return all_spec_urls
    
    def query_ollama(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.1,
            "format": "json"         
        }
        
        try:
            response = requests.post(self.ollama_url, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()
            return result.get('response', '')
        except requests.exceptions.Timeout:
            print("Timeout - Le modèle met trop de temps à répondre")
            return "{}"
        except Exception as e:
            print(f"Erreur Ollama: {e}")
            return "{}"
    
    def scrape_article(self, url: str) -> dict:
        """Scraper un article web (optimisé pour ultimatespecs.com)"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extraire titre
            title = ''
            if soup.find('title'):
                title = soup.find('title').text
            elif soup.find('h1'):
                title = soup.find('h1').get_text().strip()
            
            # Pour ultimatespecs.com: extraire specs techniques
            text_parts = []
            
            # Paragraphes
            paragraphs = soup.find_all('p')
            text_parts.extend([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
            
            # Tables de spécifications (communes sur ultimatespecs)
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        row_text = ' '.join([cell.get_text().strip() for cell in cells])
                        text_parts.append(row_text)
            
            # Listes
            lists = soup.find_all(['ul', 'ol'])
            for lst in lists:
                items = lst.find_all('li')
                text_parts.extend([item.get_text().strip() for item in items if item.get_text().strip()])
            
            # Headers (h2, h3) pour les sections
            section_headers = soup.find_all(['h2', 'h3', 'h4'])
            text_parts.extend([h.get_text().strip() for h in section_headers if h.get_text().strip()])
            
            text = ' '.join(text_parts)
            
            # Limiter la taille pour éviter overflow
            text = text[:10000]  # Augmenté pour specs détaillées
            
            print(f"  Scraping: {len(text)} caractères extraits")
            
            return {
                'url': url,
                'title': title,
                'text': text
            }
        except requests.exceptions.HTTPError as e:
            print(f"Erreur HTTP {e.response.status_code}: {e}")
            return None
        except Exception as e:
            print(f"Erreur scraping: {e}")
            return None
    
    def extract_with_ollama(self, text: str) -> dict:
        """Extraire entités et relations avec Ollama"""
        
        prompt = f"""You are an expert in automotive technical specifications extraction. Extract structured data from car specifications.

TEXT:
{text}

TASK:
Extract automotive entities and their relationships. Focus on:

1. MANUFACTURER: Car brand (e.g., Acura, BMW, Tesla)
2. CAR MODEL: Specific model name (e.g., ILX, 3 Series, Model S)
3. FUEL TYPE: gasoline/petrol, diesel, electric, hybrid, plug-in hybrid
4. TRANSMISSION: automatic, manual, CVT, dual-clutch, sequential
5. DRIVE TYPE: FWD (front-wheel drive), RWD (rear-wheel drive), AWD (all-wheel drive), 4WD
6. ENGINE: Engine code or type
7. TECHNICAL DATA: cylinders, displacement, horsepower, torque

Relationships to identify:
- manufactures: Manufacturer → Car Model
- hasFuelType: Car Model → Fuel Type
- hasTransmission: Car Model → Transmission Type
- hasDriveType: Car Model → Drive Type
- hasEngine: Car Model → Engine

Return ONLY valid JSON with this structure:
{{
  "entities": [
    {{"text": "Acura", "type": "Manufacturer"}},
    {{"text": "ILX 2.4", "type": "CarModel"}},
    {{"text": "Gasoline", "type": "FuelType"}},
    {{"text": "Automatic", "type": "TransmissionType"}},
    {{"text": "FWD", "type": "DriveType"}}
  ],
  "relations": [
    {{"subject": "Acura", "predicate": "manufactures", "object": "ILX 2.4"}},
    {{"subject": "ILX 2.4", "predicate": "hasFuelType", "object": "Gasoline"}},
    {{"subject": "ILX 2.4", "predicate": "hasTransmission", "object": "Automatic"}},
    {{"subject": "ILX 2.4", "predicate": "hasDriveType", "object": "FWD"}}
  ]
}}

Return ONLY the JSON without markdown code blocks or explanations."""
        
        print("  Envoi à Ollama... (peut prendre 30-60s)")
        response_text = self.query_ollama(prompt)
        
        try:
            # Nettoyer la réponse si besoin
            response_text = response_text.strip()
            # Extraire JSON si encapsulé dans du markdown
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0]
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0]
            
            result = json.loads(response_text)
            
            # Valider la structure
            if 'entities' not in result:
                result['entities'] = []
            if 'relations' not in result:
                result['relations'] = []
                
            return result
            
        except json.JSONDecodeError as e:
            print(f"Erreur parsing JSON: {e}")
            print(f"  Réponse brute: {response_text[:200]}...")
            return {"entities": [], "relations": []}
        except Exception as e:
            print(f"Erreur extraction: {e}")
            return {"entities": [], "relations": []}
    
    def add_to_graph(self, extraction: dict, source_url: str):
        """Ajouter au graphe RDF"""
        
        # Mapping types → classes ontologie
        type_mapping = {
            'Manufacturer': AUTO.Manufacturer,
            'CarModel': AUTO.Car,
            'FuelType': AUTO.FuelType,
            'Transmission': AUTO.TransmissionType,
            'TransmissionType': AUTO.TransmissionType,
            'DriveType': AUTO.DriveType,
            'Engine': AUTO.Engine,
            'EngineType': AUTO.Engine
        }
        
        # Stocker les URIs des entités
        entity_uris = {}
        
        # Ajouter entités
        for entity in extraction.get('entities', []):
            text = entity.get('text', '')
            entity_type = entity.get('type', '')
            
            if not text or not entity_type:
                continue
            
            if entity_type in type_mapping:
                # Créer URI
                uri = AUTO[self._normalize(text)]
                entity_uris[text] = uri
                
                # Ajouter triplets
                self.graph.add((uri, RDF.type, type_mapping[entity_type]))
                self.graph.add((uri, RDFS.label, Literal(text, lang='en')))
                self.graph.add((uri, AUTO.extractedFrom, URIRef(source_url)))
        
        # Ajouter relations
        for relation in extraction.get('relations', []):
            subject = relation.get('subject', '')
            predicate = relation.get('predicate', '')
            obj = relation.get('object', '')
            
            if not subject or not predicate or not obj:
                continue
            
            if subject in entity_uris and obj in entity_uris:
                pred_uri = AUTO[predicate]
                self.graph.add((
                    entity_uris[subject],
                    pred_uri,
                    entity_uris[obj]
                ))
    
    def _normalize(self, text: str) -> str:
        # Nettoyer les caractères spéciaux
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'\s+', '_', text)
        
        # Les URIs RDF ne peuvent pas commencer par un chiffre
        # Préfixer avec un underscore si nécessaire
        if text and text[0].isdigit():
            text = '_' + text
        
        return text
    
    def process_urls(self, urls: list):
        total_entities = 0
        total_relations = 0
        
        for i, url in enumerate(urls):
            print(f"\n{'='*60}")
            print(f"[{i+1}/{len(urls)}] {url}")
            print('='*60)
            
            # Scraper
            article = self.scrape_article(url)
            if not article:
                print("Échec du scraping")
                continue
            
            print(f"  Titre: {article['title'][:60]}...")
            print(f"  Texte: {len(article['text'])} caractères")
            
            # Extraire avec Ollama
            extraction = self.extract_with_ollama(article['text'])
            
            num_entities = len(extraction.get('entities', []))
            num_relations = len(extraction.get('relations', []))
            
            print(f"  Entités: {num_entities}")
            print(f"  Relations: {num_relations}")
            
            total_entities += num_entities
            total_relations += num_relations
            
            # Ajouter au graphe
            self.add_to_graph(extraction, url)
            
            # Petite pause entre requêtes
            if i < len(urls) - 1:
                time.sleep(2)
        
        print(f"Total entités extraites: {total_entities}")
        print(f"Total relations extraites: {total_relations}")
    
    def save(self, output_path="kg_ollama_output.ttl"):
        self.graph.serialize(destination=output_path, format='turtle')
        print(f"\nGraphe sauvegardé: {output_path}")
        print(f"  Total triplets: {len(self.graph)}")
        


# Exemple d'utilisation
if __name__ == "__main__":
    
    print("="*60)
    print("CONSTRUCTION DE GRAPHE DE CONNAISSANCES AVEC OLLAMA")
    print("Collecte automatique depuis UltimateSpecs.com")
    print("="*60)
    print("\nPré-requis:")
    print("1. Ollama installé et en cours d'exécution")
    print("2. Modèle téléchargé: ollama pull phi3")
    print()
    
    # Configuration
    MODE = "test"  # "test" ou "full"
    
    try:
        # Construire le KG
        builder = OllamaKGBuilder(model="phi3")
        
        if MODE == "test":
            print("\nMODE TEST: Collecte limitée")
            # Test avec quelques marques seulement
            urls = builder.collect_all_urls(
                max_manufacturers=3,  # 3 marques
                max_models_per_manufacturer=2  # 2 modèles par marque
            )
        else:
            print("\nMODE COMPLET: Collecte de toutes les données")
            print("   (Cela peut prendre plusieurs heures!)")
            urls = builder.collect_all_urls()
        
        # Demander confirmation si beaucoup d'URLs
        if len(urls) > 20:
            print(f"\n{len(urls)} URLs à traiter.")
            confirm = input("Continuer? (o/n): ")
            if confirm.lower() != 'o':
                print("Annulé.")
                exit()
        
        # Traiter les URLs
        builder.process_urls(urls)
        
        # Sauvegarder
        builder.save("kg_from_web_ollama.ttl")
        
        print("\nTERMINE!")
        
    except KeyboardInterrupt:
        print("\n\nInterruption utilisateur")
        print("Sauvegarde du graphe partiel...")
        try:
            builder.save("kg_from_web_ollama_partial.ttl")
            print("Graphe partiel sauvegardé")
        except:
            pass
    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()
