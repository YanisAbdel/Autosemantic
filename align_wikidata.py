"""Align local manufacturers with Wikidata.

This script scans the knowledge graph to find every resource typed as
`:Manufacturer`, queries Wikidata for likely matches, and produces
`owl:sameAs` links in a separate Turtle file.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from rdflib import Graph, Namespace, RDF, RDFS, URIRef


WIKIDATA_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "AutosemanticAligner/1.0 (https://www.univ-projet.fr/)"
DESCRIPTION_HINTS = (
    "automobile manufacturer",
    "car manufacturer",
    "vehicle manufacturer",
    "automaker",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Align :Manufacturer resources with Wikidata entities",
    )
    parser.add_argument(
        "--input",
        default="output.ttl",
        help="Path to the local Turtle graph that contains manufacturers",
    )
    parser.add_argument(
        "--output",
        default="align_wikidata_output.ttl",
        help="Where to write the generated owl:sameAs triples",
    )
    parser.add_argument(
        "--cache",
        default="align_wikidata_cache.json",
        help="Optional cache file to avoid repeated Wikidata lookups",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Language to use when searching Wikidata labels",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=5,
        help="Number of candidates to fetch per manufacturer",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.1,
        help="Seconds to sleep between Wikidata calls to be polite",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def load_graph(path: str) -> Graph:
    graph = Graph()
    graph.parse(path, format="turtle")
    return graph


def load_cache(path: str) -> Dict[str, str]:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    return {}


def save_cache(path: str, cache: Dict[str, str]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(cache, handle, ensure_ascii=False, indent=2)


def extract_manufacturers(graph: Graph) -> List[Tuple[URIRef, str]]:
    ns = Namespace("http://www.univ-projet.fr/ontologies/autosemantica#")
    manufacturers: List[Tuple[URIRef, str]] = []

    for subject in graph.subjects(RDF.type, ns.Manufacturer):
        label = _get_label(graph, subject)
        manufacturers.append((subject, label))

    return manufacturers


def _get_label(graph: Graph, subject: URIRef) -> str:
    for _, _, literal in graph.triples((subject, RDFS.label, None)):
        return str(literal)
    return subject.split("/")[-1]


def search_wikidata(label: str, language: str, max_results: int) -> List[dict]:
    params = {
        "action": "wbsearchentities",
        "format": "json",
        "language": language,
        "search": label,
        "limit": max_results,
    }
    url = f"{WIKIDATA_API}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": USER_AGENT})

    with urlopen(request, timeout=15) as response:  # noqa: S310
        payload = json.load(response)
    return payload.get("search", [])


def choose_candidate(candidates: Iterable[dict], label: str) -> Optional[dict]:
    label_norm = label.lower()
    candidates_list = list(candidates)

    for candidate in candidates_list:
        if candidate.get("label", "").lower() == label_norm:
            return candidate

    for candidate in candidates_list:
        description = (candidate.get("description") or "").lower()
        if any(hint in description for hint in DESCRIPTION_HINTS):
            return candidate

    if candidates_list:
        return candidates_list[0]
    return None


def align_manufacturers(
    manufacturers: List[Tuple[URIRef, str]],
    language: str,
    max_results: int,
    cache: Dict[str, str],
    sleep_seconds: float,
) -> Tuple[List[Tuple[URIRef, URIRef]], List[str]]:
    alignments: List[Tuple[URIRef, URIRef]] = []
    missing: List[str] = []

    for subject, label in manufacturers:
        if label in cache:
            qid = cache[label]
            logging.debug("Cache hit for %s -> %s", label, qid)
            alignments.append((subject, URIRef(f"https://www.wikidata.org/entity/{qid}")))
            continue

        try:
            candidates = search_wikidata(label, language, max_results)
        except Exception as exc:  # noqa: BLE001
            logging.warning("Search failed for %s: %s", label, exc)
            missing.append(label)
            continue

        best = choose_candidate(candidates, label)
        if not best:
            logging.info("No candidate found for %s", label)
            missing.append(label)
            continue

        qid = best.get("id")
        if not qid:
            logging.info("Candidate without id for %s", label)
            missing.append(label)
            continue

        cache[label] = qid
        alignments.append((subject, URIRef(f"https://www.wikidata.org/entity/{qid}")))
        logging.info("Aligned %s -> %s (%s)", label, qid, best.get("description", ""))
        time.sleep(sleep_seconds)

    return alignments, missing


def write_alignments(path: str, alignments: List[Tuple[URIRef, URIRef]]) -> None:
    owl = Namespace("http://www.w3.org/2002/07/owl#")
    graph = Graph()
    for local_uri, wikidata_uri in alignments:
        graph.add((local_uri, owl.sameAs, wikidata_uri))
    graph.serialize(destination=path, format="turtle")


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )

    logging.info("Loading graph from %s", args.input)
    graph = load_graph(args.input)
    manufacturers = extract_manufacturers(graph)
    logging.info("Found %d manufacturers", len(manufacturers))

    cache = load_cache(args.cache)

    alignments, missing = align_manufacturers(
        manufacturers=manufacturers,
        language=args.language,
        max_results=args.max_results,
        cache=cache,
        sleep_seconds=args.sleep,
    )

    if alignments:
        write_alignments(args.output, alignments)
        logging.info("Wrote %d owl:sameAs links to %s", len(alignments), args.output)
    else:
        logging.info("No alignments generated")

    save_cache(args.cache, cache)
    if missing:
        logging.info("No match for %d manufacturers: %s", len(missing), ", ".join(missing))


if __name__ == "__main__":
    main()
