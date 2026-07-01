import os
import uuid
import json
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from langchain_community.document_loaders import PyPDFLoader
from groq import Groq

load_dotenv()
app=Flask(__name__)
CORS(app)

os.makedirs("./uploads",exist_ok=True)

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# In-memory session store
# { session_id: { role, resume_text, questions, answers, evaluations, current_q, done } }
sessions = {}

ROLES = {
    "aiml":      "AI/ML Engineer",
    "webdev":    "Full Stack Web Developer",
    "fullstack": "Full Stack Developer",
    "backend":   "Backend Developer",
    "data":      "Data Scientist"
}


def parse_resume(pdf_path):
    pages=PyPDFLoader(pdf_path).load()
    text="\n".join(p.page_content for p in pages)
    return "\n".join(l.strip() for l in text.splitlines() if l.strip())
 
def generate_questions(resume_text,role,n=5):
    prompt = f"""You are a technical interviewer hiring for a {role} position.
Based on this resume, generate exactly {n} interview questions.
Rules:
- Be specific to their actual projects and skills
- Mix technical and project-based questions
- Number each question like: 1. question here
- No extra text, just the questions

Resume:
{resume_text}

Generate {n} questions:"""
    response=groq_client.chat.completions.create(
        model      = "llama-3.3-70b-versatile",
        messages   = [{"role": "user", "content": prompt}],
        max_tokens = 400,
        temperature= 0.7
    )
    raw = response.choices[0].message.content.strip()
    questions=[]
    for line in raw.splitlines():
        line=line.strip()
        if line and line[0].isdigit():
            q=line.split(".",1)[-1].strip()
            if q:
                questions.append(q)
    return questions[:n]

def evaluate_answer(question,answer,role,resume_text):
    if not answer or len(answer.strip())<5:
        return {"score": 0, "good": "No answer provided.",
                "missing": "Please provide a complete answer.",
                "tip": "Even a partial answer is better than nothing."}
    prompt = f"""You are a {role} interviewer evaluating this answer.

Question: {question}
Answer: {answer}
Resume context: {resume_text[:300]}

Respond in EXACT format:
SCORE: [1-10]
GOOD: [one sentence what was good]
MISSING: [one sentence what was missing]
TIP: [one sentence specific advice]"""
    response=groq_client.chat.completions.create(
        model      = "llama-3.3-70b-versatile",
        messages   = [{"role": "user", "content": prompt}],
        max_tokens = 150,
        temperature= 0.3
    )
    raw=response.choices[0].message.content.strip()
    result = {"score":5 , "good":"" , "missing":"", "tip":"" }
    for line in raw.splitlines():
        if line.startswith("SCORE:"):
            try:
                result["score"] = int(line.split(":", 1)[1].strip().split()[0])
            except:
                result["score"] = 5
        elif line.startswith("GOOD:"):
            result["good"] = line.split(":", 1)[1].strip()
        elif line.startswith("MISSING:"):
            result["missing"] = line.split(":", 1)[1].strip()
        elif line.startswith("TIP:"):
            result["tip"] = line.split(":", 1)[1].strip()
    result["score"] = max(1, min(10, result["score"]))
    return result

def generate_summary(questions,answers,evaluations,role):
    scores     = [e["score"] for e in evaluations]
    total      = sum(scores)
    max_score  = len(questions) * 10
    percentage = round((total / max_score) * 100)
    grade="Excellent" if percentage >= 80 else \
                 "Good"      if percentage >= 60 else \
                 "Average"   if percentage >= 40 else "Needs Improvement"
    qa = "\n".join(
        f"Q{i+1}: {q}\nA: {a[:80]}\nScore: {e['score']}/10"
        for i, (q, a, e) in enumerate(zip(questions, answers, evaluations))
    )
    prompt = f"""Interview summary for {role} candidate:
{qa}

Respond in EXACT format:
FEEDBACK: [2 sentences overall assessment]
STRENGTHS: [one key strength]
IMPROVE: [one most important thing to work on]"""

    response = groq_client.chat.completions.create(
        model      = "llama-3.3-70b-versatile",
        messages   = [{"role": "user", "content": prompt}],
        max_tokens = 150,
        temperature= 0.3
    )
    raw       = response.choices[0].message.content.strip()
    feedback  = strengths = improve = ""
    for line in raw.splitlines():
        if line.startswith("FEEDBACK:"):
            feedback  = line.split(":", 1)[1].strip()
        elif line.startswith("STRENGTHS:"):
            strengths = line.split(":", 1)[1].strip()
        elif line.startswith("IMPROVE:"):
            improve   = line.split(":", 1)[1].strip()

    return {
        "total_score": total,
        "max_score":   max_score,
        "percentage":  percentage,
        "grade":       grade,
        "scores":      scores,
        "feedback":    feedback,
        "strengths":   strengths,
        "improve":     improve
    }

@app.route("/start",methods=["POST"])
def start():
    # Get role from form data
    role_key=request.form.get("role","aiml")
    role = ROLES.get(role_key,"AI/ML Engineer")

    # Get resume file
    file=request.files.get("file")
    if not file :
        return jsonify({"error":"Resume PDF required"}),400
    # Save + parse resume
    filename = f"{str(uuid.uuid4())[:8]}_{secure_filename(file.filename)}"
    filepath=f"./uploads/{filename}"
    file.save(filepath)
    resume_text=parse_resume(filepath)
    # Generate questions
    questions = generate_questions(resume_text,role)
    # Create session
    session_id=str(uuid.uuid4())[:8]
    sessions[session_id]={
        "role": role,
        "resume_text":resume_text,
        "questions":   questions,
        "answers":     [],
        "evaluations": [],
        "current_q":   0,
        "done":        False
    }
    return jsonify({
        "session_id":      session_id,
        "role":            role,
        "total_questions": len(questions),
        "question_number": 1,
        "question":        questions[0]
    }), 201

# ROUTE 2: POST /answer
# Submit answer → get evaluation + next question

@app.route("/answer",methods=["POST"])
def answer():
    data=request.get_json()
    session_id=data.get("session_id")
    answer=data.get("answer","").strip()

    if session_id not in sessions:
        return jsonify({"error":"Session not found"}),404
    
    session=sessions[session_id]

    if session["done"]:
        return jsonify({"error": "Interview already complete"}), 400
    
    current_idx=session["current_q"]
    question =session["questions"][current_idx]

    #Evaluate answer
    evaluation = evaluate_answer(
        question,
        answer,
        session["role"],
        session["resulte_text"]
    )

    # Store answer + evaluation
    session["answers"].append(answer)
    session["evaluations"].append(evaluation)
    session["current_q"] += 1

    # Check if interview is done
    if session["current_q"] >= len(session["questions"]):
        session["done"] = True
        return jsonify({
            "evaluation":      evaluation,
            "question_number": current_idx + 1,
            "done":            True,
            "message":         "Interview complete! Call /summary for results."
        })

    # Return evaluation + next question
    next_q = session["questions"][session["current_q"]]
    return jsonify({
        "evaluation":      evaluation,
        "question_number": current_idx + 1,
        "done":            False,
        "next_question":   {
            "question_number": session["current_q"] + 1,
            "question":        next_q
        }
    })

# ============================================================
# ROUTE 3: GET /summary/<session_id>
# Get final score + feedback after all questions answered
# ============================================================

@app.route("/summary/<session_id>", methods=["GET"])
def summary(session_id):
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404

    session = sessions[session_id]

    if not session["done"]:
        answered = len(session["answers"])
        total    = len(session["questions"])
        return jsonify({
            "error":    f"Interview not complete yet ({answered}/{total} answered)"
        }), 400

    result = generate_summary(
        session["questions"],
        session["answers"],
        session["evaluations"],
        session["role"]
    )

    # Add per-question breakdown
    result["breakdown"] = [
        {
            "question":   q,
            "answer":     a,
            "score":      e["score"],
            "good":       e["good"],
            "missing":    e["missing"],
            "tip":        e["tip"]
        }
        for q, a, e in zip(
            session["questions"],
            session["answers"],
            session["evaluations"]
        )
    ]

    return jsonify(result)


# ── Health check ───────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status":   "running",
        "sessions": len(sessions),
        "routes": {
            "start":   "POST /start   — upload resume + role",
            "answer":  "POST /answer  — submit answer",
            "summary": "GET  /summary/<session_id>"
        }
    })


if __name__ == "__main__":
    app.run(debug=True, port=5003)