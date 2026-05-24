# ============================================================
# MOCK INTERVIEWER — DAY 2
# Goal: Evaluate user answers and generate scores + feedback
# Run each section in Jupyter Notebook cell by cell
# ============================================================

import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


# ============================================================
# PART 1: Single Answer Evaluator
# ============================================================

print("=" * 55)
print("PART 1: Answer Evaluator")
print("=" * 55)

def evaluate_answer(question, answer, role, resume_text):
    """
    Evaluate a single interview answer.
    Returns: { score, good, missing, tip }
    """

    # If answer is too short — handle gracefully
    if not answer or len(answer.strip()) < 5:
        return {
            "score":   0,
            "good":    "No answer provided.",
            "missing": "Please provide a complete answer.",
            "tip":     "Even a partial answer is better than nothing."
        }

    prompt = f"""You are an experienced {role} interviewer evaluating a candidate's answer.

Question: {question}

Candidate's Answer: {answer}

Candidate's Resume Context: {resume_text[:500]}

Evaluate the answer and respond in this EXACT format (no extra text):
SCORE: [number from 1-10]
GOOD: [one sentence — what was good about the answer]
MISSING: [one sentence — what was missing or could be better]
TIP: [one sentence — specific advice to improve]"""

    response = groq_client.chat.completions.create(
        model      = "llama-3.3-70b-versatile",
        messages   = [{"role": "user", "content": prompt}],
        max_tokens = 200,
        temperature= 0.3
    )

    raw = response.choices[0].message.content.strip()

    # Parse the structured response
    result = {"score": 5, "good": "", "missing": "", "tip": ""}
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

    # Clamp score between 1 and 10
    result["score"] = max(1, min(10, result["score"]))
    return result


# ── Test the evaluator ────────────────────────────────────

# Load resume from Day 1
try:
    with open("parsed_resume.json") as f:
        resume_text = json.load(f)["text"]
    print("✅ Resume loaded from Day 1")
except:
    resume_text = "Python developer with experience in ML and web development"
    print("⚠️  Using fallback resume text")

role = "AI/ML Engineer"

# Test 1: Good answer
print("\n--- Test 1: Strong answer ---")
q1 = "Can you explain how your sentiment classifier works end to end?"
a1 = """I trained a Logistic Regression model on 50,000 IMDB reviews.
First I cleaned the text by lowercasing, removing HTML tags and punctuation.
Then I used TF-IDF vectorization with 10,000 features and bigrams to convert
text to numbers. Trained Logistic Regression, got 88% accuracy with F1 of 0.88.
Saved with joblib and deployed as a Flask REST API."""

eval1 = evaluate_answer(q1, a1, role, resume_text)
print(f"Question: {q1}")
print(f"Answer:   {a1[:100]}...")
print(f"\nScore:    {eval1['score']}/10")
print(f"Good:     {eval1['good']}")
print(f"Missing:  {eval1['missing']}")
print(f"Tip:      {eval1['tip']}")

# Test 2: Weak answer
print("\n--- Test 2: Weak answer ---")
q2 = "What is overfitting and how did you handle it in your projects?"
a2 = "Overfitting is when the model is too accurate on training data."

eval2 = evaluate_answer(q2, a2, role, resume_text)
print(f"Question: {q2}")
print(f"Answer:   {a2}")
print(f"\nScore:    {eval2['score']}/10")
print(f"Good:     {eval2['good']}")
print(f"Missing:  {eval2['missing']}")
print(f"Tip:      {eval2['tip']}")

# Test 3: Empty answer
print("\n--- Test 3: Empty answer ---")
eval3 = evaluate_answer(q2, "", role, resume_text)
print(f"Score:    {eval3['score']}/10")
print(f"Missing:  {eval3['missing']}")


# ============================================================
# PART 2: Final Summary Generator
# After all 5 questions are answered
# ============================================================

print("\n" + "=" * 55)
print("PART 2: Final Summary")
print("=" * 55)

def generate_summary(questions, answers, evaluations, role):
    """
    Generate overall interview summary after all answers.
    Returns: { total_score, max_score, percentage, grade, feedback, strengths, improvements }
    """
    # Calculate score
    scores      = [e["score"] for e in evaluations]
    total_score = sum(scores)
    max_score   = len(questions) * 10
    percentage  = round((total_score / max_score) * 100)

    # Grade
    if percentage >= 80:
        grade = "Excellent"
    elif percentage >= 60:
        grade = "Good"
    elif percentage >= 40:
        grade = "Average"
    else:
        grade = "Needs Improvement"

    # Build Q&A summary for LLM
    qa_summary = ""
    for i, (q, a, e) in enumerate(zip(questions, answers, evaluations), 1):
        qa_summary += f"\nQ{i}: {q}\nAnswer: {a[:100]}...\nScore: {e['score']}/10\n"

    prompt = f"""You interviewed a candidate for a {role} position.
Here is the complete interview:
{qa_summary}

Write a brief interview summary in this EXACT format:
FEEDBACK: [2 sentences — overall performance assessment]
STRENGTHS: [one key strength shown across answers]
IMPROVE: [one most important thing to work on]"""

    response = groq_client.chat.completions.create(
        model      = "llama-3.3-70b-versatile",
        messages   = [{"role": "user", "content": prompt}],
        max_tokens = 200,
        temperature= 0.3
    )

    raw      = response.choices[0].message.content.strip()
    feedback = ""
    strengths = ""
    improve   = ""

    for line in raw.splitlines():
        if line.startswith("FEEDBACK:"):
            feedback  = line.split(":", 1)[1].strip()
        elif line.startswith("STRENGTHS:"):
            strengths = line.split(":", 1)[1].strip()
        elif line.startswith("IMPROVE:"):
            improve   = line.split(":", 1)[1].strip()

    return {
        "total_score":  total_score,
        "max_score":    max_score,
        "percentage":   percentage,
        "grade":        grade,
        "scores":       scores,
        "feedback":     feedback,
        "strengths":    strengths,
        "improve":      improve
    }


# ── Test with a simulated full interview ─────────────────

questions = [
    "Explain your sentiment classifier end to end.",
    "What is overfitting and how did you handle it?",
    "How does your RAG app retrieve relevant chunks?",
    "Why did you choose Logistic Regression for text classification?",
    "What would you improve about your projects?"
]

answers = [
    "I used TF-IDF and Logistic Regression on 50k reviews, got 88% accuracy, deployed with Flask.",
    "Overfitting is when model memorizes training data. I used cross validation to check.",
    "I convert the question to an embedding using sentence-transformers, then query ChromaDB for top 3 similar chunks using cosine similarity.",
    "Logistic Regression works well with high dimensional sparse data like TF-IDF vectors. It's fast and interpretable.",
    "I would upgrade from TF-IDF to BERT embeddings for better accuracy and add reranking to the RAG pipeline."
]

print("Evaluating all 5 answers...")
evaluations = []
for i, (q, a) in enumerate(zip(questions, answers)):
    print(f"  Evaluating Q{i+1}...")
    ev = evaluate_answer(q, a, role, resume_text)
    evaluations.append(ev)
    print(f"  Score: {ev['score']}/10")

print("\nGenerating summary...")
summary = generate_summary(questions, answers, evaluations, role)

print(f"\n{'='*50}")
print("INTERVIEW SUMMARY")
print(f"{'='*50}")
print(f"Total Score:  {summary['total_score']}/{summary['max_score']}")
print(f"Percentage:   {summary['percentage']}%")
print(f"Grade:        {summary['grade']}")
print(f"Scores:       {summary['scores']}")
print(f"\nFeedback:     {summary['feedback']}")
print(f"Strengths:    {summary['strengths']}")
print(f"Improve:      {summary['improve']}")


# ============================================================
# PART 3: Complete Interview Runner
# Full end-to-end simulation in terminal
# This is what Flask wraps on Day 3
# ============================================================

print("\n" + "=" * 55)
print("PART 3: Full Interview Simulation")
print("=" * 55)

def run_interview(resume_text, role_key, questions):
    """
    Run a complete interview session.
    Collect answers → evaluate each → generate summary.
    Returns complete session result.
    """
    role        = role_key
    answers     = []
    evaluations = []

    print(f"\n🎤 Starting {role} Interview")
    print(f"You will be asked {len(questions)} questions.")
    print("Type your answer and press Enter.\n")

    for i, question in enumerate(questions, 1):
        print(f"\nQ{i}/{len(questions)}: {question}")
        print("-" * 50)
        answer = input("Your answer: ").strip()

        print("\nEvaluating...")
        evaluation = evaluate_answer(question, answer, role, resume_text)
        answers.append(answer)
        evaluations.append(evaluation)

        print(f"Score: {evaluation['score']}/10")
        print(f"✅ {evaluation['good']}")
        print(f"⚠️  {evaluation['missing']}")
        print(f"💡 {evaluation['tip']}")

    # Final summary
    summary = generate_summary(questions, answers, evaluations, role)

    print(f"\n{'='*50}")
    print("FINAL RESULTS")
    print(f"{'='*50}")
    print(f"Score: {summary['total_score']}/{summary['max_score']} ({summary['percentage']}%) — {summary['grade']}")
    print(f"\n{summary['feedback']}")
    print(f"\nStrength: {summary['strengths']}")
    print(f"Work on:  {summary['improve']}")

    return {
        "questions":   questions,
        "answers":     answers,
        "evaluations": evaluations,
        "summary":     summary
    }

# Uncomment to run interactive interview in terminal:
# from mock_day1 import parse_resume, generate_questions, ROLES
# resume = parse_resume("resume.pdf")
# qs     = generate_questions(resume, "aiml")
# result = run_interview(resume, "AI/ML Engineer", qs)


# ============================================================
# DAY 2 CHALLENGE
# ============================================================

print("\n" + "=" * 55)
print("DAY 2 CHALLENGE")
print("=" * 55)
print("""
1. Run the evaluator on YOUR real answers.
   Open the questions generated from Day 1.
   Answer them honestly and evaluate each one.
   What score do you get?

2. Test a deliberately bad answer:
   "I don't know" or "I used Python"
   Does the evaluator catch it and give useful feedback?

3. Test a very long detailed answer (5+ sentences).
   Does the score go up compared to a 1 sentence answer?

4. Look at your lowest scoring answer.
   Read the TIP it gives you.
   Rewrite your answer using that tip.
   Does the score improve on the second try?

5. Most important:
   The questions + evaluations from YOUR real resume
   are the best interview prep you have.
   Do the full simulation once before Day 3.
""")

# ─────────────────────────────────────────────
# Day 2 done when you've run evaluate_answer()
# on at least 3 of your own real answers.
#
# Come back and say "mock day 3" — Flask API.
# Just 3 routes. Done in 1 day.
# ─────────────────────────────────────────────
