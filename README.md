# Wellness Platform - (AI Assistant)

An AI-powered wellness platform with personalized meal planning, recipe management, nutrition tracking, and RAG-grounded generation.

## Project Overview

This project keeps the original health profile, analytics, auth, and dashboard features, then adds:

- Conversational wellness assistant with persistent chat history
- Multi-turn context handling with automatic history compression for long chats
- Structured tool/function calling for health metrics, goals, meal plans, recipes, nutrition, and chart payloads
- Natural-language chart requests (weight trend line, protein vs target bar, macro breakdown pie)
- Context-aware proactive visualization suggestions (protein/weight/macro conversations)
- Safety guardrails for medical boundaries, out-of-scope prompts, and PII protection
- Robust conversation input handling for empty, long, symbol-heavy, and code-like prompts
- Daily and weekly AI-generated meal plans
- Meal plan customization (swap/reorder/regenerate/manual add)
- Versioned meal plans with restore support
- Recipe search/filter/details and AI custom recipe generation
- Shopping list generation with categorization, quantity updates, and exclusions
- Nutrition tracking (calories/macros/micronutrients), progress bars, trend lines, micronutrient target comparison, and AI summaries
- Retrieval-Augmented Generation pipeline with >=500 ingredients and >=500 recipes
- Function-calling based nutrition calculations

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL
- Frontend: React + TypeScript + Vite + Tailwind + Recharts
- AI: OpenAI chat completions + tool/function-calling
- RAG: local embedding + vector similarity retrieval
- Containers: Docker + Docker Compose

## One-Command Setup (Docker Only)

1. Copy environment template:

```bash
cp .env.example .env
```

2. Start everything:

```bash
docker compose up --build
```

That command starts PostgreSQL, backend, runs migrations, seeds RAG data, and serves frontend.

## App URLs

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8001`
- Swagger docs: `http://localhost:8001/docs`

## Usage Guide

1. Register and verify email.
2. Create health profile (includes dietary + nutrition planning fields).
3. Open **Meal Plan**:
   - Profile data is reused and prefilled.
   - Generate daily or weekly plans.
   - Regenerate full plan or a single meal.
   - Reorder/swap meals and restore previous versions.
4. Open **Recipes**:
   - Search by text, ingredient, cuisine.
   - Generate custom recipe from RAG context.
   - Adjust servings (ingredients + nutrition recalculated via function calling).
   - Get ingredient substitutions.
5. Open **Shopping**:
   - Generate list from meal plan.
   - Items grouped to meaningful categories.
   - Update quantities or exclude items.
6. Open **Dashboard** and **Progress Charts**:
   - Daily calories/macros and target progress bars.
   - Micronutrient intake vs recommended daily values (Vitamin D, B12, Iron).
   - Weekly/monthly deficit-surplus trend lines.
   - AI nutrition highlights, deficiency recommendations, and food suggestions for specific micronutrients.
7. Open **Assistant**:
   - Ask conversational questions across health metrics, goals, meal plans, recipes, and nutrition.
   - Use follow-up prompts like "Can you tell me more about that?" and "Is that enough protein?".
   - Toggle response mode between concise and detailed.
   - Request charts by natural language and view chart previews directly in the conversation.
   - Markdown-style assistant responses (headings, bullets, bold emphasis) are rendered in the chat UI.
   - If you add or edit a custom meal in Meal Plan, the assistant reflects it on the next relevant meal query (no manual refresh required).

## Prompt Engineering Strategy

### Conversational Assistant System Prompt

The assistant uses a single structured system prompt that enforces:

- role and capability boundaries (wellness-only scope)
- response formatting expectations (scannable sections + bullets)
- concise vs detailed mode behavior
- safety constraints (no diagnosis, urgent-care escalation wording)
- privacy constraints (never reveal email/DOB/credentials/other-user data)
- tool usage instruction (must call tools for personal account data)

Prompt examples are embedded for health metrics, progress summaries, meal-plan summaries, and medical-boundary responses so output style is consistent across query types.

Meal planning uses **sequential prompting with 3 steps**:

1. **Strategy step**: derives calorie distribution, macro focus, and pacing from user profile.
2. **Structure step**: converts strategy into day-level meal slots and plan skeleton.
3. **Generation step**: creates concrete meals grounded with retrieved recipe context.

Few-shot style consistency is enforced with structured JSON prompts and schema-oriented responses.

## AI Model Selection Rationale

- `gpt-3.5-turbo` is used for recipe/plan reasoning because it offers a practical quality/latency/cost balance.
- The same model is used for assistant chat because requirements emphasize breadth of everyday queries and follow-ups over deep specialist reasoning.
- Nutrition calculations are **not trusted to free-form generation** and always run via explicit function execution.
- Temperature and top-p are adjusted by step:
  - lower temperature for deterministic strategy/structure
  - slightly higher temperature for meal variety
- Assistant settings:
  - concise mode: lower temperature for compact predictable answers
  - detailed mode: slightly higher temperature and larger token budget for fuller explanation

## RAG Implementation

Pipeline:

1. Database stores recipe + ingredient corpus.
2. Embeddings are generated for recipe text using lightweight local vectors.
3. Similarity retrieval ranks relevant recipes.
4. Retrieved context is injected into augmented prompt.
5. Final response is generated from augmented context.

Community-driven improvement support:

- Recipe rating endpoint (`/recipes/{id}/rate`) boosts higher-rated recipes in retrieval ranking.
- Verified recommendation feed (`/recipes/recommendations/verified`) highlights highly-rated approved recipes.
- Moderation workflow (`/recipes/moderation/queue`, `/recipes/{id}/moderate`) supports approve/reject/flag quality control.

## Data Model Decisions

### Units and Time Standards

- Solids: grams
- Liquids: milliliters
- Energy: kilocalories
- Time durations: minutes
- Date/time fields: ISO 8601

### Core Added Schemas

- `ingredients`: includes `id`/`label`/`unit`/`quantity`/`nutrition`
- `recipes`: includes all required fields (`id`, `title`, `cuisine`, `meal`, `servings`, `ingredients`, `summary`, `time`, `difficulty_level`, `dietary_tags`, `source`, `img`, `preparation`)
- `recipes.nutrition`: extended with `fiber_g`, `sugar_g`, `sodium_mg`, `glycemic_index`, `antioxidant_profile`, `nutrient_density_score`, `processing_level`, `environmental_impact`, and `satiety_index`
- `meal_plans` + `meal_plan_versions`: plan content + restorable history
- `nutrition_logs`: per-meal/per-day nutrition intake

### Preference Coverage

- Supports >=15 dietary preferences.
- Supports >=10 allergies/intolerances.

## Function Calling for Nutrition

Nutrition analysis uses `calculate_nutrition(ingredients, servings)` tool definitions and dispatch.

It is used for:

- meal nutrition totals
- recipe generation nutrition completion
- serving-size adjustment recalculations

## Conversational Assistant Architecture and Request Flow

### Two-layer architecture

- Conversation Layer (frontend + assistant API):
  - chat UI, input validation, response mode toggle, persistent history load
  - message storage and retrieval per authenticated user conversation
  - response rendering (structured text + optional chart payload)
- Data Access Layer (assistant tools):
  - health metrics and trend retrieval
  - goals/preferences retrieval
  - meal plan and recipe lookup
  - nutrition totals and target comparison
  - chart payload generation for line/bar/pie requests

### Request flow

1. User sends message in Assistant page.
2. Message is validated and persisted.
3. Context manager selects relevant recent messages and applies compression summary for long chats.
4. LLM receives system prompt + selected context and may call tools.
5. Tool outputs are merged into final response text (and optional chart payload).
6. Assistant response is persisted and rendered in chat.

## Conversation Management Approach

- Multi-turn support keeps at least 5+ turns available for reference resolution.
- Automatic compression activates for longer conversations (10+ user turns) and stores a rolling summary.
- Dynamic context management prioritizes recent messages and includes older messages matching the current topic.
- Visualization suggestions consider current prompt + recent topic context to recommend relevant charts.
- Conversation history is persisted in DB, enabling close/re-open continuity.

## Assistant Function Calling Details

Assistant tools (all scoped to `current_user` and validated):

- `get_health_metrics(metric_type, time_period)`
- `get_health_goals_and_preferences(include_preferences)`
- `get_meal_plan(timeframe)`
- `get_recipe_for_meal(meal_name, day_hint)`
- `get_nutrition_summary(period)`
- `get_chart_data(chart_kind, period)`

Function-call validations occur before retrieval (invalid enums, missing required fields, unauthorized cross-user IDs, and unavailable data all return structured errors).

## Error Handling and Recovery

### Covered Cases

- malformed JSON/tool arguments
- missing function parameters
- invalid values
- function execution failures
- timeouts
- AI rate limits
- connectivity/API errors
- empty chat messages and overly long chat input
- unsupported control characters (binary/hidden chars) in chat input
- symbol-heavy malformed chat input
- code-snippet style prompts handled gracefully with a wellness-scope redirect
- missing conversation or unauthorized conversation access
- missing profile/plan/log data for requested timeframe
- chart data unavailable for requested period

### Recovery

- fallback to direct deterministic nutrition function execution
- fallback deterministic assistant responses when model call fails
- graceful user-facing error messages
- meal generation fallbacks when model call fails

## Assistant Safety and Boundaries

- No medical diagnosis: urgent symptom prompts return immediate professional-care recommendation.
- PII protection: assistant can personalize with name only; no email, DOB, credentials, or other-user data is exposed.
- Prompt-injection boundary: assistant tools are always executed with authenticated `current_user` scope.
- Out-of-scope prompts are redirected to supported wellness capabilities.

## API Surface Added

- `POST /meal-plans/generate`
- `GET /meal-plans`, `GET /meal-plans/{id}`
- `POST /meal-plans/{id}/swap`
- `POST /meal-plans/{id}/manual-add`
- `POST /meal-plans/{id}/regenerate`
- `GET /meal-plans/{id}/alternatives`
- `GET /meal-plans/{id}/versions`
- `POST /meal-plans/{id}/restore/{version_id}`
- `GET /recipes`, `GET /recipes/{id}`
- `POST /recipes/generate`
- `POST /recipes/substitute`
- `POST /recipes/portion`
- `POST /recipes/{id}/rate`
- `GET /recipes/recommendations/verified`
- `GET /recipes/moderation/queue`
- `POST /recipes/{id}/moderate`
- `GET /shopping-list`, `PUT /shopping-list`
- `POST /nutrition/logs`, `GET /nutrition/logs`
- `GET /nutrition/summary/daily`
- `GET /nutrition/summary/weekly`
- `GET /nutrition/trends`
- `GET /nutrition/insights`
- `POST /assistant/conversations`
- `GET /assistant/conversations`
- `GET /assistant/conversations/latest`
- `GET /assistant/conversations/{conversation_id}`
- `POST /assistant/conversations/{conversation_id}/messages`

## Development Verification

Backend syntax:

```bash
python -m compileall backend/app
```

Frontend build:

```bash
cd frontend && npm run build
```

End-to-end:

```bash
docker compose up --build
```

## Notes

- OAuth/email flows still require proper credentials in `.env`.

## Prerequisites

- Docker Desktop (with Docker Compose support)
- OpenAI API key (for AI-powered generation/insights)
- OAuth provider credentials (Google/GitHub) if testing social login
- SMTP credentials if testing email verification and password reset

## Environment Variables

Use `.env.example` as the source of truth. Key values:

- `DATABASE_URL`, `SECRET_KEY`, `OPENAI_API_KEY`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_USE_TLS`
- `FRONTEND_URL`, `APP_URL`
- `ENFORCE_HTTPS`, `ENCRYPTION_KEY` (optional override)

## Core Platform Features (Also Included)

- Authentication: register/login, email verification, password reset, optional 2FA
- Profile and health data management with privacy controls
- Analytics: BMI, wellness score, weekly/monthly progress, goal proximity
- AI insights for status, recommendations, and periodic summaries
- Security and privacy controls aligned to practical GDPR expectations
- Conversational assistant with persisted memory, scoped function-calling, chart previews, and safety boundaries

## Core API Surface (Existing + New)

Authentication:

- `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`
- `GET /auth/verify-email`
- `POST /auth/request-password-reset`, `POST /auth/reset-password`
- `GET /auth/oauth/{provider}/login`, `GET /auth/oauth/{provider}/callback`
- `POST /auth/2fa/enable`, `POST /auth/2fa/verify`, `POST /auth/2fa/disable`, `POST /auth/2fa/verify-login`

Users/Profile/Analytics:

- `GET /users/me`, `PUT /users/me`, `GET /users/me/export`
- `GET /health-profile`, `POST /health-profile`, `PUT /health-profile`, `DELETE /health-profile`, `GET /health-profile/history`
- `POST /analytics/metrics`, `GET /analytics/metrics`
- `GET /analytics/bmi`, `GET /analytics/wellness-score`
- `GET /analytics/progress/weekly`, `GET /analytics/progress/monthly`
- `GET /analytics/goals/proximity`
- `POST /ai-insights/generate/{insight_type}`, `GET /ai-insights`, `GET /ai-insights/latest`

Meal planning/recipes/shopping/nutrition endpoints are listed in `API Surface Added` above.

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── utils/
│   │   └── migrations/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── types/
│   └── package.json
├── docker-compose.yml
└── README.md
```

## Security and Privacy

- Password hashing via bcrypt
- JWT access + refresh tokens
- Verification checks before protected flows
- Input validation with Pydantic and ORM-safe DB access
- Assistant route-level validation for malformed chat input and clear user-facing error responses
- Privacy-aware AI normalization and encrypted health snapshots
- Assistant-level safety middleware behavior (medical escalation wording, PII boundary refusals, out-of-scope redirection)
- HTTPS support in production via `ENFORCE_HTTPS=true`

## Limitations

- API quotas/rate limits can affect AI responsiveness
- OAuth features require provider app setup and callback URL correctness
- Email flows require valid SMTP credentials
- AI output quality may vary; fallbacks are implemented for resilience
