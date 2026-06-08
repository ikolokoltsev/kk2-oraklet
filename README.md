# KK2 – Oraklet

A typed LLM chain with FastAPI and SmolLLM.

Oraklet is a REST API that accepts a CSV dataset, analyzes it with Pandas, and answers
natural-language questions about the data using a local SmolLLM model. The whole
question → prompt → model → answer flow runs through a custom, strongly-typed
`Runnable` chain composed with the `|` operator:

```
oraklet = PromptBuilder() | LLMRunner() | ResponseParser()
```

## Requirements

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/) for dependency management
- ~300 MB disk for the model (downloaded automatically on first `/ai/ask` call)

## Installation

```bash
uv sync
```

This creates a virtual environment and installs all dependencies from `pyproject.toml`.

## Running the server

```bash
uv run uvicorn app.main:app --reload
```

The API is then available at http://localhost:8000, and interactive Swagger docs at
http://localhost:8000/docs.

> The first `/ai/ask` request downloads `HuggingFaceTB/SmolLM2-135M-Instruct` (~300 MB)
> and runs it on CPU. Expect a few seconds per answer — this is normal for a local model.

## Endpoints

| Method | Path           | Description                                                   |
| ------ | -------------- | ------------------------------------------------------------- |
| GET    | `/health`      | Liveness check                                                |
| POST   | `/data/upload` | Upload a CSV (form-data), store it in memory, return metadata |
| GET    | `/data/stats`  | Pandas `describe()` of the stored dataset as JSON             |
| POST   | `/ai/ask`      | Ask a question about the dataset; answered by the LLM chain   |

## Example calls

You can try everything interactively via Swagger at http://localhost:8000/docs, or with curl:

```bash
# Health
curl http://localhost:8000/health
# {"status": "ok"}

# Upload a dataset
curl -X POST http://localhost:8000/data/upload -F "file=@data.csv"
# {"rows": 150, "columns": ["city", "temp_c", ...], "dtypes": {"city": "object", ...}}

# Descriptive statistics
curl http://localhost:8000/data/stats
# Pandas describe() as JSON, keyed by column

# Ask a question
curl -X POST http://localhost:8000/ai/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Which city has the highest average temperature?"}'
# {
#   "question": "Which city has the highest average temperature?",
#   "answer": "...",
#   "model": "HuggingFaceTB/SmolLM2-135M-Instruct"
# }
```

## Error handling

| Situation                                           | Status |
| --------------------------------------------------- | ------ |
| Invalid extension / unreadable / empty CSV          | 400    |
| `/ai/ask` called before any dataset is uploaded     | 400    |
| `/data/stats` called before any dataset is uploaded | 404    |
| Upload larger than `MAX_FILE_SIZE_MB`               | 413    |
| Model error or timeout                              | 500    |

## Testing

```bash
uv run pytest app/tests/ -v # all tests
uv run pytest app/tests/ -v -k chain # only the Runnable-step tests
```

## Project structure

```
app/
├── main.py          # FastAPI app + routes
├── config.py        # Settings (pydantic-settings, reads .env)
├── schemas.py       # API request/response models
├── data.py          # Pandas helpers + in-memory dataset store
├── chain/
│   ├── runnable.py  # Generic Runnable[I, O], RunnableLambda, RunnableSequence
│   ├── steps.py     # PromptBuilder, LLMRunner, ResponseParser
│   └── pipeline.py  # oraklet = PromptBuilder() | LLMRunner() | ResponseParser()
└── tests/
    ├── test_endpoints.py
    └── test_chain.py
```

## Assumptions

- **Single in-memory dataset.** The uploaded dataset is held in a module-level variable,
  not a database. Uploading a new file replaces the previous one. The dataset is lost on
  server restart, and the design is not safe for concurrent users — it is sufficient for
  a single-user assignment but not for production.
- **CSV only.** Only `.csv` files are accepted. The reader tries UTF-8 first, then Latin-1;
  anything else is rejected with 400.
- **Local model on CPU.** The model runs locally via `transformers.pipeline`. No API key
  is required. The 135M model is small enough for a laptop but is limited in answer quality.
- **The model is treated as untrusted output.** `ResponseParser` extracts the relevant part
  of the raw generation rather than trusting it verbatim; answers may still be imperfect or
  hallucinated, as expected from a small model.

## Future plans

1. Update Rest API to SSR by using htmx to return a complete page.
2. Since we will have a page as an answer we can build a selector to pick an LLM version
   from the list, so we can pick the model depending on our needs.
3. Add authorization and sessions for separate loaded files, in the same way we have separated
   sessions in Claude, Chat GPT, etc.
4. Implement service with data preparation and cleaning configuration. So we can prepare
   data as we want for every csv we upload. Reason: we don't know the structure and dataset
   specifics upfront, so we need to have at least easy tools to make data cleaner.
