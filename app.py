import streamlit as st
import os
from openai import OpenAI
from google import genai

# Set page configuration
st.set_page_config(page_title="Multi-LLM Chat Assistant", layout="centered")
st.title("🤖 Multi-LLM Chat Assistant")

# Model and Key Management Sidebar 
with st.sidebar:
    st.subheader("Configuration")
    
    # 1.1 Model Selection
    selected_model = st.selectbox(
        "Choose LLM Provider:",
        options=["OpenAI (ChatGPT)", "Google (Gemini)", "xAI (Grok)"],
        index=0 # Default to OpenAI
    )

    # 1.2 API Key Input (Security Measure)
    api_key_placeholder = st.empty()
    if selected_model == "OpenAI (ChatGPT)":
        api_key = api_key_placeholder.text_input(
            "Enter OpenAI API Key (sk-...) 👇", 
            type="password", 
            key="openai_key"
        )
    elif selected_model == "Google (Gemini)":
        api_key = api_key_placeholder.text_input(
            "Enter Gemini API Key (AIza...) 👇", 
            type="password", 
            key="gemini_key"
        )
    elif selected_model == "xAI (Grok)":
        api_key = api_key_placeholder.text_input(
            "Enter Grok API Key 👇", 
            type="password", 
            key="grok_key"
        )
    
    # 1.3 Model Specific Settings
    temperature = st.slider(
        "Temperature", 
        min_value=0.0, 
        max_value=1.0, 
        value=0.7, 
        step=0.01,
        help="Controls randomness: lower is more deterministic, higher is more creative."
    )
    
    # 1.4 Clear Chat History Button
    if st.button("Clear Chat History", key="clear_chat"):
        st.session_state.messages = []
        st.rerun()

# --- 2. STATE MANAGEMENT (CHAT HISTORY) ---

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! Please select your LLM and enter your API key to begin."}
    ]

# --- 3. CORE LOGIC: API CALL FUNCTION ---

def get_llm_response(model_provider, api_key, prompt_messages, temp):
    """Handles the API call to the selected LLM provider."""
    
    # Extract the user's most recent prompt
    user_prompt = prompt_messages[-1]["content"]

    try:
        if not api_key:
            return "❌ ERROR: Please enter a valid API Key in the sidebar."

        if model_provider == "OpenAI (ChatGPT)":
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini", # Or gpt-4, gpt-3.5-turbo
                messages=prompt_messages,
                temperature=temp,
                stream=True
            )
            return response
            
        elif model_provider == "Google (Gemini)":
            client = genai.Client(api_key=api_key)
            # Gemini models use a slightly different message format (role: user/model)
            gemini_messages = [{"role": m["role"].replace("assistant", "model"), "parts": [m["content"]]} for m in prompt_messages]
            
            # The streaming interface in the `google-genai` SDK is used differently
            # For simplicity here, we'll use the non-streaming call to return the full response text.
            model = client.models.get_model("gemini-2.5-flash") 
            response = model.generate_content(
                contents=gemini_messages,
                config=genai.types.GenerateContentConfig(temperature=temp)
            )
            return response.text
            
        elif model_provider == "xAI (Grok)":
            # Grok API is accessed via an OpenAI-compatible interface
            # Replace with the official base_url when available/deployed
            client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1") 
            response = client.chat.completions.create(
                model="grok-1", # or grok-3
                messages=prompt_messages,
                temperature=temp,
                stream=True
            )
            return response

    except Exception as e:
        # A robust way to catch auth, rate-limiting, and other API errors
        return f"❌ LLM API Error: {e}"

# --- 4. MAIN CHAT INTERFACE ---

# Display all messages in the chat history
for message in st.session_state.messages:
    # Use selected_model for the assistant's avatar/name
    role = message["role"]
    display_role = "user" if role == "user" else selected_model
    with st.chat_message(display_role):
        st.markdown(message["content"])

# Process user input
if prompt := st.chat_input("Ask your question here..."):
    # 1. Add user message to history and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Get the response from the selected LLM
    with st.chat_message(selected_model):
        
        # Streamlit provides a placeholder for streaming responses
        response_placeholder = st.empty()
        
        # Prepare messages for API call (full history for context)
        prompt_messages = st.session_state.messages
        
        # Call the LLM
        response = get_llm_response(selected_model, api_key, prompt_messages, temperature)

        # 3. Handle and display the response
        if isinstance(response, str) and response.startswith("❌"):
            response_placeholder.markdown(response)
            # Stop execution or error out since API failed
            st.error("API call failed. Check your key and model name.")
            st.stop()
        
        if selected_model == "OpenAI (ChatGPT)" or selected_model == "xAI (Grok)":
            # For streaming APIs (like OpenAI)
            full_response = response_placeholder.write_stream(response)
        elif selected_model == "Google (Gemini)":
            # For non-streaming text response
            full_response = response
            response_placeholder.markdown(full_response)
        
        # 4. Add the final, complete response to the chat history
        st.session_state.messages.append({"role": "assistant", "content": full_response})
