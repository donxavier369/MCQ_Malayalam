import streamlit as st
import json
import google.generativeai as genai
import os
import time  # Added for time tracking

gemini_api_key = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=gemini_api_key)

class DummyRequest:
    def __init__(self, data):
        self.data = data

class DummyResponse:
    def __init__(self, data, status):
        self.data = data
        self.status = status

def mcq_generation_view(request):
    input_text = request.data.get("text_content")
    num_questions = request.data.get("num_questions", 10)
    print(f"num_questions {num_questions}")

    if not input_text:
        return DummyResponse({"error": "No text content provided to generate MCQs."}, status=400)

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = f"""
        Given the following text, generate {num_questions} Multiple Choice Questions (MCQs) in Malayalam.
        Each question should have 4 answer options (A, B, C, D) with only one correct answer.
        For each question, also provide a hint in Malayalam that helps to guess the answer but does not directly reveal it.
        Additionally, provide a rationale for the correct answer, explaining why it is correct, in Malayalam.

        Provide the output in a strict JSON format. The structure should be an array of question objects,
        where each object has:
        - "question_text": The question itself.
        - "options": An array of objects, each with "label" (A, B, C, D) and "text" (the option text).
        - "correct_answer_label": The label of the correct option (e.g., "A", "B").
        - "hint": A hint for the question.
        - "rationale": An explanation for the correct answer.

        Example of expected JSON structure for one question:
        {{
            "question_text": "ഒരു ഉദാഹരണ ചോദ്യം?",
            "options": [
                {{"label": "A", "text": "ഓപ്ഷൻ എ"}},
                {{"label": "B", "text": "ഓപ്ഷൻ ബി"}},
                {{"label": "C", "text": "ഓപ്ഷൻ സി"}},
                {{"label": "D", "text": "ഓപ്ഷൻ ഡി"}}
            ],
            "correct_answer_label": "C",
            "hint": "ഈ ചോദ്യത്തിനുള്ള സൂചന.",
            "rationale": "ശരിയായ ഉത്തരത്തിന്റെ വിശദീകരണം."
        }}

        Now, generate {num_questions} MCQs from the following text:

        ---
        {input_text}
        ---
        """

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )

        try:
            json_string = response.text.strip()
            if json_string.startswith("json") and json_string.endswith(""):
                json_string = json_string[7:-3].strip()

            mcqs_data = json.loads(json_string)

        except json.JSONDecodeError:
            print(f"Failed to parse JSON: {response.text}")
            return DummyResponse(
                {"error": "Failed to parse JSON response from AI. Raw response: " + response.text},
                status=500
            )

        if not isinstance(mcqs_data, list) or not all(isinstance(item, dict) for item in mcqs_data):
            print(f"Unexpected JSON structure: {mcqs_data}")
            return DummyResponse(
                {"error": "AI returned unexpected JSON structure. Please try again."},
                status=500
            )

        return DummyResponse(mcqs_data, status=200)

    except Exception as e:
        print(f"Error in mcq_generation_view: {e}")
        return DummyResponse({"error": f"An error occurred: {str(e)}"}, status=500)

# --- Streamlit App ----------------------------------------------------

st.set_page_config(page_title="Malayalam MCQ Generator", layout="wide")

st.title("📚 Malayalam MCQ Generator")
st.markdown("Enter a Malayalam passage below to generate multiple choice questions.")

# Text input
text_content = st.text_area("Enter Malayalam Text", height=300, key="input_text_area")

# Dropdown to select number of questions
st.markdown("#### 📌 Select how many MCQs you want to generate:")
num_questions = st.selectbox(
    "Number of Questions",
    options=list(range(1, 101)),
    index=9,
    key="mcq_count"
)

# Initialize session state variables
if 'mcqs' not in st.session_state:
    st.session_state.mcqs = []
if 'selected_options' not in st.session_state:
    st.session_state.selected_options = {}
if 'generation_time' not in st.session_state:  # Added for storing generation time
    st.session_state.generation_time = None

# Function to clear MCQs and selections
def clear_mcqs():
    st.session_state.mcqs = []
    st.session_state.selected_options = {}
    st.session_state.generation_time = None  # Clear generation time

# Submit button
if st.button("Generate MCQs", on_click=clear_mcqs):
    if not text_content.strip():
        st.warning("Please enter some text to generate MCQs.")
    else:
        with st.spinner("Generating questions..."):
            try:
                # Measure start time
                start_time = time.time()

                # Create DummyRequest object
                request = DummyRequest(data={
                    "text_content": text_content,
                    "num_questions": num_questions
                })

                response = mcq_generation_view(request)

                # Measure end time and calculate duration
                end_time = time.time()
                elapsed_time = round(end_time - start_time, 2)  # Round to 2 decimal places
                st.session_state.generation_time = elapsed_time

                if response.status == 200:
                    st.session_state.mcqs = response.data
                    st.success(f"MCQs generated successfully! Time taken: {elapsed_time} seconds")
                else:
                    st.error("❌ Failed to generate questions.")
                    st.code(response.data)
            except Exception as e:
                st.error(f"Error during MCQ generation: {str(e)}")

# # Display generation time if available
# if st.session_state.generation_time is not None:
#     st.info(f"⏱️ Time taken to generate MCQs: {st.session_state.generation_time} seconds")

# Display generated MCQs
if st.session_state.mcqs:
    st.markdown("---")
    st.header("Generated Questions")

    for idx, q in enumerate(st.session_state.mcqs, start=1):
        st.markdown(f"### ❓ Question {idx}: {q['question_text']}")

        options_list = [f"{opt['label']}. {opt['text']}" for opt in q["options"]]
        option_values = [opt['label'] for opt in q["options"]]

        radio_key = f"q_{idx}_radio"
        current_selection_label = st.session_state.selected_options.get(radio_key, None)
        current_selection_index = None
        if current_selection_label in option_values:
            current_selection_index = option_values.index(current_selection_label)

        selected_full_option_text = st.radio(
            "Select your answer:",
            options=options_list,  # Corrected from options-ai to options_list
            index=current_selection_index,
            key=radio_key,
            on_change=lambda key=radio_key: st.session_state.selected_options.update({key: st.session_state[key].split(". ")[0]})
        )

        if selected_full_option_text:
            st.session_state.selected_options[radio_key] = selected_full_option_text.split(". ")[0]

        with st.expander(f"💡 Show Hint for Question {idx}"):
            st.info(f"**Hint:** {q['hint']}")

        selected_answer_for_current_q_label = st.session_state.selected_options.get(radio_key)
        if selected_answer_for_current_q_label:
            is_correct = selected_answer_for_current_q_label == q['correct_answer_label']
            if is_correct:
                st.success(f"✅ **Correct!** Your answer: {selected_answer_for_current_q_label}")
            else:
                st.error(f"❌ **Incorrect!** Your answer: {selected_answer_for_current_q_label}")
            st.success(f"**Correct Answer:** {q['correct_answer_label']}")
            st.markdown(f"🧠 **Rationale:** {q['rationale']}")

        st.markdown("---")

    # Score Summary
    total_questions = len(st.session_state.mcqs)
    answered_questions = len(st.session_state.selected_options)

    if answered_questions == total_questions:
        correct_count = 0
        for idx, q in enumerate(st.session_state.mcqs, start=1):
            key = f"q_{idx}_radio"
            selected_label = st.session_state.selected_options.get(key)
            if selected_label == q["correct_answer_label"]:
                correct_count += 1

        percentage = round((correct_count / total_questions) * 100, 2)

        st.markdown("## 🏁 Result Summary")
        st.success(f"✅ You got **{correct_count} / {total_questions}** correct!")
        st.info(f"📊 Your score is **{percentage}%**")