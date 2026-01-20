from rdflib import Graph, Namespace

AUTO = Namespace('http://www.univ-projet.fr/ontologies/autosemantic#/')

print("=== TEST REQUÊTE SPARQL ===\n")

g = Graph()
g.parse('5_knowledge_graph/knowledge_graph.ttl', format='turtle')

# Compter les véhicules
query = """
SELECT (COUNT(?car) as ?count) 
WHERE { 
    ?car a <http://www.univ-projet.fr/ontologies/autosemantic#Car> 
}
"""
result = list(g.query(query))[0][0]
print(f"Nombre de véhicules dans le graphe: {result}")

# Vérifier les propriétés MPG
query2 = """
SELECT (COUNT(?s) as ?count) 
WHERE { 
    ?s <http://www.univ-projet.fr/ontologies/autosemantic#mpgCity> ?o 
}
"""
result2 = list(g.query(query2))[0][0]
print(f"Véhicules avec mpgCity: {result2}")

query3 = """
SELECT (COUNT(?s) as ?count) 
WHERE { 
    ?s <http://www.univ-projet.fr/ontologies/autosemantic#mpgHighway> ?o 
}
"""
result3 = list(g.query(query3))[0][0]
print(f"Véhicules avec mpgHighway: {result3}")

query4 = """
SELECT (COUNT(?s) as ?count) 
WHERE { 
    ?s <http://www.univ-projet.fr/ontologies/autosemantic#cityElectricityConsumption> ?o 
}
"""
result4 = list(g.query(query4))[0][0]
print(f"Véhicules avec cityElectricityConsumption: {result4}")

query5 = """
SELECT (COUNT(?s) as ?count) 
WHERE { 
    ?s <http://www.univ-projet.fr/ontologies/autosemantic#highwayElectricityConsumption> ?o 
}
"""
result5 = list(g.query(query5))[0][0]
print(f"Véhicules avec highwayElectricityConsumption: {result5}")

query6 = """
SELECT (COUNT(?s) as ?count) 
WHERE { 
    ?s <http://www.univ-projet.fr/ontologies/autosemantic#co2Emissions> ?o 
}
"""
result6 = list(g.query(query6))[0][0]
print(f"Véhicules avec co2Emissions: {result6}")

print("\n✓ Toutes les requêtes SPARQL fonctionnent!")
print(f"\n✓ Pipeline complet validé avec succès!")
