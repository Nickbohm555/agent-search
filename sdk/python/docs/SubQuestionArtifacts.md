# SubQuestionArtifacts


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**citation_rows_by_index** | [**Dict[str, CitationSourceRow]**](CitationSourceRow.md) |  | [optional] 
**expanded_queries** | **List[str]** |  | [optional] 
**reranked_docs** | [**List[CitationSourceRow]**](CitationSourceRow.md) |  | [optional] 
**retrieval_provenance** | **List[object]** |  | [optional] 
**retrieved_docs** | [**List[CitationSourceRow]**](CitationSourceRow.md) |  | [optional] 
**sub_answer** | **str** |  | [optional] [default to '']
**sub_question** | **str** |  | 

## Example

```python
from openapi_client.models.sub_question_artifacts import SubQuestionArtifacts

# TODO update the JSON string below
json = "{}"
# create an instance of SubQuestionArtifacts from a JSON string
sub_question_artifacts_instance = SubQuestionArtifacts.from_json(json)
# print the JSON string representation of the object
print(SubQuestionArtifacts.to_json())

# convert the object into a dict
sub_question_artifacts_dict = sub_question_artifacts_instance.to_dict()
# create an instance of SubQuestionArtifacts from a dict
sub_question_artifacts_from_dict = SubQuestionArtifacts.from_dict(sub_question_artifacts_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


