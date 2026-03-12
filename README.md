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

The adaptive algorithm starts every student at a default ability score of `0.5`. Each question has a predefined difficulty score between `0.1` and `1.0`, and after every response the system compares the student’s current ability with the question difficulty using a simple 1D IRT-inspired logistic model.

If the student answers correctly, their ability score increases, and if they answer incorrectly, it decreases. The size of the update depends on how expected the outcome was. A correct answer on a harder question increases ability more than a correct answer on an easy one, while an incorrect answer on an easy question lowers ability more than missing a hard question. The updated score is then added to a safe range so it stays between the configured floor and ceiling.

For the next question, the engine selects an unanswered item whose difficulty is closest to the student’s updated ability score. It also applies light topic balancing so the test does not keep selecting too many questions from the same topic in a row. This makes the test progressively adapt to the student’s estimated proficiency while still covering a reasonable spread of topics.

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

AI tools were used to speed up planning and implementation of the project. They helped in organizing the project structure, refining parts of the FastAPI API design, and improving documentation wording. Most of the implementation work, debugging, and testing flow still depended on manual review and local verification. 

The main challenges AI could not solve on its own were environment-specific issues. In particular, dependency compatibility on Python 3.14 required manual adjustment of package versions, and MongoDB connectivity had to be debugged based on the local machine setup. AI could suggest likely fixes, but verifying runtime behavior, checking installed tools, and resolving infrastructure issues still required direct manual validation.

## API Documentation

### `GET /health`
Basic health-check endpoint to confirm that the API is running.

### `POST /admin/seed`
Seeds the MongoDB `questions` collection with the GRE-style sample question bank.

Response fields:
- `inserted_count`: number of newly inserted questions
- `updated_count`: number of existing questions updated by `question_id`
- `total_questions`: total number of questions in the collection

### `POST /sessions`
Creates a new adaptive test session and returns the first question.

Response fields:
- `session_id`: unique session identifier
- `ability_score`: starting ability value
- `question`: first question object
- `remaining_questions`: number of questions left in the session

### `POST /sessions/{session_id}/answers`
Submits an answer for the current question, updates the student’s ability estimate, and returns either the next question or the final session summary.

Request body:
```json
{
  "question_id": "alg-001",
  "selected_answer": "B"
}

