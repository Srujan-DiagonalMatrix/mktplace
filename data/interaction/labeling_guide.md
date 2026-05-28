# Labeling Guide for Human-Like Car-Buying Assistant

## 1. Assistant action labels
- ask_follow_up: Ask one relevant next question tied to current context.
- clarify_with_options: Resolve ambiguity by offering concise options.
- summarize_and_confirm: Summarize captured preferences and seek confirmation.
- recommend_transition: Move from discovery to recommendations.
- close_or_handoff: End politely or handoff when user intent is complete.

## 2. Golden response rules
- Ask only one question per turn unless user explicitly asks for multiple details.
- Reference user’s latest meaningful detail when possible.
- Avoid repeating already-answered slots unless contradiction detected.
- Keep tone concise, friendly, factual.

## 3. Ambiguity and contradiction
Mark needs_clarification=true when:
- user says: maybe / not sure / depends / idk
- conflicting info appears in same turn (e.g., "manual... actually automatic")

## 4. Bad action examples
- Asking unrelated slots when user is confused.
- Repeating the same question verbatim after a valid answer.
- Making claims about guaranteed approval or legal/financial outcomes.

## 5. Outcome labels
- progressed: conversation moved toward completion.
- stalled: no net progress for this turn.
- dropped: user disengaged after this region.
- completed: enough information gathered and user reached recommendation/handoff stage.