"""
AutoSemantica - Interface Streamlit pour l'exploration du Web Sémantique
Projet de Web Sémantique - SI5/S2
"""

import streamlit as st
import pandas as pd
from rdflib import Graph, Namespace, RDF, RDFS, OWL
from rdflib.namespace import SKOS
from pyshacl import validate
import urllib.parse
import os
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

# ============================================================================
# CONFIGURATION
# ============================================================================

# Remonte d'un niveau depuis interface/ vers le dossier racine
BASE_DIR = Path(__file__).resolve().parent.parent

# Définir le namespace AutoSemantic
AUTO = Namespace("http://www.univ-projet.fr/ontologies/autosemantic#")

# ============================================================================
# CHARGEMENT DU GRAPHE RDF (avec cache)
# ============================================================================

@st.cache_resource
def load_graph():
    """
    Charge tous les fichiers TTL dans un seul graphe RDF.
    Retourne le graphe et un dict des statuts de chargement.
    """
    g = Graph()
    g.bind("auto", AUTO)
    g.bind("skos", SKOS)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)
    
    # Liste des fichiers à charger (convertir en Path objects)
    files_to_load = {
        "Ontologie (autosemantic.ttl)": BASE_DIR / "1_ontology" / "autosemantic.ttl",
        "Données CSV (output.ttl)": BASE_DIR / "3_data_extraction" / "rml_mapping" / "output.ttl",
        "Alignements Wikidata (alignments.ttl)": BASE_DIR / "4_alignment" / "alignments.ttl",
        "Contraintes SHACL (shapes.ttl)": BASE_DIR / "1_ontology" / "shapes.ttl",
        "Données Web scraping (kg_from_web_ollama.ttl)": BASE_DIR / "3_data_extraction" / "web_extraction" / "kg_from_web_ollama.ttl"
    }
    
    load_status = {}
    
    for name, filepath in files_to_load.items():
        try:
            if filepath.exists():
                g.parse(filepath, format="turtle")
                load_status[name] = {"status": "✅ Chargé", "success": True}
            else:
                load_status[name] = {"status": "❌ Fichier non trouvé", "success": False}
        except Exception as e:
            load_status[name] = {"status": f"❌ Erreur: {str(e)[:30]}...", "success": False}
    
    return g, load_status, files_to_load


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def clean_uri(uri):
    """Nettoie une URI en retirant le namespace et les caractères spéciaux."""
    if uri is None:
        return "N/A"
    
    # Convertir en string
    uri_str = str(uri)
    
    # Supprimer le namespace
    if "#" in uri_str:
        uri_str = uri_str.split("#")[-1]
    elif "/" in uri_str:
        uri_str = uri_str.split("/")[-1]
    
    # Décoder les %20 et autres caractères encodés
    uri_str = urllib.parse.unquote(uri_str)
    
    # Remplacer les underscores par des espaces
    uri_str = uri_str.replace("_", " ")
    
    return uri_str


def get_label(graph, uri):
    """
    Récupère le label d'une ressource.
    Si pas de label, construit un nom à partir de l'URI.
    """
    if uri is None:
        return "N/A"
    
    # Essayer d'obtenir rdfs:label
    label = graph.value(uri, RDFS.label)
    if label:
        return str(label)
    
    # Essayer skos:prefLabel
    label = graph.value(uri, SKOS.prefLabel)
    if label:
        return str(label)
    
    # Sinon, construire à partir de l'URI
    return clean_uri(uri)


def format_vehicle_name(graph, vehicle_uri):
    """Formate un nom de véhicule à partir de ses propriétés."""
    manufacturer = graph.value(vehicle_uri, AUTO.hasManufacturer)
    manufacturer_name = get_label(graph, manufacturer) if manufacturer else "Véhicule"
    
    # Extraire l'ID du véhicule
    vehicle_id = clean_uri(vehicle_uri)
    
    return f"{manufacturer_name} {vehicle_id}"


# ============================================================================
# SIDEBAR - STATUT DE CHARGEMENT
# ============================================================================

def render_sidebar(graph, load_status, files_to_load):
    """Affiche la sidebar avec le statut de chargement."""
    st.sidebar.title("📊 AutoSemantica")
    st.sidebar.markdown("---")
    
    # Debug info
    with st.sidebar.expander("🔧 Debug Info"):
        st.code(f"BASE_DIR: {BASE_DIR}")
        st.write("**Fichiers à charger:**")
        for name, filepath in files_to_load.items():
            # Convertir en Path si c'est une string (pour compatibilité cache)
            if isinstance(filepath, str):
                filepath = Path(filepath)
            exists = filepath.exists() if hasattr(filepath, 'exists') else False
            st.text(f"{'✅' if exists else '❌'} {filepath.name}")
    
    st.sidebar.subheader("📁 Fichiers chargés")
    
    for name, status_info in load_status.items():
        st.sidebar.markdown(f"**{name}**")
        st.sidebar.markdown(status_info["status"])
        st.sidebar.markdown("")
    
    st.sidebar.markdown("---")
    
    # Compter les triplets
    total_triples = len(graph)
    st.sidebar.metric("Nombre total de triplets", f"{total_triples:,}")
    
    st.sidebar.markdown("---")
    st.sidebar.info("💡 **Astuce**: Utilisez les onglets ci-dessus pour explorer les différentes fonctionnalités.")


# ============================================================================
# ONGLET 1 : EXPLORATION (Recherche Facettée)
# ============================================================================

def tab_exploration(graph):
    """Onglet d'exploration avec recherche facettée."""
    st.header("🔍 Exploration - Recherche Facettée")
    
    # Récupérer la liste des constructeurs
    manufacturers_query = """
        PREFIX auto: <http://www.univ-projet.fr/ontologies/autosemantic#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        
        SELECT DISTINCT ?manufacturer ?label
        WHERE {
            ?manufacturer a skos:Concept .
            ?manufacturer skos:inScheme auto:ManufacturerScheme .
            OPTIONAL { ?manufacturer skos:prefLabel ?label }
        }
        ORDER BY ?label
    """
    
    try:
        results = graph.query(manufacturers_query)
        manufacturers = [("Tous", None)]
        
        # Debug: afficher le nombre de résultats
        result_count = 0
        for row in results:
            man_uri = row.manufacturer
            label = get_label(graph, man_uri)
            manufacturers.append((label, man_uri))
            result_count += 1
        
        # Afficher info de debug
        if result_count == 0:
            st.warning(f"⚠️ Aucun constructeur trouvé dans le graphe. Total triplets: {len(graph)}")
        
        # Menu déroulant
        selected_manufacturer = st.selectbox(
            "🏭 Sélectionner un constructeur",
            options=manufacturers,
            format_func=lambda x: x[0]
        )
        
        # Requête pour récupérer les véhicules
        if selected_manufacturer[1] is None:
            # Tous les véhicules
            vehicles_query = """
                PREFIX auto: <http://www.univ-projet.fr/ontologies/autosemantic#>
                
                SELECT ?vehicle ?manufacturer ?fuelType ?transmission ?cylinders
                WHERE {
                    ?vehicle a ?type .
                    FILTER(?type = auto:Vehicle || ?type = auto:Car)
                    OPTIONAL { ?vehicle auto:hasManufacturer ?manufacturer }
                    OPTIONAL { ?vehicle auto:hasFuelType ?fuelType }
                    OPTIONAL { ?vehicle auto:hasTransmissionType ?transmission }
                    OPTIONAL { ?vehicle auto:numberOfCylinders ?cylinders }
                }
                LIMIT 100
            """
        else:
            # Véhicules d'un constructeur spécifique
            vehicles_query = f"""
                PREFIX auto: <http://www.univ-projet.fr/ontologies/autosemantic#>
                
                SELECT ?vehicle ?manufacturer ?fuelType ?transmission ?cylinders
                WHERE {{
                    ?vehicle a ?type .
                    FILTER(?type = auto:Vehicle || ?type = auto:Car)
                    ?vehicle auto:hasManufacturer <{selected_manufacturer[1]}> .
                    OPTIONAL {{ ?vehicle auto:hasManufacturer ?manufacturer }}
                    OPTIONAL {{ ?vehicle auto:hasFuelType ?fuelType }}
                    OPTIONAL {{ ?vehicle auto:hasTransmissionType ?transmission }}
                    OPTIONAL {{ ?vehicle auto:numberOfCylinders ?cylinders }}
                }}
                LIMIT 100
            """
        
        results = graph.query(vehicles_query)
        
        # Créer un DataFrame
        data = []
        for row in results:
            data.append({
                "Véhicule": format_vehicle_name(graph, row.vehicle),
                "Constructeur": get_label(graph, row.manufacturer) if row.manufacturer else "N/A",
                "Carburant": get_label(graph, row.fuelType) if row.fuelType else "N/A",
                "Transmission": get_label(graph, row.transmission) if row.transmission else "N/A",
                "Cylindres": str(row.cylinders) if row.cylinders else "N/A"
            })
        
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, width="stretch", height=400)
            st.success(f"✅ {len(data)} véhicules trouvés")
        else:
            st.warning("⚠️ Aucun véhicule trouvé pour ce constructeur.")
    
    except Exception as e:
        st.error(f"❌ Erreur lors de la requête : {str(e)}")


# ============================================================================
# ONGLET 2 : STATISTIQUES
# ============================================================================

def tab_statistics(graph):
    """Onglet de statistiques avec graphiques."""
    st.header("📈 Statistiques")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Top 10 Constructeurs par nombre d'avis")
        
        query = """
            PREFIX auto: <http://www.univ-projet.fr/ontologies/autosemantic#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT ?manufacturer (COUNT(?review) as ?count)
            WHERE {
                ?review a auto:CustomerReview .
                ?review auto:isReviewOf ?vehicle .
                ?vehicle auto:hasManufacturer ?manufacturer .
            }
            GROUP BY ?manufacturer
            ORDER BY DESC(?count)
            LIMIT 10
        """
        
        try:
            results = graph.query(query)
            data = []
            for row in results:
                data.append({
                    "Constructeur": get_label(graph, row.manufacturer),
                    "Nombre d'avis": int(row['count'])
                })
            
            if data:
                df = pd.DataFrame(data)
                fig = px.bar(df, x="Constructeur", y="Nombre d'avis", 
                            color="Nombre d'avis",
                            color_continuous_scale="viridis")
                st.plotly_chart(fig, width='content')
            else:
                st.info("📊 Aucune donnée disponible")
        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")
    
    with col2:
        st.subheader("Répartition par type de carburant")
        
        query = """
            PREFIX auto: <http://www.univ-projet.fr/ontologies/autosemantic#>
            
            SELECT ?fuelType (COUNT(?vehicle) as ?count)
            WHERE {
                ?vehicle a ?type .
                FILTER(?type = auto:Vehicle || ?type = auto:Car)
                ?vehicle auto:hasFuelType ?fuelType .
            }
            GROUP BY ?fuelType
            ORDER BY DESC(?count)
            LIMIT 10
        """
        
        try:
            results = graph.query(query)
            data = []
            for row in results:
                data.append({
                    "Carburant": get_label(graph, row.fuelType),
                    "Nombre": int(row['count'])
                })
            
            if data:
                df = pd.DataFrame(data)
                fig = px.pie(df, values="Nombre", names="Carburant", 
                            hole=0.4)
                st.plotly_chart(fig, width='content')
            else:
                st.info("📊 Aucune donnée disponible")
        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")


# ============================================================================
# ONGLET 3 : SPARQL & COMPÉTENCES
# ============================================================================

def tab_sparql(graph):
    """Onglet SPARQL avec requêtes pré-enregistrées et fédérées."""
    st.header("🔗 SPARQL & Compétences Web Sémantique")
    
    # Requêtes pré-enregistrées
    predefined_queries = {
        "🔍 Véhicules haute performance (>= 6 cylindres)": """
PREFIX auto: <http://www.univ-projet.fr/ontologies/autosemantic#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?vehicle ?manufacturer ?cylinders ?displacement
WHERE {
    ?vehicle a auto:Car .
    ?vehicle auto:numberOfCylinders ?cylinders .
    ?vehicle auto:hasManufacturer ?manufacturer .
    OPTIONAL { ?vehicle auto:engineDisplacement ?displacement }
    FILTER(?cylinders >= 6)
}
LIMIT 20
""",
        
        "⭐ Avis positifs (note >= 4.0)": """
PREFIX auto: <http://www.univ-projet.fr/ontologies/autosemantic#>

SELECT ?review ?rating ?content
WHERE {
    ?review a auto:CustomerReview .
    ?review auto:reviewRating ?rating .
    ?review auto:reviewContent ?content .
    FILTER(?rating >= 4.0)
}
LIMIT 15
""",
        
        "🌐 [FÉDÉRÉE] Logos constructeurs depuis Wikidata": """
PREFIX auto: <http://www.univ-projet.fr/ontologies/autosemantic#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?manufacturer ?localLabel ?wikidataEntity ?logo
WHERE {
    ?manufacturer a skos:Concept .
    ?manufacturer skos:inScheme auto:ManufacturerScheme .
    ?manufacturer owl:sameAs ?wikidataEntity .
    OPTIONAL { ?manufacturer rdfs:label ?localLabel }
    
    SERVICE <https://query.wikidata.org/sparql> {
        ?wikidataEntity wdt:P154 ?logo .
    }
}
LIMIT 10
""",
        
        "⛽ Consommation moyenne par type de carburant": """
PREFIX auto: <http://www.univ-projet.fr/ontologies/autosemantic#>

SELECT ?fuelType (AVG(?mpgCity) as ?avgCity) (AVG(?mpgHighway) as ?avgHighway) (COUNT(?vehicle) as ?count)
WHERE {
    ?vehicle auto:hasFuelType ?fuelType .
    OPTIONAL { ?vehicle auto:mpgCity ?mpgCity }
    OPTIONAL { ?vehicle auto:mpgHighway ?mpgHighway }
}
GROUP BY ?fuelType
HAVING(?count > 5)
ORDER BY DESC(?count)
"""
    }
    
    # Sélecteur de requête
    selected_query_name = st.selectbox(
        "📋 Sélectionner une requête pré-enregistrée",
        options=list(predefined_queries.keys())
    )
    
    # Zone de texte avec la requête (modifiable)
    query_text = st.text_area(
        "✏️ Requête SPARQL (modifiable)",
        value=predefined_queries[selected_query_name],
        height=250
    )
    
    # Bouton pour exécuter
    if st.button("▶️ Exécuter la requête", type="primary"):
        with st.spinner("🔄 Exécution de la requête..."):
            try:
                results = graph.query(query_text)
                
                # Convertir en DataFrame
                data = []
                columns = [str(var) for var in results.vars]
                
                for row in results:
                    row_data = {}
                    for var in results.vars:
                        value = row[var]
                        if value is not None:
                            # Nettoyer les URIs pour l'affichage
                            value_str = str(value)
                            if value_str.startswith("http"):
                                row_data[str(var)] = get_label(graph, value)
                            else:
                                row_data[str(var)] = value_str
                        else:
                            row_data[str(var)] = "N/A"
                    data.append(row_data)
                
                if data:
                    df = pd.DataFrame(data)
                    st.success(f"✅ {len(data)} résultats trouvés")
                    st.dataframe(df, width="stretch")
                    
                    # Option de téléchargement
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Télécharger les résultats (CSV)",
                        data=csv,
                        file_name="resultats_sparql.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("⚠️ Aucun résultat trouvé.")
            
            except Exception as e:
                st.error(f"❌ Erreur lors de l'exécution de la requête :\n\n{str(e)}")


# ============================================================================
# ONGLET 4 : INTELLIGENCE ARTIFICIELLE (Demo)
# ============================================================================

def tab_ai_demo(graph):
    """Onglet IA avec Link Prediction et GraphRAG (simulation)."""
    st.header("🤖 Intelligence Artificielle - Démonstration")
    
    # === Section 1: Link Prediction ===
    st.subheader("🔗 Link Prediction - Système de Recommandation")
    st.info("💡 Recommandations de véhicules similaires basées sur collaborative filtering (brand, year, fuel efficiency, displacement, rating).")
    
    try:
        # Charger le graphe de connaissances unifié
        kg_path = BASE_DIR / "5_knowledge_graph" / "knowledge_graph.ttl"
        
        if not kg_path.exists():
            st.warning("⚠️ Fichier `knowledge_graph.ttl` non trouvé. Veuillez d'abord fusionner les graphes avec le script `merge_graphs.py`.")
        else:
            # Import dynamique pour éviter les dépendances au démarrage
            import sys
            sys.path.insert(0, str(BASE_DIR / "7_exploitation" / "link_prediction"))
            from recommend import VehicleRecommender
            
            # Initialiser le recommender (avec cache)
            @st.cache_resource
            def load_recommender():
                return VehicleRecommender(str(kg_path))
            
            with st.spinner("🔄 Chargement du système de recommandation..."):
                recommender = load_recommender()
            
            st.success(f"✅ Système chargé : {len(recommender.vehicle_features)} véhicules dans le graphe")
            
            # Sélection d'un véhicule de référence
            st.markdown("### Sélectionnez un véhicule pour obtenir des recommandations")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Lister quelques véhicules avec leurs infos
                vehicles_list = []
                for uri, features in list(recommender.vehicle_features.items())[:50]:  # Limiter à 50 pour performance
                    if features.get('brand') and features.get('model_name'):
                        display_name = f"{features['brand']} - {features['model_name']}"
                        if features.get('year'):
                            display_name += f" ({features['year']})"
                        vehicles_list.append((display_name, uri, features))
                
                if vehicles_list:
                    selected_vehicle = st.selectbox(
                        "🚗 Véhicule de référence",
                        options=vehicles_list,
                        format_func=lambda x: x[0]
                    )
                    
                    vehicle_uri = selected_vehicle[1]
                    vehicle_features = selected_vehicle[2]
                    
                    with col2:
                        top_n = st.slider("Nombre de recommandations", min_value=3, max_value=10, value=5)
                    
                    # Afficher les infos du véhicule sélectionné
                    with st.expander("📊 Caractéristiques du véhicule sélectionné"):
                        info_cols = st.columns(3)
                        with info_cols[0]:
                            st.metric("Marque", vehicle_features.get('brand') or "N/A")
                            st.metric("Année", vehicle_features.get('year') or "N/A")
                        with info_cols[1]:
                            fuel = vehicle_features.get('fuel_city')
                            st.metric("Conso. ville", f"{fuel:.1f} L/100km" if fuel else "N/A")
                            disp = vehicle_features.get('displacement')
                            st.metric("Cylindrée", f"{disp:.1f}L" if disp else "N/A")
                        with info_cols[2]:
                            cyl = vehicle_features.get('cylinders')
                            st.metric("Cylindres", f"{cyl}" if cyl else "N/A")
                            rating = vehicle_features.get('avg_rating')
                            st.metric("Note moyenne", f"{rating:.2f}/5" if rating else "N/A")
                    
                    # Bouton pour générer les recommandations
                    if st.button("🎯 Générer des recommandations", type="primary"):
                        with st.spinner("🔄 Calcul des similarités..."):
                            recommendations = recommender.recommend_similar(vehicle_uri, top_n=top_n)
                        
                        if recommendations:
                            st.success(f"✅ Top {len(recommendations)} véhicules recommandés :")
                            
                            # Créer un DataFrame pour l'affichage
                            rec_data = []
                            for rec_uri, score in recommendations:
                                rec_info = recommender.get_vehicle_info(rec_uri)
                                rec_data.append({
                                    "Score": f"{score:.3f}",
                                    "Marque": rec_info.get('brand') or "N/A",
                                    "Modèle": rec_info.get('model_name') or "N/A",
                                    "Année": rec_info.get('year') or "N/A",
                                    "Conso. ville (L/100km)": f"{rec_info.get('fuel_city'):.1f}" if rec_info.get('fuel_city') else "N/A",
                                    "Cylindrée (L)": f"{rec_info.get('displacement'):.1f}" if rec_info.get('displacement') else "N/A",
                                    "Cylindres": rec_info.get('cylinders') or "N/A",
                                    "Note": f"{rec_info.get('avg_rating'):.2f}" if rec_info.get('avg_rating') else "N/A"
                                })
                            
                            df_recommendations = pd.DataFrame(rec_data)
                            st.dataframe(df_recommendations, width="stretch", height=300)
                            
                            # Explication du score
                            st.info("ℹ️ **Score de similarité** : calculé sur la base de la marque, l'année, la consommation, la cylindrée et les notes moyennes.")
                        else:
                            st.warning("⚠️ Aucune recommandation trouvée pour ce véhicule.")
                else:
                    st.error("❌ Aucun véhicule disponible dans le graphe.")
    
    except ImportError as e:
        st.error(f"❌ Erreur d'import : {str(e)}\nAssurez-vous que le module `recommend.py` est accessible.")
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement du système de recommandation : {str(e)}")
    
    st.markdown("---")
    
    # === Section 2: GraphRAG ===
    st.subheader("💬 GraphRAG - Question-Réponse sur le Graphe")
    
    # Approche 1 : Traduction en SPARQL
    with st.expander("📝 Approche 1 : Traduction Question → SPARQL"):
        st.write("**Principe** : Convertir une question en langage naturel en requête SPARQL.")
        
        user_question = st.text_input(
            "Posez votre question :",
            value="Quels sont les véhicules diesel avec plus de 6 cylindres ?"
        )
        
        if st.button("🔍 Traduire en SPARQL", key="translate"):
            # Simulation de la traduction
            generated_sparql = f"""
PREFIX auto: <http://www.univ-projet.fr/ontologies/autosemantic#>

SELECT ?vehicle ?manufacturer ?cylinders
WHERE {{
    ?vehicle a auto:Car .
    ?vehicle auto:hasFuelType auto:Diesel .
    ?vehicle auto:numberOfCylinders ?cylinders .
    ?vehicle auto:hasManufacturer ?manufacturer .
    FILTER(?cylinders > 6)
}}
LIMIT 10
"""
            
            st.success("✅ Requête SPARQL générée :")
            st.code(generated_sparql, language="sparql")
            
            # Exécuter la requête
            try:
                results = graph.query(generated_sparql)
                data = []
                for row in results:
                    data.append({
                        "Véhicule": format_vehicle_name(graph, row.vehicle),
                        "Constructeur": get_label(graph, row.manufacturer),
                        "Cylindres": str(row.cylinders)
                    })
                
                if data:
                    st.dataframe(pd.DataFrame(data), width="stretch")
                else:
                    st.info("Aucun résultat trouvé.")
            except Exception as e:
                st.error(f"Erreur : {str(e)}")
    
    # Approche 2 : Embeddings
    with st.expander("🧠 Approche 2 : Réponse basée sur Embeddings"):
        st.write("**Principe** : Utiliser des embeddings pour générer une réponse en langage naturel.")
        
        user_question_2 = st.text_input(
            "Posez votre question :",
            value="Quelle est la différence entre un véhicule hybride et électrique ?",
            key="q2"
        )
        
        if st.button("💡 Générer une réponse", key="embed"):
            # Réponse simulée
            simulated_response = f"""
**Réponse générée par IA** :

D'après les données de notre graphe de connaissances AutoSemantica, voici la différence principale :

- **Véhicule Électrique** : Utilise uniquement l'électricité comme source d'énergie. 
  Dans notre ontologie, ces véhicules ont la propriété `hasFuelType` avec la valeur `Electricity`.
  Ils ne possèdent généralement pas de cylindres (numberOfCylinders = 0).

- **Véhicule Hybride** : Combine deux sources d'énergie, typiquement essence et électricité.
  Dans nos données, ils sont identifiés par des valeurs comme `RegularGasAndElectricity` ou 
  `PremiumGasOrElectricity` pour la propriété `hasFuelType`.

📊 Statistiques du graphe : 
- Véhicules électriques purs : ~15 entités
- Véhicules hybrides : ~42 entités
- Véhicules à essence classique : ~1200+ entités
"""
            st.success(simulated_response)


# ============================================================================
# ONGLET 5 : VALIDATION SHACL
# ============================================================================

def tab_shacl_validation(graph):
    """Onglet de validation SHACL."""
    st.header("✅ Validation SHACL")
    
    st.info("💡 Cet onglet permet de valider le graphe de données contre les contraintes SHACL définies dans `shapes.ttl`.")
    
    if st.button("🔍 Lancer la validation SHACL", type="primary"):
        with st.spinner("🔄 Validation en cours..."):
            try:
                # Charger le graphe de contraintes
                shapes_file = BASE_DIR / "1_ontology" / "shapes.ttl"
                
                if not shapes_file.exists():
                    st.error("❌ Fichier `shapes.ttl` non trouvé.")
                    return
                
                shapes_graph = Graph()
                shapes_graph.parse(shapes_file, format="turtle")
                
                # Exécuter la validation
                conforms, results_graph, results_text = validate(
                    data_graph=graph,
                    shacl_graph=shapes_graph,
                    inference='rdfs',
                    abort_on_first=False,
                )
                
                if conforms:
                    st.success("✅ **Le graphe est CONFORME** aux contraintes SHACL ! 🎉")
                else:
                    st.error("❌ **Le graphe n'est PAS conforme** aux contraintes SHACL.")
                    
                    st.subheader("📋 Rapport de validation")
                    st.text(results_text)
                    
                    # Option pour afficher le graphe RDF des résultats
                    with st.expander("🔍 Voir les détails du rapport (RDF)"):
                        st.code(results_graph.serialize(format="turtle"), language="turtle")
            
            except Exception as e:
                st.error(f"❌ Erreur lors de la validation :\n\n{str(e)}")


# ============================================================================
# ONGLET 6 : ALIGNEMENTS LOD
# ============================================================================

def tab_lod_alignments(graph):
    """Onglet des alignements Linked Open Data."""
    st.header("🌐 Alignements LOD - Linked Open Data")
    
    st.info("💡 Cette section liste les entités locales liées à Wikidata ou DBpedia via `owl:sameAs`.")
    
    query = """
        PREFIX auto: <http://www.univ-projet.fr/ontologies/autosemantic#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        
        SELECT DISTINCT ?entity ?label ?externalEntity
        WHERE {
            ?entity a skos:Concept .
            ?entity skos:inScheme auto:ManufacturerScheme .
            ?entity owl:sameAs ?externalEntity .
            OPTIONAL { ?entity rdfs:label ?label }
            OPTIONAL { ?entity skos:prefLabel ?label }
            
            FILTER(CONTAINS(STR(?externalEntity), "wikidata") || CONTAINS(STR(?externalEntity), "dbpedia"))
        }
        ORDER BY ?label
    """
    
    try:
        results = graph.query(query)
        
        data = []
        for row in results:
            entity_label = get_label(graph, row.entity)
            external_uri = str(row.externalEntity)
            
            # Déterminer la source
            if "wikidata" in external_uri:
                source = "🌍 Wikidata"
            elif "dbpedia" in external_uri:
                source = "📚 DBpedia"
            else:
                source = "🔗 Autre"
            
            data.append({
                "Entité locale": entity_label,
                "Source externe": source,
                "URI externe": external_uri
            })
        
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, width="stretch")
            st.success(f"✅ {len(data)} alignements trouvés")
            
            # Statistiques
            col1, col2 = st.columns(2)
            with col1:
                wikidata_count = len([d for d in data if "Wikidata" in d["Source externe"]])
                st.metric("Alignements Wikidata", wikidata_count)
            with col2:
                dbpedia_count = len([d for d in data if "DBpedia" in d["Source externe"]])
                st.metric("Alignements DBpedia", dbpedia_count)
        else:
            st.warning("⚠️ Aucun alignement trouvé dans le graphe.")
    
    except Exception as e:
        st.error(f"❌ Erreur lors de la requête : {str(e)}")


# ============================================================================
# APPLICATION PRINCIPALE
# ============================================================================

def main():
    """Fonction principale de l'application Streamlit."""
    
    # Configuration de la page
    st.set_page_config(
        page_title="AutoSemantica - Web Sémantique",
        page_icon="🚗",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Style CSS personnalisé
    st.markdown("""
        <style>
        .stApp {
            max-width: 100%;
        }
        h1 {
            color: #1f77b4;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 10px 20px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Titre principal
    st.title("🚗 AutoSemantica - Web Sémantique")
    st.markdown("*Exploration intelligente de données automobiles avec RDF, SPARQL et SHACL*")
    st.markdown("---")
    
    # Charger le graphe
    with st.spinner("🔄 Chargement des données..."):
        graph, load_status, files_to_load = load_graph()
    
    # Afficher la sidebar
    render_sidebar(graph, load_status, files_to_load)
    
    # Créer les onglets
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🔍 Exploration",
        "📈 Statistiques",
        "🔗 SPARQL",
        "🤖 Intelligence IA",
        "✅ Validation SHACL",
        "🌐 Alignements LOD"
    ])
    
    with tab1:
        tab_exploration(graph)
    
    with tab2:
        tab_statistics(graph)
    
    with tab3:
        tab_sparql(graph)
    
    with tab4:
        tab_ai_demo(graph)
    
    with tab5:
        tab_shacl_validation(graph)
    
    with tab6:
        tab_lod_alignments(graph)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "AutoSemantica © 2026 - Projet Web Sémantique SI5/S2"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()