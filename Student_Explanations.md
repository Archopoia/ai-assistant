# Student Explanations

## Model selection and parameters
I chose `gpt-3.5-turbo` because this assistant needs to handle a broad range of practical wellness questions quickly and at reasonable cost. For concise mode, I keep temperature lower so answers are predictable and tight. For detailed mode, I allow a slightly higher temperature and higher token budget so the assistant can explain trends and recommendations in more depth.

## End-to-end request flow
When a user sends a message, it first goes through input validation in the conversation layer. Then we store the user message in the conversation history, build context from recent messages plus compressed summary if the conversation is long, and send it with the system prompt to the model. If the model needs data, it calls a tool. The data access layer executes that tool with strict current-user scope, returns structured data, and then the assistant generates the final response. Finally, we store the assistant reply and render it back in chat.

## Why this system prompt design
My system prompt clearly defines what the assistant can do (health metrics, meal plans, recipes, nutrition, chart insights), how it should speak (friendly, structured, scannable), and where it must stop (no diagnosis, no PII leakage, no other-user data). I also included response examples to keep formatting consistent across different question types.

## Conversation memory and compression
I persist conversations in the database so history survives page close/re-open. For longer chats, I compress older turns into a summary to keep token usage efficient, and I prioritize messages relevant to the current topic so follow-up questions still work naturally.

## Function-calling implementation
I implemented dedicated assistant tools for health metrics, goals/preferences, meal plans, recipe details, nutrition summaries, and chart payload generation. Every tool validates parameters before data retrieval and returns structured errors if the request is invalid or data is unavailable.

## Error handling and graceful fallback
If user input is empty or too long, the API returns clear validation messages. If model calls fail due to rate limits or connectivity issues, I fall back to deterministic responses so the conversation can continue. If requested data does not exist for that timeframe, the assistant reports that clearly instead of hallucinating.

## Security and privacy controls
All assistant data access is scoped to the authenticated user from JWT (`current_user`). The assistant explicitly blocks attempts to access other users’ information and refuses requests for sensitive PII like email, DOB, or credentials.

## Safety boundary for medical topics
For potentially urgent medical symptoms (like chest pain), the assistant does not diagnose. It clearly states the limitation and advises immediate professional medical care.