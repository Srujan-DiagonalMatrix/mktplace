# Frontend UI

The main frontend entrypoint is `src/frontend/app.py`, launched with Streamlit. It talks to the FastAPI backend through `src.frontend.api_client.client.BackendClient`.

## Page structure

The current Streamlit page is a wide, three-column layout:

1. **Left navigation rail**
   - Rendered by `sidebar_nav(active="Chat")`.
   - Shows the app icon and five menu labels: Chat, Recommendations, Finance, Shortlist, and Settings.
   - The active item is always Chat in the current app shell.

2. **Middle chat region**
   - Starts with the branded header and `New Session` button.
   - Contains the Assistant chat panel with:
     - session id display,
     - AI and user message bubbles,
     - quick-reply buttons when the assistant asks for fuel or transmission,
     - a free-text input and send button.

3. **Right recommendations region**
   - Shows a recommendations panel with a status pill:
     - `Live recommendations` when the backend call succeeds,
     - `Offline preview` when the backend cannot be reached.
   - Displays summary cards for monthly budget, finance term, and deposit.
   - Displays Top Recommendations as a fixed maximum of 3 cards, in the exact order returned by the backend (no frontend re-sorting).
   - Ends with a compact Finance Summary card.

4. **Conditional detail/enquiry area**
   - If `st.session_state["selected_vehicle_obj"]` exists, the car detail component is rendered below the main columns.
   - If `st.session_state["selected_vehicle"]` exists, the enquiry form is rendered below the main columns and prefilled with that vehicle id.

5. **Safety footer**
   - A short data-safety statement is rendered at the bottom of the page.

## Display-only areas

The current UI intentionally includes several visual/demo controls that do not yet provide complete page-level navigation or workflows:

- **Sidebar navigation**: Chat, Recommendations, Finance, Shortlist, and Settings are static labels; clicking between full pages is not implemented yet.
- **Recommendation cards renderer**: `render_recommendation_cards(recs, variant="top3", ...)` defaults to `variant="top3"`; it also supports `variant="compact"`; any unknown variant falls back to the top-3 renderer.
- **Recommendations API call defaults**: `BackendClient.get_recommendations(session_id=None, limit=3)` defaults to `limit=3`, always sends the `limit` query parameter, conditionally adds `session_id`, and uses `timeout=10` for the HTTP request.
- **Heart icon on recommendation cards**: the heart is a visual shortlist affordance only in the recommendation card shell.
- **Finance Summary button**: `View Finance Options` is a display button; detailed finance option navigation is not implemented in the current main page.
- **Finance term and deposit summary values**: the summary components read from session state, but the current main page does not expose controls for changing them.

The separately rendered `car_detail()` and `enquiry_form()` components contain working backend calls, but they only appear when session state already contains a selected vehicle value.

### Recommendation card button behavior and related session state

Each recommendation card includes three action buttons with the following behavior:

- **View Details**: writes both `st.session_state["selected_vehicle_obj"]` (full recommendation object) and `st.session_state["selected_vehicle"]` (vehicle id), then triggers a rerun so the detail panel can render below the main layout.
- **Shortlist**: writes the same two session keys and calls shortlist add (`/shortlist/add`) when a session id and backend client are available.
- **Enquire**: writes the same two session keys and triggers a rerun so the enquiry form can render prefilled with `selected_vehicle`.

Key session-state fields:

- `selected_vehicle_obj`: stores the selected recommendation object and controls whether `car_detail()` is shown.
- `selected_vehicle`: stores the selected vehicle id and controls whether `enquiry_form(default_vehicle_id=...)` is shown.

## Chat interaction flow

The Chat area is the primary complete interaction path in the current UI.

1. **Session initialization**
   - `get_session_id()` creates a lightweight Streamlit session id if one does not exist.
   - `chat_panel()` calls `_ensure_messages()` to seed the conversation with three AI messages:
     - greeting,
     - assistant purpose,
     - monthly-budget question.

2. **User sends a message**
   - The user can type free text and click the send button.
   - When quick replies are available, the user can click one of the generated reply buttons instead.
   - Both paths call `_send_message()`.

3. **Backend request**
   - `_send_message()` appends the user bubble to `st.session_state["chat_messages"]`.
   - It calls `BackendClient.post_chat()` with:

     ```json
     {"session_id": "<current session id>", "message": "<user text>"}
     ```

   - The client sends the request to `POST /chat/message` on the backend.

4. **Preference extraction and session state update**
   - The chat panel extracts known preference keys from the backend response:
     - `intent`,
     - `monthly_budget`,
     - `fuel_type`,
     - `transmission`,
     - `family_size`.
   - Any returned values are merged into `st.session_state["preferences"]`.

5. **Next assistant prompt**
   - If `monthly_budget` is still missing, the assistant asks for the monthly budget.
   - If fuel type is missing, the assistant asks for fuel type and shows quick replies: Petrol, Diesel, Hybrid / Electric.
   - If transmission is missing, the assistant asks for transmission and shows quick replies: Automatic, Manual.
   - Once those key details are present, the assistant confirms that recommendations are being generated.

6. **Recommendations refresh**
   - The main recommendations panel reads the current session id and calls `GET /recommendations/from_session`.
   - Returned recommendations are normalised from list/dict response shapes and rendered as cards.
   - If the backend call fails, the panel shows an offline-preview state and an empty/no-recommendations message.

7. **Error handling**
   - If the chat request fails, the panel appends an AI message saying the backend could not be reached.
   - Existing messages remain in Streamlit session state until the user clicks `New Session`, which resets session-scoped UI state and reruns the app.
