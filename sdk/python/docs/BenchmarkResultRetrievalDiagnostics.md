# BenchmarkResultRetrievalDiagnostics


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**k** | **int** |  | [optional] [default to 10]
**label_source** | **str** |  | [optional] 
**mrr** | **float** |  | [optional] 
**ndcg** | **float** |  | [optional] 
**recall_at_k** | **float** |  | [optional] 
**relevant_document_ids** | **List[str]** |  | [optional] 
**retrieved_document_ids** | **List[str]** |  | [optional] 

## Example

```python
from openapi_client.models.benchmark_result_retrieval_diagnostics import BenchmarkResultRetrievalDiagnostics

# TODO update the JSON string below
json = "{}"
# create an instance of BenchmarkResultRetrievalDiagnostics from a JSON string
benchmark_result_retrieval_diagnostics_instance = BenchmarkResultRetrievalDiagnostics.from_json(json)
# print the JSON string representation of the object
print(BenchmarkResultRetrievalDiagnostics.to_json())

# convert the object into a dict
benchmark_result_retrieval_diagnostics_dict = benchmark_result_retrieval_diagnostics_instance.to_dict()
# create an instance of BenchmarkResultRetrievalDiagnostics from a dict
benchmark_result_retrieval_diagnostics_from_dict = BenchmarkResultRetrievalDiagnostics.from_dict(benchmark_result_retrieval_diagnostics_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


