"""
Alignement de l'ontologie et des instances avec le Web de Données Liées (LOD)
Génère des alignements vers DBpedia, Wikidata et Schema.org
"""

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import OWL, RDF, RDFS
import requests
import json
from pathlib import Path

# Namespaces
AUTO = Namespace("http://www.univ-projet.fr/ontologies/autosemantic#")
AUTO_INST = Namespace("http://www.univ-projet.fr/ontologies/autosemantic/")  # Pour les instances
DBO = Namespace("http://dbpedia.org/ontology/")
DBR = Namespace("http://dbpedia.org/resource/")
WD = Namespace("http://www.wikidata.org/entity/")
WDT = Namespace("http://www.wikidata.org/prop/direct/")
SCHEMA = Namespace("http://schema.org/")

# Mappings manuels pour les manufacturers
MANUFACTURER_MAPPINGS = {
    "Abarth": "Q26823",
    "AlfaRomeo": "Q26921",
    "AstonMartin": "Q191253",
    "BMW": "Q26678",
    "Mercedes_Benz": "Q36008",
    "Mitsubishi": "Q36033",
    "Nissan": "Q20165",
    "Porsche": "Q40993",
    "Toyota": "Q53268"
}

class OntologyAligner:
    """Classe pour aligner l'ontologie avec les vocabulaires LOD"""
    
    def __init__(self, ontology_path, kg_path=None):
        """
        Args:
            ontology_path: Chemin vers autosemantic.ttl
            kg_path: Chemin vers knowledge_graph.ttl (pour les instances)
        """
        self.ontology = Graph()
        print(f"Chargement de l'ontologie depuis {ontology_path}...")
        self.ontology.parse(ontology_path, format='turtle')
        print(f"✅ Ontologie chargée: {len(self.ontology)} triplets")
        
        # Charger aussi le graphe de connaissances si fourni (pour les instances)
        if kg_path and Path(kg_path).exists():
            print(f"Chargement du graphe de connaissances depuis {kg_path}...")
            self.ontology.parse(kg_path, format='turtle')
            print(f"✅ Graphe fusionné chargé: {len(self.ontology)} triplets total")
        
        # Graphes pour les alignements
        self.alignments_conceptual = Graph()
        self.alignments_instances = Graph()
        
        # Bind namespaces
        for g in [self.alignments_conceptual, self.alignments_instances]:
            g.bind("auto", AUTO)
            g.bind("auto_inst", AUTO_INST)
            g.bind("dbo", DBO)
            g.bind("dbr", DBR)
            g.bind("wd", WD)
            g.bind("wdt", WDT)
            g.bind("schema", SCHEMA)
            g.bind("owl", OWL)
    
    def align_classes(self):
        """Aligner les classes OWL avec vocabulaires externes"""
        print("\n📋 Alignement des classes...")
        
        class_alignments = {
            AUTO.Vehicle: [
                (DBO.Automobile, OWL.equivalentClass),
                (SCHEMA.Vehicle, OWL.equivalentClass)
            ],
            AUTO.Car: [
                (DBO.Automobile, OWL.equivalentClass),
                (SCHEMA.Car, OWL.equivalentClass)
            ],
            AUTO.Manufacturer: [
                (DBO.Company, RDFS.subClassOf),
                (DBO.Organisation, RDFS.subClassOf),
                (SCHEMA.Organization, OWL.equivalentClass)
            ],
            AUTO.CustomerReview: [
                (DBO.Review, OWL.equivalentClass),
                (SCHEMA.Review, OWL.equivalentClass)
            ]
        }
        
        count = 0
        for local_class, alignments in class_alignments.items():
            for external_class, relation in alignments:
                self.alignments_conceptual.add((local_class, relation, external_class))
                count += 1
        
        print(f"✅ {count} alignements de classes créés")
    
    def align_properties(self):
        """Aligner les propriétés avec vocabulaires externes"""
        print("\n📋 Alignement des propriétés...")
        
        property_alignments = {
            # Object Properties
            AUTO.hasManufacturer: [
                (DBO.manufacturer, OWL.equivalentProperty),
                (SCHEMA.manufacturer, OWL.equivalentProperty),
                (WDT.P176, OWL.equivalentProperty)  # manufacturer
            ],
            
            # Datatype Properties
            AUTO.modelYear: [
                (DBO.modelYear, OWL.equivalentProperty),
                (SCHEMA.modelDate, OWL.equivalentProperty),
                (WDT.P577, OWL.equivalentProperty)  # publication date
            ],
            AUTO.engineDisplacement: [
                (WDT.P2855, OWL.equivalentProperty)  # engine displacement
            ],
            AUTO.numberOfCylinders: [
                (WDT.P1162, OWL.equivalentProperty)  # number of cylinders
            ],
            AUTO.fuelConsumptionCity: [
                (DBO.fuelCapacity, RDFS.subPropertyOf),
                (SCHEMA.fuelConsumption, OWL.equivalentProperty)
            ],
            AUTO.reviewRating: [
                (SCHEMA.ratingValue, OWL.equivalentProperty)
            ],
            AUTO.reviewContent: [
                (SCHEMA.reviewBody, OWL.equivalentProperty)
            ],
            AUTO.reviewDate: [
                (SCHEMA.datePublished, OWL.equivalentProperty)
            ]
        }
        
        count = 0
        for local_prop, alignments in property_alignments.items():
            for external_prop, relation in alignments:
                self.alignments_conceptual.add((local_prop, relation, external_prop))
                count += 1
        
        print(f"✅ {count} alignements de propriétés créés")
    
    def validate_wikidata_entity(self, qid):
        """Valider qu'une entité Wikidata existe"""
        try:
            url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def search_dbpedia_resource(self, label):
        """Rechercher une ressource DBpedia par label"""
        try:
            # DBpedia Lookup Service
            url = "https://lookup.dbpedia.org/api/search"
            params = {
                "query": label,
                "format": "json",
                "maxResults": 1
            }
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("docs"):
                    # Retourner l'URI de la première ressource
                    return data["docs"][0]["resource"][0]
            return None
        except:
            return None
    
    def align_manufacturers(self):
        """Aligner les instances de manufacturers avec Wikidata et DBpedia"""
        print("\n📋 Alignement des manufacturers...")
        
        count = 0
        for manufacturer_name, wikidata_qid in MANUFACTURER_MAPPINGS.items():
            # Les instances utilisent le namespace avec # (AUTO)
            local_uri = AUTO[manufacturer_name]
            
            # Vérifier que l'entité existe dans le graphe
            if (local_uri, RDF.type, AUTO.Manufacturer) in self.ontology:
                # Lien Wikidata
                wikidata_uri = WD[wikidata_qid]
                self.alignments_instances.add((local_uri, OWL.sameAs, wikidata_uri))
                count += 1
                
                # Lien DBpedia (essayer de trouver)
                # Convertir format: Mercedes_Benz → Mercedes-Benz
                dbpedia_label = manufacturer_name.replace("_", "-")
                dbpedia_uri = DBR[dbpedia_label]
                self.alignments_instances.add((local_uri, OWL.sameAs, dbpedia_uri))
                count += 1
                
                print(f"  ✅ {manufacturer_name} → {wikidata_qid} + DBpedia")
            else:
                print(f"  ⚠️  {manufacturer_name} non trouvé dans le graphe")
        
        print(f"✅ {count} alignements d'instances créés")
    
    def save_alignments(self, output_dir):
        """Sauvegarder les alignements"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarder alignements conceptuels (classes + propriétés)
        conceptual_file = output_dir / "alignments.ttl"
        self.alignments_conceptual.serialize(destination=str(conceptual_file), format='turtle')
        print(f"\n💾 Alignements conceptuels sauvegardés: {conceptual_file}")
        print(f"   {len(self.alignments_conceptual)} triplets")
        
        # Sauvegarder alignements d'instances
        instances_file = output_dir / "alignments_instances.ttl"
        self.alignments_instances.serialize(destination=str(instances_file), format='turtle')
        print(f"💾 Alignements d'instances sauvegardés: {instances_file}")
        print(f"   {len(self.alignments_instances)} triplets")
    
    def generate_all_alignments(self, output_dir):
        """Générer tous les alignements"""
        print("="*70)
        print("GÉNÉRATION DES ALIGNEMENTS AVEC LOD")
        print("="*70)
        
        self.align_classes()
        self.align_properties()
        self.align_manufacturers()
        
        self.save_alignments(output_dir)
        
        print("\n" + "="*70)
        print("✅ ALIGNEMENTS GÉNÉRÉS AVEC SUCCÈS")
        print("="*70)
        print(f"\nTotal:")
        print(f"  - Alignements conceptuels: {len(self.alignments_conceptual)} triplets")
        print(f"  - Alignements d'instances: {len(self.alignments_instances)} triplets")


def main():
    """Point d'entrée principal"""
    # Chemins relatifs au script
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Chemins des fichiers
    ontology_path = project_root / "1_ontology" / "autosemantic.ttl"
    kg_path = project_root / "5_knowledge_graph" / "knowledge_graph.ttl"
    output_dir = script_dir  # Sauvegarder dans 4_alignment/
    
    # Vérifier que l'ontologie existe
    if not ontology_path.exists():
        print(f"Erreur: Fichier non trouvé: {ontology_path}")
        print("Veuillez vous assurer que l'ontologie existe dans 1_ontology/")
        return
    
    # Vérifier que le graphe existe (pour les instances)
    if not kg_path.exists():
        print(f"⚠️  Attention: Graphe de connaissances non trouvé: {kg_path}")
        print("Les alignements d'instances ne seront pas générés.")
        print("Exécutez d'abord: python 5_knowledge_graph/merge_graphs.py")
        kg_path = None
    
    # Créer l'aligner et générer les alignements
    aligner = OntologyAligner(str(ontology_path), str(kg_path) if kg_path else None)
    aligner.generate_all_alignments(str(output_dir))


if __name__ == "__main__":
    main()
