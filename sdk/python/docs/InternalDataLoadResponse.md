# InternalDataLoadResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**chunks_created** | **int** |  | 
**documents_loaded** | **int** |  | 
**source_type** | **str** |  | 
**status** | **str** |  | 

## Example

```python
from openapi_client.models.internal_data_load_response import InternalDataLoadResponse

# TODO update the JSON string below
json = "{}"
# create an instance of InternalDataLoadResponse from a JSON string
internal_data_load_response_instance = InternalDataLoadResponse.from_json(json)
# print the JSON string representation of the object
print(InternalDataLoadResponse.to_json())

# convert the object into a dict
internal_data_load_response_dict = internal_data_load_response_instance.to_dict()
# create an instance of InternalDataLoadResponse from a dict
internal_data_load_response_from_dict = InternalDataLoadResponse.from_dict(internal_data_load_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


