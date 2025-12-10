import streamlit as st
from openai import OpenAI
from google import genai
import json 
import os   
from datetime import datetime 
from typing import Dict, Any, List

# --- GLOBAL CONFIGURATION CONSTANTS ---
GEMINI_MODEL_NAME = "gemini-2.5-flash"
OPENAI_MODEL_NAME = "gpt-4o-mini"
GROK_MODEL_NAME = "grok-1" 
GROK_BASE_URL = "https://api.x.ai/v1"

# --- FILE PATHS ---
SCORE_FILE = "quiz_scores.json"
QUIZ_DATA_FILE = "quiz_data.json"

# --- SCORING AND STORAGE FUNCTIONS ---

def load_scores() -> Dict[str, Any]:
    """Loads all scores from the persistent JSON file."""
    if not os.path.exists(SCORE_FILE): return {}
    try:
        with open(SCORE_FILE, 'r') as f: return json.load(f)
    except json.JSONDecodeError: return {} 

def save_score(username: str, level: str, score: int, answer_data: Dict[str, Any]):
    """Saves the score (raw count/number) for the given user and level."""
    all_scores = load_scores()
    if username not in all_scores: all_scores[username] = {}
    
    all_scores[username][level] = {
        "score_value": score, 
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "answers": answer_data
    }
    
    with open(SCORE_FILE, 'w') as f:
        json.dump(all_scores, f, indent=4)

def load_quiz_data():
    """Loads all quiz data from the central JSON file."""
    if not os.path.exists(QUIZ_DATA_FILE):
        st.error(f"Configuration Error: The quiz data file '{QUIZ_DATA_FILE}' was not found in the root directory.")
        return {}
    try:
        with open(QUIZ_DATA_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        st.error(f"Configuration Error: Failed to parse '{QUIZ_DATA_FILE}'. Check JSON formatting.")
        return {}


# --- QUIZ DATA SETUP ---
CURRENT_LEVEL_KEY = "Level 1: Fundamentals" 
FULL_QUIZ_DATA = load_quiz_data()

# Robustly filter and check quiz data
if not FULL_QUIZ_DATA:
    st.stop() 

QUIZ_DATA = FULL_QUIZ_DATA.get(CURRENT_LEVEL_KEY, {})
if not QUIZ_DATA:
    st.error(f"Error: Could not find data for level '{CURRENT_LEVEL_KEY}' in quiz_data.json.")
    st.stop()


# --- STREAMLIT PAGE CONFIG ---
st.set_page_config(page_title=f"{CURRENT_LEVEL_KEY} Quiz", layout="wide")
st.header(f"📝 {CURRENT_LEVEL_KEY} Quiz")
st.markdown(f"Answer the **{len(QUIZ_DATA)}** questions below. Score is saved upon finalization.")

# --- 2. LLM HELP FUNCTION (Complete) ---
def get_llm_help(user_answer, question, memo, selected_model, api_key) -> str:
    """Provides constructive, guided feedback from the selected LLM."""
    if not api_key: return "❌ ERROR: Please configure your API key on the 'Multi-LLM Chat Assistant' page first."

    system_prompt = (
        "You are an objective tutor and expert on the topic. The user attempted to answer a question. "
        "Your task is to analyze the user's answer, provide encouraging, constructive feedback, "
        "and gently guide them toward the key concepts from the official memo, without simply giving away the full memo. "
        "Focus on the missing or incorrect concepts in the user's response. Be concise."
    )
    
    llm_prompt = f"""
    --- Question ---
    {question}
    --- User's Answer ---
    {user_answer}
    --- Official Memo (for your reference) ---
    {memo}
    
    Please provide your constructive feedback now.
    """

    try:
        if selected_model == "OpenAI (ChatGPT)":
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=OPENAI_MODEL_NAME,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": llm_prompt}],
            )
            return response.choices[0].message.content
        
        elif selected_model == "Google (Gemini)":
            client = genai.Client(api_key=api_key)
            model = client.models.get_model(GEMINI_MODEL_NAME)
            response = model.generate_content(
                contents=[system_prompt, llm_prompt], 
            )
            return response.text
            
        elif selected_model == "xAI (Grok)":
            client = OpenAI(api_key=api_key, base_url=GROK_BASE_URL)
            response = client.chat.completions.create(
                model=GROK_MODEL_NAME,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": llm_prompt}],
            )
            return response.choices[0].message.content
        
    except Exception as e:
        return f"❌ LLM API Error: {e}"


# --- 3. SESSION STATE INITIALIZATION ---

# Initialize answer storage (using "" for open-ended text answers)
if "multi_level_answers" not in st.session_state:
    st.session_state.multi_level_answers = {}
    for level, data in FULL_QUIZ_DATA.items():
        st.session_state.multi_level_answers[level] = {}
        for q_key in data.keys():
            # Use [] for multi-select (Level 5) and "" for open-ended
            initial_value = [] if q_key in ["Q1_Multi"] else ""
            st.session_state.multi_level_answers[level][q_key] = initial_value

# Initialize help history
if "multi_level_help_history" not in st.session_state:
    st.session_state.multi_level_help_history = {level: {} for level in FULL_QUIZ_DATA.keys()}


# --- 4. MAIN QUIZ INTERFACE ---

api_key = st.session_state.get("current_api_key")
selected_model = st.session_state.get("current_api_provider", "OpenAI (ChatGPT)")
username = st.session_state.get("username")
if not username: 
    st.error("Please return to the main page and enter your username to use the quiz.") 
    st.stop()

# Ensure this level's state exists
if CURRENT_LEVEL_KEY not in st.session_state.multi_level_answers:
    st.session_state.multi_level_answers[CURRENT_LEVEL_KEY] = {q_key: "" for q_key in QUIZ_DATA.keys()}
if CURRENT_LEVEL_KEY not in st.session_state.multi_level_help_history:
    st.session_state.multi_level_help_history[CURRENT_LEVEL_KEY] = {}


current_answers = st.session_state.multi_level_answers[CURRENT_LEVEL_KEY]
current_help_history = st.session_state.multi_level_help_history[CURRENT_LEVEL_KEY]

# Display questions for this specific level
for i, (q_key, data) in enumerate(QUIZ_DATA.items()):
    st.subheader(f"Question {i + 1}: {data['question']}")
    
    user_answer = st.text_area(
        "Your Answer:",
        value=current_answers.get(q_key, ""),
        key=f"{CURRENT_LEVEL_KEY}_{q_key}_answer", 
        height=150
    )
    
    # Update session state immediately on user input
    st.session_state.multi_level_answers[CURRENT_LEVEL_KEY][q_key] = user_answer
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        is_key_missing = api_key is None or api_key == ""
        if st.button("Ask LLM for Help", key=f"{CURRENT_LEVEL_KEY}_{q_key}_help_btn", disabled=is_key_missing):
            if is_key_missing:
                st.error("Configure API key on the main page first!")
            else:
                with st.spinner(f"Contacting {selected_model} for assistance..."):
                    help_response = get_llm_help(user_answer, data["question"], data["memo"], selected_model, api_key)
                    st.session_state.multi_level_help_history[CURRENT_LEVEL_KEY][q_key] = help_response
                    st.rerun() # Use st.rerun() to immediately display the help message
    
    if q_key in current_help_history:
        with col2:
            st.info(f"💡 LLM Guidance from {selected_model}:\n\n{current_help_history[q_key]}")

    st.markdown("---")

# --- 5. FINALIZE AND SAVE SCORE SECTION ---

st.header(f"✅ Finalize and Review {CURRENT_LEVEL_KEY}")

SCORE_KEY = f"reviewed_{CURRENT_LEVEL_KEY}" 

if st.button(f"Finalize and Save Score for {CURRENT_LEVEL_KEY}", key="finalize_score_btn"):
    
    st.session_state[SCORE_KEY] = True
    
    # Score is the total number of questions in the level (e.g., 2)
    final_score = len(QUIZ_DATA) 
    
    answer_data = st.session_state.multi_level_answers[CURRENT_LEVEL_KEY]
    
    save_score(username, CURRENT_LEVEL_KEY, final_score, answer_data)
    
    st.success(f"🎉 Quiz completed! Your score ({final_score} questions completed) has been saved for user **{username}**.")
    
    st.rerun() # FIX: Use st.rerun() to refresh the page and display the memo

# --- Display Review Content (Conditional) ---
if st.session_state.get(SCORE_KEY, False):
    st.subheader(f"Official Memo and Comparison for {CURRENT_LEVEL_KEY}")
    
    for q_key, data in QUIZ_DATA.items():
        st.markdown(f"### {q_key}: {data['question']}")
        
        user_response = st.session_state.multi_level_answers[CURRENT_LEVEL_KEY].get(q_key, "No Answer Provided.")
        st.text_area("Your Submitted Answer", user_response, height=100, disabled=True, key=f"sub_ans_{CURRENT_LEVEL_KEY}_{q_key}")
        st.text_area("Official Memo", data["memo"], height=100, disabled=True, key=f"memo_ans_{CURRENT_LEVEL_KEY}_{q_key}")
        
        if q_key in current_help_history:
            st.warning(f"Last Help Message Used: {current_help_history[q_key]}")

        st.markdown("***")