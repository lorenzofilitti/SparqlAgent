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
class Concept():
    uri: Optional[str]
    label: Optional[str]
    description: Optional[str]
    parent_classes: Optional[list[str]]
    sub_classes: Optional[list[str]]
    parent_properties: Optional[list[str]]
    sub_properties: Optional[list[str]]
    _type: OntologyElement

    def to_string_for_llm(self) -> str:
        string = f"""
         Element Type: {self._type}
         URI: {self.uri}
         Label: {self.label}
         Description: {self.description}
         Parent Classes: {self.parent_classes}
         Sub Classes: {self.sub_classes}
        """
        return string

class LilaDatabaseParser():
    def __init__(self):
        self.endpoint = os.environ.get("LILA_ENDPOINT", "")
        self.classes: dict[str, Concept] = {}
        self.properties: dict[str, Concept] = {}
        self.individuals: dict[str, Concept] = {}
        self.identifier_uri_mapping: dict[str, str] = {}
        self.identifier_uri_non_unique: list[tuple[str, Concept]] = []

        self._build_indexes()

    @staticmethod
    def extract_label_from_uri(uri: str) -> Optional[str]:
        try:
            label = os.path.basename(uri) 
            label = label.split("#")
            label = label[1] if len(label) == 2 else None
        except ValueError as e:
            label = None

        return label

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
        SELECT
          ?class
          ?label
          ?description
          (GROUP_CONCAT(DISTINCT ?parentClass; SEPARATOR=", ") AS ?parent_classes)
          (GROUP_CONCAT(DISTINCT ?subClass; SEPARATOR=", ") AS ?sub_classes)
        WHERE {
          ?class a owl:Class .
          OPTIONAL { ?class rdfs:label ?label }
          OPTIONAL { ?class rdfs:comment ?description }

          OPTIONAL {
            ?class rdfs:subClassOf ?pc.
            ?pc rdfs:label ?parentClass
          }

          OPTIONAL {
            ?sc rdfs:subClassOf ?class ;
                  rdfs:label ?subClass
          }
        }
        GROUP BY ?class ?label ?description
        ORDER BY ?class
        limit 2000
        """
        router = SPARQLWrapper2(self.endpoint)
        router.setQuery(query)
        router.setReturnFormat(JSON)
        query_result = router.query()

        final_results = {}
        if query_result:
            for result in query_result.bindings:
                uri = result.get("class")
                label = result.get("label")
                description = result.get("description")
                parent_classes = result.get("parent_classes")
                sub_classes = result.get("sub_classes")

                concept = Concept(
                    uri = uri.value if uri else None,
                    label = label.value if label else self.extract_label_from_uri(uri.value),
                    description=description.value if description else None,
                    parent_classes= parent_classes.value.split(", ") if parent_classes else None,
                    sub_classes= sub_classes.value.split(", ") if sub_classes else None,
                    parent_properties= None,
                    sub_properties= None,
                    _type = OntologyElement.CLASS
                )
                uri_string = uri.value if uri else ""
                if uri_string in final_results:
                    description = description.value if description else None
                    existing_concept = final_results[uri_string]
                    concept_merge = Concept(
                        uri = concept.uri,
                        label = concept.label,
                        description=f"{existing_concept.description} {description}",
                        parent_classes= concept.parent_classes,
                        sub_classes= concept.sub_classes,
                        parent_properties= None,
                        sub_properties= None,
                        _type = OntologyElement.CLASS
                    )
                    final_results[uri_string] = concept_merge
                else:
                    final_results[uri_string] = concept
                    self.identifier_uri_non_unique.append((uri_string, concept))
        return final_results

    def _extract_properties(self) -> dict[str, Concept]:
        query = """
        SELECT
          ?property
          ?label
          ?description
          (GROUP_CONCAT(DISTINCT ?parentProperty; SEPARATOR=", ") AS ?parent_properties)
          (GROUP_CONCAT(DISTINCT ?subProperty; SEPARATOR=", ") AS ?sub_properties)
        WHERE {
          # Classe principale
          ?property a rdf:Property .
          OPTIONAL { ?property rdfs:label ?label }
          OPTIONAL { ?property rdfs:comment ?description }

          # Parent classes (opzionali)
          OPTIONAL {
            ?property rdfs:subPropertyOf ?pc.
            ?pc rdfs:label ?parentProperty
          }

          # Sub classes (opzionali)
          OPTIONAL {
            ?sc rdfs:subPropertyOf ?property ;
                  rdfs:label ?subProperty
          }
        }
        GROUP BY ?property ?label ?description
        ORDER BY ?property
        limit 2000
        """
        router = SPARQLWrapper2(self.endpoint)
        router.setQuery(query)
        router.setReturnFormat(JSON)
        query_result = router.query()

        final_results = {}
        if query_result:
            for result in query_result.bindings:
                uri = result.get("property")
                label = result.get("label")
                description = result.get("comment")
                parent_properties = result.get("parentProperties")
                sub_properties = result.get("subproperties")

                concept = Concept(
                    uri = uri.value if uri else None,
                    label = label.value if label else self.extract_label_from_uri(uri.value),
                    description= description.value if description else None,
                    parent_classes = None,
                    sub_classes = None,
                    parent_properties= parent_properties.value.split(", ") if parent_properties else None,
                    sub_properties= sub_properties.value.split(", ") if sub_properties else None,
                    _type = OntologyElement.PROPERTY
                )
                uri_string = uri.value if uri else ""
                if uri_string in final_results:
                    description = description.value if description else None
                    existing_concept = final_results[uri_string]
                    concept_merge = Concept(
                        uri = concept.uri,
                        label = concept.label,
                        description=f"{existing_concept.description} {description}",
                        parent_classes= None,
                        sub_classes= None,
                        parent_properties= concept.parent_properties,
                        sub_properties= concept.sub_properties,
                        _type = OntologyElement.PROPERTY
                    )
                    final_results[uri_string] = concept_merge
                else:
                    final_results[uri_string] = concept
                    self.identifier_uri_non_unique.append((uri_string, concept))
                final_results[uri_string] = concept
                self.identifier_uri_non_unique.append((uri_string, concept))
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
                            parent_classes= None,
                            sub_classes=None,
                            parent_properties=None,
                            sub_properties=None,
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

database_parser = LilaDatabaseParser()
def explore_concept(identifier: str, database_parser = database_parser) -> Optional[str]:
    identifier = identifier.split(":")[1]
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
