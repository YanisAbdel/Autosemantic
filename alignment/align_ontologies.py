"""Align AutoSemantic ontology with external vocabularies (DBpedia, Schema.org, Wikidata).

This script creates alignments for:
- Classes (owl:equivalentClass)
- Properties (owl:equivalentProperty)
- Instances/Resources (owl:sameAs)
"""

import argparse
import json
import logging
import time
from typing import Dict, List, Tuple
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef, Literal


# Namespaces
AUTO = Namespace("http://www.univ-projet.fr/ontologies/autosemantic#")
DBO = Namespace("http://dbpedia.org/ontology/")
DBR = Namespace("http://dbpedia.org/resource/")
SCHEMA = Namespace("https://schema.org/")
WD = Namespace("http://www.wikidata.org/entity/")
WDT = Namespace("http://www.wikidata.org/prop/direct/")

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
DBPEDIA_SPARQL = "https://dbpedia.org/sparql"
USER_AGENT = "AutosemanticAligner/2.0 (https://www.univ-projet.fr/)"


# ============================================================================
# CLASS AND PROPERTY ALIGNMENTS (Manual mappings)
# ============================================================================

CLASS_ALIGNMENTS = {
    AUTO.Vehicle: [
        (DBO.MeanOfTransportation, "DBpedia"),
        (SCHEMA.Vehicle, "Schema.org"),
    ],
    AUTO.Car: [
        (DBO.Automobile, "DBpedia"),
        (SCHEMA.Car, "Schema.org"),
    ],
    AUTO.Manufacturer: [
        (DBO.Company, "DBpedia"),
        (SCHEMA.Organization, "Schema.org"),
        (SCHEMA.Brand, "Schema.org"),
    ],
    AUTO.CustomerReview: [
        (SCHEMA.Review, "Schema.org"),
    ],
}

PROPERTY_ALIGNMENTS = {
    AUTO.hasManufacturer: [
        (DBO.manufacturer, "DBpedia"),
        (SCHEMA.manufacturer, "Schema.org"),
    ],
    AUTO.hasFuelType: [
        (SCHEMA.fuelType, "Schema.org"),
    ],
    AUTO.hasTransmissionType: [
        (SCHEMA.vehicleTransmission, "Schema.org"),
    ],
    AUTO.numberOfCylinders: [
        (DBO.numberOfCylinders, "DBpedia"),
    ],
    AUTO.engineDisplacement: [
        (DBO.displacement, "DBpedia"),
    ],
    AUTO.reviewRating: [
        (SCHEMA.ratingValue, "Schema.org"),
    ],
    AUTO.reviewContent: [
        (SCHEMA.reviewBody, "Schema.org"),
    ],
    AUTO.reviewDate: [
        (SCHEMA.datePublished, "Schema.org"),
    ],
}


# ============================================================================
# WIKIDATA SEARCH
# ============================================================================

def search_wikidata(label: str, language: str = "en", limit: int = 5) -> List[dict]:
    """Search Wikidata entities by label."""
    params = {
        "action": "wbsearchentities",
        "format": "json",
        "language": language,
        "search": label,
        "limit": limit,
    }
    url = f"{WIKIDATA_API}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": USER_AGENT})
    
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.load(response)
        return payload.get("search", [])
    except Exception as e:
        logging.warning(f"Wikidata search failed for '{label}': {e}")
        return []


def choose_best_wikidata_match(candidates: List[dict], label: str, hints: List[str] = None) -> dict:
    """Choose the best Wikidata candidate based on label match and description hints."""
    if not candidates:
        return None
    
    label_norm = label.lower()
    hints = hints or []
    
    # Exact label match
    for candidate in candidates:
        if candidate.get("label", "").lower() == label_norm:
            return candidate
    
    # Description contains hints
    if hints:
        for candidate in candidates:
            description = (candidate.get("description") or "").lower()
            if any(hint.lower() in description for hint in hints):
                return candidate
    
    # Return first result
    return candidates[0]


# ============================================================================
# DBPEDIA SEARCH
# ============================================================================

def search_dbpedia_resource(label: str) -> str:
    """Search DBpedia resource by label. Returns DBpedia URI or None."""
    # Try direct resource lookup
    resource_uri = f"http://dbpedia.org/resource/{quote(label.replace(' ', '_'))}"
    
    # Simple check: try to fetch the resource
    try:
        request = Request(resource_uri, headers={"Accept": "application/rdf+xml", "User-Agent": USER_AGENT})
        with urlopen(request, timeout=10) as response:
            if response.status == 200:
                return resource_uri
    except:
        pass
    
    return None


# ============================================================================
# INSTANCE ALIGNMENT
# ============================================================================

def align_manufacturers(graph: Graph, cache: Dict) -> List[Tuple]:
    """Align manufacturer instances with Wikidata and DBpedia."""
    alignments = []
    
    for subject in graph.subjects(RDF.type, AUTO.Manufacturer):
        label = _get_label(graph, subject)
        
        # Check cache
        cache_key = f"manufacturer_{label}"
        if cache_key in cache:
            for uri in cache[cache_key]:
                alignments.append((subject, URIRef(uri), "cached"))
            continue
        
        matched = []
        
        # Search Wikidata
        wd_candidates = search_wikidata(label, hints=["automobile manufacturer", "car manufacturer", "automaker"])
        wd_match = choose_best_wikidata_match(wd_candidates, label, hints=["automobile", "car", "manufacturer"])
        if wd_match:
            qid = wd_match.get("id")
            wd_uri = f"http://www.wikidata.org/entity/{qid}"
            alignments.append((subject, URIRef(wd_uri), "wikidata"))
            matched.append(wd_uri)
            logging.info(f"  Wikidata: {label} -> {qid} ({wd_match.get('description', '')})")
        
        # Search DBpedia
        dbp_uri = search_dbpedia_resource(label)
        if dbp_uri:
            alignments.append((subject, URIRef(dbp_uri), "dbpedia"))
            matched.append(dbp_uri)
            logging.info(f"  DBpedia: {label} -> {dbp_uri}")
        
        # Cache results
        if matched:
            cache[cache_key] = matched
        
        time.sleep(0.2)  # Be polite
    
    return alignments


def align_fuel_types(graph: Graph, cache: Dict) -> List[Tuple]:
    """Align fuel type instances with Wikidata."""
    alignments = []
    
    fuel_type_mapping = {
        "Regular": ("Q39624", "gasoline"),
        "Premium": ("Q39624", "gasoline"),
        "Diesel": ("Q19268", "diesel fuel"),
        "Electric": ("Q12725", "electricity"),
        "Gasoline": ("Q39624", "gasoline"),
        "Hybrid": ("Q273233", "hybrid vehicle"),
        "E85": ("Q620805", "E85"),
    }
    
    for subject in graph.subjects(RDF.type, AUTO.FuelType):
        label = _get_label(graph, subject)
        
        if label in fuel_type_mapping:
            qid, _ = fuel_type_mapping[label]
            wd_uri = f"http://www.wikidata.org/entity/{qid}"
            alignments.append((subject, URIRef(wd_uri), "wikidata"))
            logging.info(f"  FuelType: {label} -> {qid}")
    
    return alignments


def align_drive_types(graph: Graph) -> List[Tuple]:
    """Align drive type instances with Wikidata."""
    alignments = []
    
    drive_mapping = {
        "FrontWheelDrive": "Q253099",
        "RearWheelDrive": "Q19906",
        "FourWheelDrive": "Q193807",
        "AllWheelDrive": "Q193807",
        "FourWheelOrAllWheelDrive": "Q193807",
    }
    
    for subject in graph.subjects(RDF.type, AUTO.DriveType):
        label = _get_label(graph, subject)
        
        if label in drive_mapping:
            qid = drive_mapping[label]
            wd_uri = f"http://www.wikidata.org/entity/{qid}"
            alignments.append((subject, URIRef(wd_uri), "wikidata"))
            logging.info(f"  DriveType: {label} -> {qid}")
    
    return alignments


def _get_label(graph: Graph, subject: URIRef) -> str:
    """Get label of a resource."""
    for _, _, literal in graph.triples((subject, RDFS.label, None)):
        return str(literal)
    # Fallback to local name
    return str(subject).split("#")[-1].split("/")[-1]


# ============================================================================
# OUTPUT GENERATION
# ============================================================================

def create_alignment_graph(class_alignments: Dict, property_alignments: Dict, 
                          instance_alignments: List[Tuple]) -> Graph:
    """Create RDF graph with all alignments."""
    g = Graph()
    g.bind("auto", AUTO)
    g.bind("dbo", DBO)
    g.bind("dbr", DBR)
    g.bind("schema", SCHEMA)
    g.bind("wd", WD)
    g.bind("owl", OWL)
    
    # Class alignments
    for local_class, mappings in class_alignments.items():
        for external_class, source in mappings:
            g.add((local_class, OWL.equivalentClass, external_class))
            logging.info(f"Class: {local_class.split('#')[-1]} ≡ {external_class} ({source})")
    
    # Property alignments
    for local_prop, mappings in property_alignments.items():
        for external_prop, source in mappings:
            g.add((local_prop, OWL.equivalentProperty, external_prop))
            logging.info(f"Property: {local_prop.split('#')[-1]} ≡ {external_prop} ({source})")
    
    # Instance alignments (owl:sameAs)
    for local_uri, external_uri, source in instance_alignments:
        g.add((local_uri, OWL.sameAs, external_uri))
    
    return g


# ============================================================================
# MAIN
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Align AutoSemantic ontology with DBpedia, Schema.org, and Wikidata"
    )
    parser.add_argument(
        "--input",
        default="output.ttl",
        help="Input Turtle file containing the knowledge graph"
    )
    parser.add_argument(
        "--output",
        default="alignments.ttl",
        help="Output Turtle file for alignments"
    )
    parser.add_argument(
        "--cache",
        default="alignment_cache.json",
        help="Cache file for instance alignments"
    )
    parser.add_argument(
        "--align-instances",
        action="store_true",
        help="Align instances (manufacturers, fuel types, etc.) - can be slow"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging"
    )
    return parser.parse_args()


def load_cache(path: str) -> Dict:
    """Load cache from JSON file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_cache(path: str, cache: Dict):
    """Save cache to JSON file."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def main():
    args = parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(levelname)s] %(message)s"
    )
    
    logging.info(f"Loading graph from {args.input}")
    graph = Graph()
    graph.parse(args.input, format="turtle")
    
    logging.info("\n=== CLASS ALIGNMENTS ===")
    # Class alignments are predefined
    
    logging.info("\n=== PROPERTY ALIGNMENTS ===")
    # Property alignments are predefined
    
    instance_alignments = []
    
    if args.align_instances:
        cache = load_cache(args.cache)
        
        logging.info("\n=== MANUFACTURER ALIGNMENTS ===")
        manufacturer_alignments = align_manufacturers(graph, cache)
        instance_alignments.extend(manufacturer_alignments)
        
        logging.info("\n=== FUEL TYPE ALIGNMENTS ===")
        fuel_alignments = align_fuel_types(graph, cache)
        instance_alignments.extend(fuel_alignments)
        
        logging.info("\n=== DRIVE TYPE ALIGNMENTS ===")
        drive_alignments = align_drive_types(graph)
        instance_alignments.extend(drive_alignments)
        
        save_cache(args.cache, cache)
        logging.info(f"\nCache saved to {args.cache}")
    
    # Create output graph
    logging.info("\n=== GENERATING OUTPUT ===")
    alignment_graph = create_alignment_graph(
        CLASS_ALIGNMENTS,
        PROPERTY_ALIGNMENTS,
        instance_alignments
    )
    
    # Save
    alignment_graph.serialize(destination=args.output, format="turtle")
    logging.info(f"\nAlignments saved to {args.output}")
    logging.info(f"Total triples: {len(alignment_graph)}")
    
    # Summary
    class_count = len([t for t in alignment_graph.triples((None, OWL.equivalentClass, None))])
    prop_count = len([t for t in alignment_graph.triples((None, OWL.equivalentProperty, None))])
    instance_count = len([t for t in alignment_graph.triples((None, OWL.sameAs, None))])
    
    logging.info(f"\nSummary:")
    logging.info(f"  - Class alignments: {class_count}")
    logging.info(f"  - Property alignments: {prop_count}")
    logging.info(f"  - Instance alignments: {instance_count}")


if __name__ == "__main__":
    main()
