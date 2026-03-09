# BenchmarkResultStatusItem


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**execution_error** | **str** |  | [optional] 
**latency_ms** | **int** |  | [optional] 
**mode** | **str** |  | 
**quality** | [**BenchmarkResultQualityScore**](BenchmarkResultQualityScore.md) |  | [optional] 
**question_id** | **str** |  | 
**retrieval** | [**BenchmarkResultRetrievalDiagnostics**](BenchmarkResultRetrievalDiagnostics.md) |  | [optional] 

## Example

```python
from openapi_client.models.benchmark_result_status_item import BenchmarkResultStatusItem

# TODO update the JSON string below
json = "{}"
# create an instance of BenchmarkResultStatusItem from a JSON string
benchmark_result_status_item_instance = BenchmarkResultStatusItem.from_json(json)
# print the JSON string representation of the object
print(BenchmarkResultStatusItem.to_json())

# convert the object into a dict
benchmark_result_status_item_dict = benchmark_result_status_item_instance.to_dict()
# create an instance of BenchmarkResultStatusItem from a dict
benchmark_result_status_item_from_dict = BenchmarkResultStatusItem.from_dict(benchmark_result_status_item_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


