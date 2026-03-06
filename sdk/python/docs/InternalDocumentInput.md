# InternalDocumentInput


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**content** | **str** |  | 
**source_ref** | **str** |  | [optional] 
**source_url** | **str** |  | [optional] 
**title** | **str** |  | 

## Example

```python
from openapi_client.models.internal_document_input import InternalDocumentInput

# TODO update the JSON string below
json = "{}"
# create an instance of InternalDocumentInput from a JSON string
internal_document_input_instance = InternalDocumentInput.from_json(json)
# print the JSON string representation of the object
print(InternalDocumentInput.to_json())

# convert the object into a dict
internal_document_input_dict = internal_document_input_instance.to_dict()
# create an instance of InternalDocumentInput from a dict
internal_document_input_from_dict = InternalDocumentInput.from_dict(internal_document_input_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


