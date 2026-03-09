# BenchmarkRunCreateRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**dataset_id** | **str** |  | 
**metadata** | **object** |  | [optional] 
**modes** | [**List[BenchmarkMode]**](BenchmarkMode.md) |  | 
**targets** | [**BenchmarkTargets**](BenchmarkTargets.md) |  | [optional] 

## Example

```python
from openapi_client.models.benchmark_run_create_request import BenchmarkRunCreateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of BenchmarkRunCreateRequest from a JSON string
benchmark_run_create_request_instance = BenchmarkRunCreateRequest.from_json(json)
# print the JSON string representation of the object
print(BenchmarkRunCreateRequest.to_json())

# convert the object into a dict
benchmark_run_create_request_dict = benchmark_run_create_request_instance.to_dict()
# create an instance of BenchmarkRunCreateRequest from a dict
benchmark_run_create_request_from_dict = BenchmarkRunCreateRequest.from_dict(benchmark_run_create_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


