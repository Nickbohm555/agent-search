# BenchmarkResultQualityScore


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**error** | **str** |  | [optional] 
**judge_model** | **str** |  | [optional] 
**passed** | **bool** |  | [optional] 
**rubric_version** | **str** |  | [optional] 
**score** | **float** |  | [optional] 
**subscores** | **Dict[str, float]** |  | [optional] 

## Example

```python
from openapi_client.models.benchmark_result_quality_score import BenchmarkResultQualityScore

# TODO update the JSON string below
json = "{}"
# create an instance of BenchmarkResultQualityScore from a JSON string
benchmark_result_quality_score_instance = BenchmarkResultQualityScore.from_json(json)
# print the JSON string representation of the object
print(BenchmarkResultQualityScore.to_json())

# convert the object into a dict
benchmark_result_quality_score_dict = benchmark_result_quality_score_instance.to_dict()
# create an instance of BenchmarkResultQualityScore from a dict
benchmark_result_quality_score_from_dict = BenchmarkResultQualityScore.from_dict(benchmark_result_quality_score_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


