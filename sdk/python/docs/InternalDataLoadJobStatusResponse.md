# InternalDataLoadJobStatusResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**completed** | **int** |  | 
**error** | **str** |  | [optional] 
**job_id** | **str** |  | 
**message** | **str** |  | 
**response** | [**InternalDataLoadResponse**](InternalDataLoadResponse.md) |  | [optional] 
**status** | **str** |  | 
**total** | **int** |  | 

## Example

```python
from openapi_client.models.internal_data_load_job_status_response import InternalDataLoadJobStatusResponse

# TODO update the JSON string below
json = "{}"
# create an instance of InternalDataLoadJobStatusResponse from a JSON string
internal_data_load_job_status_response_instance = InternalDataLoadJobStatusResponse.from_json(json)
# print the JSON string representation of the object
print(InternalDataLoadJobStatusResponse.to_json())

# convert the object into a dict
internal_data_load_job_status_response_dict = internal_data_load_job_status_response_instance.to_dict()
# create an instance of InternalDataLoadJobStatusResponse from a dict
internal_data_load_job_status_response_from_dict = InternalDataLoadJobStatusResponse.from_dict(internal_data_load_job_status_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


