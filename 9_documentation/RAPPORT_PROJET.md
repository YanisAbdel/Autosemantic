# RAPPORT DE PROJET — AUTOSEMANTIC (Résumé ≤5 pages)

Date : 20 janvier 2026 — Responsable : Mathy — Environnement : Python 3.10, RDF/SPARQL, Docker

## 1. Vue d’ensemble

Objectif : construire et exploiter un graphe de connaissances automobile, de la collecte de données hétérogènes à l’interrogation SPARQL et à la recommandation.

Périmètre couvert :
- Ontologie OWL + SKOS + SHACL (contraintes) ; alignements optionnels DBpedia/Wikidata
- Extraction : CSV officiels (EPA) + web scraping (UltimateSpecs) enrichi par Ollama
- Mapping RML (CSV/JSON → RDF) via Docker rmlmapper
- Fusion et validation (SHACL + inférence OWL-RL)
- Exploitation : 6 requêtes SPARQL, recommandation (link prediction), GraphRAG (NL2SPARQL / embeddings)

## 2. Données et volumes

- CSV structurés (US Government, EPA) : vehicles.csv (6 552 lignes, 79 colonnes) — specs officielles consommation/émissions.
- CSV reviews (Kaggle, dataset public) : reviews_final.csv (~41 000 avis) — notes 1–5 et texte utilisateur.
- JSON non structuré (web) : 1 299 véhicules scrapés sur UltimateSpecs → vehicles_scraped_clean.json après LLM + normalisation.
- RDF générés :
  - output.ttl (CSV → RDF) : ~11,4 MB, 43 332 triplets
  - kg_from_web_ollama.ttl (JSON → RDF) : 23 KB, 467 triplets
  - knowledge_graph.ttl (fusion) : 11,66 MB, ~43 799 triplets, 7 243 entités, 1 299 véhicules

## 3. Ontologie et validation

- Ontologie : hiérarchie Vehicle/Car/SUV/Truck + sous-classes (HighPerformanceCar, OffroadCar, LuxuryVehicle), propriétés moteur/transmission/énergie, SKOS pour fabricants/carburants/classes/transmissions.
- SHACL : contraintes cardinalité/type sur année (xsd:integer, bornes réalistes), cylindrée/cylindres, consommation, rating 1–5, présence de manufacturer et modèle.
- Inférence OWL-RL : typage dérivé (ex: HighPerformanceCar), complétion de propriétés inverses/symétriques (≈3,5k triplets ajoutés).

## 4. Extraction et nettoyage

- Web scraping + LLM (UltimateSpecs) :
  - kg_ollama.py : BeautifulSoup4 + Ollama (phi3) pour extraire marque, modèle, année, cylindrée, cylindres, transmission, fuel, drive.
  - clean_vehicles_json.py : validation des types (int/float), filtrage d’années aberrantes, normalisation des libellés vers SKOS (fuel/drive/class/transmission), suppression valeurs bruitées.
- CSV EPA + Kaggle :
  - clean_data.py : drop colonnes redondantes, harmonisation des types numériques, parsing de displacement/cylinders, remplissage NA (median/mode), normalisation textes vers SKOS.
  - Sorties : vehicles_clean.csv, reviews_final_clean.csv prêtes pour RML.

## 5. Mapping RML (CSV/JSON → RDF)

- Fichiers : 3_data_extraction/rml_mapping/mapping.ttl (CSV) ; 3_data_extraction/web_extraction/mapping_json.ttl (JSON).
- Exécution type :
```bash
docker run --rm -v "${PWD}:/data" rmlio/rmlmapper-java:latest \
  -m /data/3_data_extraction/rml_mapping/mapping.ttl \
  -o /data/3_data_extraction/rml_mapping/output.ttl
```
- Sujets : IRIs manufacturer/year/model ; jointures véhicules ↔ avis ; datatypes xsd (année, cylindres, cylindrée, rating). Préfixes auto/skos/xsd liés.

## 6. Fusion et validation

- Fusion : merge_graphs.py charge output.ttl (CSV), kg_from_web_ollama.ttl (JSON) et éventuels alignements, bind les namespaces, écrit knowledge_graph.ttl.
- Validation : validate_ontology.py applique SHACL puis inférence OWL-RL ; journalise les violations (pour itérations) et produit un graphe enrichi exploitable immédiatement.

## 7. Alignements (optionnels)

- Vocabulaires : DBpedia, Wikidata, Schema.org. owl:sameAs sur principaux constructeurs ; skos:exactMatch sur carburants, transmissions, drives, classes.
- Intérêt : meilleure réutilisabilité LOD et fédération SPARQL ; fichiers dans 4_alignment/*.ttl.

## 8. Exploitation

### Requêtes SPARQL (6 fichiers dans 7_exploitation/sparql_queries)
- Query1 : haute performance (depuis 2000, tri cylindrée/cylindres)
- Query2 : avis positifs (≥3 avis, avg rating)
- Query3 : efficacité énergétique par constructeur (agrégations)
- Query4 : offroad 4x4/SUV (drive type)
- Query5 : véhicules de luxe (prix/puissance/options)
- Query fédérée : enrichissement DBpedia (SERVICE)

### Recommandation (link prediction)
Usage direct :
```bash
python 7_exploitation/link_prediction/recommend.py
```
OU en ciblant un contexte :
```bash
python 7_exploitation/link_prediction/recommend.py --top_k 10 --brand "Audi" --after_year 2010
```
Ce que fait le script :
- Résout automatiquement le chemin du graphe [5_knowledge_graph/knowledge_graph.ttl](5_knowledge_graph/knowledge_graph.ttl) et le charge.
- Extrait pour chaque véhicule : marque, modèle, année, conso ville, cylindrée, cylindres, note moyenne (AVG des reviewRating).
- Prend un véhicule de référence et calcule les top-N plus similaires.
Scoring (pondération simple) :
- Marque identique (+0.3)
- Année proche (jusqu’à +0.2 si écart faible)
- Conso ville proche (jusqu’à +0.15)
- Cylindrée proche (jusqu’à +0.2)
- Note moyenne proche (jusqu’à +0.15)
Personnalisation rapide :
- Pour un véhicule précis, remplacer `example_vehicle` dans `main()` par l’URI voulu (imprimé lors du premier run).
- En code : `collaborative_filtering_recommend([uri1, uri2], top_n=10)` pour partir d’une liste de véhicules appréciés.



## 10. Résultats clés

- Couverture : 7 243 entités, ~43,8k triplets (fusion) ; 1 299 véhicules scrapés intégrés.
- Qualité : contraintes SHACL passées, inférence OWL-RL appliquée.
- Requêtes SPARQL : 6 scénarios prêts à l’emploi ; fédérée pour enrichissement externe.
- Recommandation : <1s sur l’échantillon, top-k ajustable.

## 11. Points d’usage / bonnes pratiques

- Toujours lancer run_pipeline.ps1 depuis la racine du projet (résolution des chemins).
- Si Docker indisponible : exécuter les scripts Python (nettoyage, fusion) et charger les RDF déjà générés.
- Pour tester une requête : charger knowledge_graph.ttl dans votre triple store (Fuseki/GraphDB) puis exécuter le fichier .rq.
- Fichiers volumineux : output.ttl (~11,4 MB) et knowledge_graph.ttl (~11,66 MB).

## 12. Livrables principaux

- Ontologie/SHACL : 1_ontology/*.ttl
- Données nettoyées : 2_data_sources/structured/*clean.csv, 2_data_sources/unstructured/vehicles_scraped_clean.json
- RDF générés : 3_data_extraction/rml_mapping/output.ttl, 3_data_extraction/web_extraction/kg_from_web_ollama.ttl
- Graphe fusionné : 5_knowledge_graph/knowledge_graph.ttl
- Scripts : run_pipeline.ps1, merge_graphs.py, validate_ontology.py, recommend.py
- Requêtes SPARQL : 7_exploitation/sparql_queries/*.rq

## 13. Prochaines améliorations (suggestions)

1) Ajouter métriques qualité données (completeness, consistency) dans la validation.
2) Étendre les alignements instance-level (modèles emblématiques).
3) Exposer un endpoint SPARQL public ou API REST fine (FastAPI) pour la démo.

## 14. Pipeline (automatisé dans run_pipeline.ps1)

1) Nettoyage CSV/JSON
2) Extraction web (Ollama) — optionnel si JSON déjà présent
3) Mapping RML → RDF (Docker rmlio/rmlmapper-java)
4) Fusion des graphes (output.ttl + kg_from_web_ollama.ttl + alignements éventuels)
5) Validation SHACL + inférence OWL-RL
6) Alignement DBpedia/Wikidata (optionnel)
7) Tests : recommandation + requêtes SPARQL

Commande unique (depuis la racine) :
```bash
pwsh -File run_pipeline.ps1
```
