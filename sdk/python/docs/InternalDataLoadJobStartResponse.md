# InternalDataLoadJobStartResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**job_id** | **str** |  | 
**status** | **str** |  | 

## Example

```python
from openapi_client.models.internal_data_load_job_start_response import InternalDataLoadJobStartResponse

# TODO update the JSON string below
json = "{}"
# create an instance of InternalDataLoadJobStartResponse from a JSON string
internal_data_load_job_start_response_instance = InternalDataLoadJobStartResponse.from_json(json)
# print the JSON string representation of the object
print(InternalDataLoadJobStartResponse.to_json())

# convert the object into a dict
internal_data_load_job_start_response_dict = internal_data_load_job_start_response_instance.to_dict()
# create an instance of InternalDataLoadJobStartResponse from a dict
internal_data_load_job_start_response_from_dict = InternalDataLoadJobStartResponse.from_dict(internal_data_load_job_start_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


