import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- 1. API CONFIGURATION ---
API_KEY = "AIzaSyCxSqTPL9J6nslwN9fKHo5t7US9LzY9VcQ" # Double check your key here
try:
    if API_KEY:
        genai.configure(api_key=API_KEY)
        # Using the standard Flash model for best performance
        model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')
except Exception as e:
    st.error(f"Configuration Error: {e}")

# --- 2. INTERVIEW ENGINE ---
class DynamicInterview:
    def __init__(self, data_path):
        self.df = pd.read_csv(data_path)

    def generate_question(self, role, mastery, blacklist):
      # 1. Determine Difficulty
      diff = 1 if mastery < 0.4 else (3 if mastery > 0.7 else 2)

      # 2. Filter data for the role and difficulty
      pool = self.df[(self.df['role'] == role) & (self.df['difficulty'] == diff)]

      # If the pool is empty for that difficulty, broaden the search to just the role
      if pool.empty:
          pool = self.df[self.df['role'] == role]

      # 3. Pick a random row from the pool to ensure topic rotation
      topic_info = pool.sample(1).iloc[0]
      selected_topic = topic_info['topic']

      # 4. Get the last 3 questions for context
      avoid_str = ", ".join(blacklist[-3:])

      prompt = f"""
      You are a Senior Technical Interviewer for a {role} position.

      CURRENT TOPIC: {selected_topic}
      DIFFICULTY: {diff} out of 3

      PREVIOUS QUESTIONS (DO NOT REPEAT): [{avoid_str}]

      INSTRUCTION:
      Generate a unique, challenging question about {selected_topic}.
      If the previous questions were about the same topic, pivot to a different
      sub-domain or a specific real-world edge case of {selected_topic}.

      Return ONLY the question text.
      """

      response = model.generate_content(prompt)
      return response.text.strip(), selected_topic, diff

# --- 3. UI SETUP & SESSION STATE ---
st.set_page_config(page_title="Adaptive AI Interviewer", layout="wide",page_icon="🎯")
engine = DynamicInterview('knowledge_map.csv')

# Custom CSS for that "Impactful" look
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stProgress > div > div > div > div { background-color: #4CAF50; }
    </style>
    """, unsafe_allow_html=True)

# Initialize Session States
if 'mastery' not in st.session_state: st.session_state.mastery = 0.5
if 'history' not in st.session_state: st.session_state.history = []
if 'current_q' not in st.session_state: st.session_state.current_q = None
if 'eval_result' not in st.session_state: st.session_state.eval_result = None
if 'used_questions' not in st.session_state: st.session_state.used_questions = []

# Sidebar for Progress
with st.sidebar:
    st.title("🎯 Performance Tracker")
    role = st.selectbox("Career Track:", sorted(engine.df['role'].unique()))

    # Reset if role changes
    if "last_role" not in st.session_state or st.session_state.last_role != role:
        st.session_state.mastery = 0.5
        st.session_state.history = []
        st.session_state.current_q = None
        st.session_state.eval_result = None
        st.session_state.used_questions = []
        st.session_state.last_role = role

    # st.metric("Mastery Level", f"{st.session_state.mastery:.2f}")
    # st.progress(st.session_state.mastery)
    st.divider()

    if st.session_state.history:
        scores = [item['score'] for item in st.session_state.history]
        st.line_chart(scores)

    if st.button("End Interview & Get Final Report"):
        st.session_state.show_summary = True

    if st.button("🔄 Reset All Data", use_container_width=True, type="secondary"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- 4. MAIN KPI DASHBOARD (Highlighted Weighted Score) ---
st.title("🚀 AI Adaptive Interviewer")

# Excitement Prompts for Performance Streaks
last_3_scores = [h['score'] for h in st.session_state.history[-3:]]
if len(last_3_scores) == 3 and all(s >= 0.8 for s in last_3_scores):
    st.success("🔥 **ELITE STREAK:** Your technical depth is impressive. Moving to highly complex scenarios.")
elif len(last_3_scores) == 3 and all(s <= 0.3 for s in last_3_scores):
    st.warning("⚡ **ADAPTIVE SUPPORT:** We're detecting some friction. Re-calibrating to foundational concepts.")

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.metric("Weighted Mastery Score", f"{st.session_state.mastery * 100:.1f}%")
with col_b:
    tier = "Expert" if st.session_state.mastery > 0.7 else ("Intermediate" if st.session_state.mastery > 0.4 else "Foundational")
    st.metric("Current Assessment Tier", tier)
with col_c:
    st.metric("Questions Cleared", len(st.session_state.history))

st.divider()

# --- 5. SUMMARY VIEW ---
if st.session_state.get('show_summary'):
    st.header("🏁 Consolidated Performance Report")
    with st.spinner("Analyzing overall performance..."):
        summary_prompt = f"Role: {role}. History: {st.session_state.history}. Provide a detailed summary of Strengths, Weaknesses, and Areas of Improvement."
        summary = model.generate_content(summary_prompt).text
        st.markdown(summary)
    if st.button("Start New Session"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    # st.stop()

# --- 6. MAIN INTERVIEW LOOP (Correctly Indented ELSE) ---
else:
    if st.session_state.get('trigger_next'):
        st.session_state.current_q = None
        st.session_state.eval_result = None
        st.session_state.trigger_next = False
        st.rerun()

    if st.session_state.current_q is None:
        with st.spinner("🤖 AI is crafting your next challenge..."):
            try:
                q_text, topic, diff = engine.generate_question(role, st.session_state.mastery, st.session_state.used_questions)
                st.session_state.current_q = {"text": q_text, "topic": topic, "diff": diff}
                st.session_state.used_questions.append(q_text)
                st.rerun()
            except Exception as e:
                st.error(f"Generation failed: {e}")
                st.stop()

    # Interview Interface
    q = st.session_state.current_q
    st.info(f"**Focus Area:** {q['topic']} | **Difficulty Level:** {q['diff']}/3")
    st.subheader(q['text'])

    user_ans = st.text_area("Your Response:", height=150, key=f"ans_{hash(q['text'])}")

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Submit Answer", type='primary', use_container_width=True):
            if user_ans.strip():
                with st.spinner("🔍 Weighing response..."):
                    eval_prompt = f"""
                    Question: {q['text']}
                    Answer: {user_ans}
                    Critically evaluate this answer for a {role} position.
                    Format exactly as follows:
                    SCORE: [number 0.0-1.0] \n\n
                    STRENGTH: [text] \n\n
                    WEAKNESS: [text] \n\n
                    IMPROVEMENT: [text]
                    """
                    try:
                        res = model.generate_content(eval_prompt).text
                        score = 0.5
                        for line in res.split('\n'):
                            if "SCORE:" in line.upper():
                                try:
                                    raw_score = line.split(':')[-1].strip().split('/')[0].replace(' ', '')
                                    score = float(''.join(c for c in raw_score if c.isdigit() or c=='.'))
                                except:
                                    score = 0.5

                        st.session_state.mastery = max(0.1, min(1.0, st.session_state.mastery + (score - 0.5) * 0.15))
                        st.session_state.history.append({"topic": q['topic'], "score": score})
                        st.session_state.eval_result = res
                        st.rerun()
                    except Exception as e:
                        st.error(f"Evaluation Error: {e}")

    # Results Display
    if st.session_state.eval_result:
        st.markdown("### 📊 AI Evaluation")
        st.info(st.session_state.eval_result)
        with col2:
            if st.button("Next Question ➡️", use_container_width=True):
                st.session_state.trigger_next = True
                st.rerun()
