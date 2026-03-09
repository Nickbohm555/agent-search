# RuntimeAgentRunAsyncStartResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**job_id** | **str** |  | 
**run_id** | **str** |  | 
**status** | **str** |  | 

## Example

```python
from openapi_client.models.runtime_agent_run_async_start_response import RuntimeAgentRunAsyncStartResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RuntimeAgentRunAsyncStartResponse from a JSON string
runtime_agent_run_async_start_response_instance = RuntimeAgentRunAsyncStartResponse.from_json(json)
# print the JSON string representation of the object
print(RuntimeAgentRunAsyncStartResponse.to_json())

# convert the object into a dict
runtime_agent_run_async_start_response_dict = runtime_agent_run_async_start_response_instance.to_dict()
# create an instance of RuntimeAgentRunAsyncStartResponse from a dict
runtime_agent_run_async_start_response_from_dict = RuntimeAgentRunAsyncStartResponse.from_dict(runtime_agent_run_async_start_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


