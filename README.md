# Projet AutoSemantic - Web Sémantique & Graphes de Connaissances

> Application web sémantique complète pour l'analyse et la recommandation de véhicules automobiles

## Objectif du Projet

Démonstration des compétences en **Web de données**, **Ingénierie des connaissances** et **Web sémantique** à travers une application bout-en-bout incluant:
- Modélisation ontologique (OWL + SKOS)
- Extraction d'informations depuis sources hétérogènes
- Alignements avec le Linked Open Data
- Exploitation via SPARQL, Link Prediction et GraphRAG

## Structure du Projet

```
Autosemantic/
├── 1_ontology/              # Modélisation OWL + SKOS + SHACL
├── 2_data_sources/          # Données sources (structurées + non structurées)
├── 3_data_extraction/       # Extraction RML + Web scraping
├── 4_alignment/             # Alignements avec DBpedia, Wikidata, Schema.org
├── 5_knowledge_graph/       # Graphe de connaissances final
├── 6_validation/            # Validation SHACL + OWL
├── 7_exploitation/          # SPARQL, Link Prediction, GraphRAG
├── 8_interface/             # Interface utilisateur
└── 9_documentation/         # Rapport et présentation
```

## Composants Implémentés

### 1. Modélisation Ontologique (Complet)
- **OWL**: Hiérarchies de classes (Vehicle → Car/Truck/SUV), propriétés algébriques
- **SKOS**: Thésaurus (Manufacturers, FuelTypes, VehicleClasses, TransmissionTypes, DriveTypes)
- **SHACL**: Contraintes d'intégrité

Localisation: [`1_ontology/`](1_ontology/)

### 2. Population depuis Données Hétérogènes (Complet)
- **RML Mapping**: CSV → RDF avec jointures (vehicles ↔ reviews)
- **Web Scraping**: Extraction depuis ultimatespecs.com avec LLM (Ollama)

Localisation: [`3_data_extraction/`](3_data_extraction/)

### 3. Alignements LOD (Complet)
- **Classes/Propriétés**: 20 classes + 17 propriétés alignées avec DBpedia, Schema.org, Wikidata
- **Instances**: 9 manufacturers owl:sameAs vers Wikidata/DBpedia

Localisation: [`4_alignment/`](4_alignment/)

### 4. Validation (Complet)
- Validation syntaxique RDF
- Validation SHACL
- Inférence OWL-RL (993 → 3,554 triplets)

Localisation: [`6_validation/`](6_validation/)

### 5. Exploitation du Graphe (Nouveau)

#### 5.1 Requêtes SPARQL (6 requêtes)
- Query 1: Véhicules haute performance
- Query 2: Véhicules avec avis positifs
- Query 3: Efficacité énergétique par constructeur
- Query 4: Véhicules tout-terrain (4x4/SUV)
- Query 5: Analyse véhicules de luxe
- **Query Fédérée**: Enrichissement via DBpedia (SERVICE)

Localisation: [`7_exploitation/sparql_queries/`](7_exploitation/sparql_queries/)

#### 5.2 Link Prediction (Implémenté)
Recommandation de véhicules via collaborative filtering basé sur:
- Similarité de marque
- Proximité temporelle
- Caractéristiques techniques
- Évaluations clients

Localisation: [`7_exploitation/link_prediction/recommend.py`](7_exploitation/link_prediction/recommend.py)

#### 5.3 GraphRAG (2 Approches)
- **Approche 1**: Question → SPARQL → Réponse (NL2SPARQL avec templates)
- **Approche 2**: Question → Embeddings → Similarité → Réponse

Localisation: [`7_exploitation/graphrag/`](7_exploitation/graphrag/)

### 6. Interface (En cours)
Interface web/CLI pour démonstration du cas d'usage

Localisation: [`8_interface/`](8_interface/)

## Installation et Exécution

### Option 1 : Exécution Automatique (Recommandé)

```powershell
# 1. Créer un environnement conda
conda create -n autosemantic python=3.11
conda activate autosemantic

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Lancer le pipeline complet
.\run_pipeline.ps1
```

Le script exécute automatiquement :
- Nettoyage des données CSV/JSON
- Extraction web (optionnel si déjà fait)
- Mapping RML (CSV + JSON → RDF)
- Fusion des graphes
- Validation SHACL + OWL-RL
- Alignements externes (optionnel)
- Test de recommandation

### Option 2 : Exécution Manuelle

#### Étape 1 : Prérequis
```powershell
# Environnement Python
conda create -n autosemantic python=3.11
conda activate autosemantic
pip install -r requirements.txt

# Docker (pour RML Mapper)
# Vérifier : docker --version
```

#### Étape 2 : Nettoyage des Données
```powershell
python 2_data_sources/structured/clean_data.py
```
Génère `vehicles_clean.csv` et `reviews_final_clean.csv`

#### Étape 3 : Mapping RML vers RDF
```powershell
# CSV → RDF
docker run --rm -v ${PWD}:/data rmlio/rmlmapper-java:latest `
  --mappingfile /data/3_data_extraction/rml_mapping/mapping.ttl `
  --outputfile /data/3_data_extraction/rml_mapping/output.ttl `
  --serialization turtle

# JSON → RDF (si web scraping déjà effectué)
docker run --rm -v ${PWD}:/data rmlio/rmlmapper-java:latest `
  --mappingfile /data/3_data_extraction/web_extraction/mapping_json.ttl `
  --outputfile /data/3_data_extraction/web_extraction/kg_from_web_ollama.ttl `
  --serialization turtle
```

#### Étape 4 : Fusion des Graphes
```powershell
python 5_knowledge_graph/merge_graphs.py
```
Génère `knowledge_graph.ttl` (graphe fusionné)

#### Étape 5 : Validation et Inférence
```powershell
python 6_validation/validate_ontology.py
```
Applique SHACL + OWL-RL

#### Étape 6 : Exploitation

**Recommandation (Link Prediction)** :
```powershell
python 7_exploitation/link_prediction/recommend.py
```

**Interface Web** :
```powershell
streamlit run 8_interface/app.py
# Ouvrir http://localhost:8501
```

**Requêtes SPARQL** : Ouvrir les fichiers `.rq` dans `7_exploitation/sparql_queries/` avec un éditeur SPARQL (Protégé, Apache Jena)

## Statistiques du Graphe

- **Ontologie**: 993 triplets de base, 3,554 après inférence OWL-RL
- **Graphe de connaissances**: ~50,000+ triplets
- **Alignements**: 20 classes + 17 propriétés + 9 instances
- **Données**: 39 véhicules, 397 avis clients

## Documentation Détaillée

Chaque répertoire contient un README spécifique:
- [`1_ontology/README.md`](1_ontology/README.md) - Modélisation OWL/SKOS
- [`3_data_extraction/README.md`](3_data_extraction/README.md) - Extraction de données
- [`4_alignment/README.md`](4_alignment/README.md) - Alignements LOD
- [`7_exploitation/README.md`](7_exploitation/README.md) - SPARQL, Link Prediction, GraphRAG

## Auteurs

Projet réalisé dans le cadre du cours de Web Sémantique.

## Licence

Projet académique - 2026