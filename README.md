# Red Teaming Platform

A tool for testing LLM safety by running adversarial prompts (jailbreaks, prompt injection, obfuscation) against models, logging inputs/outputs, scoring safety, and displaying results in a dashboard.

## Overview

This platform helps you:
- Test LLM models against various adversarial prompts
- Score responses for safety violations
- Track and compare results over time
- Export data for further analysis

Think of it as **unit tests, but for model safety instead of code**.

## Features

- **Multiple Attack Types**: Jailbreaks, prompt injection, obfuscation, and benign control prompts
- **Safety Scoring**: Confidence-based scoring with refusal detection
- **Dashboard UI**: Web interface to view and analyze results
- **Data Export**: CSV and JSON export for further analysis
- **Configurable**: Easy to add new LLM providers and attack types

## Tech Stack

- **Backend**: Python + FastAPI
- **Database**: SQLAlchemy with SQLite
- **Frontend**: Jinja2 templates (server-rendered HTML)
- **LLM Provider**: Configurable (OpenAI implemented)

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```
LLM_PROVIDER=openai
LLM_API_KEY=your-openai-api-key-here
DATABASE_URL=sqlite:///./red_teaming.db
SECRET_KEY=your-secret-key-here
```

### 3. Run the Application

```bash
uvicorn app.main:app --reload
```

The application will be available at:
- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Usage

### Starting an Evaluation Run

#### Via Web UI

1. Visit http://localhost:8000
2. Use the API documentation at `/docs` to start a new run
3. Or use curl:

```bash
curl -X POST "http://localhost:8000/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "gpt-3.5-turbo",
    "attack_set": "default"
  }'
```

#### Via Python

```python
import requests

response = requests.post(
    "http://localhost:8000/runs",
    json={
        "model_name": "gpt-3.5-turbo",
        "attack_set": "default"
    }
)
print(response.json())  # {"run_id": 1, "status": "completed"}
```

### Viewing Results

1. **List all runs**: Visit http://localhost:8000
2. **View run details**: Click on a run ID or visit http://localhost:8000/runs/{run_id}
3. **Export data**: Click "Export CSV" or "Export JSON" buttons

### API Endpoints

- `GET /` - Dashboard home (list of all runs)
- `GET /health` - Health check
- `POST /runs` - Start a new evaluation run
- `GET /runs` - List all runs (JSON)
- `GET /runs/{run_id}` - View run details (HTML)
- `GET /runs/{run_id}/status` - Get run status
- `GET /runs/{run_id}/export?format=csv` - Export as CSV
- `GET /runs/{run_id}/export?format=json` - Export as JSON

## Project Structure

```
red-teaming-platform/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app and routes
│   ├── config.py            # Configuration management
│   ├── models.py            # Database models
│   ├── database.py          # Database setup
│   ├── model_client.py      # LLM API client
│   ├── attacks.py           # Attack prompt generators
│   ├── scoring.py           # Safety scoring logic
│   ├── runner.py            # Evaluation orchestrator
│   └── templates/           # Jinja2 HTML templates
│       ├── base.html
│       ├── runs_list.html
│       └── run_detail.html
├── tests/                   # Unit tests (to be added)
├── .env.example             # Environment variable template
├── requirements.txt         # Python dependencies
└── README.md
```

## How It Works

1. **Attack Library** (`attacks.py`): Generates adversarial prompts
2. **Model Client** (`model_client.py`): Calls LLM APIs with rate limiting
3. **Scoring** (`scoring.py`): Evaluates responses for safety
4. **Runner** (`runner.py`): Orchestrates the entire evaluation
5. **Database** (`models.py`, `database.py`): Stores all results
6. **API & UI** (`main.py`, `templates/`): Web interface for viewing results

## Safety Considerations

⚠️ **Important**: This tool is designed for safety research within provider policies. All attack prompts are clearly labeled and intended to test model boundaries, not generate actual harmful content.

- Do NOT deploy this publicly without authentication
- Keep attack prompts within provider terms of service
- Use responsibly for legitimate safety research

## Future Enhancements

- [ ] Multiple model comparison
- [ ] Real-time progress tracking
- [ ] Custom attack set builder
- [ ] Charts and visualizations
- [ ] Embedding-based clustering of failures
- [ ] Async execution for faster runs
- [ ] Additional LLM providers (Anthropic, local models)

## License

MIT License - See LICENSE file for details
