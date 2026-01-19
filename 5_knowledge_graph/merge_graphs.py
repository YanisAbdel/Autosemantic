import logging
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent

# Define input files - DATA + ALIGNMENTS
DATA_FILES = [
    PROJECT_ROOT / "3_data_extraction" / "rml_mapping" / "output.ttl",       # CSV data
    PROJECT_ROOT / "3_data_extraction" / "web_extraction" / "kg_from_web_ollama.ttl",  # Web data
    PROJECT_ROOT / "4_alignment" / "alignments_instances.ttl",               # ALIGNMENTS
]

# Output file (data only, ontology kept separate)
OUTPUT_FILE = Path(__file__).parent / "knowledge_graph.ttl"


def merge_graphs(input_files, output_file):
    """Merge multiple RDF files into a single graph."""
    
    logging.info("Creating merged knowledge graph...")
    
    # Create a new graph
    merged_graph = Graph()
    
    # Bind common namespaces
    merged_graph.bind("auto", Namespace("http://www.univ-projet.fr/ontologies/autosemantic#"))
    merged_graph.bind("dbo", Namespace("http://dbpedia.org/ontology/"))
    merged_graph.bind("dbr", Namespace("http://dbpedia.org/resource/"))
    merged_graph.bind("schema", Namespace("https://schema.org/"))
    merged_graph.bind("wd", Namespace("http://www.wikidata.org/entity/"))
    merged_graph.bind("owl", OWL)
    merged_graph.bind("rdf", RDF)
    merged_graph.bind("rdfs", RDFS)
    merged_graph.bind("sh", Namespace("http://www.w3.org/ns/shacl#"))
    merged_graph.bind("skos", Namespace("http://www.w3.org/2004/02/skos/core#"))
    
    # Load and merge each file
    total_triples = 0
    for file_path in input_files:
        if file_path.exists():
            logging.info(f"Loading: {file_path.name}")
            try:
                temp_graph = Graph()
                temp_graph.parse(str(file_path), format="turtle")
                
                # Add all triples to merged graph
                for triple in temp_graph:
                    merged_graph.add(triple)
                
                triples_count = len(temp_graph)
                total_triples += triples_count
                logging.info(f"  ✓ Added {triples_count:,} triples from {file_path.name}")
                
            except Exception as e:
                logging.error(f"  ✗ Failed to load {file_path.name}: {e}")
        else:
            logging.warning(f"  ⚠ File not found: {file_path.name}")
    
    # Save merged graph
    logging.info(f"\nSaving merged graph to: {output_file.name}")
    merged_graph.serialize(destination=str(output_file), format="turtle")
    
    # Statistics
    final_count = len(merged_graph)
    logging.info(f"\n{'='*60}")
    logging.info(f"MERGE COMPLETE")
    logging.info(f"{'='*60}")
    logging.info(f"Total triples loaded: {total_triples:,}")
    logging.info(f"Final graph size: {final_count:,} triples")
    
    if final_count < total_triples:
        duplicates = total_triples - final_count
        logging.info(f"Duplicates removed: {duplicates:,}")
    
    # Count by type
    count_classes = len(list(merged_graph.subjects(RDF.type, OWL.Class)))
    count_properties = len(list(merged_graph.subjects(RDF.type, OWL.ObjectProperty))) + \
                      len(list(merged_graph.subjects(RDF.type, OWL.DatatypeProperty)))
    count_individuals = len(set(merged_graph.subjects(RDF.type, None))) - count_classes - count_properties
    count_sameAs = len(list(merged_graph.triples((None, OWL.sameAs, None))))
    count_equivalent = len(list(merged_graph.triples((None, OWL.equivalentClass, None)))) + \
                      len(list(merged_graph.triples((None, OWL.equivalentProperty, None))))
    
    logging.info(f"\nGraph composition:")
    logging.info(f"  - Classes: {count_classes}")
    logging.info(f"  - Properties: {count_properties}")
    logging.info(f"  - Individuals: {count_individuals}")
    logging.info(f"  - owl:sameAs links: {count_sameAs}")
    logging.info(f"  - Equivalence relations: {count_equivalent}")
    logging.info(f"{'='*60}\n")
    
    return merged_graph


if __name__ == "__main__":
    logging.info("=" * 60)
    logging.info("CREATING KNOWLEDGE GRAPH")
    logging.info("=" * 60)
    
    graph = merge_graphs(DATA_FILES, OUTPUT_FILE)
    
    logging.info(f"✓ Knowledge graph saved to: {OUTPUT_FILE}\n")
    
    logging.info("=" * 60)
    logging.info("NOTE:")
    logging.info("  - Ontology (autosemantic.ttl) is kept separate")
    logging.info("  - Data conforms to the ontology model")
    logging.info("  - Alignments included for federated queries")
    logging.info("  - Use shapes.ttl for SHACL validation")
    logging.info("=" * 60)
