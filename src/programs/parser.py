from enum import Enum
from typing import Optional
import os
import tiktoken
import logfire
from dataclasses import dataclass
from SPARQLWrapper.SmartWrapper import Bindings
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
    _type: OntologyElement

    def to_string_for_llm(self) -> str:
        string = f"""
         Element Type: {self._type}
         URI: {self.uri}
         Label: {self.label}
         Description: {self.description}
        """
        if self._type == OntologyElement.CLASS:
            string += f"Parent Classes: {self.parent_classes}\nSub Classes: {self.sub_classes}\n"
        elif self._type == OntologyElement.PROPERTY:
            string += f"Parent Properties: {self.parent_classes}\nSub Properties: {self.sub_classes}\n"
        return string


class LilaDatabaseParser():
    def __init__(self):
        self.endpoint = os.environ.get("LILA_ENDPOINT", "")
        self.encoding = tiktoken.encoding_for_model(os.environ.get("TOKENIZER_MODEL"))

    @staticmethod
    def extract_label_from_uri(uri: str) -> Optional[str]:
        try:
            label = os.path.basename(uri) 
            label = label.split("#")
            label = label[1] if len(label) == 2 else None
        except ValueError:
            label = None

        return label

    def query(self, query: str):
        router = SPARQLWrapper2(self.endpoint)
        router.setQuery(query)
        router.setReturnFormat(JSON)
        query_result = router.query()
        return query_result

    def parse_results(self, results, concept_type: str) -> dict[str, Concept]:
        final_results = {}

        if isinstance(results, Bindings) and results.bindings:
            print("Ok")
            for result in results.bindings:
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
                    _type = OntologyElement.CLASS if concept_type.lower() == "class" else OntologyElement.PROPERTY
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
                        _type = OntologyElement.CLASS
                    )
                    final_results[uri_string] = concept_merge
                else:
                    final_results[uri_string] = concept

        return final_results
    
    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))



if __name__ == "__main__":
    from src.programs.tools import explore_classes_and_properties

    e = explore_classes_and_properties(identifiers=["lila:hasCitLevel", "lila:Lemma"])
    print(e)