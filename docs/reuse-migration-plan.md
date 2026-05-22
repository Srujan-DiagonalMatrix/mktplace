# Reuse & Migration Plan (Backend + Frontend)

## 1) Active backend route inventory (`src/backend/api/`)

| Journey step | Route | Method | Purpose | Reuse decision |
|---|---|---|---|---|
| Start discovery conversation | `/chat/message` | POST | Captures user intent/preferences and returns next prompt/quick replies. | **Reuse as-is** (stabilize response contract with tests). |
| Browse inventory list | `/catalog/` | GET | Filterable vehicle listing for browse and fallback discovery. | **Reuse as-is**. |
| Inspect vehicle details | `/catalog/{vehicle_id}` | GET | Single vehicle detail retrieval. | **Reuse as-is**. |
| Generate recommendations | `/recommendations/from_session` | GET | Session-aware ranked recommendations. | **Extend** (new AI rankers should preserve shape). |
| Compare selected vehicles | `/comparisons/assemble` | POST | Aggregates selected vehicles for side-by-side comparison. | **Reuse as-is**. |
| Estimate affordability | `/finance/estimate` | GET | Finance estimate using vehicle price, deposit, term. | **Extend** (optional richer estimate fields). |
| Save shortlist item | `/shortlist/add` | POST | Add vehicle to shortlist. | **Reuse as-is**. |
| Remove shortlist item | `/shortlist/remove` | POST | Remove shortlist item. | **Reuse as-is**. |
| View shortlist | `/shortlist/list` | GET | Fetch shortlist for current session. | **Reuse as-is**. |
| Submit enquiry | `/enquiries/` | POST | Lead/enquiry capture for selected vehicle and buyer data. | **Reuse as-is**. |
| Fetch enquiry | `/enquiries/{enquiry_id}` | GET | Retrieve enquiry status and payload. | **Reuse as-is**. |
| Admin enquiries list | `/admin/enquiries` | GET | Ops tooling to review enquiries. | **Extend** (add analytics metadata only). |
| Admin enquiry status update | `/admin/enquiries/{enquiry_id}/status` | POST | Ops workflow for lead lifecycle updates. | **Reuse as-is**. |
| Admin offline flush | `/admin/flush_offline` | POST | Flush offline submissions queue. | **Reuse as-is**. |

## 2) Frontend UX block inventory (`src/frontend/components/`, `src/frontend/app.py`)

### Primary app layout blocks (`src/frontend/app.py`)
- `main`, `_render_chat_panel`, `_render_recommendations_panel`, `_render_safety_footer`, `_render_title_card`, `_render_page_css`.
- Decision: **Extend** (keep current shell/layout and insert new AI modules behind feature flags).

### Components and reuse decisions

| Component | Role in user journey | Decision |
|---|---|---|
| `chat_panel.py` | Conversational intake and preference capture. | **Extend** |
| `recommendation_cards.py` | Recommendation display and card actions. | **Extend** |
| `enquiry_form.py` | Enquiry submission UX and validation trigger. | **Reuse as-is** |
| `finance_summary.py` | Readable budget/deposit/term summary. | **Reuse as-is** |
| `summary_cards.py` | High-level preference/finance recap. | **Reuse as-is** |
| `car_detail.py` | Detail + shortlist/enquiry handoff actions. | **Reuse as-is** |
| `comparison_view.py` | Side-by-side comparison UI. | **Reuse as-is** |
| `shortlist_panel.py` | Shortlist retrieval and quick visibility. | **Reuse as-is** |
| `finance_panel.py` | Direct finance estimate entry point. | **Extend** |
| `preference_controls.py` | Explicit controls for budget/fuel/transmission. | **Extend** |
| `sidebar_nav.py` | Navigation landmarks for journey sections. | **Reuse as-is** |
| `header.py` | Session control and app hero area. | **Reuse as-is** |
| `validation.py` | Enquiry validation helpers. | **Reuse as-is** |
| `errors.py` | Standardized warning/error surfacing. | **Reuse as-is** |
| `empty_states.py` | Fallback empty/loading states. | **Reuse as-is** |

## 3) Dependency map for existing flow capabilities

### Chat
- Frontend: `chat_panel` -> `client.post_chat`.
- Backend: `/chat/message` -> conversation orchestrator/session state.
- Downstream dependency: session preferences feed recommendations.

### Recommendations
- Frontend: recommendations panel + `recommendation_cards`.
- Backend: `/recommendations/from_session` using chat-derived preferences and catalog.
- Dependency on image path normalisation and catalog availability.

### Finance estimates
- Frontend: `finance_panel` and summary blocks (`finance_summary`, `summary_cards`).
- Backend: `/finance/estimate`.
- Dependency: selected vehicle identifier + pricing record.

### Enquiry capture
- Frontend: `enquiry_form` + validation helpers.
- Backend: `/enquiries/` (create), `/enquiries/{id}` (read), plus admin lifecycle routes.
- Dependency: vehicle selection from recommendation/detail journey.

## 4) Low-risk migration plan for new AI modules

1. **Freeze interface contracts first**
   - Lock route status codes, required fields, and core semantics for reusable endpoints.
   - Add/maintain contract tests before refactor (see added tests).
2. **Introduce AI modules behind adapters**
   - Keep API handlers stable; route handlers call an adapter that can switch from legacy to new AI module.
   - Avoid changing request/response models until compatibility window ends.
3. **Feature-flag new behavior**
   - Per-capability flags: chat parsing, recommendation reranking, finance enrichment.
   - Default flags off in production rollout phase 1.
4. **Shadow mode + parity checks**
   - Run old/new AI path in parallel for sampled traffic; compare ranking deltas and extracted preferences.
   - Persist comparison metrics for rollout decisions.
5. **Progressive rollout**
   - Internal users -> small cohort -> full rollout.
   - Define rollback trigger thresholds (error rate, latency, conversion drop).
6. **UI regression guardrails**
   - Keep critical render sections covered by smoke tests.
   - Restrict enhancements to additive UI regions until parity confidence is high.

## 5) Test strategy aligned to acceptance criteria

- **Interface contract tests**: reusable APIs (`chat`, `catalog`, `recommendations`, `finance`, `enquiries`) verify stable status codes and key fields.
- **UI smoke tests**: critical render sections (chat shell, recommendation cards, enquiry form trigger surfaces, summary cards) run before and after enhancements to detect breakage.
- **No rebuild required**: changes rely on existing route/component seams and additive adapters/flags.
