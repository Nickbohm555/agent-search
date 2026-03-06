# openapi_client.InternalDataApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**list_wiki_sources_api_internal_data_wiki_sources_get**](InternalDataApi.md#list_wiki_sources_api_internal_data_wiki_sources_get) | **GET** /api/internal-data/wiki-sources | List Wiki Sources
[**load_data_api_internal_data_load_post**](InternalDataApi.md#load_data_api_internal_data_load_post) | **POST** /api/internal-data/load | Load Data
[**wipe_data_api_internal_data_wipe_post**](InternalDataApi.md#wipe_data_api_internal_data_wipe_post) | **POST** /api/internal-data/wipe | Wipe Data


# **list_wiki_sources_api_internal_data_wiki_sources_get**
> WikiSourcesResponse list_wiki_sources_api_internal_data_wiki_sources_get()

List Wiki Sources

Return curated wiki source options with loaded state for the UI.

### Example


```python
import openapi_client
from openapi_client.models.wiki_sources_response import WikiSourcesResponse
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
    api_instance = openapi_client.InternalDataApi(api_client)

    try:
        # List Wiki Sources
        api_response = api_instance.list_wiki_sources_api_internal_data_wiki_sources_get()
        print("The response of InternalDataApi->list_wiki_sources_api_internal_data_wiki_sources_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling InternalDataApi->list_wiki_sources_api_internal_data_wiki_sources_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**WikiSourcesResponse**](WikiSourcesResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **load_data_api_internal_data_load_post**
> InternalDataLoadResponse load_data_api_internal_data_load_post(internal_data_load_request)

Load Data

Load internal data from deterministic wiki source.

### Example


```python
import openapi_client
from openapi_client.models.internal_data_load_request import InternalDataLoadRequest
from openapi_client.models.internal_data_load_response import InternalDataLoadResponse
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
    api_instance = openapi_client.InternalDataApi(api_client)
    internal_data_load_request = openapi_client.InternalDataLoadRequest() # InternalDataLoadRequest | 

    try:
        # Load Data
        api_response = api_instance.load_data_api_internal_data_load_post(internal_data_load_request)
        print("The response of InternalDataApi->load_data_api_internal_data_load_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling InternalDataApi->load_data_api_internal_data_load_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **internal_data_load_request** | [**InternalDataLoadRequest**](InternalDataLoadRequest.md)|  | 

### Return type

[**InternalDataLoadResponse**](InternalDataLoadResponse.md)

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

# **wipe_data_api_internal_data_wipe_post**
> WipeResponse wipe_data_api_internal_data_wipe_post()

Wipe Data

Wipe all internal documents and chunks.

### Example


```python
import openapi_client
from openapi_client.models.wipe_response import WipeResponse
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
    api_instance = openapi_client.InternalDataApi(api_client)

    try:
        # Wipe Data
        api_response = api_instance.wipe_data_api_internal_data_wipe_post()
        print("The response of InternalDataApi->wipe_data_api_internal_data_wipe_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling InternalDataApi->wipe_data_api_internal_data_wipe_post: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**WipeResponse**](WipeResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

