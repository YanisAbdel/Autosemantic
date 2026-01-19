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
        """Scraper un article web"""
        try:
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Educational Project)'
            }, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extraire texte principal
            paragraphs = soup.find_all('p')
            text = ' '.join([p.get_text().strip() for p in paragraphs])
            
            # Limiter la taille pour éviter overflow
            text = text[:8000]
            
            return {
                'url': url,
                'title': soup.find('title').text if soup.find('title') else '',
                'text': text
            }
        except Exception as e:
            print(f"Erreur scraping: {e}")
            return None
    
    def extract_with_ollama(self, text: str) -> dict:
        """Extraire entités et relations avec Ollama"""
        
        prompt = f"""You are an expert in automotive knowledge extraction. Analyze the following text and extract structured information.

TEXT:
{text}

TASK:
1. Identify all automotive entities:
   - Manufacturers (car brands)
   - Car models
   - Engine types
   - Fuel types (gasoline, diesel, electric, hybrid)
   - Transmission types (automatic, manual)
   - Technical specifications

2. Identify relationships between entities:
   - Who manufactures what
   - What characteristics vehicles have
   - Comparisons between brands

3. Return ONLY a valid JSON with this EXACT structure:
{{
  "entities": [
    {{"text": "Tesla", "type": "Manufacturer"}},
    {{"text": "Model S", "type": "CarModel"}},
    {{"text": "Electric", "type": "FuelType"}}
  ],
  "relations": [
    {{"subject": "Tesla", "predicate": "manufactures", "object": "Model S"}},
    {{"subject": "Model S", "predicate": "hasFuelType", "object": "Electric"}}
  ]
}}

IMPORTANT: Return ONLY the JSON, no explanations or markdown formatting."""
        
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
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'\s+', '_', text)
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
            
            print(f"  ✓ Entités: {num_entities}")
            print(f"  ✓ Relations: {num_relations}")
            
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
        print(f"\n Graphe sauvegardé: {output_path}")
        print(f"  Total triplets: {len(self.graph)}")
        


# Exemple d'utilisation
if __name__ == "__main__":
    
    # URLs à analyser (commencez avec peu d'URLs pour tester)
    urls = [
        "https://en.wikipedia.org/wiki/Tesla,_Inc.",
        "https://en.wikipedia.org/wiki/BMW",
        "https://en.wikipedia.org/wiki/Toyota_Prius",
        # Ajouter plus d'URLs selon vos besoins
    ]
    
    print("="*60)
    print("CONSTRUCTION DE GRAPHE DE CONNAISSANCES AVEC OLLAMA")
    print("="*60)
    print("\nPré-requis:")
    print("1. Ollama installé et en cours d'exécution")
    print("2. Modèle téléchargé: ollama pull llama3.2")
    print()
    
    try:
        # Construire le KG
        # Modèles recommandés: llama3.2, mistral, phi3
        builder = OllamaKGBuilder(model="phi3")
        
        # Traiter les URLs
        builder.process_urls(urls)
        
        # Sauvegarder
        builder.save("kg_from_web_ollama.ttl")
        
        print("\n✓ TERMINÉ!")
        
    except Exception as e:
        print(f"\n ERREUR: {e}")
