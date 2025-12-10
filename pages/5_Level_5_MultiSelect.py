import streamlit as st
import json 
import os   
from datetime import datetime 
from typing import Dict, Any, List

# --- GLOBAL CONFIGURATION CONSTANTS ---
HELP_TEMPERATURE = 0.4 
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
    with open(SCORE_FILE, 'w') as f: json.dump(all_scores, f, indent=4)

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
CURRENT_LEVEL_KEY = "Level 5: Multi-Select"
FULL_QUIZ_DATA = load_quiz_data()

if not FULL_QUIZ_DATA: st.stop()

# Extract the specific question data points
LEVEL_5_DATA = FULL_QUIZ_DATA.get(CURRENT_LEVEL_KEY, {})
if not LEVEL_5_DATA: 
    st.error(f"Error: Could not find data for level '{CURRENT_LEVEL_KEY}' in quiz_data.json.")
    st.stop()

MULTI_SELECT_QUESTION = LEVEL_5_DATA.get("Q1_Multi", {})
SINGLE_SELECT_QUESTION = LEVEL_5_DATA.get("Q2_Single", {})

if not MULTI_SELECT_QUESTION or not SINGLE_SELECT_QUESTION:
    st.error("Error: Missing Q1_Multi or Q2_Single keys in Level 5 data.")
    st.stop()


st.set_page_config(page_title=f"{CURRENT_LEVEL_KEY} Quiz", layout="wide")
st.header(f"📝 {CURRENT_LEVEL_KEY} Quiz")
st.markdown("This level has two questions with a **maximum score of 5 points** (4 points for multi-select, 1 point for single-select).")

# --- 1. SESSION STATE INITIALIZATION ---
if "multi_level_answers" not in st.session_state:
    st.session_state.multi_level_answers = {}
    for level, data in FULL_QUIZ_DATA.items():
        st.session_state.multi_level_answers[level] = {}
        for q_key in data.keys():
            # Q1_Multi must be a list [], Q2_Single must be a string ""
            initial_value = [] if q_key == "Q1_Multi" else ""
            st.session_state.multi_level_answers[level][q_key] = initial_value

if "multi_level_help_history" not in st.session_state:
    st.session_state.multi_level_help_history = {level: {} for level in FULL_QUIZ_DATA.keys()}


# --- 2. MAIN INTERFACE ---
username = st.session_state.get("username")
if not username: st.error("Please return to the main page and enter your username.") ; st.stop()


# --- Question 1: Multi-Select (Q1_Multi) ---

q1_data = MULTI_SELECT_QUESTION
st.markdown("## Question 1 (Max 4 Points)")
st.subheader(f"Q1: {q1_data['question']}")

# Display full statements
st.markdown("### Statements:")
for key, statement in q1_data['options'].items():
    st.markdown(f"**{key}.** {statement}")

st.markdown("---")

# Multiselect Input (Only keys A, B, C, D)
all_option_keys_q1 = list(q1_data["options"].keys())

# Get answer from session state (guaranteed to be a list)
previous_answer_keys_q1 = st.session_state.multi_level_answers.get(CURRENT_LEVEL_KEY, {}).get("Q1_Multi", [])

user_selected_keys_q1 = st.multiselect(
    "Select the letter(s) corresponding to the correct statements:",
    options=all_option_keys_q1,
    default=previous_answer_keys_q1,
    key=f"{CURRENT_LEVEL_KEY}_Q1_Multi_answer"
)

# Save Answer to Session State
st.session_state.multi_level_answers[CURRENT_LEVEL_KEY]["Q1_Multi"] = user_selected_keys_q1

st.markdown("---")
st.markdown("---")

# --- Question 2: Single-Select (Q2_Single) ---

q2_data = SINGLE_SELECT_QUESTION
st.markdown("## Question 2 (Max 1 Point)")
st.subheader(f"Q2: {q2_data['question']}")

# Prepare options for st.radio to display both key and statement
q2_radio_options = [f"{k}. {v}" for k, v in q2_data['options'].items()]
q2_radio_key_map = {f"{k}. {v}": k for k, v in q2_data['options'].items()}

# Get answer from session state (expected to be a string or "")
previous_answer_key_q2 = st.session_state.multi_level_answers.get(CURRENT_LEVEL_KEY, {}).get("Q2_Single", "")
default_index = None
if previous_answer_key_q2 in q2_data['options']:
    # Find the full label in the list of options to set the index
    full_label = f"{previous_answer_key_q2}. {q2_data['options'][previous_answer_key_q2]}"
    if full_label in q2_radio_options:
        default_index = q2_radio_options.index(full_label)

# Single-select Input (st.radio)
user_selected_label_q2 = st.radio(
    "Choose one correct option:",
    options=q2_radio_options,
    index=default_index, # Set default index to the previously saved answer, or None
    key=f"{CURRENT_LEVEL_KEY}_Q2_Single_radio"
)

# Map the selected label back to the single letter key (A, B, C, or D)
# NOTE: This line needs to run to define user_selected_key_q2 for the scoring logic
user_selected_key_q2 = q2_radio_key_map.get(user_selected_label_q2, "") 

# Save Answer to Session State
st.session_state.multi_level_answers[CURRENT_LEVEL_KEY]["Q2_Single"] = user_selected_key_q2

st.markdown("---")

# --- 3. SUBMIT AND REVIEW (SCORING) ---

st.header("✅ Review and Check Answer")

SCORE_SAVED_KEY = f"reviewed_{CURRENT_LEVEL_KEY}" 

# Initialize the review flag if it doesn't exist
if SCORE_SAVED_KEY not in st.session_state:
    st.session_state[SCORE_SAVED_KEY] = False

# The button handles the scoring and sets the flag to True
if st.button("Check My Selection and Save Score", key="check_multiselect"):
    
    # 1. Calculate Score for Q1 (Multi-Select, Max 4 points)
    user_set_q1 = set(user_selected_keys_q1)
    correct_set_q1 = set(q1_data['correct_answers'])
    score_q1 = len(user_set_q1.intersection(correct_set_q1))
    
    # 2. Calculate Score for Q2 (Single-Select, Max 1 point)
    score_q2 = 1 if user_selected_key_q2 == q2_data['correct_answer'] else 0
    
    # 3. Calculate Total Score
    final_score = score_q1 + score_q2
    
    # 4. Save Score to Persistent Storage
    answer_data = {
        "Q1_Multi": user_selected_keys_q1,
        "Q2_Single": user_selected_key_q2
    } 
    save_score(username, CURRENT_LEVEL_KEY, final_score, answer_data)
    
    # 5. Set the flag to display the review content
    st.session_state[SCORE_SAVED_KEY] = True 
    
    # Crucial: Force a rerun to display the saved results
    st.rerun() 

# --- Display Review Content (Conditional) ---
# This block runs only if the flag is True (i.e., after the button was pressed and rerun occurred)
if st.session_state.get(SCORE_SAVED_KEY, False):
    
    # 5. Display Feedback (Moved outside the button block)
    max_score = 5
    
    # Reload scores to get the persistence for review data
    user_scores = load_scores().get(username, {}).get(CURRENT_LEVEL_KEY, {})
    final_score = user_scores.get("score_value", 0) # Retrieve the score value
    
    st.success(f"🎉 Quiz completed! Your final score is **{final_score} out of {max_score}** and has been saved for user **{username}**.")
    
    
    st.subheader("Official Memo and Comparison")
    
    # --- Q1 Review ---
    st.markdown("### Q1 Review (Multi-Select)")
    st.markdown("#### Your Selections:")
    # Retrieve answers from the loaded score data for consistency
    saved_q1_answers = user_scores.get("answers", {}).get("Q1_Multi", [])

    if saved_q1_answers:
        selected_statements = [f"**{k}.** {q1_data['options'][k]}" for k in saved_q1_answers]
        st.info("\n\n".join(selected_statements))
    else:
        st.warning("You did not select any options for Q1.")

    st.markdown("#### Official Answer:")
    st.code(f"The correct answers are: {', '.join(q1_data['correct_answers'])}")
    st.markdown(f"> {q1_data['memo']}")

    st.markdown("---")

    # --- Q2 Review ---
    st.markdown("### Q2 Review (Single-Select)")
    st.markdown("#### Your Selection:")
    saved_q2_answer = user_scores.get("answers", {}).get("Q2_Single", "")

    if saved_q2_answer:
        st.info(f"You selected: **{saved_q2_answer}.** {q2_data['options'][saved_q2_answer]}")
    else:
        st.warning("You did not select an option for Q2.")
    
    st.markdown("#### Official Answer:")
    st.code(f"The correct answer is: {q2_data['correct_answer']}")
    st.markdown(f"> {q2_data['memo']}")
    
    # --- Image Trigger for Q2 ---
    st.markdown(f"")
    
    st.markdown("***")