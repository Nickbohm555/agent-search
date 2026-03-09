# BenchmarkWipeResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**deleted_runs** | **int** |  | 
**message** | **str** |  | 
**status** | **str** |  | 

## Example

```python
from openapi_client.models.benchmark_wipe_response import BenchmarkWipeResponse

# TODO update the JSON string below
json = "{}"
# create an instance of BenchmarkWipeResponse from a JSON string
benchmark_wipe_response_instance = BenchmarkWipeResponse.from_json(json)
# print the JSON string representation of the object
print(BenchmarkWipeResponse.to_json())

# convert the object into a dict
benchmark_wipe_response_dict = benchmark_wipe_response_instance.to_dict()
# create an instance of BenchmarkWipeResponse from a dict
benchmark_wipe_response_from_dict = BenchmarkWipeResponse.from_dict(benchmark_wipe_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


