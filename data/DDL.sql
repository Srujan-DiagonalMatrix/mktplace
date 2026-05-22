-- ============================================================
-- File: DDL.sql
-- Database: PostgreSQL 16+
-- Purpose:
--   Demo schema for AI-Driven Conversational Solution
--   for Car Finance Feedback and Insights Dashboard.
--
-- Modules covered:
--   2. Conversation Data Collection Module
--   3. AI Chatbot Module
--   4. Context & User Preference Module
--   5. Dynamic Questioning Module
--   6. Pain Point Detection Module
--   7. Sentiment & Theme Analysis Module
--   8. Pain Point Scoring Module
--
-- Notes:
--   - UUID primary keys are used for easy API/app integration.
--   - JSONB is used where AI outputs or flexible metadata may change.
--   - TEXT is used for long chatbot messages, prompts, notes and summaries.
--   - VARCHAR(500) is used for most business dimensions to avoid length issues.
--   - NUMERIC(18,2) is used for money/amount values.
--   - NUMERIC(10,4) is used for scores, confidence, APR and percentages.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS car_finance_ai;

SET search_path TO car_finance_ai, public;

-- ============================================================
-- TABLE: customers
-- Purpose:
--   Stores known customers or anonymous visitors who interact with
--   the car finance chatbot. For demo use, customer details can be
--   optional and visitor_id/session data can be used instead.
-- Module:
--   Conversation Data Collection Module
-- ============================================================

CREATE TABLE IF NOT EXISTS customers (
    customer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visitor_id VARCHAR(500),
    external_customer_ref VARCHAR(500),
    customer_name VARCHAR(500),
    email VARCHAR(500),
    phone VARCHAR(100),
    location VARCHAR(500),
    region VARCHAR(500),
    postcode VARCHAR(100),
    customer_type VARCHAR(500),
    lead_source VARCHAR(500),
    marketing_campaign VARCHAR(500),
    consent_to_contact BOOLEAN DEFAULT FALSE,
    preferred_contact_method VARCHAR(500),
    customer_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

COMMENT ON TABLE customers IS 'Stores customer or anonymous visitor profile details used to connect conversations, preferences, enquiries and dashboard insights.';
COMMENT ON COLUMN customers.customer_type IS 'Example values: new visitor, returning visitor, existing customer, demo user.';
COMMENT ON COLUMN customers.lead_source IS 'Example values: website, campaign, referral, internal demo, paid ad.';
COMMENT ON COLUMN customers.customer_metadata IS 'Flexible JSONB field for any extra customer profile attributes captured during demo conversations.';

CREATE INDEX IF NOT EXISTS idx_customers_visitor_id ON customers(visitor_id);
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_customer_type ON customers(customer_type);
CREATE INDEX IF NOT EXISTS idx_customers_created_at ON customers(created_at);


-- ============================================================
-- TABLE: conversation_sessions
-- Purpose:
--   Stores one full chatbot conversation session from start to end.
--   This is the main fact table for reporting conversation volumes,
--   completion, drop-off, enquiry submission and conversion signals.
-- Module:
--   Conversation Data Collection Module
-- ============================================================

CREATE TABLE IF NOT EXISTS conversation_sessions (
    conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(customer_id) ON DELETE SET NULL,
    session_id VARCHAR(500),
    channel VARCHAR(500),
    application_area VARCHAR(500),
    conversation_start_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    conversation_end_time TIMESTAMPTZ,
    duration_seconds INTEGER,
    conversation_status VARCHAR(500),
    journey_stage_started VARCHAR(500),
    journey_stage_ended VARCHAR(500),
    total_user_messages INTEGER DEFAULT 0,
    total_bot_messages INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    enquiry_submitted BOOLEAN DEFAULT FALSE,
    callback_requested BOOLEAN DEFAULT FALSE,
    sales_escalated BOOLEAN DEFAULT FALSE,
    converted_flag BOOLEAN DEFAULT FALSE,
    dropoff_flag BOOLEAN DEFAULT FALSE,
    dropoff_stage VARCHAR(500),
    overall_sentiment_label VARCHAR(500),
    overall_buying_intent_score INTEGER CHECK (overall_buying_intent_score IS NULL OR overall_buying_intent_score BETWEEN 1 AND 5),
    conversation_summary TEXT,
    raw_transcript TEXT,
    session_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

COMMENT ON TABLE conversation_sessions IS 'Stores one full chatbot session and high-level journey metrics for dashboard reporting.';
COMMENT ON COLUMN conversation_sessions.conversation_status IS 'Example values: in progress, completed, dropped off, escalated, converted.';
COMMENT ON COLUMN conversation_sessions.journey_stage_ended IS 'Final stage reached by the user, useful for drop-off and funnel analysis.';
COMMENT ON COLUMN conversation_sessions.conversation_summary IS 'AI-generated or system-generated summary of the full conversation.';
COMMENT ON COLUMN conversation_sessions.raw_transcript IS 'Optional full transcript text. Detailed message-level records are stored in conversation_messages.';

CREATE INDEX IF NOT EXISTS idx_conversation_sessions_customer_id ON conversation_sessions(customer_id);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_session_id ON conversation_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_status ON conversation_sessions(conversation_status);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_channel ON conversation_sessions(channel);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_start_time ON conversation_sessions(conversation_start_time);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_dropoff_flag ON conversation_sessions(dropoff_flag);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_enquiry_submitted ON conversation_sessions(enquiry_submitted);


-- ============================================================
-- TABLE: conversation_messages
-- Purpose:
--   Stores every user, bot or system message in a conversation.
--   This supports transcript replay, topic analysis, unanswered
--   question reporting and AI/NLP processing.
-- Module:
--   Conversation Data Collection Module
-- ============================================================

CREATE TABLE IF NOT EXISTS conversation_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversation_sessions(conversation_id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(customer_id) ON DELETE SET NULL,
    message_sequence INTEGER NOT NULL,
    sender_type VARCHAR(500) NOT NULL,
    message_type VARCHAR(500),
    message_text TEXT NOT NULL,
    message_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    detected_intent VARCHAR(500),
    detected_topic VARCHAR(500),
    detected_entities JSONB DEFAULT '{}'::jsonb,
    response_time_seconds INTEGER,
    was_answered BOOLEAN,
    confidence_score NUMERIC(10,4),
    ai_generated_flag BOOLEAN DEFAULT FALSE,
    contains_question_flag BOOLEAN DEFAULT FALSE,
    contains_feedback_flag BOOLEAN DEFAULT FALSE,
    contains_objection_flag BOOLEAN DEFAULT FALSE,
    message_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE conversation_messages IS 'Stores each chatbot, user and system message for transcript, NLP, intent, topic and response analysis.';
COMMENT ON COLUMN conversation_messages.sender_type IS 'Example values: user, bot, system, sales_agent.';
COMMENT ON COLUMN conversation_messages.message_type IS 'Example values: question, answer, clarification, recommendation, finance_explanation, feedback.';
COMMENT ON COLUMN conversation_messages.detected_entities IS 'JSONB field for extracted values such as budget, deposit, vehicle type, APR concern or callback request.';

CREATE UNIQUE INDEX IF NOT EXISTS uq_conversation_messages_sequence
ON conversation_messages(conversation_id, message_sequence);

CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_id ON conversation_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_customer_id ON conversation_messages(customer_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_sender_type ON conversation_messages(sender_type);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_detected_topic ON conversation_messages(detected_topic);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_detected_intent ON conversation_messages(detected_intent);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_timestamp ON conversation_messages(message_timestamp);


-- ============================================================
-- TABLE: vehicle_inventory
-- Purpose:
--   Optional demo inventory table for cars shown in the application.
--   This allows the chatbot and dashboard to link user preferences
--   and interactions back to actual vehicles.
-- Module:
--   Conversation Data Collection Module / Existing Car Finance App
-- ============================================================

CREATE TABLE IF NOT EXISTS vehicle_inventory (
    vehicle_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_reference VARCHAR(500),
    brand VARCHAR(500),
    model VARCHAR(500),
    variant VARCHAR(500),
    body_type VARCHAR(500),
    fuel_type VARCHAR(500),
    transmission VARCHAR(500),
    colour VARCHAR(500),
    vehicle_year INTEGER,
    registration_year INTEGER,
    mileage INTEGER,
    number_of_seats INTEGER,
    vehicle_price NUMERIC(18,2),
    estimated_monthly_payment NUMERIC(18,2),
    representative_apr NUMERIC(10,4),
    availability_status VARCHAR(500),
    image_url TEXT,
    vehicle_description TEXT,
    vehicle_features JSONB DEFAULT '[]'::jsonb,
    inventory_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

COMMENT ON TABLE vehicle_inventory IS 'Optional car inventory table used to connect recommendations, shortlisted vehicles and enquiries to real vehicle records.';
COMMENT ON COLUMN vehicle_inventory.availability_status IS 'Example values: available, reserved, sold, coming soon, unavailable.';
COMMENT ON COLUMN vehicle_inventory.vehicle_features IS 'JSONB list of features such as sat nav, parking camera, boot space, electric range and safety features.';

CREATE INDEX IF NOT EXISTS idx_vehicle_inventory_brand_model ON vehicle_inventory(brand, model);
CREATE INDEX IF NOT EXISTS idx_vehicle_inventory_body_type ON vehicle_inventory(body_type);
CREATE INDEX IF NOT EXISTS idx_vehicle_inventory_fuel_type ON vehicle_inventory(fuel_type);
CREATE INDEX IF NOT EXISTS idx_vehicle_inventory_price ON vehicle_inventory(vehicle_price);
CREATE INDEX IF NOT EXISTS idx_vehicle_inventory_availability ON vehicle_inventory(availability_status);


-- ============================================================
-- TABLE: vehicle_interactions
-- Purpose:
--   Stores how customers interacted with vehicles during the chat
--   or application journey: viewed, compared, shortlisted, selected
--   or enquired.
-- Module:
--   Conversation Data Collection Module
-- ============================================================

CREATE TABLE IF NOT EXISTS vehicle_interactions (
    vehicle_interaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversation_sessions(conversation_id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(customer_id) ON DELETE SET NULL,
    vehicle_id UUID REFERENCES vehicle_inventory(vehicle_id) ON DELETE SET NULL,
    vehicle_external_ref VARCHAR(500),
    brand VARCHAR(500),
    model VARCHAR(500),
    variant VARCHAR(500),
    body_type VARCHAR(500),
    fuel_type VARCHAR(500),
    transmission VARCHAR(500),
    vehicle_price NUMERIC(18,2),
    estimated_monthly_payment NUMERIC(18,2),
    interaction_type VARCHAR(500),
    recommendation_rank INTEGER,
    match_score NUMERIC(10,4),
    shortlisted_flag BOOLEAN DEFAULT FALSE,
    viewed_detail_flag BOOLEAN DEFAULT FALSE,
    enquiry_submitted_flag BOOLEAN DEFAULT FALSE,
    interaction_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    interaction_metadata JSONB DEFAULT '{}'::jsonb
);

COMMENT ON TABLE vehicle_interactions IS 'Stores customer interactions with vehicles, useful for reporting top viewed cars, shortlisted cars and enquiry conversion.';
COMMENT ON COLUMN vehicle_interactions.interaction_type IS 'Example values: viewed, recommended, shortlisted, compared, selected, enquired.';
COMMENT ON COLUMN vehicle_interactions.match_score IS 'Optional AI or rule-based recommendation match score for the customer preference.';

CREATE INDEX IF NOT EXISTS idx_vehicle_interactions_conversation_id ON vehicle_interactions(conversation_id);
CREATE INDEX IF NOT EXISTS idx_vehicle_interactions_customer_id ON vehicle_interactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_vehicle_interactions_vehicle_id ON vehicle_interactions(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_vehicle_interactions_type ON vehicle_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_vehicle_interactions_brand_model ON vehicle_interactions(brand, model);
CREATE INDEX IF NOT EXISTS idx_vehicle_interactions_timestamp ON vehicle_interactions(interaction_timestamp);


-- ============================================================
-- TABLE: customer_preferences
-- Purpose:
--   Stores vehicle and buying preferences captured from the user.
--   These preferences can be explicitly selected or inferred by AI.
-- Module:
--   Context & User Preference Module
-- ============================================================

CREATE TABLE IF NOT EXISTS customer_preferences (
    preference_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversation_sessions(conversation_id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(customer_id) ON DELETE SET NULL,
    preferred_body_type VARCHAR(500),
    preferred_brand VARCHAR(500),
    preferred_model VARCHAR(500),
    preferred_fuel_type VARCHAR(500),
    preferred_transmission VARCHAR(500),
    preferred_colour VARCHAR(500),
    number_of_seats INTEGER,
    mileage_preference_min INTEGER,
    mileage_preference_max INTEGER,
    vehicle_age_preference_min INTEGER,
    vehicle_age_preference_max INTEGER,
    usage_purpose VARCHAR(500),
    priority_factor VARCHAR(500),
    must_have_features JSONB DEFAULT '[]'::jsonb,
    nice_to_have_features JSONB DEFAULT '[]'::jsonb,
    preference_source VARCHAR(500),
    confidence_score NUMERIC(10,4),
    preference_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

COMMENT ON TABLE customer_preferences IS 'Stores car buying preferences such as body type, brand, fuel type, usage purpose and priority factor.';
COMMENT ON COLUMN customer_preferences.preference_source IS 'Example values: user_selected, chatbot_extracted, ai_inferred, imported.';
COMMENT ON COLUMN customer_preferences.priority_factor IS 'Example values: low monthly payment, low deposit, comfort, reliability, brand, boot space, fuel efficiency.';

CREATE INDEX IF NOT EXISTS idx_customer_preferences_conversation_id ON customer_preferences(conversation_id);
CREATE INDEX IF NOT EXISTS idx_customer_preferences_customer_id ON customer_preferences(customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_preferences_body_type ON customer_preferences(preferred_body_type);
CREATE INDEX IF NOT EXISTS idx_customer_preferences_brand ON customer_preferences(preferred_brand);
CREATE INDEX IF NOT EXISTS idx_customer_preferences_usage_purpose ON customer_preferences(usage_purpose);


-- ============================================================
-- TABLE: finance_preferences
-- Purpose:
--   Stores finance-related requirements, preferences and sensitivity
--   areas such as monthly budget, deposit, APR and loan term.
-- Module:
--   Context & User Preference Module
-- ============================================================

CREATE TABLE IF NOT EXISTS finance_preferences (
    finance_preference_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversation_sessions(conversation_id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(customer_id) ON DELETE SET NULL,
    monthly_budget_min NUMERIC(18,2),
    monthly_budget_max NUMERIC(18,2),
    deposit_amount NUMERIC(18,2),
    deposit_min NUMERIC(18,2),
    deposit_max NUMERIC(18,2),
    finance_type_interest VARCHAR(500),
    loan_term_months INTEGER,
    annual_mileage INTEGER,
    credit_score_band VARCHAR(500),
    apr_sensitivity VARCHAR(500),
    deposit_sensitivity VARCHAR(500),
    monthly_payment_sensitivity VARCHAR(500),
    affordability_concern_flag BOOLEAN DEFAULT FALSE,
    credit_check_concern_flag BOOLEAN DEFAULT FALSE,
    apr_concern_flag BOOLEAN DEFAULT FALSE,
    deposit_concern_flag BOOLEAN DEFAULT FALSE,
    finance_readiness VARCHAR(500),
    finance_readiness_score INTEGER CHECK (finance_readiness_score IS NULL OR finance_readiness_score BETWEEN 1 AND 5),
    preference_source VARCHAR(500),
    confidence_score NUMERIC(10,4),
    finance_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

COMMENT ON TABLE finance_preferences IS 'Stores finance preferences and concerns including monthly budget, deposit, APR sensitivity, loan term and finance readiness.';
COMMENT ON COLUMN finance_preferences.finance_type_interest IS 'Example values: PCP, HP, lease, cash purchase, unsure.';
COMMENT ON COLUMN finance_preferences.finance_readiness IS 'Example values: low, medium, high, ready_to_apply.';

CREATE INDEX IF NOT EXISTS idx_finance_preferences_conversation_id ON finance_preferences(conversation_id);
CREATE INDEX IF NOT EXISTS idx_finance_preferences_customer_id ON finance_preferences(customer_id);
CREATE INDEX IF NOT EXISTS idx_finance_preferences_budget ON finance_preferences(monthly_budget_min, monthly_budget_max);
CREATE INDEX IF NOT EXISTS idx_finance_preferences_finance_type ON finance_preferences(finance_type_interest);
CREATE INDEX IF NOT EXISTS idx_finance_preferences_readiness ON finance_preferences(finance_readiness);


-- ============================================================
-- TABLE: conversation_context
-- Purpose:
--   Stores the latest known conversation memory and context state.
--   This allows the AI chatbot to remember budget, deposit,
--   preferred car type, concern, objection and journey stage.
-- Module:
--   Context & User Preference Module
-- ============================================================

CREATE TABLE IF NOT EXISTS conversation_context (
    context_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL UNIQUE REFERENCES conversation_sessions(conversation_id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(customer_id) ON DELETE SET NULL,
    current_stage VARCHAR(500),
    previous_stage VARCHAR(500),
    last_user_intent VARCHAR(500),
    last_topic VARCHAR(500),
    known_budget NUMERIC(18,2),
    known_deposit NUMERIC(18,2),
    known_monthly_payment_preference NUMERIC(18,2),
    known_vehicle_type VARCHAR(500),
    known_brand VARCHAR(500),
    known_model VARCHAR(500),
    known_finance_concern VARCHAR(500),
    known_objection VARCHAR(500),
    context_completeness_score INTEGER CHECK (context_completeness_score IS NULL OR context_completeness_score BETWEEN 1 AND 5),
    context_summary TEXT,
    short_memory JSONB DEFAULT '{}'::jsonb,
    long_memory JSONB DEFAULT '{}'::jsonb,
    last_updated_by VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

COMMENT ON TABLE conversation_context IS 'Stores live conversation memory for the chatbot, including known customer preferences, objections and current journey stage.';
COMMENT ON COLUMN conversation_context.short_memory IS 'JSONB field for current session-level memory.';
COMMENT ON COLUMN conversation_context.long_memory IS 'JSONB field for longer-term profile memory if used later.';

CREATE INDEX IF NOT EXISTS idx_conversation_context_customer_id ON conversation_context(customer_id);
CREATE INDEX IF NOT EXISTS idx_conversation_context_current_stage ON conversation_context(current_stage);
CREATE INDEX IF NOT EXISTS idx_conversation_context_last_topic ON conversation_context(last_topic);


-- ============================================================
-- TABLE: ai_model_runs
-- Purpose:
--   Stores every OpenAI API or AI model call used for chatbot
--   response generation, summarisation, extraction, scoring or
--   insight generation.
-- Module:
--   AI Chatbot Module
-- ============================================================

CREATE TABLE IF NOT EXISTS ai_model_runs (
    ai_run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversation_sessions(conversation_id) ON DELETE CASCADE,
    message_id UUID REFERENCES conversation_messages(message_id) ON DELETE SET NULL,
    model_provider VARCHAR(500) DEFAULT 'OpenAI',
    model_name VARCHAR(500),
    prompt_type VARCHAR(500),
    system_prompt TEXT,
    user_prompt TEXT,
    full_prompt_payload JSONB DEFAULT '{}'::jsonb,
    model_response TEXT,
    response_json JSONB DEFAULT '{}'::jsonb,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    api_cost_estimate NUMERIC(18,6),
    latency_ms INTEGER,
    temperature NUMERIC(10,4),
    max_tokens INTEGER,
    success_flag BOOLEAN DEFAULT TRUE,
    error_code VARCHAR(500),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE ai_model_runs IS 'Stores AI model calls for chatbot replies, dynamic questioning, summarisation, sentiment, theme and pain point analysis.';
COMMENT ON COLUMN ai_model_runs.prompt_type IS 'Example values: chat_response, summarisation, question_generation, sentiment_analysis, pain_point_detection, scoring.';
COMMENT ON COLUMN ai_model_runs.response_json IS 'Stores structured AI output when the model returns JSON.';

CREATE INDEX IF NOT EXISTS idx_ai_model_runs_conversation_id ON ai_model_runs(conversation_id);
CREATE INDEX IF NOT EXISTS idx_ai_model_runs_message_id ON ai_model_runs(message_id);
CREATE INDEX IF NOT EXISTS idx_ai_model_runs_model_name ON ai_model_runs(model_name);
CREATE INDEX IF NOT EXISTS idx_ai_model_runs_prompt_type ON ai_model_runs(prompt_type);
CREATE INDEX IF NOT EXISTS idx_ai_model_runs_created_at ON ai_model_runs(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_model_runs_success_flag ON ai_model_runs(success_flag);


-- ============================================================
-- TABLE: dynamic_questions
-- Purpose:
--   Stores AI-generated next-best questions asked during the chat.
--   This helps analyse which questions move the customer forward
--   and where customers stop responding.
-- Module:
--   Dynamic Questioning Module
-- ============================================================

CREATE TABLE IF NOT EXISTS dynamic_questions (
    question_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversation_sessions(conversation_id) ON DELETE CASCADE,
    message_id UUID REFERENCES conversation_messages(message_id) ON DELETE SET NULL,
    ai_run_id UUID REFERENCES ai_model_runs(ai_run_id) ON DELETE SET NULL,
    question_sequence INTEGER,
    question_text TEXT NOT NULL,
    question_category VARCHAR(500),
    question_reason TEXT,
    triggering_user_intent VARCHAR(500),
    triggering_topic VARCHAR(500),
    expected_answer_type VARCHAR(500),
    question_priority INTEGER CHECK (question_priority IS NULL OR question_priority BETWEEN 1 AND 5),
    was_answered BOOLEAN DEFAULT FALSE,
    caused_dropoff_flag BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE dynamic_questions IS 'Stores follow-up questions generated by the AI agent based on conversation context and customer intent.';
COMMENT ON COLUMN dynamic_questions.question_category IS 'Example values: budget, deposit, vehicle_preference, finance_concern, trust, callback.';
COMMENT ON COLUMN dynamic_questions.expected_answer_type IS 'Example values: number, yes_no, single_choice, multi_choice, free_text.';

CREATE INDEX IF NOT EXISTS idx_dynamic_questions_conversation_id ON dynamic_questions(conversation_id);
CREATE INDEX IF NOT EXISTS idx_dynamic_questions_category ON dynamic_questions(question_category);
CREATE INDEX IF NOT EXISTS idx_dynamic_questions_was_answered ON dynamic_questions(was_answered);
CREATE INDEX IF NOT EXISTS idx_dynamic_questions_caused_dropoff ON dynamic_questions(caused_dropoff_flag);


-- ============================================================
-- TABLE: question_answers
-- Purpose:
--   Stores customer answers to AI-generated dynamic questions.
--   This supports reporting on answer rates, extracted preferences
--   and unanswered questions.
-- Module:
--   Dynamic Questioning Module
-- ============================================================

CREATE TABLE IF NOT EXISTS question_answers (
    answer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES dynamic_questions(question_id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversation_sessions(conversation_id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(customer_id) ON DELETE SET NULL,
    message_id UUID REFERENCES conversation_messages(message_id) ON DELETE SET NULL,
    answer_text TEXT,
    answer_value VARCHAR(1000),
    answer_type VARCHAR(500),
    extracted_entity VARCHAR(500),
    extracted_entities JSONB DEFAULT '{}'::jsonb,
    confidence_score NUMERIC(10,4),
    answer_timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE question_answers IS 'Stores customer answers to dynamic AI questions, including extracted entities and confidence score.';
COMMENT ON COLUMN question_answers.answer_type IS 'Example values: budget, deposit, brand_preference, finance_concern, objection, callback_request.';

CREATE INDEX IF NOT EXISTS idx_question_answers_question_id ON question_answers(question_id);
CREATE INDEX IF NOT EXISTS idx_question_answers_conversation_id ON question_answers(conversation_id);
CREATE INDEX IF NOT EXISTS idx_question_answers_customer_id ON question_answers(customer_id);
CREATE INDEX IF NOT EXISTS idx_question_answers_answer_type ON question_answers(answer_type);


-- ============================================================
-- TABLE: pain_points
-- Purpose:
--   Master reference table for pain point categories and definitions.
--   These are issues the customer may face during car finance journey.
-- Module:
--   Pain Point Detection Module
-- ============================================================

CREATE TABLE IF NOT EXISTS pain_points (
    pain_point_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pain_point_category VARCHAR(500) NOT NULL,
    pain_point_name VARCHAR(500) NOT NULL,
    pain_point_description TEXT,
    business_area VARCHAR(500),
    default_severity INTEGER CHECK (default_severity IS NULL OR default_severity BETWEEN 1 AND 5),
    active_flag BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

COMMENT ON TABLE pain_points IS 'Master list of pain point types such as pricing confusion, APR concern, deposit concern and trust issues.';
COMMENT ON COLUMN pain_points.business_area IS 'Example values: finance, vehicle, UX, sales, trust, process.';

CREATE UNIQUE INDEX IF NOT EXISTS uq_pain_points_category_name
ON pain_points(pain_point_category, pain_point_name);

CREATE INDEX IF NOT EXISTS idx_pain_points_category ON pain_points(pain_point_category);
CREATE INDEX IF NOT EXISTS idx_pain_points_business_area ON pain_points(business_area);
CREATE INDEX IF NOT EXISTS idx_pain_points_active_flag ON pain_points(active_flag);


-- ============================================================
-- TABLE: conversation_pain_points
-- Purpose:
--   Stores pain points detected within individual conversations
--   or messages. This can be generated by LLM, keyword rules or
--   manual review.
-- Module:
--   Pain Point Detection Module
-- ============================================================

CREATE TABLE IF NOT EXISTS conversation_pain_points (
    conversation_pain_point_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversation_sessions(conversation_id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(customer_id) ON DELETE SET NULL,
    message_id UUID REFERENCES conversation_messages(message_id) ON DELETE SET NULL,
    pain_point_id UUID REFERENCES pain_points(pain_point_id) ON DELETE SET NULL,
    ai_run_id UUID REFERENCES ai_model_runs(ai_run_id) ON DELETE SET NULL,
    detected_phrase TEXT,
    detection_method VARCHAR(500),
    severity_score INTEGER CHECK (severity_score IS NULL OR severity_score BETWEEN 1 AND 5),
    confidence_score NUMERIC(10,4),
    customer_emotion VARCHAR(500),
    journey_stage VARCHAR(500),
    requires_follow_up BOOLEAN DEFAULT FALSE,
    resolved_flag BOOLEAN DEFAULT FALSE,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    detection_metadata JSONB DEFAULT '{}'::jsonb
);

COMMENT ON TABLE conversation_pain_points IS 'Stores detected customer pain points at conversation or message level for reporting severity, frequency and follow-up needs.';
COMMENT ON COLUMN conversation_pain_points.detection_method IS 'Example values: LLM, keyword, rule_based, manual_review.';
COMMENT ON COLUMN conversation_pain_points.detected_phrase IS 'Message phrase or extract that triggered the pain point detection.';

CREATE INDEX IF NOT EXISTS idx_conversation_pain_points_conversation_id ON conversation_pain_points(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_pain_points_customer_id ON conversation_pain_points(customer_id);
CREATE INDEX IF NOT EXISTS idx_conversation_pain_points_message_id ON conversation_pain_points(message_id);
CREATE INDEX IF NOT EXISTS idx_conversation_pain_points_pain_point_id ON conversation_pain_points(pain_point_id);
CREATE INDEX IF NOT EXISTS idx_conversation_pain_points_severity ON conversation_pain_points(severity_score);
CREATE INDEX IF NOT EXISTS idx_conversation_pain_points_follow_up ON conversation_pain_points(requires_follow_up);
CREATE INDEX IF NOT EXISTS idx_conversation_pain_points_detected_at ON conversation_pain_points(detected_at);


-- ============================================================
-- TABLE: conversation_feedback
-- Purpose:
--   Stores feedback notes, complaints, suggestions or positive
--   comments captured directly from the customer or added by staff.
-- Module:
--   Conversation Data Collection Module / Pain Point Detection Module
-- ============================================================

CREATE TABLE IF NOT EXISTS conversation_feedback (
    feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversation_sessions(conversation_id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(customer_id) ON DELETE SET NULL,
    message_id UUID REFERENCES conversation_messages(message_id) ON DELETE SET NULL,
    feedback_type VARCHAR(500),
    feedback_text TEXT,
    feedback_source VARCHAR(500),
    feedback_category VARCHAR(500),
    sentiment_label VARCHAR(500),
    severity_score INTEGER CHECK (severity_score IS NULL OR severity_score BETWEEN 1 AND 5),
    action_required BOOLEAN DEFAULT FALSE,
    action_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE conversation_feedback IS 'Stores customer feedback, complaints, suggestions, objections and staff notes captured during or after chatbot conversations.';
COMMENT ON COLUMN conversation_feedback.feedback_type IS 'Example values: complaint, suggestion, confusion, objection, positive_feedback, staff_note.';
COMMENT ON COLUMN conversation_feedback.feedback_source IS 'Example values: customer_message, chatbot_summary, sales_agent, manual_review.';

CREATE INDEX IF NOT EXISTS idx_conversation_feedback_conversation_id ON conversation_feedback(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_feedback_customer_id ON conversation_feedback(customer_id);
CREATE INDEX IF NOT EXISTS idx_conversation_feedback_type ON conversation_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_conversation_feedback_category ON conversation_feedback(feedback_category);
CREATE INDEX IF NOT EXISTS idx_conversation_feedback_action_required ON conversation_feedback(action_required);


-- ============================================================
-- TABLE: sentiment_analysis
-- Purpose:
--   Stores sentiment and emotion results at message level or
--   conversation level. Used to understand customer mood and
--   buying intent.
-- Module:
--   Sentiment & Theme Analysis Module
-- ============================================================

CREATE TABLE IF NOT EXISTS sentiment_analysis (
    sentiment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversation_sessions(conversation_id) ON DELETE CASCADE,
    message_id UUID REFERENCES conversation_messages(message_id) ON DELETE SET NULL,
    ai_run_id UUID REFERENCES ai_model_runs(ai_run_id) ON DELETE SET NULL,
    analysis_level VARCHAR(500),
    sentiment_label VARCHAR(500),
    sentiment_score NUMERIC(10,4),
    emotion_label VARCHAR(500),
    buying_intent_score INTEGER CHECK (buying_intent_score IS NULL OR buying_intent_score BETWEEN 1 AND 5),
    urgency_score INTEGER CHECK (urgency_score IS NULL OR urgency_score BETWEEN 1 AND 5),
    confusion_score INTEGER CHECK (confusion_score IS NULL OR confusion_score BETWEEN 1 AND 5),
    frustration_score INTEGER CHECK (frustration_score IS NULL OR frustration_score BETWEEN 1 AND 5),
    confidence_score NUMERIC(10,4),
    analysis_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    analysis_metadata JSONB DEFAULT '{}'::jsonb
);

COMMENT ON TABLE sentiment_analysis IS 'Stores AI/NLP sentiment, emotion, buying intent and urgency scores for messages or full conversations.';
COMMENT ON COLUMN sentiment_analysis.analysis_level IS 'Example values: message, conversation, session_summary.';
COMMENT ON COLUMN sentiment_analysis.sentiment_label IS 'Example values: positive, neutral, negative, confused, frustrated, worried, interested.';

CREATE INDEX IF NOT EXISTS idx_sentiment_analysis_conversation_id ON sentiment_analysis(conversation_id);
CREATE INDEX IF NOT EXISTS idx_sentiment_analysis_message_id ON sentiment_analysis(message_id);
CREATE INDEX IF NOT EXISTS idx_sentiment_analysis_sentiment_label ON sentiment_analysis(sentiment_label);
CREATE INDEX IF NOT EXISTS idx_sentiment_analysis_emotion_label ON sentiment_analysis(emotion_label);
CREATE INDEX IF NOT EXISTS idx_sentiment_analysis_buying_intent ON sentiment_analysis(buying_intent_score);
CREATE INDEX IF NOT EXISTS idx_sentiment_analysis_timestamp ON sentiment_analysis(analysis_timestamp);


-- ============================================================
-- TABLE: theme_analysis
-- Purpose:
--   Stores recurring themes and topics found in conversations.
--   Used for dashboard views such as top objections, top finance
--   questions and most common customer interests.
-- Module:
--   Sentiment & Theme Analysis Module
-- ============================================================

CREATE TABLE IF NOT EXISTS theme_analysis (
    theme_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversation_sessions(conversation_id) ON DELETE CASCADE,
    ai_run_id UUID REFERENCES ai_model_runs(ai_run_id) ON DELETE SET NULL,
    theme_category VARCHAR(500),
    theme_name VARCHAR(500),
    theme_description TEXT,
    theme_frequency INTEGER DEFAULT 1,
    representative_message TEXT,
    journey_stage VARCHAR(500),
    sentiment_label VARCHAR(500),
    confidence_score NUMERIC(10,4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    theme_metadata JSONB DEFAULT '{}'::jsonb
);

COMMENT ON TABLE theme_analysis IS 'Stores themes and recurring topics detected by AI, such as APR questions, deposit concerns, SUV preference or trust issues.';
COMMENT ON COLUMN theme_analysis.theme_category IS 'Example values: finance, vehicle, pricing, trust, process, UX, sales.';
COMMENT ON COLUMN theme_analysis.theme_frequency IS 'Frequency of the theme within a conversation, batch or analysis period.';

CREATE INDEX IF NOT EXISTS idx_theme_analysis_conversation_id ON theme_analysis(conversation_id);
CREATE INDEX IF NOT EXISTS idx_theme_analysis_category ON theme_analysis(theme_category);
CREATE INDEX IF NOT EXISTS idx_theme_analysis_name ON theme_analysis(theme_name);
CREATE INDEX IF NOT EXISTS idx_theme_analysis_stage ON theme_analysis(journey_stage);
CREATE INDEX IF NOT EXISTS idx_theme_analysis_created_at ON theme_analysis(created_at);


-- ============================================================
-- TABLE: dropoff_analysis
-- Purpose:
--   Stores information about where and why a customer dropped off
--   during the chatbot journey.
-- Module:
--   Sentiment & Theme Analysis Module / Conversation Data Collection Module
-- ============================================================

CREATE TABLE IF NOT EXISTS dropoff_analysis (
    dropoff_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL UNIQUE REFERENCES conversation_sessions(conversation_id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(customer_id) ON DELETE SET NULL,
    last_user_message_id UUID REFERENCES conversation_messages(message_id) ON DELETE SET NULL,
    last_bot_message_id UUID REFERENCES conversation_messages(message_id) ON DELETE SET NULL,
    dropoff_stage VARCHAR(500),
    last_topic VARCHAR(500),
    dropoff_reason_detected VARCHAR(500),
    dropoff_reason_description TEXT,
    time_before_dropoff_seconds INTEGER,
    messages_before_dropoff INTEGER,
    reengagement_required BOOLEAN DEFAULT FALSE,
    reengagement_reason VARCHAR(500),
    confidence_score NUMERIC(10,4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    dropoff_metadata JSONB DEFAULT '{}'::jsonb
);

COMMENT ON TABLE dropoff_analysis IS 'Stores detected drop-off stage, reason and re-engagement recommendation for abandoned conversations.';
COMMENT ON COLUMN dropoff_analysis.dropoff_stage IS 'Example values: greeting, preference_collection, car_recommendation, finance_explanation, enquiry_form, final_confirmation.';
COMMENT ON COLUMN dropoff_analysis.dropoff_reason_detected IS 'Example values: price_concern, finance_confusion, no_suitable_car, too_many_questions, low_trust, user_inactive.';

CREATE INDEX IF NOT EXISTS idx_dropoff_analysis_customer_id ON dropoff_analysis(customer_id);
CREATE INDEX IF NOT EXISTS idx_dropoff_analysis_stage ON dropoff_analysis(dropoff_stage);
CREATE INDEX IF NOT EXISTS idx_dropoff_analysis_reason ON dropoff_analysis(dropoff_reason_detected);
CREATE INDEX IF NOT EXISTS idx_dropoff_analysis_reengagement ON dropoff_analysis(reengagement_required);


-- ============================================================
-- TABLE: pain_point_scores
-- Purpose:
--   Stores aggregated scoring for pain points using severity,
--   frequency, business impact and customer impact. This table
--   powers the top-priority dashboard reports.
-- Module:
--   Pain Point Scoring Module
-- ============================================================

CREATE TABLE IF NOT EXISTS pain_point_scores (
    score_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pain_point_id UUID NOT NULL REFERENCES pain_points(pain_point_id) ON DELETE CASCADE,
    score_period VARCHAR(500),
    period_start_date DATE,
    period_end_date DATE,
    occurrence_count INTEGER DEFAULT 0,
    affected_conversation_count INTEGER DEFAULT 0,
    severity_score INTEGER CHECK (severity_score IS NULL OR severity_score BETWEEN 1 AND 5),
    frequency_score INTEGER CHECK (frequency_score IS NULL OR frequency_score BETWEEN 1 AND 5),
    business_impact_score INTEGER CHECK (business_impact_score IS NULL OR business_impact_score BETWEEN 1 AND 5),
    customer_impact_score INTEGER CHECK (customer_impact_score IS NULL OR customer_impact_score BETWEEN 1 AND 5),
    conversion_impact_score INTEGER CHECK (conversion_impact_score IS NULL OR conversion_impact_score BETWEEN 1 AND 5),
    total_score NUMERIC(10,4),
    priority_rank INTEGER,
    priority_level VARCHAR(500),
    calculation_method VARCHAR(500),
    calculation_notes TEXT,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    score_metadata JSONB DEFAULT '{}'::jsonb
);

COMMENT ON TABLE pain_point_scores IS 'Stores ranked pain point scores for severity, frequency, business impact, customer impact and conversion impact.';
COMMENT ON COLUMN pain_point_scores.total_score IS 'Weighted score used to rank pain points for business action.';
COMMENT ON COLUMN pain_point_scores.priority_level IS 'Example values: low, medium, high, critical.';

CREATE INDEX IF NOT EXISTS idx_pain_point_scores_pain_point_id ON pain_point_scores(pain_point_id);
CREATE INDEX IF NOT EXISTS idx_pain_point_scores_period ON pain_point_scores(period_start_date, period_end_date);
CREATE INDEX IF NOT EXISTS idx_pain_point_scores_priority_rank ON pain_point_scores(priority_rank);
CREATE INDEX IF NOT EXISTS idx_pain_point_scores_priority_level ON pain_point_scores(priority_level);
CREATE INDEX IF NOT EXISTS idx_pain_point_scores_total_score ON pain_point_scores(total_score);


-- ============================================================
-- TABLE: business_recommendations
-- Purpose:
--   Stores business recommendations generated from pain points
--   and analysis results. This helps dashboard users understand
--   what action should be taken next.
-- Module:
--   Pain Point Scoring Module
-- ============================================================

CREATE TABLE IF NOT EXISTS business_recommendations (
    recommendation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pain_point_id UUID REFERENCES pain_points(pain_point_id) ON DELETE SET NULL,
    score_id UUID REFERENCES pain_point_scores(score_id) ON DELETE SET NULL,
    recommendation_title VARCHAR(500),
    recommendation_description TEXT,
    recommended_owner VARCHAR(500),
    action_priority VARCHAR(500),
    expected_business_benefit TEXT,
    expected_customer_benefit TEXT,
    estimated_effort VARCHAR(500),
    status VARCHAR(500),
    target_completion_date DATE,
    implemented_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ,
    recommendation_metadata JSONB DEFAULT '{}'::jsonb
);

COMMENT ON TABLE business_recommendations IS 'Stores recommended business actions based on detected and scored customer pain points.';
COMMENT ON COLUMN business_recommendations.recommended_owner IS 'Example values: product, sales, finance, UX, support, engineering.';
COMMENT ON COLUMN business_recommendations.status IS 'Example values: open, in_review, approved, implemented, rejected.';

CREATE INDEX IF NOT EXISTS idx_business_recommendations_pain_point_id ON business_recommendations(pain_point_id);
CREATE INDEX IF NOT EXISTS idx_business_recommendations_score_id ON business_recommendations(score_id);
CREATE INDEX IF NOT EXISTS idx_business_recommendations_owner ON business_recommendations(recommended_owner);
CREATE INDEX IF NOT EXISTS idx_business_recommendations_priority ON business_recommendations(action_priority);
CREATE INDEX IF NOT EXISTS idx_business_recommendations_status ON business_recommendations(status);


-- ============================================================
-- TABLE: sales_follow_up
-- Purpose:
--   Stores handover and follow-up actions for conversations that
--   need human sales or support intervention.
-- Module:
--   Conversation Data Collection Module / Pain Point Detection Module
-- ============================================================

CREATE TABLE IF NOT EXISTS sales_follow_up (
    follow_up_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversation_sessions(conversation_id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(customer_id) ON DELETE SET NULL,
    assigned_to VARCHAR(500),
    follow_up_required BOOLEAN DEFAULT TRUE,
    follow_up_reason VARCHAR(500),
    follow_up_priority VARCHAR(500),
    lead_quality VARCHAR(500),
    preferred_contact_method VARCHAR(500),
    callback_requested BOOLEAN DEFAULT FALSE,
    callback_requested_time TIMESTAMPTZ,
    follow_up_status VARCHAR(500),
    first_contacted_at TIMESTAMPTZ,
    last_contacted_at TIMESTAMPTZ,
    outcome VARCHAR(500),
    outcome_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ,
    follow_up_metadata JSONB DEFAULT '{}'::jsonb
);

COMMENT ON TABLE sales_follow_up IS 'Stores sales or support follow-up tasks generated from high-intent, confused, escalated or callback-requested conversations.';
COMMENT ON COLUMN sales_follow_up.follow_up_reason IS 'Example values: high_intent, finance_question, complaint, callback_requested, confused_customer, negative_sentiment.';
COMMENT ON COLUMN sales_follow_up.lead_quality IS 'Example values: cold, warm, hot.';
COMMENT ON COLUMN sales_follow_up.follow_up_status IS 'Example values: pending, contacted, converted, lost, no_response.';

CREATE INDEX IF NOT EXISTS idx_sales_follow_up_conversation_id ON sales_follow_up(conversation_id);
CREATE INDEX IF NOT EXISTS idx_sales_follow_up_customer_id ON sales_follow_up(customer_id);
CREATE INDEX IF NOT EXISTS idx_sales_follow_up_required ON sales_follow_up(follow_up_required);
CREATE INDEX IF NOT EXISTS idx_sales_follow_up_priority ON sales_follow_up(follow_up_priority);
CREATE INDEX IF NOT EXISTS idx_sales_follow_up_status ON sales_follow_up(follow_up_status);
CREATE INDEX IF NOT EXISTS idx_sales_follow_up_lead_quality ON sales_follow_up(lead_quality);


-- ============================================================
-- OPTIONAL SEED DATA: pain_points
-- Purpose:
--   Inserts common pain points for the demo dashboard.
--   ON CONFLICT is not used here because the unique index is not
--   expressed as a named table constraint. These INSERTs are written
--   safely using WHERE NOT EXISTS.
-- ============================================================

INSERT INTO pain_points (
    pain_point_category,
    pain_point_name,
    pain_point_description,
    business_area,
    default_severity
)
SELECT 'Pricing', 'Pricing confusion', 'Customer is unclear about vehicle price, total cost or price-on-request information.', 'finance', 4
WHERE NOT EXISTS (
    SELECT 1 FROM pain_points WHERE pain_point_category = 'Pricing' AND pain_point_name = 'Pricing confusion'
);

INSERT INTO pain_points (
    pain_point_category,
    pain_point_name,
    pain_point_description,
    business_area,
    default_severity
)
SELECT 'Finance', 'APR concern', 'Customer expresses concern or confusion about APR, interest rate or finance cost.', 'finance', 5
WHERE NOT EXISTS (
    SELECT 1 FROM pain_points WHERE pain_point_category = 'Finance' AND pain_point_name = 'APR concern'
);

INSERT INTO pain_points (
    pain_point_category,
    pain_point_name,
    pain_point_description,
    business_area,
    default_severity
)
SELECT 'Finance', 'Deposit concern', 'Customer is worried about deposit amount, affordability or upfront payment.', 'finance', 4
WHERE NOT EXISTS (
    SELECT 1 FROM pain_points WHERE pain_point_category = 'Finance' AND pain_point_name = 'Deposit concern'
);

INSERT INTO pain_points (
    pain_point_category,
    pain_point_name,
    pain_point_description,
    business_area,
    default_severity
)
SELECT 'Finance', 'Monthly payment concern', 'Customer is concerned that the monthly payment is too high or unclear.', 'finance', 5
WHERE NOT EXISTS (
    SELECT 1 FROM pain_points WHERE pain_point_category = 'Finance' AND pain_point_name = 'Monthly payment concern'
);

INSERT INTO pain_points (
    pain_point_category,
    pain_point_name,
    pain_point_description,
    business_area,
    default_severity
)
SELECT 'Finance', 'Loan term confusion', 'Customer does not understand loan duration, PCP/HP terms or repayment period.', 'finance', 4
WHERE NOT EXISTS (
    SELECT 1 FROM pain_points WHERE pain_point_category = 'Finance' AND pain_point_name = 'Loan term confusion'
);

INSERT INTO pain_points (
    pain_point_category,
    pain_point_name,
    pain_point_description,
    business_area,
    default_severity
)
SELECT 'Trust', 'Trust issue', 'Customer shows low trust in finance process, affordability checks, bank, dealer or chatbot.', 'trust', 5
WHERE NOT EXISTS (
    SELECT 1 FROM pain_points WHERE pain_point_category = 'Trust' AND pain_point_name = 'Trust issue'
);

INSERT INTO pain_points (
    pain_point_category,
    pain_point_name,
    pain_point_description,
    business_area,
    default_severity
)
SELECT 'Vehicle', 'No suitable car found', 'Customer cannot find a vehicle that matches budget, preference or availability.', 'vehicle', 4
WHERE NOT EXISTS (
    SELECT 1 FROM pain_points WHERE pain_point_category = 'Vehicle' AND pain_point_name = 'No suitable car found'
);

INSERT INTO pain_points (
    pain_point_category,
    pain_point_name,
    pain_point_description,
    business_area,
    default_severity
)
SELECT 'Experience', 'Too many questions', 'Customer appears frustrated by too many chatbot questions or long journey flow.', 'UX', 3
WHERE NOT EXISTS (
    SELECT 1 FROM pain_points WHERE pain_point_category = 'Experience' AND pain_point_name = 'Too many questions'
);

-- ============================================================
-- HELPFUL REPORTING VIEWS
-- Purpose:
--   These views are optional but useful for Streamlit dashboard
--   pages and quick demo reporting.
-- ============================================================

CREATE OR REPLACE VIEW vw_conversation_overview AS
SELECT
    cs.conversation_id,
    cs.customer_id,
    cs.channel,
    cs.conversation_start_time,
    cs.conversation_end_time,
    cs.duration_seconds,
    cs.conversation_status,
    cs.journey_stage_started,
    cs.journey_stage_ended,
    cs.total_user_messages,
    cs.total_bot_messages,
    cs.enquiry_submitted,
    cs.callback_requested,
    cs.sales_escalated,
    cs.converted_flag,
    cs.dropoff_flag,
    cs.dropoff_stage,
    cs.overall_sentiment_label,
    cs.overall_buying_intent_score,
    c.customer_type,
    c.location,
    c.region,
    c.lead_source
FROM conversation_sessions cs
LEFT JOIN customers c
    ON cs.customer_id = c.customer_id;

COMMENT ON VIEW vw_conversation_overview IS 'Dashboard view for conversation-level reporting including customer, channel, status, conversion and drop-off details.';


CREATE OR REPLACE VIEW vw_top_pain_points AS
SELECT
    pp.pain_point_id,
    pp.pain_point_category,
    pp.pain_point_name,
    pp.business_area,
    COUNT(cpp.conversation_pain_point_id) AS detected_count,
    COUNT(DISTINCT cpp.conversation_id) AS affected_conversation_count,
    AVG(cpp.severity_score)::NUMERIC(10,4) AS avg_severity_score,
    AVG(cpp.confidence_score)::NUMERIC(10,4) AS avg_confidence_score,
    MAX(cpp.detected_at) AS latest_detected_at
FROM pain_points pp
LEFT JOIN conversation_pain_points cpp
    ON pp.pain_point_id = cpp.pain_point_id
GROUP BY
    pp.pain_point_id,
    pp.pain_point_category,
    pp.pain_point_name,
    pp.business_area;

COMMENT ON VIEW vw_top_pain_points IS 'Dashboard view showing detected pain point counts, affected conversations and average severity.';


CREATE OR REPLACE VIEW vw_ai_usage_summary AS
SELECT
    date_trunc('day', created_at) AS usage_day,
    model_provider,
    model_name,
    prompt_type,
    COUNT(*) AS api_call_count,
    SUM(COALESCE(input_tokens, 0)) AS total_input_tokens,
    SUM(COALESCE(output_tokens, 0)) AS total_output_tokens,
    SUM(COALESCE(total_tokens, 0)) AS total_tokens,
    SUM(COALESCE(api_cost_estimate, 0)) AS estimated_cost,
    AVG(latency_ms)::NUMERIC(18,2) AS avg_latency_ms,
    SUM(CASE WHEN success_flag THEN 1 ELSE 0 END) AS success_count,
    SUM(CASE WHEN success_flag THEN 0 ELSE 1 END) AS failure_count
FROM ai_model_runs
GROUP BY
    date_trunc('day', created_at),
    model_provider,
    model_name,
    prompt_type;

COMMENT ON VIEW vw_ai_usage_summary IS 'Dashboard view summarising AI model usage, token volume, estimated cost, latency and failures.';


CREATE OR REPLACE VIEW vw_dropoff_summary AS
SELECT
    da.dropoff_stage,
    da.dropoff_reason_detected,
    COUNT(*) AS dropoff_count,
    AVG(da.time_before_dropoff_seconds)::NUMERIC(18,2) AS avg_time_before_dropoff_seconds,
    AVG(da.messages_before_dropoff)::NUMERIC(18,2) AS avg_messages_before_dropoff,
    SUM(CASE WHEN da.reengagement_required THEN 1 ELSE 0 END) AS reengagement_required_count
FROM dropoff_analysis da
GROUP BY
    da.dropoff_stage,
    da.dropoff_reason_detected;

COMMENT ON VIEW vw_dropoff_summary IS 'Dashboard view summarising drop-off counts by stage and reason.';


CREATE OR REPLACE VIEW vw_customer_preference_summary AS
SELECT
    cp.preferred_body_type,
    cp.preferred_brand,
    cp.preferred_fuel_type,
    cp.preferred_transmission,
    cp.usage_purpose,
    cp.priority_factor,
    COUNT(*) AS preference_count
FROM customer_preferences cp
GROUP BY
    cp.preferred_body_type,
    cp.preferred_brand,
    cp.preferred_fuel_type,
    cp.preferred_transmission,
    cp.usage_purpose,
    cp.priority_factor;

COMMENT ON VIEW vw_customer_preference_summary IS 'Dashboard view summarising common customer vehicle preferences.';


CREATE OR REPLACE VIEW vw_finance_preference_summary AS
SELECT
    fp.finance_type_interest,
    fp.loan_term_months,
    fp.credit_score_band,
    fp.apr_sensitivity,
    fp.deposit_sensitivity,
    fp.monthly_payment_sensitivity,
    fp.finance_readiness,
    COUNT(*) AS finance_preference_count,
    AVG(fp.monthly_budget_min)::NUMERIC(18,2) AS avg_monthly_budget_min,
    AVG(fp.monthly_budget_max)::NUMERIC(18,2) AS avg_monthly_budget_max,
    AVG(fp.deposit_amount)::NUMERIC(18,2) AS avg_deposit_amount
FROM finance_preferences fp
GROUP BY
    fp.finance_type_interest,
    fp.loan_term_months,
    fp.credit_score_band,
    fp.apr_sensitivity,
    fp.deposit_sensitivity,
    fp.monthly_payment_sensitivity,
    fp.finance_readiness;

COMMENT ON VIEW vw_finance_preference_summary IS 'Dashboard view summarising finance preferences such as budget, deposit, APR sensitivity and finance readiness.';


-- ============================================================
-- End of DDL.sql
-- ============================================================
