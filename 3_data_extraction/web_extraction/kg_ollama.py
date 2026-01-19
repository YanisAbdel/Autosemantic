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
        """Extraire spécifications techniques avec Ollama"""
        
        prompt = f"""Extract vehicle technical specifications from the text. Return ONLY valid JSON.

TEXT:
{text}

Extract these fields (use null if not found):
- manufacturer: Brand name (e.g., "Mercedes-Benz", "Toyota")
- modelName: Model name (e.g., "Sprinter 2019", "Camry")
- year: Model year (integer)
- fuelType: One of [Regular, Premium, Diesel, Electric, Hybrid, E85]
- transmission: Type (e.g., "Automatic (S6)", "Manual", "CVT")
- driveType: One of [FrontWheelDrive, RearWheelDrive, AllWheelDrive, FourWheelDrive]
- vehicleClass: Type (e.g., "SUV", "Sedan", "Truck", "Van")
- engineDisplacement: Displacement in liters (float, e.g., 2.0, 3.5)
- numberOfCylinders: Number of cylinders (integer, e.g., 4, 6, 8)
- horsepower: Power in HP (integer)
- mpgCity: City fuel economy (float)
- mpgHighway: Highway fuel economy (float)

Return ONLY this JSON structure:
{{
  "manufacturer": "Mercedes-Benz",
  "modelName": "Sprinter 2019 L2H2 RWD",
  "year": 2019,
  "fuelType": "Diesel",
  "transmission": "Automatic (9G-TRONIC)",
  "driveType": "RearWheelDrive",
  "vehicleClass": "Van",
  "engineDisplacement": 2.1,
  "numberOfCylinders": 4,
  "horsepower": 143,
  "mpgCity": 18.0,
  "mpgHighway": 24.0
}}

Return ONLY the JSON, no explanations."""
        
        print("  Envoi à Ollama... (peut prendre 30-60s)")
        response_text = self.query_ollama(prompt)
        
        try:
            # Nettoyer la réponse
            response_text = response_text.strip()
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0]
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0]
            
            result = json.loads(response_text)
            return result
            
        except json.JSONDecodeError as e:
            print(f"Erreur parsing JSON: {e}")
            print(f"  Réponse brute: {response_text[:200]}...")
            return None
        except Exception as e:
            print(f"Erreur extraction: {e}")
            return None
    
    def add_to_json_data(self, extraction: dict, source_url: str, vehicle_id: int):
        """Ajouter au dataset JSON"""
        if not extraction:
            return None
        
        vehicle_data = {
            "id": vehicle_id,
            "sourceUrl": source_url,
            "manufacturer": extraction.get("manufacturer"),
            "modelName": extraction.get("modelName"),
            "year": extraction.get("year"),
            "fuelType": extraction.get("fuelType"),
            "transmission": extraction.get("transmission"),
            "driveType": extraction.get("driveType"),
            "vehicleClass": extraction.get("vehicleClass"),
            "engineDisplacement": extraction.get("engineDisplacement"),
            "numberOfCylinders": extraction.get("numberOfCylinders"),
            "horsepower": extraction.get("horsepower"),
            "mpgCity": extraction.get("mpgCity"),
            "mpgHighway": extraction.get("mpgHighway")
        }
        
        # Nettoyer les valeurs None
        vehicle_data = {k: v for k, v in vehicle_data.items() if v is not None}
        
        return vehicle_data
    
    def process_urls(self, urls: list):
        """Traiter une liste d'URLs et extraire les données"""
        vehicles_data = []
        
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
            
            if extraction:
                # Ajouter au dataset JSON
                vehicle_data = self.add_to_json_data(extraction, url, i + 1)
                if vehicle_data:
                    vehicles_data.append(vehicle_data)
                    print(f"  Véhicule: {vehicle_data.get('manufacturer')} {vehicle_data.get('modelName')}")
                    print(f"  Specs: {vehicle_data.get('engineDisplacement')}L, {vehicle_data.get('numberOfCylinders')} cyl")
            else:
                print("  Échec extraction")
            
            # Petite pause entre requêtes
            if i < len(urls) - 1:
                time.sleep(2)
        
        print(f"\nTotal véhicules extraits: {len(vehicles_data)}")
        return vehicles_data
    
    def save_json(self, vehicles_data: list, output_path="vehicles_scraped.json"):
        """Sauvegarder les données en JSON"""
        if not Path(output_path).is_absolute():
            project_root = Path(__file__).parent.parent.parent
            output_path = project_root / "2_data_sources" / "unstructured" / output_path
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(vehicles_data, f, indent=2, ensure_ascii=False)
        print(f"\nDonnées JSON sauvegardées: {output_path}")
        print(f"  Total véhicules: {len(vehicles_data)}")


if __name__ == "__main__":
    import sys
    
    try:
        print("\n" + "="*60)
        print("KNOWLEDGE GRAPH BUILDER - OLLAMA + ULTIMATESPECS")
        print("="*60)
        
        builder = OllamaKGBuilder()
        
        # Mode de fonctionnement
        mode = input("\nMode? (test/full): ").strip().lower()
        
        if mode == 'test':
            print("\nMODE TEST: 3 marques, 2 modèles par marque")
            urls = builder.collect_all_urls(max_manufacturers=3, max_models_per_manufacturer=2)
        else:
            print("\nMODE COMPLET: Collecte de toutes les données")
            print("   (Cela peut prendre plusieurs heures!)")
            urls = builder.collect_all_urls()
            
            confirm = input("Continuer? (o/n): ")
            if confirm.lower() != 'o':
                print("Annulé.")
                exit()
        
        # Traiter les URLs
        vehicles_data = builder.process_urls(urls)
        
        # Sauvegarder en JSON
        builder.save_json(vehicles_data, "vehicles_scraped.json")
        
        print("\nTERMINE!")
        print("Prochaine étape: python run_rml_mapping.py pour convertir en RDF")
        
    except KeyboardInterrupt:
        print("\n\nInterruption utilisateur")
    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()
