# BenchmarkRunStatusResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**completed_questions** | **int** |  | [optional] [default to 0]
**created_at** | **float** |  | [optional] 
**dataset_id** | **str** |  | 
**error** | **str** |  | [optional] 
**finished_at** | **float** |  | [optional] 
**mode_summaries** | [**List[BenchmarkModeSummary]**](BenchmarkModeSummary.md) |  | [optional] 
**modes** | [**List[BenchmarkMode]**](BenchmarkMode.md) |  | [optional] 
**objective** | [**BenchmarkObjective**](BenchmarkObjective.md) |  | [optional] 
**results** | [**List[BenchmarkResultStatusItem]**](BenchmarkResultStatusItem.md) |  | [optional] 
**run_id** | **str** |  | 
**started_at** | **float** |  | [optional] 
**status** | [**BenchmarkRunStatus**](BenchmarkRunStatus.md) |  | 
**targets** | [**BenchmarkTargets**](BenchmarkTargets.md) |  | [optional] 
**total_questions** | **int** |  | [optional] [default to 0]

## Example

```python
from openapi_client.models.benchmark_run_status_response import BenchmarkRunStatusResponse

# TODO update the JSON string below
json = "{}"
# create an instance of BenchmarkRunStatusResponse from a JSON string
benchmark_run_status_response_instance = BenchmarkRunStatusResponse.from_json(json)
# print the JSON string representation of the object
print(BenchmarkRunStatusResponse.to_json())

# convert the object into a dict
benchmark_run_status_response_dict = benchmark_run_status_response_instance.to_dict()
# create an instance of BenchmarkRunStatusResponse from a dict
benchmark_run_status_response_from_dict = BenchmarkRunStatusResponse.from_dict(benchmark_run_status_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


