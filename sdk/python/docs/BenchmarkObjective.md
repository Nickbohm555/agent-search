# BenchmarkObjective


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**execution_mode** | [**BenchmarkExecutionMode**](BenchmarkExecutionMode.md) |  | [optional] 
**primary_kpi** | [**BenchmarkKPI**](BenchmarkKPI.md) |  | [optional] 
**secondary_kpi** | [**BenchmarkKPI**](BenchmarkKPI.md) |  | [optional] 
**targets** | [**BenchmarkTargets**](BenchmarkTargets.md) |  | [optional] 

## Example

```python
from openapi_client.models.benchmark_objective import BenchmarkObjective

# TODO update the JSON string below
json = "{}"
# create an instance of BenchmarkObjective from a JSON string
benchmark_objective_instance = BenchmarkObjective.from_json(json)
# print the JSON string representation of the object
print(BenchmarkObjective.to_json())

# convert the object into a dict
benchmark_objective_dict = benchmark_objective_instance.to_dict()
# create an instance of BenchmarkObjective from a dict
benchmark_objective_from_dict = BenchmarkObjective.from_dict(benchmark_objective_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


