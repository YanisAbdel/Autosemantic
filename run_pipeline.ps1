# ============================================================================
# PIPELINE COMPLET AUTOSEMANTIC
# ============================================================================
# Structure: 9 dossiers acadÃ©miques
#   1_ontology/ 2_data_sources/ 3_data_extraction/ 4_alignment/
#   5_knowledge_graph/ 6_validation/ 7_exploitation/ 8_interface/ 9_documentation/
# ============================================================================

Write-Host "`n============================================================"
Write-Host "AUTOSEMANTIC - PIPELINE COMPLET"
Write-Host "============================================================`n"

# ============================================================================
# PHASE 1: NETTOYAGE DES DONNEES
# ============================================================================
Write-Host "=== PHASE 1: Nettoyage des donnees sources ==="

# 1.1: Nettoyer les CSV
Write-Host "`n[1/2] Nettoyage des CSV (vehicles.csv, reviews_final.csv)..."
python 2_data_sources/structured/clean_data.py

if (Test-Path "2_data_sources/structured/vehicles_clean.csv") {
    Write-Host "    [OK] vehicles_clean.csv cree"
} else {
    Write-Host "    [ERREUR] Nettoyage CSV echoue!"
    exit 1
}

# ============================================================================
# PHASE 2: EXTRACTION WEB (OPTIONNEL - PEUT ÃŠTRE SAUTÃ‰ SI JSON EXISTE)
# ============================================================================
Write-Host "`n=== PHASE 2: Extraction web (optionnel) ==="

if (Test-Path "2_data_sources/unstructured/vehicles_scraped_clean.json") {
    Write-Host "[INFO] vehicles_scraped_clean.json existe deja - etape sautee"
} else {
    # 2.1: Scraper les donnÃ©es
    Write-Host "`n[1/2] Scraping UltimateSpecs avec Ollama..."
    python 3_data_extraction/web_extraction/kg_ollama.py

    if (Test-Path "2_data_sources/unstructured/vehicles_scraped.json") {
        Write-Host "    [OK] vehicles_scraped.json cree"
    } else {
        Write-Host "    [ERREUR] Scraping echoue!"
        exit 1
    }

    # 2.2: Nettoyer le JSON
    Write-Host "`n[2/2] Nettoyage du JSON scraped..."
    python 3_data_extraction/web_extraction/clean_vehicles_json.py

    if (Test-Path "2_data_sources/unstructured/vehicles_scraped_clean.json") {
        Write-Host "    [OK] vehicles_scraped_clean.json cree"
    } else {
        Write-Host "    [ERREUR] Nettoyage JSON echoue!"
        exit 1
    }
}

# ============================================================================
# PHASE 3: MAPPING RML (CSV + JSON -> RDF)
# ============================================================================
Write-Host "`n=== PHASE 3: Mapping RML vers RDF ==="

# 3.1: Mapping CSV -> RDF
Write-Host "`n[1/2] Mapping CSV -> RDF (output.ttl)..."
docker run --rm -v ${PWD}:/data rmlio/rmlmapper-java:latest --mappingfile /data/3_data_extraction/rml_mapping/mapping.ttl --outputfile /data/3_data_extraction/rml_mapping/output.ttl --serialization turtle

if (Test-Path "3_data_extraction/rml_mapping/output.ttl") {
    $size = (Get-Item "3_data_extraction/rml_mapping/output.ttl").Length / 1MB
    $sizeStr = [math]::Round($size, 2)
    Write-Host "    [OK] output.ttl cree ($sizeStr MB)"
} else {
    Write-Host "    [ERREUR] Mapping CSV echoue!"
    exit 1
}

# 3.2: Mapping JSON -> RDF
Write-Host "`n[2/2] Mapping JSON -> RDF (kg_from_web_ollama.ttl)..."
docker run --rm -v ${PWD}:/data rmlio/rmlmapper-java:latest --mappingfile /data/3_data_extraction/web_extraction/mapping_json.ttl --outputfile /data/3_data_extraction/web_extraction/kg_from_web_ollama.ttl --serialization turtle

if (Test-Path "3_data_extraction/web_extraction/kg_from_web_ollama.ttl") {
    $size = (Get-Item "3_data_extraction/web_extraction/kg_from_web_ollama.ttl").Length / 1KB
    $sizeStr = [math]::Round($size, 2)
    Write-Host "    [OK] kg_from_web_ollama.ttl cree ($sizeStr KB)"
} else {
    Write-Host "    [ERREUR] Mapping JSON echoue!"
    exit 1
}

# ============================================================================
# PHASE 4: FUSION DES GRAPHES
# ============================================================================
Write-Host "`n=== PHASE 4: Fusion des graphes RDF ==="
Write-Host "`nFusion: output.ttl + kg_from_web_ollama.ttl + alignments..."
python 5_knowledge_graph/merge_graphs.py

if (Test-Path "5_knowledge_graph/knowledge_graph.ttl") {
    $size = (Get-Item "5_knowledge_graph/knowledge_graph.ttl").Length / 1MB
    $sizeStr = [math]::Round($size, 2)
    Write-Host "    [OK] knowledge_graph.ttl cree ($sizeStr MB)"
} else {
    Write-Host "    [ERREUR] Fusion echouee!"
    exit 1
}

# ============================================================================
# PHASE 5: VALIDATION (SHACL + OWL-RL)
# ============================================================================
Write-Host "`n=== PHASE 5: Validation du graphe ==="
Write-Host "`nValidation SHACL + Raisonnement OWL-RL..."
python 6_validation/validate_ontology.py

if (Test-Path "1_ontology/autosemantic_inferred.ttl") {
    Write-Host "    [OK] Validation complete + inferences generees"
} else {
    Write-Host "    [WARN] Validation executee (verifier les logs)"
}

# ============================================================================
# PHASE 6: ALIGNEMENT AVEC ONTOLOGIES EXTERNES (OPTIONNEL)
# ============================================================================
Write-Host "`n=== PHASE 6: Alignement avec DBpedia/Wikidata (optionnel) ==="
Write-Host "`n[INFO] Cette etape peut prendre 10-30 minutes (requetes SPARQL externes)"
Write-Host "Voulez-vous executer l'alignement ? (O/n): " -NoNewline
$response = Read-Host

if ($response -eq "" -or $response -eq "O" -or $response -eq "o") {
    Write-Host "`nAlignement avec DBpedia et Wikidata..."
    python 4_alignment/align_ontologies.py
    
    if (Test-Path "4_alignment/alignments.ttl") {
        Write-Host "    [OK] Alignements generes"
    } else {
        Write-Host "    [WARN] Alignement termine (verifier les logs)"
    }
} else {
    Write-Host "    [SKIP] Alignement saute"
}

# ============================================================================
# PHASE 7: TEST DE RECOMMANDATION
# ============================================================================
Write-Host "`n=== PHASE 7: Test du systeme de recommandation ==="
Write-Host "`nExecution d'un exemple de recommandation..."
python 7_exploitation/link_prediction/recommend.py

Write-Host "Recommandation testee"

# ============================================================================
# RESUME FINAL
# ============================================================================
Write-Host "`n============================================================"
Write-Host "PIPELINE TERMINE AVEC SUCCES!"
Write-Host "============================================================"

Write-Host "`nFichiers generes:"
Write-Host "  2_data_sources/structured/"
Write-Host "     vehicles_clean.csv, reviews_final_clean.csv"
Write-Host "  2_data_sources/unstructured/"
Write-Host "     vehicles_scraped_clean.json"
Write-Host "  3_data_extraction/rml_mapping/"
Write-Host "     output.ttl (RDF depuis CSV)"
Write-Host "  3_data_extraction/web_extraction/"
Write-Host "     kg_from_web_ollama.ttl (RDF depuis JSON)"
Write-Host "  5_knowledge_graph/"
Write-Host "     knowledge_graph.ttl (graphe fusionne)"
Write-Host "  1_ontology/"
Write-Host "     autosemantic_inferred.ttl (avec inferences)"

Write-Host "`nEtapes interactives disponibles:"
Write-Host "  - GraphRAG (Q&A):  python 7_exploitation/graphrag/approach1_llm_to_sparql.py"
Write-Host "  - Interface web:   python 8_interface/app.py"
Write-Host "                     puis ouvrir http://localhost:5000"

Write-Host "`n============================================================`n"

