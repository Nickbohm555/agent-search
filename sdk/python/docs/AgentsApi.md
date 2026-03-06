# openapi_client.AgentsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**runtime_agent_run_api_agents_run_post**](AgentsApi.md#runtime_agent_run_api_agents_run_post) | **POST** /api/agents/run | Runtime Agent Run


# **runtime_agent_run_api_agents_run_post**
> RuntimeAgentRunResponse runtime_agent_run_api_agents_run_post(runtime_agent_run_request)

Runtime Agent Run

### Example


```python
import openapi_client
from openapi_client.models.runtime_agent_run_request import RuntimeAgentRunRequest
from openapi_client.models.runtime_agent_run_response import RuntimeAgentRunResponse
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.AgentsApi(api_client)
    runtime_agent_run_request = openapi_client.RuntimeAgentRunRequest() # RuntimeAgentRunRequest | 

    try:
        # Runtime Agent Run
        api_response = api_instance.runtime_agent_run_api_agents_run_post(runtime_agent_run_request)
        print("The response of AgentsApi->runtime_agent_run_api_agents_run_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgentsApi->runtime_agent_run_api_agents_run_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **runtime_agent_run_request** | [**RuntimeAgentRunRequest**](RuntimeAgentRunRequest.md)|  | 

### Return type

[**RuntimeAgentRunResponse**](RuntimeAgentRunResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

