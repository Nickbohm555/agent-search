# CitationSourceRow


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**citation_index** | **int** |  | 
**content** | **str** |  | [optional] [default to '']
**document_id** | **str** |  | [optional] [default to '']
**rank** | **int** |  | 
**score** | **float** |  | [optional] 
**source** | **str** |  | [optional] [default to '']
**title** | **str** |  | [optional] [default to '']

## Example

```python
from openapi_client.models.citation_source_row import CitationSourceRow

# TODO update the JSON string below
json = "{}"
# create an instance of CitationSourceRow from a JSON string
citation_source_row_instance = CitationSourceRow.from_json(json)
# print the JSON string representation of the object
print(CitationSourceRow.to_json())

# convert the object into a dict
citation_source_row_dict = citation_source_row_instance.to_dict()
# create an instance of CitationSourceRow from a dict
citation_source_row_from_dict = CitationSourceRow.from_dict(citation_source_row_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


