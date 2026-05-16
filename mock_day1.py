# ============================================================
# MOCK INTERVIEWER — DAY 1
# Goal: Parse a resume PDF and generate 5 interview
#       questions based on its content + job role
# Run each section in Jupyter Notebook cell by cell
# ============================================================

import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from groq import Groq

load_dotenv()
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


# ============================================================
# PART 1: Parse the Resume
# ============================================================

print("=" * 55)
print("PART 1: Resume Parser")
print("=" * 55)

def parse_resume(pdf_path):
    """
    Load resume PDF and extract all text.
    Returns clean text string.
    """
    loader = PyPDFLoader(pdf_path)
    pages  = loader.load()

    # Join all pages into one string
    full_text = "\n".join(page.page_content for page in pages)

    # Basic cleanup
    full_text = "\n".join(
        line.strip() for line in full_text.splitlines()
        if line.strip()  # remove empty lines
    )

    return full_text


# Test with your own resume
# Change this path to your resume PDF
RESUME_PATH = "resume.pdf"

# If you don't have a resume PDF yet, create a simple one:
try:
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 8, """Garv Rawat
rawatgarv46@gmail.com | github.com/Garv72526

EDUCATION
VIT Chennai — B.Tech ECE | CGPA: 9.06 | 2023-2027

SKILLS
Python, React.js, Node.js, Flask, Scikit-learn, LangChain,
ChromaDB, NLP, TF-IDF, Logistic Regression, MongoDB, Socket.io

PROJECTS
SocialSphere — AI-Powered Social Networking App
- Trained TF-IDF + Logistic Regression sentiment classifier
  on 50,000 IMDB reviews achieving 88% accuracy
- Deployed via Flask REST API, integrated into social media app
- Real-time messaging using Socket.io

DocChat — Multi-Document RAG Application
- Built RAG pipeline using LangChain and ChromaDB
- Semantic search across multiple PDFs with page citations
- Flask API + React frontend, conversation memory

ACHIEVEMENTS
- 3rd place nationally at Gujarat Robofest 4.0, awarded INR 5,00,000
- IBM DevOps Fundamentals Certification
""")
    pdf.output("resume.pdf")
    print("✅ Sample resume.pdf created")
    RESUME_PATH = "resume.pdf"
except Exception as e:
    print(f"Create your own resume.pdf manually: {e}")

# Parse it
resume_text = parse_resume(RESUME_PATH)
print(f"\nResume parsed successfully!")
print(f"Total characters: {len(resume_text)}")
print(f"\nPreview:\n{resume_text[:500]}...")


# ============================================================
# ============================================================

print("\n" + "=" * 55)
print("PART 2: Question Generator")
print("=" * 55)

# Available job roles
ROLES = {
    "aiml":      "AI/ML Engineer",
    "webdev":    "Full Stack Web Developer",
    "fullstack": "Full Stack Developer",
    "backend":   "Backend Developer",
    "data":      "Data Scientist"
}

def generate_questions(resume_text, role_key, n_questions=5):
    """
    Generate interview questions based on resume content + role.
    Returns list of question strings.
    """
    role_name = ROLES.get(role_key, role_key)

    prompt = f"""You are an experienced technical interviewer hiring for a {role_name} position.

Based on the candidate's resume below, generate exactly {n_questions} interview questions.

Rules:
- Mix of technical and project-based questions
- Questions must be SPECIFIC to what's on their resume
  (mention their actual projects, skills, and technologies)
- Start with easier questions, end with harder ones
- Each question on a new line starting with a number and period
- No explanations, just the questions

Resume:
{resume_text}

Generate {n_questions} interview questions:"""

    response = groq_client.chat.completions.create(
        model      = "llama-3.3-70b-versatile",
        messages   = [{"role": "user", "content": prompt}],
        max_tokens = 500,
        temperature= 0.7   # slightly creative for varied questions
    )

    raw = response.choices[0].message.content.strip()

    # Parse questions into a list
    questions = []
    for line in raw.splitlines():
        line = line.strip()
        # Keep lines that start with a number
        if line and line[0].isdigit():
            # Remove "1. " prefix
            question = line.split(".", 1)[-1].strip()
            if question:
                questions.append(question)

    return questions[:n_questions]  # ensure exactly n questions


# Test question generation for different roles
print("\nGenerating questions for AI/ML role...")
questions_aiml = generate_questions(resume_text, "aiml")

print(f"\n{'='*50}")
print("AI/ML Interview Questions:")
print(f"{'='*50}")
for i, q in enumerate(questions_aiml, 1):
    print(f"\nQ{i}: {q}")

print("\n" + "-"*50)
print("\nGenerating questions for Web Dev role...")
questions_web = generate_questions(resume_text, "webdev")

print(f"\n{'='*50}")
print("Web Dev Interview Questions:")
print(f"{'='*50}")
for i, q in enumerate(questions_web, 1):
    print(f"\nQ{i}: {q}")


# ============================================================
# PART 3: Session Manager
# Keeps track of the interview state
# ============================================================

print("\n" + "=" * 55)
print("PART 3: Session Manager")
print("=" * 55)

# 🔑 A session stores everything about one interview
# We'll use this in Flask on Day 3

def create_session(resume_text, role_key):
    """Create a new interview session"""
    questions = generate_questions(resume_text, role_key)
    return {
        "role":          ROLES.get(role_key, role_key),
        "resume_text":   resume_text,
        "questions":     questions,
        "answers":       [],      # filled as user answers
        "evaluations":   [],      # filled as AI evaluates
        "current_q":     0,       # which question we're on
        "done":          False
    }

def get_current_question(session):
    """Get the current question"""
    idx = session["current_q"]
    if idx >= len(session["questions"]):
        return None
    return {
        "question_number": idx + 1,
        "total":           len(session["questions"]),
        "question":        session["questions"][idx]
    }

def submit_answer(session, answer):
    """Add answer to session, move to next question"""
    session["answers"].append(answer)
    session["current_q"] += 1
    if session["current_q"] >= len(session["questions"]):
        session["done"] = True
    return session

# Test the session
print("\nCreating interview session...")
session = create_session(resume_text, "aiml")

print(f"Role: {session['role']}")
print(f"Questions generated: {len(session['questions'])}")
print(f"\nFirst question: {get_current_question(session)['question']}")

# Simulate answering
session = submit_answer(session, "I would use dropout and cross validation")
print(f"\nAfter answering Q1:")
print(f"Current question index: {session['current_q']}")
print(f"Next question: {get_current_question(session)['question']}")
print(f"Done: {session['done']}")


# ============================================================
# PART 4: Save parsed resume
# So Flask doesn't need to re-parse on every request
# ============================================================

print("\n" + "=" * 55)
print("PART 4: Save Resume Text")
print("=" * 55)

import json

def save_resume(resume_text, filepath="parsed_resume.json"):
    with open(filepath, "w") as f:
        json.dump({"text": resume_text}, f)
    print(f"✅ Saved to {filepath}")

def load_resume(filepath="parsed_resume.json"):
    with open(filepath) as f:
        return json.load(f)["text"]

save_resume(resume_text)
loaded = load_resume()
print(f"Loaded back: {len(loaded)} characters ✅")


# ============================================================
# DAY 1 CHALLENGE
# ============================================================

print("\n" + "=" * 55)
print("DAY 1 CHALLENGE")
print("=" * 55)
print("""
1. Use YOUR actual resume PDF (not the sample).
   Set RESUME_PATH to your real resume.
   Are the questions specific to your actual projects?

2. Generate questions for 3 different roles.
   Which role gives the most relevant questions?
   Which questions would you struggle to answer?

3. Try passing a very short resume (just name + skills).
   Does the question quality drop?
   What does this tell you about resume quality and AI?

4. Most important:
   Look at the generated questions for your real resume.
   For each one — can you answer it?
   The ones you can't answer → add to my_notes.md
   and prepare those answers before your interview.
""")

# ─────────────────────────────────────────────
# Day 1 done when questions generate correctly
# from YOUR real resume for the AI/ML role.
#
# Come back and say "mock day 2" — we build
# the answer evaluator and scoring system.
# ─────────────────────────────────────────────
