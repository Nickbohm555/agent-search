# openapi_client.BenchmarksApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**cancel_run_api_benchmarks_runs_run_id_cancel_post**](BenchmarksApi.md#cancel_run_api_benchmarks_runs_run_id_cancel_post) | **POST** /api/benchmarks/runs/{run_id}/cancel | Cancel Run
[**compare_run_modes_api_benchmarks_runs_run_id_compare_get**](BenchmarksApi.md#compare_run_modes_api_benchmarks_runs_run_id_compare_get) | **GET** /api/benchmarks/runs/{run_id}/compare | Compare Run Modes
[**create_benchmark_run_api_benchmarks_runs_post**](BenchmarksApi.md#create_benchmark_run_api_benchmarks_runs_post) | **POST** /api/benchmarks/runs | Create Benchmark Run
[**get_run_api_benchmarks_runs_run_id_get**](BenchmarksApi.md#get_run_api_benchmarks_runs_run_id_get) | **GET** /api/benchmarks/runs/{run_id} | Get Run
[**list_runs_api_benchmarks_runs_get**](BenchmarksApi.md#list_runs_api_benchmarks_runs_get) | **GET** /api/benchmarks/runs | List Runs
[**wipe_benchmark_data_api_benchmarks_wipe_post**](BenchmarksApi.md#wipe_benchmark_data_api_benchmarks_wipe_post) | **POST** /api/benchmarks/wipe | Wipe Benchmark Data


# **cancel_run_api_benchmarks_runs_run_id_cancel_post**
> BenchmarkRunCancelResponse cancel_run_api_benchmarks_runs_run_id_cancel_post(run_id)

Cancel Run

### Example


```python
import openapi_client
from openapi_client.models.benchmark_run_cancel_response import BenchmarkRunCancelResponse
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
    api_instance = openapi_client.BenchmarksApi(api_client)
    run_id = 'run_id_example' # str | 

    try:
        # Cancel Run
        api_response = api_instance.cancel_run_api_benchmarks_runs_run_id_cancel_post(run_id)
        print("The response of BenchmarksApi->cancel_run_api_benchmarks_runs_run_id_cancel_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling BenchmarksApi->cancel_run_api_benchmarks_runs_run_id_cancel_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **run_id** | **str**|  | 

### Return type

[**BenchmarkRunCancelResponse**](BenchmarkRunCancelResponse.md)

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

# **compare_run_modes_api_benchmarks_runs_run_id_compare_get**
> BenchmarkRunCompareResponse compare_run_modes_api_benchmarks_runs_run_id_compare_get(run_id)

Compare Run Modes

### Example


```python
import openapi_client
from openapi_client.models.benchmark_run_compare_response import BenchmarkRunCompareResponse
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
    api_instance = openapi_client.BenchmarksApi(api_client)
    run_id = 'run_id_example' # str | 

    try:
        # Compare Run Modes
        api_response = api_instance.compare_run_modes_api_benchmarks_runs_run_id_compare_get(run_id)
        print("The response of BenchmarksApi->compare_run_modes_api_benchmarks_runs_run_id_compare_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling BenchmarksApi->compare_run_modes_api_benchmarks_runs_run_id_compare_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **run_id** | **str**|  | 

### Return type

[**BenchmarkRunCompareResponse**](BenchmarkRunCompareResponse.md)

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

# **create_benchmark_run_api_benchmarks_runs_post**
> BenchmarkRunCreateResponse create_benchmark_run_api_benchmarks_runs_post(benchmark_run_create_request)

Create Benchmark Run

### Example


```python
import openapi_client
from openapi_client.models.benchmark_run_create_request import BenchmarkRunCreateRequest
from openapi_client.models.benchmark_run_create_response import BenchmarkRunCreateResponse
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
    api_instance = openapi_client.BenchmarksApi(api_client)
    benchmark_run_create_request = openapi_client.BenchmarkRunCreateRequest() # BenchmarkRunCreateRequest | 

    try:
        # Create Benchmark Run
        api_response = api_instance.create_benchmark_run_api_benchmarks_runs_post(benchmark_run_create_request)
        print("The response of BenchmarksApi->create_benchmark_run_api_benchmarks_runs_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling BenchmarksApi->create_benchmark_run_api_benchmarks_runs_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **benchmark_run_create_request** | [**BenchmarkRunCreateRequest**](BenchmarkRunCreateRequest.md)|  | 

### Return type

[**BenchmarkRunCreateResponse**](BenchmarkRunCreateResponse.md)

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

# **get_run_api_benchmarks_runs_run_id_get**
> BenchmarkRunStatusResponse get_run_api_benchmarks_runs_run_id_get(run_id)

Get Run

### Example


```python
import openapi_client
from openapi_client.models.benchmark_run_status_response import BenchmarkRunStatusResponse
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
    api_instance = openapi_client.BenchmarksApi(api_client)
    run_id = 'run_id_example' # str | 

    try:
        # Get Run
        api_response = api_instance.get_run_api_benchmarks_runs_run_id_get(run_id)
        print("The response of BenchmarksApi->get_run_api_benchmarks_runs_run_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling BenchmarksApi->get_run_api_benchmarks_runs_run_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **run_id** | **str**|  | 

### Return type

[**BenchmarkRunStatusResponse**](BenchmarkRunStatusResponse.md)

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

# **list_runs_api_benchmarks_runs_get**
> BenchmarkRunListResponse list_runs_api_benchmarks_runs_get()

List Runs

### Example


```python
import openapi_client
from openapi_client.models.benchmark_run_list_response import BenchmarkRunListResponse
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
    api_instance = openapi_client.BenchmarksApi(api_client)

    try:
        # List Runs
        api_response = api_instance.list_runs_api_benchmarks_runs_get()
        print("The response of BenchmarksApi->list_runs_api_benchmarks_runs_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling BenchmarksApi->list_runs_api_benchmarks_runs_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**BenchmarkRunListResponse**](BenchmarkRunListResponse.md)

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

# **wipe_benchmark_data_api_benchmarks_wipe_post**
> BenchmarkWipeResponse wipe_benchmark_data_api_benchmarks_wipe_post()

Wipe Benchmark Data

### Example


```python
import openapi_client
from openapi_client.models.benchmark_wipe_response import BenchmarkWipeResponse
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
    api_instance = openapi_client.BenchmarksApi(api_client)

    try:
        # Wipe Benchmark Data
        api_response = api_instance.wipe_benchmark_data_api_benchmarks_wipe_post()
        print("The response of BenchmarksApi->wipe_benchmark_data_api_benchmarks_wipe_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling BenchmarksApi->wipe_benchmark_data_api_benchmarks_wipe_post: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**BenchmarkWipeResponse**](BenchmarkWipeResponse.md)

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

