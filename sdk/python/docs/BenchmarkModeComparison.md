# BenchmarkModeComparison


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**correctness_delta** | **float** |  | [optional] 
**correctness_rate** | **float** |  | [optional] 
**mode** | [**BenchmarkMode**](BenchmarkMode.md) |  | 
**p95_latency_delta_ms** | **float** |  | [optional] 
**p95_latency_ms** | **float** |  | [optional] 

## Example

```python
from openapi_client.models.benchmark_mode_comparison import BenchmarkModeComparison

# TODO update the JSON string below
json = "{}"
# create an instance of BenchmarkModeComparison from a JSON string
benchmark_mode_comparison_instance = BenchmarkModeComparison.from_json(json)
# print the JSON string representation of the object
print(BenchmarkModeComparison.to_json())

# convert the object into a dict
benchmark_mode_comparison_dict = benchmark_mode_comparison_instance.to_dict()
# create an instance of BenchmarkModeComparison from a dict
benchmark_mode_comparison_from_dict = BenchmarkModeComparison.from_dict(benchmark_mode_comparison_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


