# InternalDataLoadRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**documents** | [**List[InternalDocumentInput]**](InternalDocumentInput.md) |  | [optional] 
**source_type** | **str** |  | [optional] [default to 'inline']
**wiki** | [**WikiLoadInput**](WikiLoadInput.md) |  | [optional] 

## Example

```python
from openapi_client.models.internal_data_load_request import InternalDataLoadRequest

# TODO update the JSON string below
json = "{}"
# create an instance of InternalDataLoadRequest from a JSON string
internal_data_load_request_instance = InternalDataLoadRequest.from_json(json)
# print the JSON string representation of the object
print(InternalDataLoadRequest.to_json())

# convert the object into a dict
internal_data_load_request_dict = internal_data_load_request_instance.to_dict()
# create an instance of InternalDataLoadRequest from a dict
internal_data_load_request_from_dict = InternalDataLoadRequest.from_dict(internal_data_load_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


