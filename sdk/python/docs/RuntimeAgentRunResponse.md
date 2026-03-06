# RuntimeAgentRunResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**main_question** | **str** |  | [optional] [default to '']
**output** | **str** |  | 
**sub_qa** | [**List[SubQuestionAnswer]**](SubQuestionAnswer.md) |  | [optional] 

## Example

```python
from openapi_client.models.runtime_agent_run_response import RuntimeAgentRunResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RuntimeAgentRunResponse from a JSON string
runtime_agent_run_response_instance = RuntimeAgentRunResponse.from_json(json)
# print the JSON string representation of the object
print(RuntimeAgentRunResponse.to_json())

# convert the object into a dict
runtime_agent_run_response_dict = runtime_agent_run_response_instance.to_dict()
# create an instance of RuntimeAgentRunResponse from a dict
runtime_agent_run_response_from_dict = RuntimeAgentRunResponse.from_dict(runtime_agent_run_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


