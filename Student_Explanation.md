# Student Explanations
## Sequential Prompting (3-step logic)

I split meal planning into three prompts because one big prompt gave inconsistent structure and weaker nutrition alignment.  
Step 1 builds strategy from profile and goals, step 2 turns strategy into a daily or weekly meal structure, and step 3 generates concrete meals using retrieved recipe context.  
Each step uses the previous output, so the final plan is more coherent than single-shot generation.

## RAG Pipeline Components and Why They Matter

My RAG flow is: database -> embedding -> retrieval -> augmentation -> generation.  
The recipe and ingredient database gives grounded source material, embeddings make semantic search possible, retrieval picks relevant examples, augmented prompts inject those examples into generation, and final generation adapts them to the user profile.  
This reduces hallucination and keeps recipes more realistic than generating from scratch.

## Why I Chose Model + Function Calling Split

I use a general LLM for reasoning and customization, but nutrition math is handled through explicit function calling.  
That split keeps creative planning where the model is strong, while calculations stay deterministic and auditable.

## Few-Shot Example Selection Strategy

I use structured JSON output examples that match my required schema, not random style examples.  
I picked examples that represent common meal plans and edge constraints, so model outputs are consistent with what the frontend and validators expect.

## Temperature and Top-p Choices

For strategy and structure prompts, I keep temperature lower so the output stays predictable and stable.  
For concrete meal suggestions, I allow slightly more creativity so users get variety.  
Top-p is used to control diversity without losing coherence.

## How Function Calling Improves Reliability

The model is required to call `calculate_nutrition` for nutrition results instead of estimating values in plain text.  
I validate arguments, handle missing parameters and invalid values, and return clear errors for timeout/rate-limit/connectivity cases.  
If the model call fails, I use fallback execution so the app can still continue.

## Error Handling and Recovery

I treat AI output as untrusted input and validate/parse everything before use.  
I handle malformed JSON, tool argument issues, API failures, and network problems.  
Recovery is done with retries and deterministic fallback paths so users are not blocked.

## Why This Improves Over Non-RAG/Single-Prompt Approach

Single prompt generation tends to drift in format and nutrition quality.  
With sequential prompts plus RAG, the model gets clear stage-by-stage constraints and grounded recipe context, so quality and consistency are better.

## How Personalization Uses Existing Profile Data

I reuse profile and goal data directly: activity level, dietary info, restrictions, weight goals, and target calories/macros.  
The planner pre-fills these values so users confirm instead of re-entering them.  
That keeps the flow seamless and more personalized.

## Wellness Score Integration with Nutrition

When nutrition logs are recorded, I apply adherence logic relative to calorie targets and update wellness trend impact.  
That connects nutrition behavior to overall wellness scoring instead of treating these as isolated features.
