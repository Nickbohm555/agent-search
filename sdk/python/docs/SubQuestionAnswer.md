# SubQuestionAnswer


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**answerable** | **bool** |  | [optional] [default to False]
**expanded_query** | **str** |  | [optional] [default to '']
**sub_agent_response** | **str** |  | [optional] [default to '']
**sub_answer** | **str** |  | 
**sub_question** | **str** |  | 
**tool_call_input** | **str** |  | [optional] [default to '']
**verification_reason** | **str** |  | [optional] [default to '']

## Example

```python
from openapi_client.models.sub_question_answer import SubQuestionAnswer

# TODO update the JSON string below
json = "{}"
# create an instance of SubQuestionAnswer from a JSON string
sub_question_answer_instance = SubQuestionAnswer.from_json(json)
# print the JSON string representation of the object
print(SubQuestionAnswer.to_json())

# convert the object into a dict
sub_question_answer_dict = sub_question_answer_instance.to_dict()
# create an instance of SubQuestionAnswer from a dict
sub_question_answer_from_dict = SubQuestionAnswer.from_dict(sub_question_answer_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


