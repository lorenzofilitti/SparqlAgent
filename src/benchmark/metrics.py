# from SPARQLWrapper import get_sparql_dataframe #TODO ?

from rdflib.plugins.sparql.parser import parseQuery
from SPARQLWrapper import JSON, SPARQLWrapper2
from SPARQLWrapper.SmartWrapper import Bindings


class Benchmark:
    def __init__(self, sparql_queries: list[str]) -> None:
        self.sparql_queries = sparql_queries

        # Syntax 
        self.num_correct_queries = 0
        self.num_incorrect_queries = 0
        self.syntax_accuracy = None

        #Execution
        self.num_results = 0
        self.execution_accuracy = None


    @staticmethod
    def is_syntax_correct(sparql_query: str) -> bool:
        try:
            parseQuery(sparql_query)
            return True
        except Exception:
            return False


    def syntax_validity(self) -> None:
        self.num_correct_queries = len(
            [q for q in self.sparql_queries if Benchmark.is_syntax_correct(q)]
        )
        self.num_incorrect_queries = len(
            [q for q in self.sparql_queries if not Benchmark.is_syntax_correct(q)]
        )
        self.syntax_accuracy = (
            f"{(self.num_correct_queries / len(self.sparql_queries) * 100):.2f}%"
            if len(self.sparql_queries) > 0
            else 0
        )


    def execution_validity(self) -> None:
        num_res = 0
        router = SPARQLWrapper2("https://lila-erc.eu/sparql/lila_knowledge_base/sparql")
        router.setReturnFormat(JSON)
        
        for query in self.sparql_queries:
            try:
                router.setQuery(query)
                results = router.query()
                if isinstance(results, Bindings):
                    bindings = results.fullResult["results"]["bindings"]
                    if bindings:
                        num_res += 1

            except Exception:
                continue
               
        self.num_results = num_res
        self.execution_accuracy = (
            f"{(self.num_results / len(self.sparql_queries) * 100):.2f}%"
            if len(self.sparql_queries) > 0
            else 0
        )


    def evaluate_results(self):
        # LLL as a judge?
        pass

    
    def run(self) -> None:
        self.syntax_validity()
        self.execution_validity()

    


if __name__=="__main__":
    bm = Benchmark(["select ?lemma where {?lemma a lila:Ciao}", "select ?lemma where {?lemma a lila:Lemma} limit 1"])
    bm.run()

    print("### Syntax ###")
    print(f"Correct queries: {bm.num_correct_queries}")
    print(f"Syntax accuracy: {bm.syntax_accuracy}\n")

    print("### Execution ###")
    print(f"Returned results: {bm.num_results}")
    print(f"Execution accuracy: {bm.execution_accuracy}")
