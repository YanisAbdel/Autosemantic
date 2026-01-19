
import logging
from pathlib import Path
from rdflib import Graph
import owlrl

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

PROJECT_ROOT = Path(__file__).parent

# Files
ONTOLOGY_FILE = PROJECT_ROOT / "autosemantic.ttl"
SHAPES_FILE = PROJECT_ROOT / "shapes.ttl"
DATA_FILE = PROJECT_ROOT / "knowledge_graph.ttl"


def validate_syntax(file_path):
    """Validate RDF syntax."""
    logging.info(f"\n{'='*60}")
    logging.info(f"VALIDATING SYNTAX: {file_path.name}")
    logging.info(f"{'='*60}")
    
    try:
        g = Graph()
        g.parse(str(file_path), format="turtle")
        logging.info(f"✓ Valid RDF syntax ({len(g):,} triples)")
        return True, g
    except Exception as e:
        logging.error(f"✗ Syntax error: {e}")
        return False, None


def validate_shacl(data_file, shapes_file, ontology_file):
    """Validate data against SHACL shapes."""
    logging.info(f"\n{'='*60}")
    logging.info(f"VALIDATING SHACL CONSTRAINTS")
    logging.info(f"{'='*60}")
    
    try:
        from pyshacl import validate
        
        conforms, results_graph, results_text = validate(
            data_graph=str(data_file),
            shacl_graph=str(shapes_file),
            ont_graph=str(ontology_file),
            inference='rdfs',
            abort_on_first=False,
            allow_infos=True,
            allow_warnings=True
        )
        
        if conforms:
            logging.info("✓ All SHACL constraints satisfied")
        else:
            logging.warning("✗ SHACL validation failures:")
            print(results_text)
        
        return conforms
        
    except ImportError:
        logging.warning("⚠ pyshacl not installed. Run: pip install pyshacl")
        return None
    except Exception as e:
        logging.error(f"✗ SHACL validation error: {e}")
        return False


def apply_reasoning(graph):
    """Apply OWL-RL reasoning."""
    logging.info(f"\n{'='*60}")
    logging.info(f"APPLYING OWL-RL REASONING")
    logging.info(f"{'='*60}")
    
    try:
        initial_size = len(graph)
        logging.info(f"Initial triples: {initial_size:,}")
        
        # Apply RDFS + OWL-RL reasoning
        owlrl.DeductiveClosure(owlrl.RDFS_OWLRL_Semantics).expand(graph)
        
        final_size = len(graph)
        inferred = final_size - initial_size
        
        logging.info(f"Final triples: {final_size:,}")
        logging.info(f"✓ Inferred {inferred:,} new triples")
        
        return True
        
    except ImportError:
        logging.warning("⚠ owlrl not installed. Run: pip install owlrl")
        return None
    except Exception as e:
        logging.error(f"✗ Reasoning error: {e}")
        return False


def main():
    logging.info("="*60)
    logging.info("AUTOSEMANTIC ONTOLOGY VALIDATION")
    logging.info("="*60)
    
    # 1. Validate syntax
    results = {}
    
    for file in [ONTOLOGY_FILE, SHAPES_FILE, DATA_FILE]:
        if file.exists():
            valid, graph = validate_syntax(file)
            results[file.name] = {"syntax": valid, "graph": graph}
        else:
            logging.warning(f"⚠ File not found: {file.name}")
    
    # 2. SHACL validation
    if DATA_FILE.exists() and SHAPES_FILE.exists():
        shacl_valid = validate_shacl(DATA_FILE, SHAPES_FILE, ONTOLOGY_FILE)
        results["shacl"] = shacl_valid
    
    # 3. Apply reasoning to ontology
    if ONTOLOGY_FILE.exists() and results.get("autosemantic.ttl", {}).get("graph"):
        onto_graph = results["autosemantic.ttl"]["graph"]
        reasoning_ok = apply_reasoning(onto_graph)
        results["reasoning"] = reasoning_ok
        
        # Save inferred ontology
        if reasoning_ok:
            output_file = PROJECT_ROOT / "autosemantic_inferred.ttl"
            onto_graph.serialize(destination=str(output_file), format="turtle")
            logging.info(f"✓ Inferred ontology saved to: {output_file.name}")
    
    # Summary
    logging.info(f"\n{'='*60}")
    logging.info("VALIDATION SUMMARY")
    logging.info(f"{'='*60}")
    
    all_valid = all(
        v.get("syntax", False) if isinstance(v, dict) else v 
        for v in results.values() if v is not None
    )
    
    if all_valid:
        logging.info("✓ All validations passed!")
    else:
        logging.warning("⚠ Some validations failed. See details above.")
    
    return all_valid


if __name__ == "__main__":
    main()
