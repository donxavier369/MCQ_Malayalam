import streamlit as st
import json # For parsing JSON strings if needed
import google.generativeai as genai
import os
# from dotenv import load_dotenv # Add this if you are using a .env file

# Load environment variables from .env file (if it exists)
# load_dotenv()

# --- DummyRequest and MCQGenerationView (from your backend logic, adjusted for direct use) ---
# This part simulates your DRF view for direct integration into Streamlit.
# In a real deployed app, you'd make an HTTP request to your DRF backend.

# genai.configure(api_key=os.environ.getenv("GEMINI_API_KEY"))

genai.configure(api_key="AIzaSyC8xdTVFonqv36WolweYZOy9JvvEVg1Jzo")


class DummyRequest:
    def __init__(self, data):
        self.data = data

class DummyResponse:
    def __init__(self, data, status):
        self.data = data
        self.status = status

def mcq_generation_view(request):
    input_text = request.data.get("text_content")

    if not input_text:
        return DummyResponse({"error": "No text content provided to generate MCQs."}, status=400)

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = f"""
        Given the following text, generate 10 Multiple Choice Questions (MCQs) in Malayalam.
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

        Now, generate the 10 MCQs from the following text:

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
            # Ensure the response.text is a valid JSON string before loading
            # Sometimes the model might include markdown backticks (```json ... ```)
            # We can strip them if necessary.
            json_string = response.text.strip()
            if json_string.startswith("```json") and json_string.endswith("```"):
                json_string = json_string[7:-3].strip()

            mcqs_data = json.loads(json_string)

        except json.JSONDecodeError:
            print(f"Failed to parse JSON: {response.text}") # Debugging
            return DummyResponse(
                {"error": "Failed to parse JSON response from AI. Raw response: " + response.text},
                status=500
            )

        # Basic validation to ensure the output is a list of dictionaries as expected
        if not isinstance(mcqs_data, list) or not all(isinstance(item, dict) for item in mcqs_data):
            print(f"Unexpected JSON structure: {mcqs_data}")
            return DummyResponse(
                {"error": "AI returned unexpected JSON structure. Please try again."},
                status=500
            )


        return DummyResponse(mcqs_data, status=200)

    except Exception as e:
        print(f"Error in mcq_generation_view: {e}") # Debugging
        return DummyResponse({"error": f"An error occurred: {str(e)}"}, status=500)

# --- Streamlit App ---

st.set_page_config(page_title="Malayalam MCQ Generator", layout="wide")

st.title("📚 Malayalam MCQ Generator using Gemini API")
st.markdown("Enter a Malayalam passage below to generate 10 multiple choice questions.")

# Text input
text_content = st.text_area("Enter Malayalam Text", height=300, key="input_text_area")

# Initialize session state variables if they don't exist
if 'mcqs' not in st.session_state:
    st.session_state.mcqs = []
if 'selected_options' not in st.session_state:
    st.session_state.selected_options = {} # To store user's selected answer for each question

# Function to clear MCQs and selections when new text is entered or generated
def clear_mcqs():
    st.session_state.mcqs = []
    st.session_state.selected_options = {}

# Submit button
if st.button("Generate MCQs", on_click=clear_mcqs): # Clear existing MCQs on new generation
    if not text_content.strip():
        st.warning("Please enter some text to generate MCQs.")
    else:
        with st.spinner("Generating questions..."):
            try:
                # Create DummyRequest object with the text input
                request = DummyRequest(data={"text_content": text_content})

                # Call the local Python function (simulating your API call)
                response = mcq_generation_view(request)

                if response.status == 200:
                    st.session_state.mcqs = response.data
                    st.success("MCQs generated successfully!")
                else:
                    st.error("❌ Failed to generate questions.")
                    st.code(response.data)
            except Exception as e:
                st.exception(f"Error during MCQ generation: {str(e)}")

# Display generated MCQs if available in session state
if st.session_state.mcqs:
    st.markdown("---")
    st.header("Generated Questions")

    for idx, q in enumerate(st.session_state.mcqs, start=1):
        st.markdown(f"### ❓ Question {idx}: {q['question_text']}")

        # Prepare options for st.radio
        # options_list will now look like ["A. Option Text 1", "B. Option Text 2", ...]
        options_list = [f"{opt['label']}. {opt['text']}" for opt in q["options"]]
        option_values = [opt['label'] for opt in q["options"]] # Values to store in session state (A, B, C, D)

        # Create unique key for each radio button group
        radio_key = f"q_{idx}_radio"

        # Check if an option was previously selected for this question
        # We store the *label* (A,B,C,D) in session state, but we need its index for `st.radio`
        current_selection_label = st.session_state.selected_options.get(radio_key, None)
        current_selection_index = None
        if current_selection_label in option_values:
            current_selection_index = option_values.index(current_selection_label)

        # Radio button for answer selection
        selected_full_option_text = st.radio(
            "Select your answer:",
            options=options_list,
            index=current_selection_index, # Set initial selection
            key=radio_key,
            # REMOVED format_func=lambda x: x.split(". ")[0],
            # Callback function when a radio button is clicked
            on_change=lambda key=radio_key: st.session_state.selected_options.update({key: st.session_state[key].split(". ")[0]})
        )

        # Ensure the selected label is stored correctly in session_state immediately after selection
        if selected_full_option_text:
            st.session_state.selected_options[radio_key] = selected_full_option_text.split(". ")[0]


        # Hint - hidden by default
        with st.expander(f"💡 Show Hint for Question {idx}"):
            st.info(f"**Hint:** {q['hint']}")

        # Rationale - hidden by default, shown only if an answer is selected
        selected_answer_for_current_q_label = st.session_state.selected_options.get(radio_key)

        if selected_answer_for_current_q_label: # If an answer has been selected
            # Display correct answer and rationale after selection
            is_correct = selected_answer_for_current_q_label == q['correct_answer_label']
            if is_correct:
                st.success(f"✅ **Correct!** Your answer: {selected_answer_for_current_q_label}")
            else:
                st.error(f"❌ **Incorrect!** Your answer: {selected_answer_for_current_q_label}")
            st.success(f"**Correct Answer:** {q['correct_answer_label']}") # Always show correct answer
            st.markdown(f"🧠 **Rationale:** {q['rationale']}")

        st.markdown("---")