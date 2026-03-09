# BenchmarkModeSummary


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**avg_latency_ms** | **float** |  | [optional] 
**completed_questions** | **int** |  | 
**correctness_rate** | **float** |  | [optional] 
**mode** | [**BenchmarkMode**](BenchmarkMode.md) |  | 
**p95_latency_ms** | **float** |  | [optional] 
**total_questions** | **int** |  | 

## Example

```python
from openapi_client.models.benchmark_mode_summary import BenchmarkModeSummary

# TODO update the JSON string below
json = "{}"
# create an instance of BenchmarkModeSummary from a JSON string
benchmark_mode_summary_instance = BenchmarkModeSummary.from_json(json)
# print the JSON string representation of the object
print(BenchmarkModeSummary.to_json())

# convert the object into a dict
benchmark_mode_summary_dict = benchmark_mode_summary_instance.to_dict()
# create an instance of BenchmarkModeSummary from a dict
benchmark_mode_summary_from_dict = BenchmarkModeSummary.from_dict(benchmark_mode_summary_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


