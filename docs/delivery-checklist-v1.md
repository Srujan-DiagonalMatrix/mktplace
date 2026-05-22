# Delivery Checklist (v1 Demo Baseline)

## Purpose
Single source of truth for demo scope, acceptance gates, KPI definitions, and module traceability for the AI car-buying assistant MVP.

## In-Scope Demo Capabilities
- Guided conversation to capture buyer preferences (budget, fuel type, body style, seats, transmission).
- Preference extraction and orchestration of recommendation requests.
- Recommendation list with explainability snippets and shortlist/enquiry actions.
- Finance estimate summary (monthly estimate, term, deposit assumptions).
- Comparison and shortlist workflows.
- Enquiry capture and persistence for offline follow-up.
- Admin visibility for enquiries and backend health endpoint checks.

## Out-of-Scope (Explicit)
- Real credit checks or bureau pulls.
- Live lender or finance-provider integrations.
- Production-grade authentication/authorization (enterprise SSO, MFA, RBAC hardening).

## Required Acceptance Criteria by Module

### 1) Conversation & Preference Capture
- User can submit chat messages and receive assistant responses.
- Session ID is created and persisted for the conversation.
- Preferences are captured or updated from conversation context.
- Failure path returns a safe user-visible fallback message.

### 2) Recommendation Engine
- Recommendations honor known filters (budget, fuel, seats, transmission where provided).
- Ranked list returns deterministic top-N output for stable fixture input.
- Recommendation cards render make/model + pricing + action controls.

### 3) Finance Estimation
- Finance estimate returns monthly payment signal for a valid vehicle + terms payload.
- Missing/invalid payload values are validated with explicit error responses.
- Finance summary renders formatted monetary values and term/deposit context.

### 4) Comparison & Shortlist
- User can add vehicles to shortlist without breaking active session.
- Comparison endpoint returns structured items for selected vehicle IDs.
- Frontend panel renders shortlist and comparison affordances.

### 5) Enquiry Capture & Admin Review
- Enquiry submission stores lead details with linked session/vehicle context.
- Offline enquiry flush path supports replay from local JSONL backlog.
- Admin API can retrieve enquiry records for review.

### 6) Inventory & Asset Resolution
- Catalog loads from default dataset and supports budget filtering.
- Image resolver returns a valid image path or placeholder fallback.
- Data normalization/seed scripts run without schema regressions.

## KPI Definitions (Measurable)

```yaml
kpi_schema:
  version: 1
  windows:
    aggregation_period: daily
  metrics:
    conversation_completion_rate:
      description: Share of started conversations that reach recommendation stage.
      formula: completed_conversations / started_conversations
      numerator_event: conversation_recommendations_rendered
      denominator_event: conversation_started
      target: ">=0.70"
    drop_off_rate_by_stage:
      description: Stage-level abandonment before progressing to the next stage.
      formula: 1 - (stage_progressed / stage_entered)
      stages:
        - conversation_started
        - preferences_captured
        - recommendations_rendered
        - enquiry_started
        - enquiry_submitted
      target: "<=0.35 per stage"
    pain_point_detection_coverage:
      description: Portion of conversations where at least one pain point is detected.
      formula: conversations_with_pain_points / conversations_analyzed
      target_range: "0.20-0.80"
    sentiment_distribution_quality:
      description: Quality gate on sentiment class distribution to catch classifier drift.
      checks:
        - neutral_ratio_between: [0.20, 0.70]
        - positive_ratio_between: [0.10, 0.70]
        - negative_ratio_between: [0.05, 0.50]
        - unknown_ratio_max: 0.10
```

## Traceability Matrix

| Module | Backend service/API | Frontend component/page | Storage table/file | Test suite location |
|---|---|---|---|---|
| Conversation & Preference Capture | `src/backend/api/chat.py`; `src/backend/services/ai/conversation_orchestrator.py`; `src/backend/services/ai/preference_extractor.py` | `src/frontend/components/chat_panel.py` | `src/backend/models/session.py` | `tests/unit/test_chat_api.py`; `tests/integration/test_chat_api.py` |
| Recommendation Engine | `src/backend/api/recommendations.py`; `src/backend/services/recommendations/ranker.py`; `src/backend/services/recommendations/filtering.py` | `src/frontend/components/recommendation_cards.py` | `data/dataset.csv` | `tests/unit/test_recommendation_ranker.py`; `tests/integration/test_recommendation_api.py` |
| Finance Estimation | `src/backend/api/finance.py`; `src/backend/services/finance/estimator.py` | `src/frontend/components/finance_summary.py`; `src/frontend/components/finance_panel.py` | `src/backend/models/finance.py` | `tests/unit/test_finance_estimator.py`; `tests/integration/test_finance_api.py` |
| Comparison & Shortlist | `src/backend/api/comparisons.py`; `src/backend/api/shortlist.py`; `src/backend/services/recommendations/comparison_service.py`; `src/backend/services/leads/shortlist_service.py` | `src/frontend/components/comparison_view.py`; `src/frontend/components/shortlist_panel.py` | `src/backend/models/leads.py` | `tests/integration/test_comparison_shortlist_enquiry.py` |
| Enquiry Capture & Admin Review | `src/backend/api/enquiries.py`; `src/backend/api/admin.py`; `src/backend/services/leads/enquiry_service.py` | `src/frontend/components/enquiry_form.py` | `src/backend/models/leads.py`; `data/offline_enquiries.jsonl` | `tests/integration/test_admin_api.py`; `tests/e2e/test_admin_flow.py` |
| Inventory & Asset Resolution | `src/backend/api/catalog.py`; `src/backend/api/image_paths.py`; `src/backend/services/inventory/catalog.py`; `src/backend/services/inventory/image_resolver.py` | `src/frontend/components/car_detail.py`; `src/frontend/components/recommendation_cards.py` | `data/dataset.csv`; `assets/vehicles/` | `tests/unit/test_inventory_loader.py`; `tests/unit/test_image_resolver.py`; `tests/unit/test_image_resolver_paths.py` |

## Baseline v1 Demo Script (Freeze)
Use this exact script as the regression baseline for each phase gate.

1. **Start session**: Open frontend and verify default welcome prompt is visible.
2. **Budget intent**: Send message: "I can spend about £500/month."; confirm budget updates in summary.
3. **Preference refinement**: Send message: "I need a hybrid SUV with 5 seats and automatic."; confirm stored preferences update.
4. **Recommendation gate**: Load recommendations and confirm at least 3 vehicles render with actions.
5. **Finance gate**: Open finance panel for one recommended vehicle; verify monthly estimate and term/deposit formatting.
6. **Shortlist gate**: Add two vehicles to shortlist and open comparison view.
7. **Enquiry gate**: Submit enquiry with contact details and selected vehicle.
8. **Admin gate**: Verify enquiry appears in admin flow/API response.
9. **Health gate**: Call backend health endpoint and confirm success response.

### Phase Validation Rule
- A phase is accepted only if all prior script steps still pass and KPI schema remains unchanged unless version is incremented.
