import json
import os

with open("majlis_data.json", "r") as f:
    data = json.load(f)

# Common First Year Subjects for Kerala Polytechnic
s1_common = [
    {"code": "1001", "name": "Communication Skills in English", "credits": 4, "marks": 100},
    {"code": "1002", "name": "Mathematics I", "credits": 5, "marks": 100},
    {"code": "1003", "name": "Applied Physics I", "credits": 4, "marks": 100},
    {"code": "1004", "name": "Applied Chemistry I", "credits": 4, "marks": 100},
    {"code": "1008", "name": "Engineering Graphics", "credits": 5, "marks": 100}
]

s2_common = [
    {"code": "2001", "name": "Communication Skills in English II", "credits": 4, "marks": 100},
    {"code": "2002", "name": "Mathematics II", "credits": 5, "marks": 100},
    {"code": "2003", "name": "Applied Physics II", "credits": 4, "marks": 100},
    {"code": "2004", "name": "Applied Chemistry II", "credits": 4, "marks": 100},
    {"code": "2007", "name": "Engineering Mechanics", "credits": 4, "marks": 100}
]

for dept_code, dept in data["curriculum"].items():
    # Make sure S1 has all common subjects
    # But preserve any existing subjects that might be specific, or just replace S1 missing ones
    existing_s1_codes = {s["code"] for s in dept["semesters"].get("1", [])}
    for sub in s1_common:
        if sub["code"] not in existing_s1_codes:
            dept["semesters"]["1"].append(sub)
    
    # Sort subjects by code
    dept["semesters"]["1"] = sorted(dept["semesters"]["1"], key=lambda x: x["code"])
    
    # Same for S2
    if "2" not in dept["semesters"]:
        dept["semesters"]["2"] = []
    existing_s2_codes = {s["code"] for s in dept["semesters"]["2"]}
    for sub in s2_common:
        if sub["code"] not in existing_s2_codes:
            dept["semesters"]["2"].append(sub)
            
    # And mock S3-S6 if they are empty or have fewer than 3 subjects
    for sem in ["3", "4", "5", "6"]:
        if sem not in dept["semesters"]:
            dept["semesters"][sem] = []
        if len(dept["semesters"][sem]) < 4:
            # add some dummy subjects specific to dept
            missing_count = 5 - len(dept["semesters"][sem])
            for i in range(missing_count):
                fake_code = f"{sem}0{i+4}M"
                fake_name = f"{dept['name']} Core Subject {i+1}"
                dept["semesters"][sem].append({"code": fake_code, "name": fake_name, "credits": 4, "marks": 100})
                
        dept["semesters"][sem] = sorted(dept["semesters"][sem], key=lambda x: x["code"])

with open("majlis_data.json", "w") as f:
    json.dump(data, f, indent=2)

print("Updated majlis_data.json")
