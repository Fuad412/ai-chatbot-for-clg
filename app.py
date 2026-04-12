from flask import Flask, render_template, jsonify, request
import json
import difflib
import os
import re

# Try to import Gemini AI for the conversational fallback
try:
    from google import genai
    from google.genai import types
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

app = Flask(__name__)

# Load Data
basedir = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(basedir, 'majlis_data.json')
majlis_data = {}

def load_data():
    global majlis_data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            majlis_data = json.load(f)
    else:
        print("Error: majlis_data.json not found!")

load_data()

@app.route('/')
def index():
    """Renders the main page."""
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    """Returns the full data structure."""
    return jsonify(majlis_data)

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Chatbot Logic.
    Receives user message, processes intent, and returns a response.
    """
    # Reload data ensures edits to majlis_data.json appear instantly without restarting
    load_data() 
    
    data = request.json
    user_message = data.get('message', '').lower().strip()
    
    response = {
        "text": "I'm not sure I understand. You can ask me about Syllabus, Fees, Admissions, or Facilities.",
        "options": []
    }

    # Helper: Fuzzy Keyword Matcher
    def contains_intent(text, keywords):
        import re
        # 1. Check exact word match (using word boundary so 'hi' doesn't match 'this')
        for k in keywords:
            if re.search(r'\b' + re.escape(k) + r'\b', text):
                return True
        # 2. Check for typos (slow but smart)
        text_words = text.split()
        for word in text_words:
            # cutoff=0.8 means 80% similarity allowed to avoid false positives on short words
            matches = difflib.get_close_matches(word, keywords, n=1, cutoff=0.8)
            if matches: return True
        return False

    # 1. Greetings
    if contains_intent(user_message, ['hi', 'hello', 'hey', 'start', 'greetings']):
        response["text"] = "Hello! I am the Majlis AI Assistant. How can I help you today?"
        response["options"] = ["Syllabus", "Fee Payment", "Admissions", "Facilities", "About"]
        return jsonify(response)

    # 2. Intent: Fees / Linways
    if contains_intent(user_message, ['fee', 'fees', 'payment', 'pay', 'linways', 'bill']):
        response["text"] = "<b>Are you a new student?</b><br>If you are a new joinee, please contact the management for fee details at <b>+91 8281899825</b>.<br><br><b>Already studying here?</b><br>If you are already a student, you can pay your fees through the Linways portal. <br>Login Instructions: Username & Password is your Admission Number."
        response["options"] = [{"label": "Open Linways", "action": "link", "url": "https://majlispolytechnic.linways.com/"}]
        return jsonify(response)

    # 2.5 Intelligent Dept Detection (e.g. "Civil syllabus", "computer semester 4")
    # This must run BEFORE the generic Syllabus intent so specific queries bypass the generic menu.
    for code, info in majlis_data['curriculum'].items():
        # Distinctive names: filter out generic words like 'engineering', '&', 'and'
        names = [w.lower() for w in info['name'].split() if w.lower() not in ['engineering', '&', 'and']]
        
        # Check if code is mentioned. BUT 'me' is an english pronoun ("tell me a joke").
        # Fix: Only accept short codes if they are alone, or paired with academic words.
        context_regex = r'\b(sem|semester|s[1-6]|syllabus|subject|portion)\b'
        has_context = bool(re.search(context_regex, user_message))
        is_exact_code = bool(re.search(r'\b' + code.lower() + r'\b', user_message))
        
        valid_code_match = is_exact_code and (len(user_message.split()) <= 2 or has_context)
        
        # Check if the message mentions this department distinctly
        if contains_intent(user_message, names) or valid_code_match:
             
             # Check for ANY digit 1-6 in the message representing the semester
             # This handles "sem 4", "semester 4", "4th", "s4" and typos like "semster 4"
             found_sem = None
             
             # Regex looks for a digit 1-6 that is either standalone or preceded by 's' (s4)
             sem_match = re.search(r'\b[1-6]\b|s[1-6]\b', user_message)
             
             if sem_match:
                 # Extract the digit
                 digit = re.search(r'[1-6]', sem_match.group(0)).group(0)
                 if digit in info['semesters']:
                     found_sem = digit
                     
             if found_sem:
                 # DIRECT SUCCESS: Show the table immediately!
                 subjects = info['semesters'][found_sem]
                 table_html = "<table class='chat-table'><tr><th>#</th><th>Code</th><th>Subject</th><th>Credits</th></tr>"
                 for i, sub in enumerate(subjects):
                    table_html += f"<tr><td>{i+1}</td><td>{sub['code']}</td><td>{sub['name']}</td><td>{sub['credits']}</td></tr>"
                 table_html += "</table>"
        
                 response["text"] = f"Here is the syllabus for <b>{info['name']} - Semester {found_sem}</b>:<br>{table_html}"
                 response["options"] = [{"label": "Check Another Dept", "action": "post", "value": "syllabus"}]
                 return jsonify(response)
                 
             # If Dept found but No Semester found
             response["text"] = f"I see you're asking about <b>{info['name']}</b>. Which semester?"
             btns = []
             for sem in sorted(info['semesters'].keys()):
                 btns.append({"label": f"Semester {sem}", "action": "post", "value": f"sem:{code}:{sem}"})
             
             response["options"] = btns
             return jsonify(response)

    # 3. Intent: Syllabus (Priority) - Generic
    if contains_intent(user_message, ['syllabus', 'curriculum', 'portion', 'subjects', 'academic']):
        response["text"] = "Please select your department:"
        btns = []
        for code, info in majlis_data['curriculum'].items():
            btns.append({"label": info['name'], "action": "post", "value": f"dept:{code}"})
        response["options"] = btns
        return jsonify(response)

    # 4. Intent: Facilities
    if contains_intent(user_message, ['hostel', 'accomodation', 'room', 'stay']):
        hostel = majlis_data['facilities']['hostel']
        response["text"] = f"<b>Hostel Info:</b><br>{hostel['description']} ({hostel['type']})"
        return jsonify(response)
    
    if contains_intent(user_message, ['bus', 'transport', 'route', 'vehicle']):
        routes = ", ".join(majlis_data['facilities']['bus_routes'])
        response["text"] = f"<b>Bus Routes Available:</b><br>{routes}"
        return jsonify(response)

    # 5. Intent: Admissions
    if contains_intent(user_message, ['admission', 'admissions', 'join', 'seat', 'quota']):
        adm = majlis_data['admissions']
        docs = "</li><li>".join(adm['documents_required'])
        response["text"] = f"<b>Admissions {majlis_data['college_info']['contact']['phone']}</b><br>{adm['process']}<br><br><b>Documents:</b><ul><li>{docs}</li></ul>"
        return jsonify(response)

    # Handle Dept Selection (Hidden intent strings)
    if user_message.startswith("dept:"):
        dept_code = user_message.split(":")[1].upper()
        dept = majlis_data['curriculum'].get(dept_code)
        if dept:
            response["text"] = f"You selected <b>{dept['name']}</b>. Which semester?"
            btns = []
            for sem in sorted(dept['semesters'].keys()):
                btns.append({"label": f"Semester {sem}", "action": "post", "value": f"sem:{dept_code}:{sem}"})
            response["options"] = btns
        return jsonify(response)

    # Handle Sem Selection
    if user_message.startswith("sem:"):
        parts = user_message.split(":")
        dept_code = parts[1].upper()
        sem = parts[2]
        # Safety check
        if dept_code in majlis_data['curriculum'] and sem in majlis_data['curriculum'][dept_code]['semesters']:
            subjects = majlis_data['curriculum'][dept_code]['semesters'][sem]
            
            table_html = "<table class='chat-table'><tr><th>#</th><th>Code</th><th>Subject</th><th>Credits</th></tr>"
            for i, sub in enumerate(subjects):
                table_html += f"<tr><td>{i+1}</td><td>{sub['code']}</td><td>{sub['name']}</td><td>{sub['credits']}</td></tr>"
            table_html += "</table>"
            
            response["text"] = f"Here is the syllabus for <b>{dept_code} - Semester {sem}</b>:<br>{table_html}"
            response["options"] = [{"label": "Check Another Dept", "action": "post", "value": "syllabus"}]
        else:
             response["text"] = "Sorry, I couldn't find data for that semester."
             
        return jsonify(response)

    # 6. Intent: Subject Search (Fuzzy Match - Fallback)
    # Re-using the same logic but formatting differently
    all_subjects = []
    for dept in majlis_data['curriculum'].values():
        for subjects in dept['semesters'].values():
            for sub in subjects:
                all_subjects.append(sub['name'])
    
    # Lower cutoff slightly to catch more typos in long subject names
    matches = difflib.get_close_matches(user_message, all_subjects, n=1, cutoff=0.5)
    
    if matches:
        match_name = matches[0]
        # Find details
        for dept_code, dept_data in majlis_data['curriculum'].items():
            for sem, subjects in dept_data['semesters'].items():
                for subject in subjects:
                    if subject['name'] == match_name:
                        response["text"] = f"Found it!<br><b>{subject['name']}</b><br>Code: {subject['code']}<br>Dept: {dept_code}, Sem: {sem}<br>Credits: {subject['credits']}"
                        return jsonify(response)

    # 7. Integrated Generative AI Fallback
    # If the user's message didn't match any hardcoded intents, ask the AI!
    if HAS_GEMINI:
        # Uses environment variable if found, otherwise uses your provided key
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            try:
                client = genai.Client(api_key=api_key)
                
                # We give the AI a "System Prompt" context so it knows who it is, along with real college facts
                contact_info = majlis_data.get('college_info', {}).get('contact', {})
                real_phone = contact_info.get('phone', '+91 8281899825')
                real_email = contact_info.get('email', 'info@majliscomplex.org')
                
                sys_instruct = f"You are a helpful, friendly AI assistant for Majlis Polytechnic College. The official college phone number is {real_phone} and email is {real_email}. Use this factual data. ONLY answer queries related to the college, project, admissions, syllabus, or academics. If the user asks 'who are you' or about your identity, proudly introduce yourself as the 'Majlis Helpdesk Chatbot'. If the user asks a social or general query (e.g., 'how are you', 'tell me a joke', 'how is the weather'), politely decline and state that you can only answer college-related questions. Keep the response short (1-3 sentences max). Use <br> for new lines instead of markdown."
                
                response_text = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=user_message,
                    config=types.GenerateContentConfig(
                        system_instruction=sys_instruct,
                        temperature=0.7,
                    ),
                )
                
                if response_text.text:
                    response["text"] = response_text.text
                    return jsonify(response)
            except Exception as e:
                print(f"Gemini AI Error: {e}")
                response["text"] = f"An error occurred with the AI service: {e}. Please check your API key."
                return jsonify(response)
        else:
            response["text"] = "Gemini API key is not configured."
            return jsonify(response)
    else:
        response["text"] = "Gemini AI module is not installed (`google-genai`), so AI fallback is disabled."
        return jsonify(response)

    # Final Default Fallback
    return jsonify(response)

if __name__ == '__main__':
    # Run slightly verbose for debugging, accessible on network
    app.run(debug=True, host='0.0.0.0', port=5000)
