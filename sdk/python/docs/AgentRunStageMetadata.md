# AgentRunStageMetadata


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**emitted_at** | **float** |  | [optional] 
**lane_index** | **int** |  | [optional] [default to 0]
**lane_total** | **int** |  | [optional] [default to 0]
**stage** | **str** |  | 
**status** | **str** |  | 
**sub_question** | **str** |  | [optional] [default to '']

## Example

```python
from openapi_client.models.agent_run_stage_metadata import AgentRunStageMetadata

# TODO update the JSON string below
json = "{}"
# create an instance of AgentRunStageMetadata from a JSON string
agent_run_stage_metadata_instance = AgentRunStageMetadata.from_json(json)
# print the JSON string representation of the object
print(AgentRunStageMetadata.to_json())

# convert the object into a dict
agent_run_stage_metadata_dict = agent_run_stage_metadata_instance.to_dict()
# create an instance of AgentRunStageMetadata from a dict
agent_run_stage_metadata_from_dict = AgentRunStageMetadata.from_dict(agent_run_stage_metadata_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


