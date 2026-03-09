# BenchmarkRunCancelResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**message** | **str** |  | 
**status** | **str** |  | 

## Example

```python
from openapi_client.models.benchmark_run_cancel_response import BenchmarkRunCancelResponse

# TODO update the JSON string below
json = "{}"
# create an instance of BenchmarkRunCancelResponse from a JSON string
benchmark_run_cancel_response_instance = BenchmarkRunCancelResponse.from_json(json)
# print the JSON string representation of the object
print(BenchmarkRunCancelResponse.to_json())

# convert the object into a dict
benchmark_run_cancel_response_dict = benchmark_run_cancel_response_instance.to_dict()
# create an instance of BenchmarkRunCancelResponse from a dict
benchmark_run_cancel_response_from_dict = BenchmarkRunCancelResponse.from_dict(benchmark_run_cancel_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


