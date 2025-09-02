# OZ Listings Document Processor

This project is an automated data pipeline to ingest real estate deal documents, extract structured data using AI, and create listings for the OZListings platform.

## Architecture Overview

The system is designed as a serverless, event-driven pipeline on Google Cloud Platform (GCP) that integrates with the existing Supabase infrastructure.

```mermaid
graph TD
    subgraph "Browser (oz-dev-dash)"
        A[Developer Uploads Multiple Files]
    end

    subgraph "Supabase"
        B[1. Upload to Supabase Storage<br/>(raw-docs bucket)]
        F[Supabase Postgres DB<br/>(listings_drafts table)]
    end

    subgraph "GCP"
        C[2. Supabase Webhook Trigger]
        D[3. Cloud Run Service (Processing Core)]
    end

    subgraph "Third-Party APIs"
        E[4. Mistral OCR API]
        G[5. Vertex AI Gemini API<br/>(with Search Grounding)]
    end

    A -- "Uploads via Supabase SDK" --> B
    B -- "On new files, sends webhook" --> C
    C -- "Directly triggers" --> D
    D -- "a. Downloads & sends files to Mistral" --> E
    E -- "b. Returns structured Markdown" --> D
    D -- "c. Combines Markdown & sends prompt" --> G
    G -- "d. Returns final Listing JSON" --> D
    D -- "e. Writes JSON to DB" --> F
```

### Technology Stack

*   **Language:** Python 3.14
*   **Package Management:** `uv` (for speed and modern tooling)
*   **Cloud Platform:** Google Cloud Platform (GCP)
*   **Core Services:**
    *   **Cloud Run:** Hosts the main containerized Python application with an HTTP endpoint that receives webhooks directly from Supabase.
*   **Third-Party AI Services:**
    *   **Mistral OCR API:** For converting uploaded documents (PDFs, images) into structured Markdown text while preserving document layout and structure.
    *   **Vertex AI Gemini API:** For generating the final structured JSON response using the detailed instructions from `oz-dev-dash/docs/perplexity-prompt.md`. Gemini's search grounding capability provides access to current market data and real estate trends.
*   **Database:** Supabase Postgres (your existing database).
*   **File Storage:** Supabase Storage (for both raw document uploads and processed images).

## Workflow

1.  **File Upload:** A developer uploads multiple documents (PDFs, scanned images, etc.) via a new UI component in the `oz-dev-dash` admin panel. The frontend uses the Supabase SDK to upload directly to a new `raw-docs` bucket in your existing Supabase Storage.

2.  **Pipeline Trigger:** When the upload completes, Supabase sends a webhook directly to your Cloud Run service's HTTP endpoint. The webhook contains information about all the uploaded files.

3.  **Core Processing:** The Cloud Run service performs the main logic:
    a.  **Document Processing Loop:** The service iterates through each uploaded document sequentially (for simplicity - parallel processing can be added later when needed).
    b.  **OCR with Mistral:** For each document, the service downloads it from Supabase Storage and sends it to the Mistral OCR API. Mistral performs OCR and returns structured Markdown that preserves the document's layout, tables, and formatting.
    c.  **Content Consolidation:** After all documents are processed, the service concatenates all the Markdown outputs into a single, comprehensive context document.
    d.  **AI Data Extraction:** The service then calls the Vertex AI Gemini API with:
        *   The detailed instructions from `oz-dev-dash/docs/perplexity-prompt.md` as the system prompt
        *   The consolidated Markdown from all documents as the user input
        *   Search grounding enabled to access current market data and real estate trends
    e.  **Process Response:** Gemini returns a structured JSON object matching the `Listing` type. This JSON is validated against the expected schema.
    f.  **Image Handling:** Any images extracted during the OCR process are uploaded to your existing Supabase Storage bucket.
    g.  **Finalize Data:** The public URLs for the images are inserted into the JSON, and the final, complete `Listing` object is written to a `listings_drafts` table in your Supabase Postgres database.

4.  **Human Review:** The `oz-dev-dash` frontend reads from the `listings_drafts` table to allow for a final review and approval step.

## Project Setup

### Local Development

1.  **Install `uv`** (if not already installed):
    ```shell
    # macOS/Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Windows
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    # Or via pip
    pip install uv
    ```

2.  **Clone and setup the project:**
    ```shell
    cd oz-doc-processor
    uv sync
    ```
    
    This single command will:
    - Automatically create a virtual environment with Python 3.13
    - Install all dependencies from `pyproject.toml`
    - Generate a lock file for reproducible builds

3.  **Activate the environment:**
    ```shell
    source .venv/bin/activate
    ```

### Dependencies (pyproject.toml)

The project uses modern Python package management with `pyproject.toml`:

```toml
[project]
dependencies = [
    "requests>=2.32.5",
    "python-dotenv>=1.1.1", 
    "pandas>=2.3.2",
    "numpy>=2.3.2",
    "jsonschema>=4.25.1",
    "rich>=14.1.0"
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.4.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.28.1",
    "python-dateutil>=2.9.0"
]
```

**Key packages:**
- **FastAPI/Uvicorn:** Web server (to be added)
- **Supabase:** Database client (to be added)
- **Mistral AI/Vertex AI:** AI processing APIs (to be added)
- **Pillow:** Image processing (to be added)
- **Rich:** Beautiful terminal output

### `Dockerfile` for Cloud Run

This Dockerfile includes all necessary system dependencies for the processing libraries.

```dockerfile
# Use a slim, modern Python base image
FROM python:3.14-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
    libtiff-dev \
    libopenjp2-7-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy requirements and install python packages using uv
COPY ./requirements.txt /app/requirements.txt
RUN uv pip install --no-cache -r /app/requirements.txt --system

# Copy the rest of your application code
COPY . /app

# Expose the port the app will run on
EXPOSE 8080

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

## Cloud Run Configuration

When deploying to Cloud Run, the following settings are recommended as a starting point:

*   **CPU:** 2 vCPUs
*   **Memory:** 2 GiB
*   **Request Timeout:** 15-30 minutes
*   **Concurrency:** 1 (Crucial for ensuring one batch of documents is processed at a time per instance)

## API Integration Examples

### Mistral OCR API

**Official Documentation:** [Mistral AI OCR API](https://docs.mistral.ai/api/ocr/)

**Basic Usage:**
```python
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

# Initialize client
client = MistralClient(api_key="your-api-key")

# Process a document with OCR
response = client.ocr.process(
    file="path/to/document.pdf",
    model="mistral-large-latest"
)

# The response contains structured Markdown
markdown_content = response.content
```

**Handling Multiple Documents:**
```python
import asyncio
from mistralai.async_client import MistralAsyncClient

async def process_documents(documents):
    client = MistralAsyncClient(api_key="your-api-key")
    
    results = []
    for doc in documents:
        # Process each document sequentially
        response = await client.ocr.process(
            file=doc,
            model="mistral-large-latest"
        )
        results.append(response.content)
    
    return results
```

### Vertex AI Gemini API (with Search Grounding)

**Official Documentation:** [Vertex AI Gemini API](https://cloud.google.com/vertex-ai/docs/generative-ai/grounding)

**Basic Usage with Search Grounding:**
```python
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel, Tool

# Initialize Vertex AI
aiplatform.init(project="your-project-id", location="us-central1")

# Create the Gemini model with search grounding
model = GenerativeModel("gemini-1.5-flash")

# Enable Google Search grounding
tool = Tool.from_google_search_retrieval(
    max_snippets=10,
    max_chunks_per_snippet=3
)

# Generate content with search grounding
response = model.generate_content(
    "What are the latest trends in opportunity zone real estate investments?",
    tools=[tool]
)
```

**Complete Listing Generation Example:**
```python
def generate_listing_json(consolidated_markdown, system_prompt):
    """
    Generate structured listing JSON using Gemini with search grounding
    """
    model = GenerativeModel("gemini-1.5-flash")
    
    # Enable search grounding for current market data
    search_tool = Tool.from_google_search_retrieval(
        max_snippets=15,
        max_chunks_per_snippet=5
    )
    
    # Create the prompt
    prompt = f"""
    {system_prompt}
    
    Please analyze the following real estate deal documents and generate a structured JSON response:
    
    {consolidated_markdown}
    
    Return only valid JSON matching the specified schema.
    """
    
    response = model.generate_content(
        prompt,
        tools=[search_tool],
        generation_config={
            "temperature": 0.1,  # Low temperature for consistent output
            "max_output_tokens": 8192
        }
    )
    
    return response.text
```

## Security Considerations

*   **Webhook Authentication:** The Cloud Run service must validate that incoming webhooks are actually from Supabase by checking a shared secret token.
*   **API Keys:** Store your Mistral and Vertex AI API keys securely in GCP Secret Manager.
*   **File Access:** Ensure the service only has access to the specific Supabase Storage buckets it needs.

## Cost Considerations

This system will incur costs from three sources:
*   **GCP Cloud Run:** For compute resources
*   **Mistral OCR API:** Approximately $1 per 1000 pages processed
*   **Vertex AI Gemini API:** For the final LLM call to generate the structured JSON (with search grounding)

## Future Enhancements

*   **Parallel Processing:** When performance becomes a bottleneck, the sequential document processing loop can be upgraded to use Python's `asyncio` for concurrent API calls to Mistral.
*   **Batch Processing:** For very large document sets, consider implementing a queue-based system that can process documents in smaller batches.
*   **Caching:** Implement caching for OCR results to avoid re-processing the same documents. 