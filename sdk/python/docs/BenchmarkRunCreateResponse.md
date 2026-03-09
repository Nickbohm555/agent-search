# BenchmarkRunCreateResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**run_id** | **str** |  | 
**status** | [**BenchmarkRunStatus**](BenchmarkRunStatus.md) |  | 

## Example

```python
from openapi_client.models.benchmark_run_create_response import BenchmarkRunCreateResponse

# TODO update the JSON string below
json = "{}"
# create an instance of BenchmarkRunCreateResponse from a JSON string
benchmark_run_create_response_instance = BenchmarkRunCreateResponse.from_json(json)
# print the JSON string representation of the object
print(BenchmarkRunCreateResponse.to_json())

# convert the object into a dict
benchmark_run_create_response_dict = benchmark_run_create_response_instance.to_dict()
# create an instance of BenchmarkRunCreateResponse from a dict
benchmark_run_create_response_from_dict = BenchmarkRunCreateResponse.from_dict(benchmark_run_create_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


