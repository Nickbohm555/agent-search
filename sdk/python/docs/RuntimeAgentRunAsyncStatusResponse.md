# RuntimeAgentRunAsyncStatusResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**cancel_requested** | **bool** |  | [optional] [default to False]
**decomposition_sub_questions** | **List[str]** |  | [optional] 
**elapsed_ms** | **int** |  | [optional] 
**error** | **str** |  | [optional] 
**finished_at** | **float** |  | [optional] 
**job_id** | **str** |  | 
**message** | **str** |  | [optional] [default to '']
**output** | **str** |  | [optional] [default to '']
**result** | [**RuntimeAgentRunResponse**](RuntimeAgentRunResponse.md) |  | [optional] 
**run_id** | **str** |  | [optional] [default to '']
**stage** | **str** |  | [optional] [default to '']
**stages** | [**List[AgentRunStageMetadata]**](AgentRunStageMetadata.md) |  | [optional] 
**started_at** | **float** |  | [optional] 
**status** | **str** |  | 
**sub_qa** | [**List[SubQuestionAnswer]**](SubQuestionAnswer.md) |  | [optional] 
**sub_question_artifacts** | [**List[SubQuestionArtifacts]**](SubQuestionArtifacts.md) |  | [optional] 

## Example

```python
from openapi_client.models.runtime_agent_run_async_status_response import RuntimeAgentRunAsyncStatusResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RuntimeAgentRunAsyncStatusResponse from a JSON string
runtime_agent_run_async_status_response_instance = RuntimeAgentRunAsyncStatusResponse.from_json(json)
# print the JSON string representation of the object
print(RuntimeAgentRunAsyncStatusResponse.to_json())

# convert the object into a dict
runtime_agent_run_async_status_response_dict = runtime_agent_run_async_status_response_instance.to_dict()
# create an instance of RuntimeAgentRunAsyncStatusResponse from a dict
runtime_agent_run_async_status_response_from_dict = RuntimeAgentRunAsyncStatusResponse.from_dict(runtime_agent_run_async_status_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


