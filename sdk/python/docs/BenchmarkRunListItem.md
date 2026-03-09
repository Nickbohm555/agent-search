# BenchmarkRunListItem


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**created_at** | **float** |  | [optional] 
**dataset_id** | **str** |  | 
**finished_at** | **float** |  | [optional] 
**modes** | [**List[BenchmarkMode]**](BenchmarkMode.md) |  | [optional] 
**run_id** | **str** |  | 
**started_at** | **float** |  | [optional] 
**status** | [**BenchmarkRunStatus**](BenchmarkRunStatus.md) |  | 

## Example

```python
from openapi_client.models.benchmark_run_list_item import BenchmarkRunListItem

# TODO update the JSON string below
json = "{}"
# create an instance of BenchmarkRunListItem from a JSON string
benchmark_run_list_item_instance = BenchmarkRunListItem.from_json(json)
# print the JSON string representation of the object
print(BenchmarkRunListItem.to_json())

# convert the object into a dict
benchmark_run_list_item_dict = benchmark_run_list_item_instance.to_dict()
# create an instance of BenchmarkRunListItem from a dict
benchmark_run_list_item_from_dict = BenchmarkRunListItem.from_dict(benchmark_run_list_item_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


