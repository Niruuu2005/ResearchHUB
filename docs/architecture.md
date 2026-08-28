# ResearchLite — System Architecture & Specification

---

## 1. High-Level Architecture

ResearchLite is structured as a decoupled, asynchronous microservice that mediates between end-user clients and external knowledge registries.

```mermaid
flowchart TD
    Client["Client (Browser UI / REST Client)"]
    
    subgraph FastAPI Runtime
        Router["API Router (/health, /research, /papers)"]
        Service["Research Orchestration Service"]
        
        subgraph Adapters
            Wiki["Wikipedia Adapter"]
            OpenAlex["OpenAlex Adapter"]
            Crossref["Crossref Adapter"]
        end
        
        subgraph Pipeline Engines
            Dedup["Deduplication Engine"]
            Extractor["Key-Point Extractor"]
        end
    end
    
    subgraph External Public APIs
        ExtWiki[("Wikipedia REST API")]
        ExtAlex[("OpenAlex Works API")]
        ExtCross[("Crossref Works API")]
    end
    
    Client -->|HTTP Request| Router
    Router --> Service
    
    Service -.->|async query| Wiki
    Service -.->|async query| OpenAlex
    Service -.->|async query| Crossref
    
    Wiki --> ExtWiki
    OpenAlex --> ExtAlex
    Crossref --> ExtCross
    
    ExtWiki -.->|summary extract| Wiki
    ExtAlex -.->|works metadata| OpenAlex
    ExtCross -.->|bibliographic items| Crossref
    
    Wiki --> Service
    OpenAlex --> Dedup
    Crossref --> Dedup
    
    Dedup -->|unique papers| Service
    Service --> Extractor
    Extractor -->|synthesized payload| Router
    Router -->|JSON Response| Client
```

---

## 2. Asynchronous Execution & Sequence Diagram

The following sequence diagram illustrates the lifecycle of a `POST /research` request:

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Browser
    participant API as FastAPI Router
    participant Service as ResearchService
    participant Wiki as WikipediaService
    participant Alex as OpenAlexService
    participant Cross as CrossrefService

    User->>API: POST /research {"topic": "Quantum Computing"}
    API->>API: Validate input (Pydantic)
    API->>Service: perform_research("Quantum Computing")
    
    par Async Wikipedia Call
        Service->>Wiki: fetch_summary("Quantum Computing")
        Wiki->>Wiki: GET https://en.wikipedia.org/api/rest_v1/...
        Wiki-->>Service: (title, extract, url)
    and Async OpenAlex Call
        Service->>Alex: search_papers("Quantum Computing")
        Alex->>Alex: GET https://api.openalex.org/works?search=...
        Alex-->>Service: [Paper, Paper, ...]
    and Async Crossref Call
        Service->>Cross: search_papers("Quantum Computing")
        Cross->>Cross: GET https://api.crossref.org/works?query=...
        Cross-->>Service: [Paper, Paper, ...]
    end

    Service->>Service: Deduplicate papers by DOI & Title
    Service->>Service: Extract key points from summary
    Service->>Service: Assemble ResearchResponse + warnings
    Service-->>API: ResearchResponse
    API-->>User: HTTP 200 JSON Response
```

---

## 3. Data Model Architecture

```mermaid
classDiagram
    class ResearchRequest {
        +str topic
        +validate_and_strip_topic()
    }

    class Paper {
        +str title
        +List[str] authors
        +int year
        +str source
        +str url
        +str doi
    }

    class Source {
        +str name
        +str title
        +str url
    }

    class ResearchResponse {
        +str topic
        +str summary
        +List[str] key_points
        +List[Paper] papers
        +List[Source] sources
        +List[str] warnings
    }

    class HealthResponse {
        +str status
        +str service
        +str version
    }

    ResearchResponse *-- Paper
    ResearchResponse *-- Source
```

---

## 4. Resilience & Error Handling Architecture

The service adheres to the **Bulkhead and Fallback Pattern**:

1. **Isolation**: A slow or non-responsive provider does not exhaust thread pools because all operations run asynchronously on non-blocking event loops.
2. **Timeouts**: Every HTTP call is bounded by a client-level timeout (default: 10s).
3. **Graceful Fallback**: If an external provider returns an error, the exception is caught, added as a warning entry, and the response is served with the available data.
