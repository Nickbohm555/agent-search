# openapi_client.AgentsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**runtime_agent_run_api_agents_run_post**](AgentsApi.md#runtime_agent_run_api_agents_run_post) | **POST** /api/agents/run | Runtime Agent Run
[**runtime_agent_run_async_api_agents_run_async_post**](AgentsApi.md#runtime_agent_run_async_api_agents_run_async_post) | **POST** /api/agents/run-async | Runtime Agent Run Async
[**runtime_agent_run_cancel_api_agents_run_cancel_job_id_post**](AgentsApi.md#runtime_agent_run_cancel_api_agents_run_cancel_job_id_post) | **POST** /api/agents/run-cancel/{job_id} | Runtime Agent Run Cancel
[**runtime_agent_run_status_api_agents_run_status_job_id_get**](AgentsApi.md#runtime_agent_run_status_api_agents_run_status_job_id_get) | **GET** /api/agents/run-status/{job_id} | Runtime Agent Run Status


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

# **runtime_agent_run_async_api_agents_run_async_post**
> RuntimeAgentRunAsyncStartResponse runtime_agent_run_async_api_agents_run_async_post(runtime_agent_run_request)

Runtime Agent Run Async

### Example


```python
import openapi_client
from openapi_client.models.runtime_agent_run_async_start_response import RuntimeAgentRunAsyncStartResponse
from openapi_client.models.runtime_agent_run_request import RuntimeAgentRunRequest
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
        # Runtime Agent Run Async
        api_response = api_instance.runtime_agent_run_async_api_agents_run_async_post(runtime_agent_run_request)
        print("The response of AgentsApi->runtime_agent_run_async_api_agents_run_async_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgentsApi->runtime_agent_run_async_api_agents_run_async_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **runtime_agent_run_request** | [**RuntimeAgentRunRequest**](RuntimeAgentRunRequest.md)|  | 

### Return type

[**RuntimeAgentRunAsyncStartResponse**](RuntimeAgentRunAsyncStartResponse.md)

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

# **runtime_agent_run_cancel_api_agents_run_cancel_job_id_post**
> RuntimeAgentRunAsyncCancelResponse runtime_agent_run_cancel_api_agents_run_cancel_job_id_post(job_id)

Runtime Agent Run Cancel

### Example


```python
import openapi_client
from openapi_client.models.runtime_agent_run_async_cancel_response import RuntimeAgentRunAsyncCancelResponse
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
    job_id = 'job_id_example' # str | 

    try:
        # Runtime Agent Run Cancel
        api_response = api_instance.runtime_agent_run_cancel_api_agents_run_cancel_job_id_post(job_id)
        print("The response of AgentsApi->runtime_agent_run_cancel_api_agents_run_cancel_job_id_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgentsApi->runtime_agent_run_cancel_api_agents_run_cancel_job_id_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **job_id** | **str**|  | 

### Return type

[**RuntimeAgentRunAsyncCancelResponse**](RuntimeAgentRunAsyncCancelResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **runtime_agent_run_status_api_agents_run_status_job_id_get**
> RuntimeAgentRunAsyncStatusResponse runtime_agent_run_status_api_agents_run_status_job_id_get(job_id)

Runtime Agent Run Status

### Example


```python
import openapi_client
from openapi_client.models.runtime_agent_run_async_status_response import RuntimeAgentRunAsyncStatusResponse
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
    job_id = 'job_id_example' # str | 

    try:
        # Runtime Agent Run Status
        api_response = api_instance.runtime_agent_run_status_api_agents_run_status_job_id_get(job_id)
        print("The response of AgentsApi->runtime_agent_run_status_api_agents_run_status_job_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AgentsApi->runtime_agent_run_status_api_agents_run_status_job_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **job_id** | **str**|  | 

### Return type

[**RuntimeAgentRunAsyncStatusResponse**](RuntimeAgentRunAsyncStatusResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

