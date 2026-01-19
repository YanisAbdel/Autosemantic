from rdflib import Graph
import os

# Chemin vers le fichier
ttl_file = "output.ttl"

print(f"--- DÉBUT DU DIAGNOSTIC ---")
print(f"📂 Recherche du fichier : {ttl_file}")

if not os.path.exists(ttl_file):
    print(f"❌ ERREUR : Le fichier '{ttl_file}' n'existe pas !")
    print("   -> Vérifie que tu l'as bien généré avec 'python -m morph_kgc graph/config.ini'")
    exit()

g = Graph()
try:
    print("⏳ Chargement du graphe en cours...")
    g.parse(ttl_file, format="turtle")
    print(f"✅ Graphe chargé avec succès : {len(g)} triplets.")
except Exception as e:
    print(f"❌ ERREUR DE LECTURE : {e}")
    exit()

# 1. Vérification des Manufacturers (URIs brutes)
print("\n--- 1. ANALYSE DES CONSTRUCTEURS (Top 5) ---")
q = """
PREFIX : <http://www.univ-projet.fr/ontologies/autosemantic#>
SELECT DISTINCT ?m WHERE { 
    ?car :hasManufacturer ?m . 
} LIMIT 5
"""
results = g.query(q)

if len(results) == 0:
    print("❌ AIE : Aucun constructeur trouvé ! Le mapping a échoué ou le prédicat est faux.")
    print("   -> Je cherche n'importe quel triplet pour voir à quoi ça ressemble...")
    # On affiche 3 triplets au hasard pour voir la structure
    for s, p, o in g.query("SELECT * WHERE { ?s ?p ?o } LIMIT 3"):
        print(f"   Hasard: {s} \n           -> {p} \n           -> {o}")
else:
    for row in results:
        # On affiche l'URI brute entre crochets pour bien voir les espaces éventuels
        print(f"URI trouvée : <{row.m}>")

# 2. Vérification des Voitures liées
print("\n--- 2. TEST DE RECUPERATION VOITURE ---")
# On prend le premier constructeur trouvé pour tester
if len(results) > 0:
    first_manuf = list(results)[0].m
    print(f"Test avec le constructeur : <{first_manuf}>")
    
    q_car = f"""
    PREFIX : <http://www.univ-projet.fr/ontologies/autosemantic#>
    SELECT ?label WHERE {{ 
        ?car :hasManufacturer <{first_manuf}> ;
             rdfs:label ?label .
    }} LIMIT 3
    """
    res_car = g.query(q_car)
    if len(res_car) == 0:
        print("⚠️ Aucune voiture trouvée pour ce constructeur exact.")
    else:
        print("✅ Voitures trouvées :")
        for row in res_car:
            print(f"   - {row.label}")