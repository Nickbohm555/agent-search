# BenchmarkRunCompareResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**baseline_mode** | [**BenchmarkMode**](BenchmarkMode.md) |  | [optional] 
**comparisons** | [**List[BenchmarkModeComparison]**](BenchmarkModeComparison.md) |  | [optional] 
**run_id** | **str** |  | 

## Example

```python
from openapi_client.models.benchmark_run_compare_response import BenchmarkRunCompareResponse

# TODO update the JSON string below
json = "{}"
# create an instance of BenchmarkRunCompareResponse from a JSON string
benchmark_run_compare_response_instance = BenchmarkRunCompareResponse.from_json(json)
# print the JSON string representation of the object
print(BenchmarkRunCompareResponse.to_json())

# convert the object into a dict
benchmark_run_compare_response_dict = benchmark_run_compare_response_instance.to_dict()
# create an instance of BenchmarkRunCompareResponse from a dict
benchmark_run_compare_response_from_dict = BenchmarkRunCompareResponse.from_dict(benchmark_run_compare_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


