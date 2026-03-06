# WikiSourcesResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**sources** | [**List[WikiSourceOption]**](WikiSourceOption.md) |  | 

## Example

```python
from openapi_client.models.wiki_sources_response import WikiSourcesResponse

# TODO update the JSON string below
json = "{}"
# create an instance of WikiSourcesResponse from a JSON string
wiki_sources_response_instance = WikiSourcesResponse.from_json(json)
# print the JSON string representation of the object
print(WikiSourcesResponse.to_json())

# convert the object into a dict
wiki_sources_response_dict = wiki_sources_response_instance.to_dict()
# create an instance of WikiSourcesResponse from a dict
wiki_sources_response_from_dict = WikiSourcesResponse.from_dict(wiki_sources_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


