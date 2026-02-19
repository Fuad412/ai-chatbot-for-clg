from flask import Flask, render_template, jsonify, request
import json
import difflib
import os

app = Flask(__name__)

# Load Data
DATA_FILE = 'majlis_data.json'
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
        # 1. Check direct substring (fast)
        for k in keywords:
            if k in text: return True
        # 2. Check for typos (slow but smart)
        text_words = text.split()
        all_matches = []
        for word in text_words:
            # cutoff=0.7 means 70% similarity allowed (e.g. syllubus -> syllabus)
            matches = difflib.get_close_matches(word, keywords, n=1, cutoff=0.7)
            if matches: return True
        return False

    # 1. Greetings
    if contains_intent(user_message, ['hi', 'hello', 'hey', 'start', 'greetings']):
        response["text"] = "Hello! I am the Majlis AI Assistant. How can I help you today?"
        response["options"] = ["Syllabus", "Fee Payment", "Admissions", "Facilities", "About"]
        return jsonify(response)

    # 2. Intent: Fees / Linways
    if contains_intent(user_message, ['fee', 'fees', 'payment', 'pay', 'linways', 'bill']):
        response["text"] = "You can pay your fees through the Linways portal. <br><br><b>Login Instructions:</b><br>1. Username: Admission Number<br>2. Password: Admission Number<br>3. Go to 'Online Payments'"
        response["options"] = [{"label": "Open Linways", "action": "link", "url": "https://majlispolytechnic.linways.com/"}]
        return jsonify(response)

    # 3. Intent: Syllabus (Priority)
    if contains_intent(user_message, ['syllabus', 'curriculum', 'portion', 'subjects', 'academic']):
        response["text"] = "Please select your department:"
        btns = []
        for code, info in majlis_data['curriculum'].items():
            btns.append({"label": info['name'], "action": "post", "value": f"dept:{code}"})
        response["options"] = btns
        return jsonify(response)
    
    # 3.5 Intelligent Dept Detection (e.g. "Civil syllabus", "computer semester 4")
    for code, info in majlis_data['curriculum'].items():
        dept_keywords = info['name'].lower().split() + [code.lower()]
        
        # Check if the message mentions this department
        if contains_intent(user_message, dept_keywords):
             
             # IMPROVED: Check for ANY digit 1-6 in the message representing the semester
             # This handles "sem 4", "semester 4", "4th", "s4" and typos like "semster 4"
             import re
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
                 table_html = "<table class='chat-table'><tr><th>Code</th><th>Subject</th><th>Credits</th></tr>"
                 for sub in subjects:
                    table_html += f"<tr><td>{sub['code']}</td><td>{sub['name']}</td><td>{sub['credits']}</td></tr>"
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
            
            table_html = "<table class='chat-table'><tr><th>Code</th><th>Subject</th><th>Credits</th></tr>"
            for sub in subjects:
                table_html += f"<tr><td>{sub['code']}</td><td>{sub['name']}</td><td>{sub['credits']}</td></tr>"
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

    return jsonify(response)

if __name__ == '__main__':
    # Run slightly verbose for debugging, accessible on network
    app.run(debug=True, host='0.0.0.0', port=5000)
