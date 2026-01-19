# ============================================================================
# PIPELINE COMPLET: Scraping -> JSON -> Nettoyage -> RML -> RDF
# ============================================================================

# Étape 1: Scraper les données depuis UltimateSpecs
Write-Host "=== ETAPE 1: Scraping ===" -ForegroundColor Green
python graph/kg_ollama.py

# Vérifier que le fichier JSON a été créé
if (Test-Path "graph/vehicles_scraped.json") {
    Write-Host "OK: vehicles_scraped.json créé" -ForegroundColor Green
} else {
    Write-Host "ERREUR: Scraping échoué!" -ForegroundColor Red
    exit 1
}

# Étape 2: Nettoyer les données
Write-Host "`n=== ETAPE 2: Nettoyage ===" -ForegroundColor Green
python graph/clean_vehicles_json.py

# Vérifier que le fichier nettoyé a été créé
if (Test-Path "graph/vehicles_scraped_clean.json") {
    Write-Host "OK: vehicles_scraped_clean.json créé" -ForegroundColor Green
} else {
    Write-Host "ERREUR: Nettoyage échoué!" -ForegroundColor Red
    exit 1
}

# Étape 3: Appliquer le mapping RML avec Docker
Write-Host "`n=== ETAPE 3: Mapping RML -> RDF ===" -ForegroundColor Green
Push-Location graph
docker run --rm -v ${PWD}:/data rmlio/rmlmapper-java:latest --mappingfile /data/mapping_json.ttl --outputfile /data/kg_from_web_ollama.ttl --serialization turtle
Pop-Location

# Vérifier que le fichier RDF a été créé
if (Test-Path "graph/kg_from_web_ollama.ttl") {
    Write-Host "OK: kg_from_web_ollama.ttl créé" -ForegroundColor Green
} else {
    Write-Host "ERREUR: Mapping échoué!" -ForegroundColor Red
    exit 1
}

# Résumé final
Write-Host "`n" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "PIPELINE TERMINÉ AVEC SUCCÈS!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Fichiers générés:" -ForegroundColor Green
Write-Host "  1. graph/vehicles_scraped.json (données brutes)" -ForegroundColor Green
Write-Host "  2. graph/vehicles_scraped_clean.json (données nettoyées)" -ForegroundColor Green
Write-Host "  3. graph/kg_from_web_ollama.ttl (graphe RDF final)" -ForegroundColor Green
Write-Host "" -ForegroundColor Green
Write-Host "Prochaines étapes:" -ForegroundColor Yellow
Write-Host "  1. Fusionner avec output.ttl (données CSV)" -ForegroundColor Yellow
Write-Host "  2. Créer shapes.ttl (SHACL validation)" -ForegroundColor Yellow
Write-Host "  3. Créer thesaurus.ttl (SKOS)" -ForegroundColor Yellow
Write-Host "  4. Exécuter align_ontologies.py (alignement multi-ontologies)" -ForegroundColor Yellow
