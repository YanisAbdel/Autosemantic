import streamlit as st
from rdflib import Graph, Namespace
import pandas as pd
import urllib.parse

# --- CONFIGURATION ---
st.set_page_config(page_title="AutoSemantic", page_icon="🚗", layout="wide")
AUTO = Namespace("http://www.univ-projet.fr/ontologies/autosemantic#")

# --- CHARGEMENT DU GRAPHE ---
@st.cache_resource
def load_graph():
    g = Graph()
    # On charge les deux fichiers
    files = ["autosemantic.ttl", "output.ttl"]
    print("\n--- CHARGEMENT ---")
    for f in files:
        try:
            g.parse(f, format="turtle")
            print(f"✅ {f} chargé.")
        except Exception as e:
            st.error(f"Erreur chargement {f}: {e}")
    print(f"📊 Total: {len(g)} triplets")
    return g

g = load_graph()

# --- NETTOYAGE ---
def clean_uri(uri):
    if not uri: return "N/A"
    text = str(uri).split('#')[-1].split('/')[-1]
    return urllib.parse.unquote(text).replace('_', ' ')

# --- SIDEBAR ---
st.sidebar.title("🔍 Filtres")

# Récupération des fabricants
query_manufacturers = """
    PREFIX : <http://www.univ-projet.fr/ontologies/autosemantic#>
    SELECT DISTINCT ?m WHERE { ?car :hasManufacturer ?m . } ORDER BY ?m
"""
res_manuf = g.query(query_manufacturers)

# Dictionnaire { Nom_Propre : URI_Complete }
manuf_map = {}
for row in res_manuf:
    manuf_map[clean_uri(row.m)] = str(row.m)

liste_manuf = sorted(list(manuf_map.keys()))
liste_manuf.insert(0, "Tous")
choix_manuf = st.sidebar.selectbox("Fabricant", liste_manuf)

# --- NAVIGATION ---
tab1, tab2 = st.tabs(["🚙 Recherche Véhicules", "📊 Statistiques"])

# === ONGLET 1 : RECHERCHE ===
with tab1:
    st.header("Explorateur de Véhicules")
    
    # Filtre Fabricant
    filter_clause = ""
    if choix_manuf != "Tous":
        target_uri = manuf_map[choix_manuf]
        filter_clause = f'FILTER(STR(?manufURI) = "{target_uri}")'

    # REQUÊTE ROBUSTE (Tout est OPTIONAL sauf le type)
    query_cars = f"""
        PREFIX : <http://www.univ-projet.fr/ontologies/autosemantic#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?carURI ?label ?manufURI ?cylinders ?displacement ?transURI ?fuelURI
        WHERE {{
            ?carURI a :Car .
            
            # Label est maintenant OPTIONNEL !
            OPTIONAL {{ ?carURI rdfs:label ?label }}
            
            OPTIONAL {{ ?carURI :hasManufacturer ?manufURI }}
            OPTIONAL {{ ?carURI :numberOfCylinders ?cylinders }}
            OPTIONAL {{ ?carURI :engineDisplacement ?displacement }}
            OPTIONAL {{ ?carURI :hasTransmissionType ?transURI }}
            OPTIONAL {{ ?carURI :hasFuelType ?fuelURI }}
            
            {filter_clause}
        }}
        LIMIT 200
    """
    
    if st.button("Lancer la recherche", key="btn_search"):
        results = g.query(query_cars)
        
        data = []
        for row in results:
            # Gestion du nom manquant : on prend l'ID de l'URI
            if row.label:
                nom_vehicule = str(row.label)
            else:
                # Fallback : on prend la fin de l'URI (ex: vehicle/2405 -> "Véhicule 2405")
                nom_vehicule = f"Véhicule {str(row.carURI).split('/')[-1]}"

            data.append({
                "Véhicule": nom_vehicule,
                "Fabricant": clean_uri(row.manufURI),
                "Cylindres": str(row.cylinders) if row.cylinders else "-",
                "Cylindrée": str(row.displacement) if row.displacement else "-",
                "Transmission": clean_uri(row.transURI),
                "Carburant": clean_uri(row.fuelURI)
            })
        
        if data:
            st.dataframe(pd.DataFrame(data), width='stretch')
            st.success(f"{len(data)} véhicules trouvés.")
        else:
            st.warning("Aucun résultat.")

# === ONGLET 2 : STATS ===
with tab2:
    st.header("Analyse")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Top Fabricants (par Avis)")
        q_stats = """
            PREFIX : <http://www.univ-projet.fr/ontologies/autosemantic#>
            SELECT ?mURI (COUNT(?rev) as ?nb) WHERE {
                ?rev a :CustomerReview ; :isReviewOf ?v .
                ?v :hasManufacturer ?mURI .
            } GROUP BY ?mURI ORDER BY DESC(?nb) LIMIT 10
        """
        try:
            res = g.query(q_stats)
            df_stats = pd.DataFrame([
                {"Fabricant": clean_uri(r.mURI), "Avis": int(r.nb)} for r in res
            ])
            if not df_stats.empty:
                st.bar_chart(df_stats.set_index("Fabricant"))
            else:
                st.info("Pas assez de données pour les stats.")
        except: st.write("Calcul impossible.")

    with col2:
        st.subheader("Volumétrie")
        st.metric("Total Triplets", len(g))