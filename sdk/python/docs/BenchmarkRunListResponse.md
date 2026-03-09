# BenchmarkRunListResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**runs** | [**List[BenchmarkRunListItem]**](BenchmarkRunListItem.md) |  | [optional] 

## Example

```python
from openapi_client.models.benchmark_run_list_response import BenchmarkRunListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of BenchmarkRunListResponse from a JSON string
benchmark_run_list_response_instance = BenchmarkRunListResponse.from_json(json)
# print the JSON string representation of the object
print(BenchmarkRunListResponse.to_json())

# convert the object into a dict
benchmark_run_list_response_dict = benchmark_run_list_response_instance.to_dict()
# create an instance of BenchmarkRunListResponse from a dict
benchmark_run_list_response_from_dict = BenchmarkRunListResponse.from_dict(benchmark_run_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


