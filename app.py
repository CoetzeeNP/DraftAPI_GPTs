import streamlit as st
from streamlit import switch_page
from openai import OpenAI
from google import genai
import os 
import json 
from datetime import datetime
from typing import Dict, Any, List, Union

# --- CONFIGURATION CONSTANTS ---
GEMINI_MODEL_NAME = "gemini-2.5-flash"
OPENAI_MODEL_NAME = "gpt-4o-mini"
GROK_MODEL_NAME = "grok-1" 
GROK_BASE_URL = "https://api.x.ai/v1" 

# --- HYPERPARAMETER BASELINE DEFAULTS ---
# Mimics common API defaults for temperature and top_p.
LLM_DEFAULTS = {
    "temperature": 0.7, 
    "top_p": 1.0,      
    "top_k": None      
}

# --- CUSTOM HYPERPARAMETER PROFILES (Your "Invisible" Control) ---
# Any parameter set here will OVERRIDE the LLM_DEFAULTS for that specific provider.
CUSTOM_LLM_PROFILES = {
    "OpenAI (ChatGPT)": {
        "temperature": 0.5, # Custom: More deterministic than 0.7
        "top_p": 0.9,       
    },
    "Google (Gemini)": {
        "temperature": 0.3, # Custom: Highly focused/factual
        "top_p": 0.95,
        "top_k": 30
    },
    "xAI (Grok)": {
        "temperature": 0.8, # Custom: More creative/conversational
    }
}


# --- FILE PATHS ---
SCORE_FILE = "quiz_scores.json"
QUIZ_PAGE_PREFIX = "pages/" 

# --- QUIZ LEVEL DEFINITIONS ---
QUIZ_LEVELS = {
    "Level 1: Fundamentals": "1_Level_1_Quiz.py",
    "Level 2: Architecture": "2_Level_2_Quiz.py",
    "Level 3: Advanced Concepts": "3_Level_3_Quiz.py",
    "Level 4: Implementation": "4_Level_4_Quiz.py",
    "Level 5: Multi-Select": "5_Level_5_MultiSelect.py"
}

# --- UTILITY FUNCTION TO RETRIEVE SECRET ---
def get_secret_key(provider: str) -> str:
    """Retrieves the API key for the specified provider from st.secrets."""
    key_map = {
        "OpenAI (ChatGPT)": "api_keys.openai",
        "Google (Gemini)": "api_keys.google",
        "xAI (Grok)": "api_keys.grok"
    }
    secret_key_path = key_map.get(provider)
    if secret_key_path:
        key = st.secrets.get(secret_key_path)
        return key if key else ""
    return ""

# --- SCORING AND STORAGE FUNCTIONS ---
def load_scores() -> Dict[str, Any]:
    """Loads all scores from the persistent JSON file."""
    if not os.path.exists(SCORE_FILE): return {}
    try:
        with open(SCORE_FILE, 'r') as f: return json.load(f)
    except json.JSONDecodeError: return {} 

# --- CORE PAGE SETUP ---
st.set_page_config(page_title="Multi-LLM Chat Assistant", layout="centered")
st.title("🤖 Multi-LLM Quiz and Chat Assistant")

# --- USERNAME INPUT & VALIDATION ---
user_name = st.text_input("Enter your unique Username to save scores:", key="user_name_input")
st.session_state["username"] = user_name

if not user_name:
    st.warning("Please enter a username to proceed, chat, and save your quiz scores.")
    st.stop() 

# --- QUIZ NAVIGATION AND SCORE DISPLAY ---
st.header("Jump to Quiz Levels")
col_user, col_logout = st.columns([4, 1])

with col_user:
    st.markdown(f"Logged in as: **{user_name}**. Scores will be saved under this name.")

with col_logout:
    if st.button("🚪 Logout", key="logout_btn"):
        # Clear the username and session state
        del st.session_state["username"]
        if "user_name_input" in st.session_state: del st.session_state["user_name_input"]
        st.session_state.messages = [] 
        st.rerun() 

st.markdown("---") 

# Load existing scores for the current user
all_scores = load_scores()
user_scores = all_scores.get(user_name, {})

# --- Function to display score and button ---
def display_quiz_level(level_name, file_path, column, user_scores):
    score_data = user_scores.get(level_name)
    
    if "Level 5" in level_name:
        # Assuming Level 5 score is 5 points (4+1)
        max_score = 5
    else:
        # Assuming Levels 1-4 scores are 2 points (2 questions)
        max_score = 2 

    display_score = f"{score_data['score_value']} / {max_score}" if score_data else "Not Taken"
    display_emoji = "✅" if score_data and score_data['score_value'] == max_score else ("➡️" if not score_data else "⚠️")

    with column:
        st.markdown(f"**{level_name}**")
        st.markdown(f"Score: **{display_score}**")
        
        if st.button(f"{display_emoji} Go to {level_name.split(':')[0]}", key=f"go_to_{level_name}"):
            switch_page(file_path.replace(QUIZ_PAGE_PREFIX, "")) 


# --- Displaying Navigation and Scores in Columns ---
cols = st.columns(len(QUIZ_LEVELS))

for i, (level, file) in enumerate(QUIZ_LEVELS.items()):
    display_quiz_level(level, file, cols[i], user_scores)

st.markdown("---") 

# --- 1. CONFIGURATION (Sidebar - Secrets Driven and Parameter Loading) ---
with st.sidebar:
    st.subheader("LLM Configuration")
    
    # 1. Model Selection
    selected_model = st.selectbox(
        "Choose LLM Provider:",
        options=["OpenAI (ChatGPT)", "Google (Gemini)", "xAI (Grok)"],
        index=0 
    )
    st.session_state["current_api_provider"] = selected_model
    st.session_state["selected_model"] = selected_model 

    # 2. Key Retrieval
    api_key = get_secret_key(selected_model)
    st.session_state["current_api_key"] = api_key 
    
    # 3. Load Dynamic Parameters (BASELINE + OVERRIDE)
    params = LLM_DEFAULTS.copy()
    params.update(CUSTOM_LLM_PROFILES.get(selected_model, {}))
    st.session_state["llm_params"] = params

    # 4. Status Display
    key_status = '✅ Key Loaded (from secrets.toml)' if api_key else '❌ Key Missing in secrets.toml'
    st.info(f"**Selected Provider:** {selected_model}\n**Key Status:** {key_status}")
    
    st.markdown("---")
    st.markdown(f"***Current Model Profile (Hidden Parameters):***")
    # Display the active parameters being used
    st.markdown(f"* Temperature: **{params.get('temperature')}** (Default: {LLM_DEFAULTS['temperature']})")
    st.markdown(f"* Top P: **{params.get('top_p')}** (Default: {LLM_DEFAULTS['top_p']})")
    if params.get('top_k') is not None:
        st.markdown(f"* Top K: **{params.get('top_k')}** (Default: None)")

    if st.button("Clear Chat History", key="clear_chat"):
        st.session_state.messages = []
        st.rerun()

# --- 2. STATE MANAGEMENT (CHAT HISTORY) ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": f"Hello! LLM chat is powered by **{selected_model}**. Ask me anything about LLMs!"}
    ]

# --- 3. CORE LOGIC: API CALL FUNCTION (Updated to use dynamic parameters) ---
def get_llm_response(model_provider, api_key, prompt_messages, params: Dict[str, Union[float, int, None]]):
    """Handles the API call to the selected LLM provider with dynamic parameters."""
    
    temp = params.get('temperature', 0.7)
    top_p = params.get('top_p', 1.0)
    top_k = params.get('top_k')
    
    try:
        if not api_key: return "❌ ERROR: The API Key is missing in your `secrets.toml` file for this provider."

        # Filter messages for OpenAI/Grok compatibility (role mapping)
        openai_messages = [{"role": m["role"], "content": m["content"]} for m in prompt_messages]
        
        if model_provider == "OpenAI (ChatGPT)":
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=OPENAI_MODEL_NAME, 
                messages=openai_messages, 
                temperature=temp, 
                top_p=top_p,
                stream=True
            )
            return response
            
        elif model_provider == "Google (Gemini)":
            client = genai.Client(api_key=api_key)
            # Adapt messages for Gemini format (user/model roles)
            gemini_messages = [{"role": m["role"].replace("assistant", "model"), "parts": [m["content"]]} for m in prompt_messages]
            
            # Configure generation parameters
            config = genai.types.GenerateContentConfig(
                temperature=temp,
                top_p=top_p,
                top_k=top_k if top_k is not None else 40 # Default Top K for Gemini if not provided
            )
            
            model = client.models.get_model(GEMINI_MODEL_NAME) 
            response = model.generate_content(contents=gemini_messages, config=config)
            return response.text
            
        elif model_provider == "xAI (Grok)":
            client = OpenAI(api_key=api_key, base_url=GROK_BASE_URL) 
            response = client.chat.completions.create(
                model=GROK_MODEL_NAME, 
                messages=openai_messages, 
                temperature=temp,
                top_p=top_p,
                stream=True
            )
            return response

    except Exception as e:
        return f"❌ LLM API Error: {e}"

# --- 4. MAIN CHAT INTERFACE ---
for message in st.session_state.messages:
    role = message["role"]
    display_role = "user" if role == "user" else selected_model
    with st.chat_message(display_role):
        st.markdown(message["content"])

if prompt := st.chat_input(f"Ask your question to {selected_model} here..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message(selected_model):
        response_placeholder = st.empty()
        prompt_messages = st.session_state.messages 
        
        # Pass dynamic parameters to the response function
        response = get_llm_response(
            selected_model, 
            st.session_state.get("current_api_key"), 
            prompt_messages, 
            st.session_state.get("llm_params", {})
        )

        if isinstance(response, str) and response.startswith("❌"):
            full_response = response
            response_placeholder.markdown(full_response)
            st.error("API call failed. Check your `secrets.toml` file.")
            
        
        elif selected_model == "OpenAI (ChatGPT)" or selected_model == "xAI (Grok)":
            full_response = ""
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    response_placeholder.markdown(full_response)
            
        elif selected_model == "Google (Gemini)":
            full_response = response
            response_placeholder.markdown(full_response)
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})