# from SPARQLWrapper import get_sparql_dataframe #TODO ?
from enum import Enum
from typing import Optional
from dataclasses import dataclass
import time

from rdflib.plugins.sparql.parser import parseQuery
from SPARQLWrapper import JSON, SPARQLWrapper2
from SPARQLWrapper.SmartWrapper import Bindings


class QueryStatus(Enum):
    SYNTAX_ERROR = "syntax_error"
    EXECUTION_ERROR = "execution_error"
    EMPTY_RESULT = "empty_result"
    HAS_RESULTS = "has_results"

@dataclass
class QueryEvaluation:
    generated_query: str
    status: QueryStatus
    result_count: int
    execution_time: Optional[float] = None



class Benchmark:
    def __init__(
            self, 
            sparql_queries: list[str]
            ) -> None:
        
        self.sparql_queries = sparql_queries
        self.endpoint = "https://lila-erc.eu/sparql/lila_knowledge_base/sparql"

        # Syntax 
        self.num_correct_queries = 0
        self.num_incorrect_queries = 0
        self.syntax_accuracy = None

        #Execution
        self.num_with_results = 0
        self.num_empty_results = 0
        self.execution_accuracy = None
        self.num_executable_queries = 0

        self.evaluations = []

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
        router = SPARQLWrapper2(self.endpoint)
        router.setReturnFormat(JSON)

        for query in self.sparql_queries:
            _start = time.time()

            if not self.is_syntax_correct(query):
                self.evaluations.append(QueryEvaluation(
                    generated_query=query,
                    status=QueryStatus.SYNTAX_ERROR,
                    result_count=0,
                ))
                continue

            try:
                router.setQuery(query)
                results = router.query()
                execution_time = time.time() - _start

                if isinstance(results, Bindings):
                    bindings = results.fullResult["results"]["bindings"]
                    results_count = len(bindings)

                    if results_count > 0:
                        self.num_with_results += 1
                        status = QueryStatus.HAS_RESULTS
                    else:
                        self.num_empty_results += 1
                        status = QueryStatus.EMPTY_RESULT
                    
                    self.num_executable_queries += 1
                    
                    self.evaluations.append(QueryEvaluation(
                        generated_query=query,
                        status=status,
                        result_count=results_count,
                        execution_time=execution_time
                    ))

            except Exception:
                self.num_execution_errors += 1
                self.evaluations.append(QueryEvaluation(
                    generated_query=query,
                    status=QueryStatus.EXECUTION_ERROR,
                    result_count=0,
                    execution_time=time.time() - _start
                ))
               
        self.execution_accuracy = (
            f"{(self.num_executable_queries / len(self.sparql_queries) * 100):.2f}%"
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

    print(bm.evaluations)
