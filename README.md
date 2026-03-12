# AI-Driven Adaptive Diagnostic Engine

A FastAPI-based backend prototype for a 1D adaptive diagnostic test. The system seeds a GRE-style question bank into MongoDB, starts quiz sessions, updates a student's estimated ability after each answer, and generates a 3-step study plan from their performance.

## Tech Stack

- Python
- FastAPI
- Pydantic
- MongoDB
- OpenAI API (optional, with fallback study-plan generation)
- Pytest

## Project Structure

```text
app/
  api/         # FastAPI route modules
  db/          # MongoDB helpers
  models/      # Pydantic schemas
  scripts/     # Seed data and CLI helpers
  services/    # Adaptive logic, session lifecycle, study plans
  config.py    # Environment-based settings
  main.py      # FastAPI app entrypoint
tests/         # Unit and API tests
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start MongoDB locally or provide an Atlas connection string.

## Environment Variables

These can be set in your shell or in a local `.env` file.

```env
APP_ENV=development
MONGO_URI=mongodb://localhost:27017
MONGO_DATABASE=adaptive_diagnostic_engine
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
TEST_QUESTION_LIMIT=10
BASELINE_ABILITY=0.5
ABILITY_FLOOR=0.1
ABILITY_CEILING=1.0
ABILITY_STEP_SCALE=0.18
```

## Running the Project

Start the FastAPI app with Uvicorn:

```bash
uvicorn app.main:app --reload
```

The API docs will be available at:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## Seeding Questions

You can seed the GRE-style question bank in either of these ways.

CLI:

```bash
python -m app.scripts.seed_questions
```

API:

```bash
curl -X POST http://127.0.0.1:8000/admin/seed
```

The seeding logic is unchanging and upserts by `question_id`.

## API Endpoints

- `GET /health`
- `POST /admin/seed`
- `POST /sessions`
- `POST /sessions/{session_id}/answers`
- `GET /sessions/{session_id}`
- `POST /sessions/{session_id}/study-plan`

## Example Flow

1. Seed the question bank.
2. Start a session:

```bash
curl -X POST http://127.0.0.1:8000/sessions
```

3. Submit an answer:

```bash
curl -X POST http://127.0.0.1:8000/sessions/<session_id>/answers \
  -H "Content-Type: application/json" \
  -d '{"question_id":"alg-001","selected_answer":"B"}'
```

4. Fetch session state:

```bash
curl http://127.0.0.1:8000/sessions/<session_id>
```

5. Generate the study plan after completion:

```bash
curl -X POST http://127.0.0.1:8000/sessions/<session_id>/study-plan
```

## Adaptive Algorithm

The adaptive engine uses a simple 1D IRT-inspired update rule:

- each session starts at a baseline ability score of `0.5`
- each question has a difficulty score from `0.1` to `1.0`
- after each answer, the engine computes an expected probability of success using a logistic function over `ability - difficulty`
- the ability score is updated by moving it toward `(observed - expected)` and then clamped to configured bounds
- the next question is chosen from unanswered items closest to the current ability estimate, with light topic balancing to avoid repeatedly selecting one topic

This is intentionally simpler than a full calibrated psychometric IRT model, but it is deterministic, explainable, and appropriate for a demo assignment.

## Study Plan Generation

After a session is completed, the service builds a compact performance summary:

- total correct and incorrect answers
- highest difficulty reached
- weakest topics
- per-topic performance breakdown

If `OPENAI_API_KEY` is configured, the service attempts to generate a short personalized 3-step study plan with the configured model. If no API key is present, or generation fails, the API returns a deterministic fallback study plan so the demo still works.

## Running Tests

Run the test suite with:

```bash
pytest
```

The tests use an in-memory fake database for service and API flow coverage, so they do not require a running MongoDB instance.

## AI Log

AI tools were used to speed up implementation planning, scaffolding, and iterative code generation. They were also used to help structure the adaptive-engine logic, test coverage, and README content.

Challenges that still require human review:

- dependency installation and runtime verification in the local environment
- final API behavior checks with a real MongoDB instance
- optional validation of the OpenAI integration path with a real API key
