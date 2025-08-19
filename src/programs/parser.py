from enum import Enum
from typing import Optional
import os
import logfire
from dataclasses import dataclass
from SPARQLWrapper import JSON, SPARQLWrapper2
from dotenv import load_dotenv
load_dotenv()
logfire.configure(token=os.environ.get("LOGFIRE_TOKEN"), service_name="SparqlAgent")

class OntologyElement(Enum):
    CLASS = "class"
    PROPERTY = "property"
    INDIVIDUAL = "individual"

@dataclass
class URI():
    uri: Optional[str]
    label: Optional[str]

@dataclass
class Concept():
    uri: Optional[str]
    label: Optional[str]
    description: Optional[str]
    parent_class: Optional[URI]
    sub_class: Optional[URI]
    _type: OntologyElement

    def to_string_for_llm(self) -> str:
        string = f"""
         Element Type: {self._type}
         URI: {self.uri}
         Label: {self.label}
         Description: {self.description}
         Parent Class: {self.parent_class}
         Sub Class: {self.sub_class}
        """
        return string

class LilaDatabaseParser():
    def __init__(self):
        self.endpoint = os.environ.get("LILA_ENDPOINT", "")
        self.classes: dict[str, Concept] = {}
        self.properties: dict[str, Concept] = {}
        self.individuals: dict[str, Concept] = {}
        self.identifier_uri_mapping: dict[str, str] = {}

        self._build_indexes()

    def _build_indexes(self) -> None:
        self.classes = self._extract_classes()
        logfire.info(f"Extracted {len(self.classes)} classes")
        self.properties = self._extract_properties()
        logfire.info(f"Extracted {len(self.properties)} properties")
#        self.individuals = self._extract_named_individuals()
#        logfire.info(f"Extracted {len(self.individuals)} individuals")
        self.identifier_uri_mapping = self._create_identifier_id_mapping()

    def _extract_classes(self) -> dict[str, Concept]:
        query = """
        SELECT ?class ?label ?comment ?subclass ?parentClass ?label_2 ?label_sub WHERE {
            ?class a owl:Class .
            OPTIONAL { ?class rdfs:label ?label }
            OPTIONAL { ?class rdfs:comment ?comment }
            OPTIONAL {
                ?class rdfs:subClassOf ?parentClass .
                ?parentClass rdfs:label ?label_2
            }
            OPTIONAL {
                ?subclass rdfs:subClassOf ?class .
                ?subclass rdfs:label ?label_sub
            }
        }
        """
        router = SPARQLWrapper2(self.endpoint)
        router.setQuery(query)
        router.setReturnFormat(JSON)
        query_result = router.query().fullResult

        bindings = query_result["results"]["bindings"]
        final_results = {}
        if bindings:
            for result in bindings:
                uri = result.get("class").get("value", None)
                label = os.path.basename(uri)
                description = result.get("comment")
                parent_class = result.get("parentClass")
                pc_label = result.get("label_2")
                subclass = result.get("subclass")
                sc_label = result.get("label_sub")

                final_results[uri] = Concept(
                    uri = uri,
                    label = label if label else None,
                    description=description.get("value") if description else None,
                    parent_class= URI(
                        uri = parent_class.get("value") if parent_class else None,
                        label = pc_label.get("value") if pc_label else None
                    ),
                    sub_class= URI(
                        uri = subclass.get("value") if subclass else None,
                        label = sc_label.get("value") if sc_label else None
                    ),
                    _type = OntologyElement.CLASS
                )
        return final_results

    def _extract_properties(self) -> dict[str, Concept]:
        query = """
        SELECT ?property ?label ?comment ?subproperty ?parentProperty ?label_2 ?label_sub WHERE {
            ?property a rdf:Property .
            OPTIONAL { ?property rdfs:label ?label }
            OPTIONAL { ?property rdfs:comment ?comment }
            OPTIONAL {
                ?property rdfs:subPropertyOf ?parentProperty .
                ?parentProperty rdfs:label ?label_2
            }
            OPTIONAL {
                ?subclass rdfs:subPropertyOf ?class .
                ?subclass rdfs:label ?label_sub
            }
        }
        """
        router = SPARQLWrapper2(self.endpoint)
        router.setQuery(query)
        router.setReturnFormat(JSON)
        query_result = router.query().fullResult

        bindings = query_result["results"]["bindings"]

        final_results = {}
        if bindings:
            for result in bindings:
                uri = result.get("property").get("value", None)
                label = os.path.basename(uri)
                description = result.get("comment")
                parent_prop = result.get("parentProperty")
                pp_label = result.get("label_2")
                sub_prop = result.get("subproperty")
                sp_label = result.get("label_sub")

                final_results[uri] = Concept(
                        uri = uri,
                        label = label if label else None,
                        description=description.get("value") if description else None,
                        parent_class= URI(
                            uri = parent_prop.get("value")if parent_prop else None,
                            label = pp_label.get("value")if pp_label else None
                        ),
                        sub_class= URI(
                            uri = sub_prop.get("value")if sub_prop else None,
                            label = sp_label.get("value")if sp_label else None
                        ),
                        _type = OntologyElement.PROPERTY
                    )
        return final_results

    def _extract_named_individuals(self) -> dict[str, Concept]:
        query = """
        SELECT ?individual ?label ?comment ?parentProperty ?label_2 WHERE {
          ?individual a owl:NamedIndividual .
          OPTIONAL { ?individual rdfs:label ?label }
          }
        """
        router = SPARQLWrapper2(self.endpoint)
        router.setQuery(query)
        router.setReturnFormat(JSON)
        query_result = router.query().fullResult

        bindings = query_result["results"]["bindings"]

        final_results = {}
        if bindings:
            for result in bindings:
                uri = result.get("individual").get("value", None)
                label = os.path.basename(uri)
                final_results[uri] = Concept(
                            uri = uri,
                            label = label if label else None,
                            description= None,
                            parent_class= None,
                            sub_class=None,
                            _type = OntologyElement.INDIVIDUAL
                        )
        return final_results

    def find_concept(self, identifier: Optional[str]) -> Optional[Concept]:
        if identifier is None:
            return None
        elif identifier in self.classes:
            return self.classes[identifier]
        elif identifier in self.properties:
            return self.properties[identifier]
        elif identifier in self.individuals:
            return self.individuals[identifier]

    def _create_identifier_id_mapping(self) -> dict[str, str]:
        mapping = {}
        for uri, concept in self.classes.items():
            mapping[concept.label] = uri
        for uri, concept in self.properties.items():
            mapping[concept.label] = uri
        for uri, concept in self.individuals.items():
            mapping[concept.label] = uri

        self.identifier_uri_mapping = mapping
        return mapping

    def map_identifier_to_uri(self, identifier) -> Optional[str]:
        if identifier in self.identifier_uri_mapping:
            return self.identifier_uri_mapping[identifier]
        else:
            return None


def explore_concept(identifier: Optional[str] = None) -> Optional[str]:
    database_parser = LilaDatabaseParser()
    logfire.info(f"Exploring concept with identifier: {identifier}")
    if identifier:
        concept = database_parser.find_concept(identifier)
        if concept:
            return concept.to_string_for_llm()
        else:
            uri = database_parser.map_identifier_to_uri(identifier)
            concept = database_parser.find_concept(uri)
            if concept:
                return concept.to_string_for_llm()
            else:
                logfire.info(f"Concept not found for URI: {uri}")
    else:
        print("No identifier provided")
