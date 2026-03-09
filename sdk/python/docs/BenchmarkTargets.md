# BenchmarkTargets


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**max_cost_usd** | **float** |  | [optional] [default to 5.0]
**max_latency_ms_p95** | **int** |  | [optional] [default to 30000]
**min_correctness** | **float** |  | [optional] [default to 0.75]

## Example

```python
from openapi_client.models.benchmark_targets import BenchmarkTargets

# TODO update the JSON string below
json = "{}"
# create an instance of BenchmarkTargets from a JSON string
benchmark_targets_instance = BenchmarkTargets.from_json(json)
# print the JSON string representation of the object
print(BenchmarkTargets.to_json())

# convert the object into a dict
benchmark_targets_dict = benchmark_targets_instance.to_dict()
# create an instance of BenchmarkTargets from a dict
benchmark_targets_from_dict = BenchmarkTargets.from_dict(benchmark_targets_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


