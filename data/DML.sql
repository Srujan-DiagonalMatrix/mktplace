-- ============================================================
-- File: seed_demo_data.sql
-- Database: PostgreSQL 16+
-- Purpose:
--   Generate demo data for AI-Driven Conversational Solution
--   for Car Finance Feedback and Insights Dashboard.
--
-- Important:
--   1. Run DDL.sql first.
--   2. Run this script after DDL.sql.
--   3. This script truncates demo tables and inserts 250 rows
--      into every base table.
--   4. Views do not require insert data.
--
-- Tables populated:
--   customers
--   conversation_sessions
--   conversation_messages
--   vehicle_inventory
--   vehicle_interactions
--   customer_preferences
--   finance_preferences
--   conversation_context
--   ai_model_runs
--   dynamic_questions
--   question_answers
--   pain_points
--   conversation_pain_points
--   conversation_feedback
--   sentiment_analysis
--   theme_analysis
--   dropoff_analysis
--   pain_point_scores
--   business_recommendations
--   sales_follow_up
-- ============================================================

BEGIN;

SET search_path TO car_finance_ai, public;

-- ------------------------------------------------------------
-- Clean existing demo data.
-- This keeps the script repeatable for demo environments.
-- ------------------------------------------------------------

TRUNCATE TABLE
    sales_follow_up,
    business_recommendations,
    pain_point_scores,
    dropoff_analysis,
    theme_analysis,
    sentiment_analysis,
    conversation_feedback,
    conversation_pain_points,
    question_answers,
    dynamic_questions,
    ai_model_runs,
    conversation_context,
    finance_preferences,
    customer_preferences,
    vehicle_interactions,
    vehicle_inventory,
    conversation_messages,
    conversation_sessions,
    customers,
    pain_points
RESTART IDENTITY CASCADE;

-- ------------------------------------------------------------
-- Helper function to generate deterministic UUIDs.
-- This keeps relationships stable across all demo tables.
-- ------------------------------------------------------------

DROP FUNCTION IF EXISTS demo_uuid(TEXT, INTEGER);

CREATE OR REPLACE FUNCTION demo_uuid(p_prefix TEXT, p_n INTEGER)
RETURNS UUID
LANGUAGE SQL
IMMUTABLE
AS $$
    SELECT (
        substr(md5(p_prefix || '-' || p_n::text), 1, 8) || '-' ||
        substr(md5(p_prefix || '-' || p_n::text), 9, 4) || '-' ||
        substr(md5(p_prefix || '-' || p_n::text), 13, 4) || '-' ||
        substr(md5(p_prefix || '-' || p_n::text), 17, 4) || '-' ||
        substr(md5(p_prefix || '-' || p_n::text), 21, 12)
    )::uuid;
$$;

-- ============================================================
-- 1. customers
-- 250 demo customers / visitors.
-- ============================================================

INSERT INTO customers (
    customer_id,
    visitor_id,
    external_customer_ref,
    customer_name,
    email,
    phone,
    location,
    region,
    postcode,
    customer_type,
    lead_source,
    marketing_campaign,
    consent_to_contact,
    preferred_contact_method,
    customer_metadata,
    created_at,
    updated_at
)
SELECT
    demo_uuid('customer', g),
    'VIS-' || lpad(g::text, 5, '0'),
    'EXT-CUST-' || lpad(g::text, 5, '0'),
    'Demo Customer ' || g,
    'customer' || g || '@demo-carfinance.co.uk',
    '+4477009' || lpad(g::text, 5, '0'),
    (ARRAY['London','Birmingham','Manchester','Leeds','Bristol','Liverpool','Nottingham','Sheffield','Cardiff','Reading'])[((g - 1) % 10) + 1],
    (ARRAY['South East','West Midlands','North West','Yorkshire','South West','North West','East Midlands','Yorkshire','Wales','South East'])[((g - 1) % 10) + 1],
    (ARRAY['SW1A 1AA','B1 1AA','M1 1AE','LS1 1UR','BS1 1AD','L1 8JQ','NG1 1AA','S1 2HE','CF10 1EP','RG1 1LZ'])[((g - 1) % 10) + 1],
    (ARRAY['new visitor','returning visitor','existing customer','demo user'])[((g - 1) % 4) + 1],
    (ARRAY['website','paid search','social campaign','email campaign','dealer referral','internal demo'])[((g - 1) % 6) + 1],
    (ARRAY['Spring Finance Campaign','Low Deposit Campaign','EV Finance Campaign','Family SUV Campaign','Used Car Finance Campaign'])[((g - 1) % 5) + 1],
    CASE WHEN g % 3 <> 0 THEN TRUE ELSE FALSE END,
    (ARRAY['email','phone','whatsapp','no preference'])[((g - 1) % 4) + 1],
    jsonb_build_object(
        'demo_segment', (ARRAY['budget focused','family buyer','EV curious','first-time finance','brand loyal'])[((g - 1) % 5) + 1],
        'customer_score', 1 + ((g - 1) % 5)
    ),
    now() - ((250 - g) || ' days')::interval,
    now() - ((250 - g) || ' days')::interval + interval '2 hours'
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 2. vehicle_inventory
-- 250 demo vehicles available for recommendation and reporting.
-- ============================================================

INSERT INTO vehicle_inventory (
    vehicle_id,
    stock_reference,
    brand,
    model,
    variant,
    body_type,
    fuel_type,
    transmission,
    colour,
    vehicle_year,
    registration_year,
    mileage,
    number_of_seats,
    vehicle_price,
    estimated_monthly_payment,
    representative_apr,
    availability_status,
    image_url,
    vehicle_description,
    vehicle_features,
    inventory_metadata,
    created_at,
    updated_at
)
SELECT
    demo_uuid('vehicle', g),
    'STK-' || lpad(g::text, 5, '0'),
    (ARRAY['Toyota','Volkswagen','BMW','Audi','Mercedes-Benz','Ford','Kia','Hyundai','Nissan','Tesla'])[((g - 1) % 10) + 1],
    (ARRAY['Corolla','Golf','3 Series','A3','A-Class','Focus','Sportage','Tucson','Qashqai','Model 3'])[((g - 1) % 10) + 1],
    (ARRAY['SE','Sport','Premium','Business','Family','Executive'])[((g - 1) % 6) + 1],
    (ARRAY['Hatchback','SUV','Saloon','Estate','Crossover'])[((g - 1) % 5) + 1],
    (ARRAY['Petrol','Diesel','Hybrid','Electric'])[((g - 1) % 4) + 1],
    (ARRAY['Manual','Automatic'])[((g - 1) % 2) + 1],
    (ARRAY['Black','White','Silver','Blue','Grey','Red'])[((g - 1) % 6) + 1],
    2018 + (g % 8),
    2018 + (g % 8),
    5000 + (g * 217),
    4 + (g % 4),
    9500 + (g * 145),
    180 + (g % 120),
    6.9000 + ((g % 30)::numeric / 10),
    (ARRAY['available','available','available','reserved','coming soon'])[((g - 1) % 5) + 1],
    'https://demo-carfinance.local/images/car-' || g || '.jpg',
    'Demo vehicle for AI car finance journey: suitable for customer preference and finance recommendation testing.',
    jsonb_build_array(
        (ARRAY['parking sensors','sat nav','heated seats','reverse camera','adaptive cruise'])[((g - 1) % 5) + 1],
        (ARRAY['low mileage','family friendly','fuel efficient','premium interior','EV compatible'])[((g - 1) % 5) + 1]
    ),
    jsonb_build_object(
        'dealer_region', (ARRAY['South','Midlands','North','Wales'])[((g - 1) % 4) + 1],
        'demo_stock_age_days', g % 90
    ),
    now() - ((g % 120) || ' days')::interval,
    now() - ((g % 15) || ' days')::interval
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 3. pain_points
-- 250 demo pain point master records.
-- This creates enough variation for dashboard filtering.
-- ============================================================

INSERT INTO pain_points (
    pain_point_id,
    pain_point_category,
    pain_point_name,
    pain_point_description,
    business_area,
    default_severity,
    active_flag,
    created_at,
    updated_at
)
SELECT
    demo_uuid('pain_point', g),
    (ARRAY['Pricing','Finance','Deposit','APR','Loan Term','Trust','Vehicle','Experience','Credit Check','Application Process'])[((g - 1) % 10) + 1],
    (ARRAY[
        'Pricing confusion',
        'APR concern',
        'Deposit concern',
        'Monthly payment concern',
        'Loan term confusion',
        'Trust issue',
        'No suitable car found',
        'Too many questions',
        'Credit check worry',
        'Application process unclear'
    ])[((g - 1) % 10) + 1] || ' - scenario ' || lpad(g::text, 3, '0'),
    'Demo pain point used for car finance chatbot analytics, scoring and business prioritisation reporting.',
    (ARRAY['finance','finance','finance','finance','finance','trust','vehicle','UX','risk','process'])[((g - 1) % 10) + 1],
    1 + ((g - 1) % 5),
    TRUE,
    now() - ((250 - g) || ' days')::interval,
    now() - ((250 - g) || ' days')::interval + interval '1 hour'
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 4. conversation_sessions
-- 250 conversations linked to 250 customers.
-- ============================================================

INSERT INTO conversation_sessions (
    conversation_id,
    customer_id,
    session_id,
    channel,
    application_area,
    conversation_start_time,
    conversation_end_time,
    duration_seconds,
    conversation_status,
    journey_stage_started,
    journey_stage_ended,
    total_user_messages,
    total_bot_messages,
    total_messages,
    enquiry_submitted,
    callback_requested,
    sales_escalated,
    converted_flag,
    dropoff_flag,
    dropoff_stage,
    overall_sentiment_label,
    overall_buying_intent_score,
    conversation_summary,
    raw_transcript,
    session_metadata,
    created_at,
    updated_at
)
SELECT
    demo_uuid('conversation', g),
    demo_uuid('customer', g),
    'SESSION-' || lpad(g::text, 5, '0'),
    (ARRAY['web app','mobile web','internal demo','sales-assisted'])[((g - 1) % 4) + 1],
    'AI car finance feedback chatbot',
    now() - ((250 - g) || ' days')::interval,
    now() - ((250 - g) || ' days')::interval + ((300 + (g * 7) % 1800) || ' seconds')::interval,
    300 + ((g * 7) % 1800),
    CASE
        WHEN g % 10 = 0 THEN 'converted'
        WHEN g % 5 = 0 THEN 'dropped off'
        WHEN g % 7 = 0 THEN 'escalated'
        ELSE 'completed'
    END,
    'greeting',
    (ARRAY['preference_collection','car_recommendation','finance_explanation','enquiry_form','final_confirmation'])[((g - 1) % 5) + 1],
    3 + (g % 8),
    4 + (g % 8),
    7 + (g % 16),
    CASE WHEN g % 4 = 0 OR g % 10 = 0 THEN TRUE ELSE FALSE END,
    CASE WHEN g % 6 = 0 THEN TRUE ELSE FALSE END,
    CASE WHEN g % 7 = 0 THEN TRUE ELSE FALSE END,
    CASE WHEN g % 10 = 0 THEN TRUE ELSE FALSE END,
    CASE WHEN g % 5 = 0 THEN TRUE ELSE FALSE END,
    CASE
        WHEN g % 5 = 0 THEN (ARRAY['preference_collection','car_recommendation','finance_explanation','enquiry_form'])[((g - 1) % 4) + 1]
        ELSE NULL
    END,
    (ARRAY['positive','neutral','negative','confused','frustrated'])[((g - 1) % 5) + 1],
    1 + ((g - 1) % 5),
    'Customer discussed car finance needs including budget, deposit, vehicle preference and finance concerns. Demo summary for dashboard reporting.',
    'User asked about monthly payment, deposit, APR and suitable vehicles. Bot responded with finance guidance and vehicle recommendations.',
    jsonb_build_object(
        'experiment_name', 'car_finance_feedback_demo',
        'journey_version', 'v1',
        'persona', (ARRAY['budget buyer','family buyer','EV explorer','premium buyer','first time finance customer'])[((g - 1) % 5) + 1]
    ),
    now() - ((250 - g) || ' days')::interval,
    now() - ((250 - g) || ' days')::interval + interval '30 minutes'
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 5. conversation_messages
-- 250 messages linked to conversations.
-- ============================================================

INSERT INTO conversation_messages (
    message_id,
    conversation_id,
    customer_id,
    message_sequence,
    sender_type,
    message_type,
    message_text,
    message_timestamp,
    detected_intent,
    detected_topic,
    detected_entities,
    response_time_seconds,
    was_answered,
    confidence_score,
    ai_generated_flag,
    contains_question_flag,
    contains_feedback_flag,
    contains_objection_flag,
    message_metadata,
    created_at
)
SELECT
    demo_uuid('message', g),
    demo_uuid('conversation', g),
    demo_uuid('customer', g),
    1,
    CASE WHEN g % 2 = 0 THEN 'user' ELSE 'bot' END,
    (ARRAY['question','answer','clarification','recommendation','finance_explanation','feedback'])[((g - 1) % 6) + 1],
    CASE
        WHEN g % 10 = 1 THEN 'What monthly payment would I need for a family SUV with low deposit?'
        WHEN g % 10 = 2 THEN 'I am confused about APR and total finance cost.'
        WHEN g % 10 = 3 THEN 'Can you show electric cars with lower running cost?'
        WHEN g % 10 = 4 THEN 'The deposit looks high. Do I have another option?'
        WHEN g % 10 = 5 THEN 'I am not sure whether PCP or HP is better for me.'
        WHEN g % 10 = 6 THEN 'Please shortlist cars below my monthly budget.'
        WHEN g % 10 = 7 THEN 'I want a reliable car for family and school runs.'
        WHEN g % 10 = 8 THEN 'Can someone call me back to explain finance?'
        WHEN g % 10 = 9 THEN 'I do not understand the credit check step.'
        ELSE 'The chatbot recommendation was helpful but I need clearer pricing.'
    END,
    now() - ((250 - g) || ' days')::interval + interval '2 minutes',
    (ARRAY['ask_finance','compare_cars','ask_apr','ask_deposit','request_callback','express_concern','shortlist_vehicle'])[((g - 1) % 7) + 1],
    (ARRAY['monthly payment','APR','deposit','loan term','vehicle preference','credit check','callback'])[((g - 1) % 7) + 1],
    jsonb_build_object(
        'budget', 200 + (g % 150),
        'deposit', 500 + (g % 20) * 100,
        'topic_strength', 1 + ((g - 1) % 5)
    ),
    1 + (g % 12),
    CASE WHEN g % 6 <> 0 THEN TRUE ELSE FALSE END,
    round((0.55 + ((g % 45)::numeric / 100))::numeric, 4),
    CASE WHEN g % 2 <> 0 THEN TRUE ELSE FALSE END,
    TRUE,
    CASE WHEN g % 8 = 0 THEN TRUE ELSE FALSE END,
    CASE WHEN g % 4 = 0 THEN TRUE ELSE FALSE END,
    jsonb_build_object('source_component', 'streamlit_chat', 'message_quality', (ARRAY['good','average','needs review'])[((g - 1) % 3) + 1]),
    now() - ((250 - g) || ' days')::interval + interval '2 minutes'
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 6. vehicle_interactions
-- 250 interactions linked to conversations, customers and vehicles.
-- ============================================================

INSERT INTO vehicle_interactions (
    vehicle_interaction_id,
    conversation_id,
    customer_id,
    vehicle_id,
    vehicle_external_ref,
    brand,
    model,
    variant,
    body_type,
    fuel_type,
    transmission,
    vehicle_price,
    estimated_monthly_payment,
    interaction_type,
    recommendation_rank,
    match_score,
    shortlisted_flag,
    viewed_detail_flag,
    enquiry_submitted_flag,
    interaction_timestamp,
    interaction_metadata
)
SELECT
    demo_uuid('vehicle_interaction', g),
    demo_uuid('conversation', g),
    demo_uuid('customer', g),
    demo_uuid('vehicle', g),
    'STK-' || lpad(g::text, 5, '0'),
    (ARRAY['Toyota','Volkswagen','BMW','Audi','Mercedes-Benz','Ford','Kia','Hyundai','Nissan','Tesla'])[((g - 1) % 10) + 1],
    (ARRAY['Corolla','Golf','3 Series','A3','A-Class','Focus','Sportage','Tucson','Qashqai','Model 3'])[((g - 1) % 10) + 1],
    (ARRAY['SE','Sport','Premium','Business','Family','Executive'])[((g - 1) % 6) + 1],
    (ARRAY['Hatchback','SUV','Saloon','Estate','Crossover'])[((g - 1) % 5) + 1],
    (ARRAY['Petrol','Diesel','Hybrid','Electric'])[((g - 1) % 4) + 1],
    (ARRAY['Manual','Automatic'])[((g - 1) % 2) + 1],
    9500 + (g * 145),
    180 + (g % 120),
    (ARRAY['viewed','recommended','shortlisted','compared','selected','enquired'])[((g - 1) % 6) + 1],
    1 + ((g - 1) % 5),
    round((0.50 + ((g % 50)::numeric / 100))::numeric, 4),
    CASE WHEN g % 3 = 0 THEN TRUE ELSE FALSE END,
    CASE WHEN g % 2 = 0 THEN TRUE ELSE FALSE END,
    CASE WHEN g % 4 = 0 THEN TRUE ELSE FALSE END,
    now() - ((250 - g) || ' days')::interval + interval '5 minutes',
    jsonb_build_object('recommendation_reason', 'Matched budget, body type and finance preference')
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 7. customer_preferences
-- 250 preference rows linked to conversations/customers.
-- ============================================================

INSERT INTO customer_preferences (
    preference_id,
    conversation_id,
    customer_id,
    preferred_body_type,
    preferred_brand,
    preferred_model,
    preferred_fuel_type,
    preferred_transmission,
    preferred_colour,
    number_of_seats,
    mileage_preference_min,
    mileage_preference_max,
    vehicle_age_preference_min,
    vehicle_age_preference_max,
    usage_purpose,
    priority_factor,
    must_have_features,
    nice_to_have_features,
    preference_source,
    confidence_score,
    preference_metadata,
    created_at,
    updated_at
)
SELECT
    demo_uuid('customer_preference', g),
    demo_uuid('conversation', g),
    demo_uuid('customer', g),
    (ARRAY['Hatchback','SUV','Saloon','Estate','Crossover'])[((g - 1) % 5) + 1],
    (ARRAY['Toyota','Volkswagen','BMW','Audi','Mercedes-Benz','Ford','Kia','Hyundai','Nissan','Tesla'])[((g - 1) % 10) + 1],
    (ARRAY['Corolla','Golf','3 Series','A3','A-Class','Focus','Sportage','Tucson','Qashqai','Model 3'])[((g - 1) % 10) + 1],
    (ARRAY['Petrol','Diesel','Hybrid','Electric'])[((g - 1) % 4) + 1],
    (ARRAY['Manual','Automatic'])[((g - 1) % 2) + 1],
    (ARRAY['Black','White','Silver','Blue','Grey','Red'])[((g - 1) % 6) + 1],
    4 + (g % 4),
    0,
    10000 + (g * 300),
    0,
    8,
    (ARRAY['family','commute','business use','long distance travel','first car'])[((g - 1) % 5) + 1],
    (ARRAY['low monthly payment','low deposit','reliability','comfort','fuel efficiency','brand preference'])[((g - 1) % 6) + 1],
    jsonb_build_array('parking sensors','good boot space','low running cost'),
    jsonb_build_array('heated seats','reverse camera','premium interior'),
    (ARRAY['user_selected','chatbot_extracted','ai_inferred'])[((g - 1) % 3) + 1],
    round((0.60 + ((g % 40)::numeric / 100))::numeric, 4),
    jsonb_build_object('preference_strength', 1 + ((g - 1) % 5)),
    now() - ((250 - g) || ' days')::interval + interval '3 minutes',
    now() - ((250 - g) || ' days')::interval + interval '6 minutes'
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 8. finance_preferences
-- 250 finance preference rows.
-- ============================================================

INSERT INTO finance_preferences (
    finance_preference_id,
    conversation_id,
    customer_id,
    monthly_budget_min,
    monthly_budget_max,
    deposit_amount,
    deposit_min,
    deposit_max,
    finance_type_interest,
    loan_term_months,
    annual_mileage,
    credit_score_band,
    apr_sensitivity,
    deposit_sensitivity,
    monthly_payment_sensitivity,
    affordability_concern_flag,
    credit_check_concern_flag,
    apr_concern_flag,
    deposit_concern_flag,
    finance_readiness,
    finance_readiness_score,
    preference_source,
    confidence_score,
    finance_metadata,
    created_at,
    updated_at
)
SELECT
    demo_uuid('finance_preference', g),
    demo_uuid('conversation', g),
    demo_uuid('customer', g),
    150 + (g % 100),
    250 + (g % 180),
    500 + ((g % 20) * 100),
    0 + ((g % 5) * 100),
    1500 + ((g % 20) * 150),
    (ARRAY['PCP','HP','lease','cash purchase','unsure'])[((g - 1) % 5) + 1],
    (ARRAY[24,36,48,60])[((g - 1) % 4) + 1],
    (ARRAY[6000,8000,10000,12000,15000])[((g - 1) % 5) + 1],
    (ARRAY['excellent','good','fair','poor','unknown'])[((g - 1) % 5) + 1],
    (ARRAY['low','medium','high'])[((g - 1) % 3) + 1],
    (ARRAY['low','medium','high'])[(g % 3) + 1],
    (ARRAY['low','medium','high'])[((g + 1) % 3) + 1],
    CASE WHEN g % 4 = 0 THEN TRUE ELSE FALSE END,
    CASE WHEN g % 9 = 0 THEN TRUE ELSE FALSE END,
    CASE WHEN g % 5 = 0 THEN TRUE ELSE FALSE END,
    CASE WHEN g % 6 = 0 THEN TRUE ELSE FALSE END,
    (ARRAY['low','medium','high','ready_to_apply'])[((g - 1) % 4) + 1],
    1 + ((g - 1) % 5),
    (ARRAY['user_selected','chatbot_extracted','ai_inferred'])[((g - 1) % 3) + 1],
    round((0.58 + ((g % 42)::numeric / 100))::numeric, 4),
    jsonb_build_object('finance_goal', 'Find affordable monthly plan', 'risk_flag', CASE WHEN g % 9 = 0 THEN 'credit concern' ELSE 'none' END),
    now() - ((250 - g) || ' days')::interval + interval '4 minutes',
    now() - ((250 - g) || ' days')::interval + interval '7 minutes'
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 9. conversation_context
-- 250 context memory records, one per conversation.
-- ============================================================

INSERT INTO conversation_context (
    context_id,
    conversation_id,
    customer_id,
    current_stage,
    previous_stage,
    last_user_intent,
    last_topic,
    known_budget,
    known_deposit,
    known_monthly_payment_preference,
    known_vehicle_type,
    known_brand,
    known_model,
    known_finance_concern,
    known_objection,
    context_completeness_score,
    context_summary,
    short_memory,
    long_memory,
    last_updated_by,
    created_at,
    updated_at
)
SELECT
    demo_uuid('conversation_context', g),
    demo_uuid('conversation', g),
    demo_uuid('customer', g),
    (ARRAY['preference_collection','car_recommendation','finance_explanation','enquiry_form','final_confirmation'])[((g - 1) % 5) + 1],
    (ARRAY['greeting','preference_collection','car_recommendation','finance_explanation'])[((g - 1) % 4) + 1],
    (ARRAY['ask_finance','compare_cars','ask_apr','ask_deposit','request_callback','express_concern'])[((g - 1) % 6) + 1],
    (ARRAY['monthly payment','APR','deposit','loan term','vehicle preference','credit check'])[((g - 1) % 6) + 1],
    250 + (g % 180),
    500 + ((g % 20) * 100),
    180 + (g % 120),
    (ARRAY['Hatchback','SUV','Saloon','Estate','Crossover'])[((g - 1) % 5) + 1],
    (ARRAY['Toyota','Volkswagen','BMW','Audi','Mercedes-Benz','Ford','Kia','Hyundai','Nissan','Tesla'])[((g - 1) % 10) + 1],
    (ARRAY['Corolla','Golf','3 Series','A3','A-Class','Focus','Sportage','Tucson','Qashqai','Model 3'])[((g - 1) % 10) + 1],
    (ARRAY['APR concern','deposit concern','monthly payment concern','credit check concern','no concern'])[((g - 1) % 5) + 1],
    (ARRAY['too expensive','deposit too high','APR unclear','not enough vehicle choice','needs human explanation'])[((g - 1) % 5) + 1],
    1 + ((g - 1) % 5),
    'Context memory contains customer budget, deposit, preferred vehicle type and finance concern for next-best response generation.',
    jsonb_build_object('budget', 250 + (g % 180), 'stage', 'active conversation memory'),
    jsonb_build_object('previous_interest', 'car finance', 'customer_segment', (ARRAY['budget buyer','family buyer','EV explorer'])[((g - 1) % 3) + 1]),
    'ai_agent',
    now() - ((250 - g) || ' days')::interval + interval '5 minutes',
    now() - ((250 - g) || ' days')::interval + interval '8 minutes'
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 10. ai_model_runs
-- 250 OpenAI/demo model usage records.
-- ============================================================

INSERT INTO ai_model_runs (
    ai_run_id,
    conversation_id,
    message_id,
    model_provider,
    model_name,
    prompt_type,
    system_prompt,
    user_prompt,
    full_prompt_payload,
    model_response,
    response_json,
    input_tokens,
    output_tokens,
    total_tokens,
    api_cost_estimate,
    latency_ms,
    temperature,
    max_tokens,
    success_flag,
    error_code,
    error_message,
    created_at
)
SELECT
    demo_uuid('ai_run', g),
    demo_uuid('conversation', g),
    demo_uuid('message', g),
    'OpenAI',
    (ARRAY['gpt-4o-mini','gpt-4.1-mini','gpt-4.1'])[((g - 1) % 3) + 1],
    (ARRAY['chat_response','question_generation','sentiment_analysis','pain_point_detection','theme_analysis','scoring'])[((g - 1) % 6) + 1],
    'You are a helpful car finance assistant. Ask relevant questions and explain finance clearly.',
    'Customer message about car finance, budget, deposit, APR or vehicle recommendation.',
    jsonb_build_object('temperature', 0.2, 'journey_stage', (ARRAY['preference','recommendation','finance','enquiry'])[((g - 1) % 4) + 1]),
    'Demo AI response explaining the finance option, asking a follow-up question, or extracting insight for reporting.',
    jsonb_build_object(
        'detected_intent', (ARRAY['ask_apr','ask_deposit','compare_vehicle','request_callback'])[((g - 1) % 4) + 1],
        'confidence', round((0.60 + ((g % 40)::numeric / 100))::numeric, 4)
    ),
    300 + (g % 500),
    120 + (g % 250),
    420 + (g % 750),
    round((0.001 + ((g % 30)::numeric / 10000))::numeric, 6),
    600 + (g % 2400),
    0.2000,
    800,
    CASE WHEN g % 50 = 0 THEN FALSE ELSE TRUE END,
    CASE WHEN g % 50 = 0 THEN 'DEMO_TIMEOUT' ELSE NULL END,
    CASE WHEN g % 50 = 0 THEN 'Demo simulated timeout for error reporting.' ELSE NULL END,
    now() - ((250 - g) || ' days')::interval + interval '6 minutes'
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 11. dynamic_questions
-- 250 AI-generated follow-up questions.
-- ============================================================

INSERT INTO dynamic_questions (
    question_id,
    conversation_id,
    message_id,
    ai_run_id,
    question_sequence,
    question_text,
    question_category,
    question_reason,
    triggering_user_intent,
    triggering_topic,
    expected_answer_type,
    question_priority,
    was_answered,
    caused_dropoff_flag,
    created_at
)
SELECT
    demo_uuid('dynamic_question', g),
    demo_uuid('conversation', g),
    demo_uuid('message', g),
    demo_uuid('ai_run', g),
    1 + ((g - 1) % 5),
    (ARRAY[
        'What monthly payment would feel comfortable for you?',
        'How much deposit would you prefer to pay upfront?',
        'Would you prefer PCP, HP, lease or are you unsure?',
        'Is lower monthly payment or lower deposit more important?',
        'Would you like a sales adviser to explain this finance option?'
    ])[((g - 1) % 5) + 1],
    (ARRAY['budget','deposit','finance_type','priority','callback'])[((g - 1) % 5) + 1],
    'AI generated this question based on the previous user message and current journey context.',
    (ARRAY['ask_finance','ask_deposit','ask_apr','compare_cars','request_callback'])[((g - 1) % 5) + 1],
    (ARRAY['monthly payment','deposit','APR','vehicle recommendation','callback'])[((g - 1) % 5) + 1],
    (ARRAY['number','number','single_choice','single_choice','yes_no'])[((g - 1) % 5) + 1],
    1 + ((g - 1) % 5),
    CASE WHEN g % 6 <> 0 THEN TRUE ELSE FALSE END,
    CASE WHEN g % 20 = 0 THEN TRUE ELSE FALSE END,
    now() - ((250 - g) || ' days')::interval + interval '7 minutes'
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 12. question_answers
-- 250 answers to dynamic questions.
-- ============================================================

INSERT INTO question_answers (
    answer_id,
    question_id,
    conversation_id,
    customer_id,
    message_id,
    answer_text,
    answer_value,
    answer_type,
    extracted_entity,
    extracted_entities,
    confidence_score,
    answer_timestamp
)
SELECT
    demo_uuid('question_answer', g),
    demo_uuid('dynamic_question', g),
    demo_uuid('conversation', g),
    demo_uuid('customer', g),
    demo_uuid('message', g),
    (ARRAY[
        'I can afford around 300 per month.',
        'I would prefer the lowest possible deposit.',
        'I am unsure between PCP and HP.',
        'Lower monthly payment is more important for me.',
        'Yes, I would like someone to call me.'
    ])[((g - 1) % 5) + 1],
    (ARRAY['300','low deposit','unsure','low monthly payment','callback requested'])[((g - 1) % 5) + 1],
    (ARRAY['budget','deposit','finance_type','priority','callback_request'])[((g - 1) % 5) + 1],
    (ARRAY['monthly_budget','deposit_preference','finance_type','priority_factor','callback'])[((g - 1) % 5) + 1],
    jsonb_build_object(
        'monthly_budget', 200 + (g % 180),
        'deposit', 500 + ((g % 20) * 100),
        'callback_requested', CASE WHEN g % 5 = 0 THEN TRUE ELSE FALSE END
    ),
    round((0.60 + ((g % 40)::numeric / 100))::numeric, 4),
    now() - ((250 - g) || ' days')::interval + interval '8 minutes'
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 13. conversation_pain_points
-- 250 detected pain point records.
-- ============================================================

INSERT INTO conversation_pain_points (
    conversation_pain_point_id,
    conversation_id,
    customer_id,
    message_id,
    pain_point_id,
    ai_run_id,
    detected_phrase,
    detection_method,
    severity_score,
    confidence_score,
    customer_emotion,
    journey_stage,
    requires_follow_up,
    resolved_flag,
    detected_at,
    detection_metadata
)
SELECT
    demo_uuid('conversation_pain_point', g),
    demo_uuid('conversation', g),
    demo_uuid('customer', g),
    demo_uuid('message', g),
    demo_uuid('pain_point', g),
    demo_uuid('ai_run', g),
    (ARRAY[
        'APR is confusing',
        'Deposit looks too high',
        'Monthly payment is too expensive',
        'I do not understand PCP versus HP',
        'I cannot find the right car'
    ])[((g - 1) % 5) + 1],
    (ARRAY['LLM','keyword','rule_based','manual_review'])[((g - 1) % 4) + 1],
    1 + ((g - 1) % 5),
    round((0.55 + ((g % 45)::numeric / 100))::numeric, 4),
    (ARRAY['confused','frustrated','worried','neutral','interested'])[((g - 1) % 5) + 1],
    (ARRAY['preference_collection','car_recommendation','finance_explanation','enquiry_form','final_confirmation'])[((g - 1) % 5) + 1],
    CASE WHEN g % 4 = 0 THEN TRUE ELSE FALSE END,
    CASE WHEN g % 6 = 0 THEN TRUE ELSE FALSE END,
    now() - ((250 - g) || ' days')::interval + interval '9 minutes',
    jsonb_build_object('detector_version', 'v1', 'rule_family', 'car_finance_feedback')
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 14. conversation_feedback
-- 250 customer/staff feedback records.
-- ============================================================

INSERT INTO conversation_feedback (
    feedback_id,
    conversation_id,
    customer_id,
    message_id,
    feedback_type,
    feedback_text,
    feedback_source,
    feedback_category,
    sentiment_label,
    severity_score,
    action_required,
    action_notes,
    created_at
)
SELECT
    demo_uuid('conversation_feedback', g),
    demo_uuid('conversation', g),
    demo_uuid('customer', g),
    demo_uuid('message', g),
    (ARRAY['complaint','suggestion','confusion','objection','positive_feedback','staff_note'])[((g - 1) % 6) + 1],
    (ARRAY[
        'Finance explanation needs to be clearer.',
        'Please show total cost and monthly cost together.',
        'I do not understand how APR affects my payment.',
        'Deposit is higher than expected.',
        'The vehicle recommendation was helpful.',
        'Sales team should follow up with this customer.'
    ])[((g - 1) % 6) + 1],
    (ARRAY['customer_message','chatbot_summary','sales_agent','manual_review'])[((g - 1) % 4) + 1],
    (ARRAY['pricing','APR','deposit','loan term','vehicle recommendation','callback'])[((g - 1) % 6) + 1],
    (ARRAY['positive','neutral','negative','confused','frustrated'])[((g - 1) % 5) + 1],
    1 + ((g - 1) % 5),
    CASE WHEN g % 3 = 0 THEN TRUE ELSE FALSE END,
    'Demo action note for business dashboard and follow-up workflow.',
    now() - ((250 - g) || ' days')::interval + interval '10 minutes'
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 15. sentiment_analysis
-- 250 sentiment analysis records.
-- ============================================================

INSERT INTO sentiment_analysis (
    sentiment_id,
    conversation_id,
    message_id,
    ai_run_id,
    analysis_level,
    sentiment_label,
    sentiment_score,
    emotion_label,
    buying_intent_score,
    urgency_score,
    confusion_score,
    frustration_score,
    confidence_score,
    analysis_timestamp,
    analysis_metadata
)
SELECT
    demo_uuid('sentiment', g),
    demo_uuid('conversation', g),
    demo_uuid('message', g),
    demo_uuid('ai_run', g),
    (ARRAY['message','conversation','session_summary'])[((g - 1) % 3) + 1],
    (ARRAY['positive','neutral','negative','confused','frustrated'])[((g - 1) % 5) + 1],
    round((-1.0 + ((g % 200)::numeric / 100))::numeric, 4),
    (ARRAY['interested','worried','confused','frustrated','ready to buy'])[((g - 1) % 5) + 1],
    1 + ((g - 1) % 5),
    1 + (g % 5),
    1 + ((g + 1) % 5),
    1 + ((g + 2) % 5),
    round((0.60 + ((g % 40)::numeric / 100))::numeric, 4),
    now() - ((250 - g) || ' days')::interval + interval '11 minutes',
    jsonb_build_object('analysis_model', 'demo_sentiment_classifier', 'journey_stage', (ARRAY['preference','recommendation','finance','enquiry'])[((g - 1) % 4) + 1])
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 16. theme_analysis
-- 250 recurring theme records.
-- ============================================================

INSERT INTO theme_analysis (
    theme_id,
    conversation_id,
    ai_run_id,
    theme_category,
    theme_name,
    theme_description,
    theme_frequency,
    representative_message,
    journey_stage,
    sentiment_label,
    confidence_score,
    created_at,
    theme_metadata
)
SELECT
    demo_uuid('theme', g),
    demo_uuid('conversation', g),
    demo_uuid('ai_run', g),
    (ARRAY['finance','vehicle','pricing','trust','process','UX'])[((g - 1) % 6) + 1],
    (ARRAY['APR question','deposit concern','SUV preference','monthly payment concern','credit check question','callback request'])[((g - 1) % 6) + 1],
    'Recurring theme detected in customer conversation for demo dashboard insight.',
    1 + (g % 6),
    (ARRAY[
        'Customer asked about APR and total finance cost.',
        'Customer wanted lower deposit options.',
        'Customer preferred a family SUV.',
        'Customer needed monthly payment clarity.',
        'Customer was unsure about credit check.',
        'Customer requested sales follow-up.'
    ])[((g - 1) % 6) + 1],
    (ARRAY['preference_collection','car_recommendation','finance_explanation','enquiry_form'])[((g - 1) % 4) + 1],
    (ARRAY['positive','neutral','negative','confused','frustrated'])[((g - 1) % 5) + 1],
    round((0.57 + ((g % 42)::numeric / 100))::numeric, 4),
    now() - ((250 - g) || ' days')::interval + interval '12 minutes',
    jsonb_build_object('theme_cluster', (g % 12), 'reporting_bucket', 'business insight')
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 17. dropoff_analysis
-- 250 drop-off analysis rows.
-- One per conversation. Some are completed journeys marked as
-- not_dropped to keep dashboard data complete.
-- ============================================================

INSERT INTO dropoff_analysis (
    dropoff_id,
    conversation_id,
    customer_id,
    last_user_message_id,
    last_bot_message_id,
    dropoff_stage,
    last_topic,
    dropoff_reason_detected,
    dropoff_reason_description,
    time_before_dropoff_seconds,
    messages_before_dropoff,
    reengagement_required,
    reengagement_reason,
    confidence_score,
    created_at,
    dropoff_metadata
)
SELECT
    demo_uuid('dropoff', g),
    demo_uuid('conversation', g),
    demo_uuid('customer', g),
    demo_uuid('message', g),
    demo_uuid('message', g),
    CASE
        WHEN g % 5 = 0 THEN (ARRAY['preference_collection','car_recommendation','finance_explanation','enquiry_form'])[((g - 1) % 4) + 1]
        ELSE 'completed_journey'
    END,
    (ARRAY['monthly payment','APR','deposit','loan term','vehicle preference','credit check'])[((g - 1) % 6) + 1],
    CASE
        WHEN g % 5 = 0 THEN (ARRAY['price_concern','finance_confusion','no_suitable_car','too_many_questions','low_trust'])[((g - 1) % 5) + 1]
        ELSE 'not_dropped'
    END,
    CASE
        WHEN g % 5 = 0 THEN 'Customer stopped during the journey after a finance or vehicle concern.'
        ELSE 'Conversation completed or progressed without detected drop-off.'
    END,
    180 + (g * 4),
    3 + (g % 12),
    CASE WHEN g % 5 = 0 OR g % 7 = 0 THEN TRUE ELSE FALSE END,
    CASE WHEN g % 5 = 0 THEN 'Re-engage customer with simpler finance explanation.' ELSE NULL END,
    round((0.60 + ((g % 40)::numeric / 100))::numeric, 4),
    now() - ((250 - g) || ' days')::interval + interval '13 minutes',
    jsonb_build_object('dropoff_detector', 'demo_rule_and_ai', 'session_active_minutes', 5 + (g % 25))
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 18. pain_point_scores
-- 250 scoring rows linked to pain points.
-- ============================================================

INSERT INTO pain_point_scores (
    score_id,
    pain_point_id,
    score_period,
    period_start_date,
    period_end_date,
    occurrence_count,
    affected_conversation_count,
    severity_score,
    frequency_score,
    business_impact_score,
    customer_impact_score,
    conversion_impact_score,
    total_score,
    priority_rank,
    priority_level,
    calculation_method,
    calculation_notes,
    calculated_at,
    score_metadata
)
SELECT
    demo_uuid('pain_point_score', g),
    demo_uuid('pain_point', g),
    (ARRAY['daily','weekly','monthly','demo-run'])[((g - 1) % 4) + 1],
    current_date - ((g % 30) || ' days')::interval,
    current_date,
    1 + (g % 40),
    1 + (g % 30),
    1 + ((g - 1) % 5),
    1 + (g % 5),
    1 + ((g + 1) % 5),
    1 + ((g + 2) % 5),
    1 + ((g + 3) % 5),
    round((
        ((1 + ((g - 1) % 5)) * 0.30) +
        ((1 + (g % 5)) * 0.25) +
        ((1 + ((g + 1) % 5)) * 0.25) +
        ((1 + ((g + 2) % 5)) * 0.10) +
        ((1 + ((g + 3) % 5)) * 0.10)
    )::numeric, 4),
    g,
    CASE
        WHEN g <= 50 THEN 'critical'
        WHEN g <= 125 THEN 'high'
        WHEN g <= 200 THEN 'medium'
        ELSE 'low'
    END,
    (ARRAY['manual','weighted','AI-assisted'])[((g - 1) % 3) + 1],
    'Demo weighted pain point score calculated from severity, frequency, business impact, customer impact and conversion impact.',
    now() - ((250 - g) || ' days')::interval + interval '14 minutes',
    jsonb_build_object('weighting_version', 'v1', 'used_for_dashboard', TRUE)
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 19. business_recommendations
-- 250 recommended actions linked to pain points and scores.
-- ============================================================

INSERT INTO business_recommendations (
    recommendation_id,
    pain_point_id,
    score_id,
    recommendation_title,
    recommendation_description,
    recommended_owner,
    action_priority,
    expected_business_benefit,
    expected_customer_benefit,
    estimated_effort,
    status,
    target_completion_date,
    implemented_at,
    created_at,
    updated_at,
    recommendation_metadata
)
SELECT
    demo_uuid('business_recommendation', g),
    demo_uuid('pain_point', g),
    demo_uuid('pain_point_score', g),
    (ARRAY[
        'Simplify APR explanation',
        'Show monthly cost breakdown',
        'Add lower deposit filter',
        'Improve PCP versus HP guidance',
        'Trigger sales callback for confused customers'
    ])[((g - 1) % 5) + 1] || ' #' || g,
    'Recommended business action generated from chatbot insights and pain point scoring for demo reporting.',
    (ARRAY['product','sales','finance','UX','support','engineering'])[((g - 1) % 6) + 1],
    CASE
        WHEN g <= 50 THEN 'critical'
        WHEN g <= 125 THEN 'high'
        WHEN g <= 200 THEN 'medium'
        ELSE 'low'
    END,
    'Improve enquiry conversion, reduce drop-off and increase customer confidence.',
    'Customer receives clearer explanation, better recommendations and faster support.',
    (ARRAY['small','medium','large'])[((g - 1) % 3) + 1],
    (ARRAY['open','in_review','approved','implemented','rejected'])[((g - 1) % 5) + 1],
    current_date + ((g % 45) || ' days')::interval,
    CASE WHEN g % 5 = 4 THEN now() - ((g % 20) || ' days')::interval ELSE NULL END,
    now() - ((250 - g) || ' days')::interval + interval '15 minutes',
    now() - ((250 - g) || ' days')::interval + interval '16 minutes',
    jsonb_build_object('dashboard_card', TRUE, 'business_case', 'car finance feedback optimisation')
FROM generate_series(1, 250) AS gs(g);

-- ============================================================
-- 20. sales_follow_up
-- 250 sales/support follow-up records.
-- ============================================================

INSERT INTO sales_follow_up (
    follow_up_id,
    conversation_id,
    customer_id,
    assigned_to,
    follow_up_required,
    follow_up_reason,
    follow_up_priority,
    lead_quality,
    preferred_contact_method,
    callback_requested,
    callback_requested_time,
    follow_up_status,
    first_contacted_at,
    last_contacted_at,
    outcome,
    outcome_notes,
    created_at,
    updated_at,
    follow_up_metadata
)
SELECT
    demo_uuid('sales_follow_up', g),
    demo_uuid('conversation', g),
    demo_uuid('customer', g),
    (ARRAY['Sales Agent A','Sales Agent B','Finance Specialist','Customer Support','Unassigned'])[((g - 1) % 5) + 1],
    CASE WHEN g % 4 <> 0 THEN TRUE ELSE FALSE END,
    (ARRAY['high_intent','finance_question','complaint','callback_requested','confused_customer','negative_sentiment'])[((g - 1) % 6) + 1],
    (ARRAY['low','medium','high','critical'])[((g - 1) % 4) + 1],
    (ARRAY['cold','warm','hot'])[((g - 1) % 3) + 1],
    (ARRAY['email','phone','whatsapp','no preference'])[((g - 1) % 4) + 1],
    CASE WHEN g % 6 = 0 THEN TRUE ELSE FALSE END,
    CASE WHEN g % 6 = 0 THEN now() + ((g % 72) || ' hours')::interval ELSE NULL END,
    (ARRAY['pending','contacted','converted','lost','no_response'])[((g - 1) % 5) + 1],
    CASE WHEN g % 5 IN (1,2,3) THEN now() - ((g % 15) || ' days')::interval ELSE NULL END,
    CASE WHEN g % 5 IN (1,2,3) THEN now() - ((g % 5) || ' days')::interval ELSE NULL END,
    (ARRAY['pending','customer contacted','finance explained','enquiry converted','customer not interested'])[((g - 1) % 5) + 1],
    'Demo follow-up outcome note for sales dashboard and workflow reporting.',
    now() - ((250 - g) || ' days')::interval + interval '17 minutes',
    now() - ((250 - g) || ' days')::interval + interval '18 minutes',
    jsonb_build_object('sales_playbook', 'car finance objection handling', 'priority_score', 1 + ((g - 1) % 5))
FROM generate_series(1, 250) AS gs(g);

-- ------------------------------------------------------------
-- Remove helper function after use to keep schema clean.
-- ------------------------------------------------------------

DROP FUNCTION IF EXISTS demo_uuid(TEXT, INTEGER);

COMMIT;

-- ============================================================
-- Validation query
-- Run this after script execution to confirm every table has
-- 250 demo rows.
-- ============================================================

SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM car_finance_ai.customers
UNION ALL SELECT 'conversation_sessions', COUNT(*) FROM car_finance_ai.conversation_sessions
UNION ALL SELECT 'conversation_messages', COUNT(*) FROM car_finance_ai.conversation_messages
UNION ALL SELECT 'vehicle_inventory', COUNT(*) FROM car_finance_ai.vehicle_inventory
UNION ALL SELECT 'vehicle_interactions', COUNT(*) FROM car_finance_ai.vehicle_interactions
UNION ALL SELECT 'customer_preferences', COUNT(*) FROM car_finance_ai.customer_preferences
UNION ALL SELECT 'finance_preferences', COUNT(*) FROM car_finance_ai.finance_preferences
UNION ALL SELECT 'conversation_context', COUNT(*) FROM car_finance_ai.conversation_context
UNION ALL SELECT 'ai_model_runs', COUNT(*) FROM car_finance_ai.ai_model_runs
UNION ALL SELECT 'dynamic_questions', COUNT(*) FROM car_finance_ai.dynamic_questions
UNION ALL SELECT 'question_answers', COUNT(*) FROM car_finance_ai.question_answers
UNION ALL SELECT 'pain_points', COUNT(*) FROM car_finance_ai.pain_points
UNION ALL SELECT 'conversation_pain_points', COUNT(*) FROM car_finance_ai.conversation_pain_points
UNION ALL SELECT 'conversation_feedback', COUNT(*) FROM car_finance_ai.conversation_feedback
UNION ALL SELECT 'sentiment_analysis', COUNT(*) FROM car_finance_ai.sentiment_analysis
UNION ALL SELECT 'theme_analysis', COUNT(*) FROM car_finance_ai.theme_analysis
UNION ALL SELECT 'dropoff_analysis', COUNT(*) FROM car_finance_ai.dropoff_analysis
UNION ALL SELECT 'pain_point_scores', COUNT(*) FROM car_finance_ai.pain_point_scores
UNION ALL SELECT 'business_recommendations', COUNT(*) FROM car_finance_ai.business_recommendations
UNION ALL SELECT 'sales_follow_up', COUNT(*) FROM car_finance_ai.sales_follow_up
ORDER BY table_name;

-- ============================================================
-- End of seed_demo_data.sql
-- ============================================================
