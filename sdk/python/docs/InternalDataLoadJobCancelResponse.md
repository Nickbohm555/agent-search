# InternalDataLoadJobCancelResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**message** | **str** |  | 
**status** | **str** |  | 

## Example

```python
from openapi_client.models.internal_data_load_job_cancel_response import InternalDataLoadJobCancelResponse

# TODO update the JSON string below
json = "{}"
# create an instance of InternalDataLoadJobCancelResponse from a JSON string
internal_data_load_job_cancel_response_instance = InternalDataLoadJobCancelResponse.from_json(json)
# print the JSON string representation of the object
print(InternalDataLoadJobCancelResponse.to_json())

# convert the object into a dict
internal_data_load_job_cancel_response_dict = internal_data_load_job_cancel_response_instance.to_dict()
# create an instance of InternalDataLoadJobCancelResponse from a dict
internal_data_load_job_cancel_response_from_dict = InternalDataLoadJobCancelResponse.from_dict(internal_data_load_job_cancel_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


