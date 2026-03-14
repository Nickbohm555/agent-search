# agent-search generated HTTP SDK

This package is the generated Python client for the public `agent-search` HTTP API. Use it when you need the same request and response shapes exposed by `/api/agents/run`, `/run-async`, and `/run-resume`.

Canonical request names for new integrations:

- `controls`
- `runtime_config`
- `custom_prompts`

Canonical response read for sub-answers:

- `sub_answers`, with `sub_qa` kept as a compatibility fallback

## Requirements

Python 3.11+

## Installation

Install the generated client from this repository:

```bash
python -m pip install --upgrade pip
pip install -e ./sdk/python
```

If you only need the in-process sync SDK, install `agent-search-core` instead:

```bash
pip install agent-search-core
```

## Sync run with controls, runtime_config, and custom_prompts

```python
import openapi_client
from openapi_client.models.runtime_agent_run_controls import RuntimeAgentRunControls
from openapi_client.models.runtime_agent_run_request import RuntimeAgentRunRequest
from openapi_client.models.runtime_agent_run_runtime_config import RuntimeAgentRunRuntimeConfig
from openapi_client.models.runtime_custom_prompts import RuntimeCustomPrompts
from openapi_client.models.runtime_hitl_control import RuntimeHitlControl
from openapi_client.models.runtime_query_expansion_control import RuntimeQueryExpansionControl
from openapi_client.models.runtime_rerank_control import RuntimeRerankControl
from openapi_client.models.runtime_subquestion_hitl_control import RuntimeSubquestionHitlControl

configuration = openapi_client.Configuration(host="http://localhost:8000")

with openapi_client.ApiClient(configuration) as api_client:
    api = openapi_client.AgentsApi(api_client)
    response = api.runtime_agent_run_api_agents_run_post(
        RuntimeAgentRunRequest(
            query="What changed in the runtime?",
            controls=RuntimeAgentRunControls(
                rerank=RuntimeRerankControl(enabled=True),
                query_expansion=RuntimeQueryExpansionControl(enabled=True),
                hitl=RuntimeHitlControl(
                    subquestions=RuntimeSubquestionHitlControl(enabled=True),
                ),
            ),
            runtime_config=RuntimeAgentRunRuntimeConfig(
                rerank=RuntimeRerankControl(enabled=True),
                query_expansion=RuntimeQueryExpansionControl(enabled=True),
            ),
            custom_prompts=RuntimeCustomPrompts(
                subanswer="Answer each sub-question with concise cited evidence only.",
                synthesis="Write a short synthesis that preserves citation markers.",
            ),
        )
    )

    sub_answers = response.sub_answers or response.sub_qa or []
    print(response.output)
    print(len(sub_answers))
```

Compatibility notes:

- Omit `controls` and `runtime_config` to preserve prior behavior.
- Omit `custom_prompts` to keep built-in prompt defaults.
- `custom-prompts` is still accepted by the backend as an input alias, but new code should send `custom_prompts`.

## Async HITL start and typed resume

```python
import openapi_client
from openapi_client.models.runtime_agent_run_controls import RuntimeAgentRunControls
from openapi_client.models.runtime_agent_run_request import RuntimeAgentRunRequest
from openapi_client.models.runtime_agent_run_resume_request import RuntimeAgentRunResumeRequest
from openapi_client.models.runtime_hitl_control import RuntimeHitlControl
from openapi_client.models.runtime_subquestion_decision import RuntimeSubquestionDecision
from openapi_client.models.runtime_subquestion_hitl_control import RuntimeSubquestionHitlControl
from openapi_client.models.runtime_subquestion_resume_envelope import RuntimeSubquestionResumeEnvelope

configuration = openapi_client.Configuration(host="http://localhost:8000")

with openapi_client.ApiClient(configuration) as api_client:
    api = openapi_client.AgentsApi(api_client)
    started = api.runtime_agent_run_async_api_agents_run_async_post(
        RuntimeAgentRunRequest(
            query="Review the proposed sub-questions.",
            controls=RuntimeAgentRunControls(
                hitl=RuntimeHitlControl(
                    subquestions=RuntimeSubquestionHitlControl(enabled=True),
                ),
            ),
        )
    )

    resumed = api.runtime_agent_run_resume_api_agents_run_resume_job_id_post(
        started.job_id,
        RuntimeAgentRunResumeRequest(
            resume=RuntimeSubquestionResumeEnvelope(
                checkpoint_id="chk_123",
                decisions=[
                    RuntimeSubquestionDecision(
                        subquestion_id="sq_1",
                        action="approve",
                    )
                ],
            )
        ),
    )

    print(started.job_id, resumed.status)
```

Legacy `resume=True` still works. Use typed envelopes for new HITL flows because they require `checkpoint_id` and explicit decisions.

## Reading additive sub_answers safely

```python
sub_answers = response.sub_answers or response.sub_qa or []
for item in sub_answers:
    print(item.sub_question, item.sub_answer)
```

`sub_answers` is additive. Keep the `sub_qa` fallback until every deployed client reads the new field.

## Release alignment

Use these docs together when upgrading:

- [Migration guide](../../docs/migration-guide.md)
- [1.0.3 release notes](../../docs/releases/1.0.3-sdk-contract-parity.md)
- [Core SDK README](../core/README.md)

## Documentation for API Endpoints

All URIs are relative to *http://localhost*

Class | Method | HTTP request | Description
------------ | ------------- | ------------- | -------------
*AgentsApi* | [**runtime_agent_run_api_agents_run_post**](docs/AgentsApi.md#runtime_agent_run_api_agents_run_post) | **POST** /api/agents/run | Runtime Agent Run
*AgentsApi* | [**runtime_agent_run_async_api_agents_run_async_post**](docs/AgentsApi.md#runtime_agent_run_async_api_agents_run_async_post) | **POST** /api/agents/run-async | Runtime Agent Run Async
*AgentsApi* | [**runtime_agent_run_cancel_api_agents_run_cancel_job_id_post**](docs/AgentsApi.md#runtime_agent_run_cancel_api_agents_run_cancel_job_id_post) | **POST** /api/agents/run-cancel/{job_id} | Runtime Agent Run Cancel
*AgentsApi* | [**runtime_agent_run_events_api_agents_run_events_job_id_get**](docs/AgentsApi.md#runtime_agent_run_events_api_agents_run_events_job_id_get) | **GET** /api/agents/run-events/{job_id} | Runtime Agent Run Events
*AgentsApi* | [**runtime_agent_run_resume_api_agents_run_resume_job_id_post**](docs/AgentsApi.md#runtime_agent_run_resume_api_agents_run_resume_job_id_post) | **POST** /api/agents/run-resume/{job_id} | Runtime Agent Run Resume
*AgentsApi* | [**runtime_agent_run_status_api_agents_run_status_job_id_get**](docs/AgentsApi.md#runtime_agent_run_status_api_agents_run_status_job_id_get) | **GET** /api/agents/run-status/{job_id} | Runtime Agent Run Status
*DefaultApi* | [**health_api_health_get**](docs/DefaultApi.md#health_api_health_get) | **GET** /api/health | Health
*InternalDataApi* | [**list_wiki_sources_api_internal_data_wiki_sources_get**](docs/InternalDataApi.md#list_wiki_sources_api_internal_data_wiki_sources_get) | **GET** /api/internal-data/wiki-sources | List Wiki Sources
*InternalDataApi* | [**load_cancel_api_internal_data_load_cancel_job_id_post**](docs/InternalDataApi.md#load_cancel_api_internal_data_load_cancel_job_id_post) | **POST** /api/internal-data/load-cancel/{job_id} | Load Cancel
*InternalDataApi* | [**load_data_api_internal_data_load_post**](docs/InternalDataApi.md#load_data_api_internal_data_load_post) | **POST** /api/internal-data/load | Load Data
*InternalDataApi* | [**load_data_async_api_internal_data_load_async_post**](docs/InternalDataApi.md#load_data_async_api_internal_data_load_async_post) | **POST** /api/internal-data/load-async | Load Data Async
*InternalDataApi* | [**load_status_api_internal_data_load_status_job_id_get**](docs/InternalDataApi.md#load_status_api_internal_data_load_status_job_id_get) | **GET** /api/internal-data/load-status/{job_id} | Load Status
*InternalDataApi* | [**wipe_data_api_internal_data_wipe_post**](docs/InternalDataApi.md#wipe_data_api_internal_data_wipe_post) | **POST** /api/internal-data/wipe | Wipe Data


## Documentation For Models

 - [AgentRunStageMetadata](docs/AgentRunStageMetadata.md)
 - [CitationSourceRow](docs/CitationSourceRow.md)
 - [HTTPValidationError](docs/HTTPValidationError.md)
 - [InternalDataLoadJobCancelResponse](docs/InternalDataLoadJobCancelResponse.md)
 - [InternalDataLoadJobStartResponse](docs/InternalDataLoadJobStartResponse.md)
 - [InternalDataLoadJobStatusResponse](docs/InternalDataLoadJobStatusResponse.md)
 - [InternalDataLoadRequest](docs/InternalDataLoadRequest.md)
 - [InternalDataLoadResponse](docs/InternalDataLoadResponse.md)
 - [InternalDocumentInput](docs/InternalDocumentInput.md)
 - [LocationInner](docs/LocationInner.md)
 - [Resume](docs/Resume.md)
 - [RuntimeAgentRunAsyncCancelResponse](docs/RuntimeAgentRunAsyncCancelResponse.md)
 - [RuntimeAgentRunAsyncStartResponse](docs/RuntimeAgentRunAsyncStartResponse.md)
 - [RuntimeAgentRunAsyncStatusResponse](docs/RuntimeAgentRunAsyncStatusResponse.md)
 - [RuntimeAgentRunControls](docs/RuntimeAgentRunControls.md)
 - [RuntimeAgentRunRequest](docs/RuntimeAgentRunRequest.md)
 - [RuntimeAgentRunResponse](docs/RuntimeAgentRunResponse.md)
 - [RuntimeAgentRunResumeRequest](docs/RuntimeAgentRunResumeRequest.md)
 - [RuntimeAgentRunRuntimeConfig](docs/RuntimeAgentRunRuntimeConfig.md)
 - [RuntimeCustomPrompts](docs/RuntimeCustomPrompts.md)
 - [RuntimeHitlControl](docs/RuntimeHitlControl.md)
 - [RuntimeQueryExpansionControl](docs/RuntimeQueryExpansionControl.md)
 - [RuntimeQueryExpansionDecision](docs/RuntimeQueryExpansionDecision.md)
 - [RuntimeQueryExpansionHitlControl](docs/RuntimeQueryExpansionHitlControl.md)
 - [RuntimeQueryExpansionResumeEnvelope](docs/RuntimeQueryExpansionResumeEnvelope.md)
 - [RuntimeRerankControl](docs/RuntimeRerankControl.md)
 - [RuntimeSubquestionDecision](docs/RuntimeSubquestionDecision.md)
 - [RuntimeSubquestionHitlControl](docs/RuntimeSubquestionHitlControl.md)
 - [RuntimeSubquestionResumeEnvelope](docs/RuntimeSubquestionResumeEnvelope.md)
 - [SubQuestionAnswer](docs/SubQuestionAnswer.md)
 - [SubQuestionArtifacts](docs/SubQuestionArtifacts.md)
 - [ValidationError](docs/ValidationError.md)
 - [WikiLoadInput](docs/WikiLoadInput.md)
 - [WikiSourceOption](docs/WikiSourceOption.md)
 - [WikiSourcesResponse](docs/WikiSourcesResponse.md)
 - [WipeResponse](docs/WipeResponse.md)


<a id="documentation-for-authorization"></a>
## Documentation For Authorization

Endpoints do not require authorization.


## Author

