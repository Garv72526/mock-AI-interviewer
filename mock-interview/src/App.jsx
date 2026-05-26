import { useState, useRef } from "react";
import axios from "axios";
import "./App.css";

const BASE = "http://localhost:5003";

const ROLES = [//for drop down options in select
  { value: "aiml",      label: "AI/ML Engineer" },
  { value: "webdev",    label: "Full Stack Web Developer" },
  { value: "fullstack", label: "Full Stack Developer" },
  { value: "backend",   label: "Backend Developer" },
  { value: "data",      label: "Data Scientist" },
];

// ── Screens ────────────────────────────────────────────────
// 1. setup    → upload resume + pick role
// 2. interview → answer questions one by one
// 3. summary  → see final score + feedback

export default function App() {
  const [screen,     setScreen]     = useState("setup");//control which page to show
  const [role,       setRole]       = useState("aiml");
  const [file,       setFile]       = useState(null);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState("");

  // Interview state
  const [sessionId,  setSessionId]  = useState(null);
  const [question,   setQuestion]   = useState("");
  const [qNumber,    setQNumber]    = useState(1);
  const [total,      setTotal]      = useState(5);
  const [answer,     setAnswer]     = useState("");
  const [evaluation, setEvaluation] = useState(null);
  const [answered,   setAnswered]   = useState(false);

  // Summary state
  const [summary,    setSummary]    = useState(null);

  const fileRef = useRef(null);


  // ── Screen 1: Start Interview ───────────────────────────
  async function handleStart(e) {
    e.preventDefault();
    if (!file) return setError("Please upload your resume PDF");

    setLoading(true);
    setError("");

    try {
      const form = new FormData();
      form.append("file", file);
      form.append("role", role);

      const res = await axios.post(`${BASE}/start`, form);
      const { session_id, question, total_questions, question_number } = res.data;

      setSessionId(session_id);
      setQuestion(question);
      setQNumber(question_number);
      setTotal(total_questions);
      setScreen("interview");

    } catch (err) {
      setError("Failed to start interview. Is the Flask server running?");
    }
    setLoading(false);
  }


  // ── Screen 2: Submit Answer ─────────────────────────────
  async function handleAnswer(e) {
    e.preventDefault();
    if (!answer.trim()) return setError("Please type an answer");

    setLoading(true);
    setError("");

    try {
      const res = await axios.post(`${BASE}/answer`, {
        session_id: sessionId,
        answer:     answer
      });

      const { evaluation, done, next_question } = res.data;

      setEvaluation(evaluation);
      setAnswered(true);

      if (done) {
        // Fetch summary after last question
        const sumRes = await axios.get(`${BASE}/summary/${sessionId}`);
        setSummary(sumRes.data);
      } else {
        // Store next question for after user clicks continue
        setQuestion(next_question.question);
        setQNumber(next_question.question_number);
      }

    } catch (err) {
      setError("Failed to submit answer.");
    }
    setLoading(false);
  }


  // Continue to next question or summary
  function handleContinue() {
    if (summary) {
      setScreen("summary");
    } else {
      setAnswer("");
      setEvaluation(null);
      setAnswered(false);
    }
  }


  // ── Restart ─────────────────────────────────────────────
  function handleRestart() {
    setScreen("setup");
    setFile(null);
    setSessionId(null);
    setQuestion("");
    setAnswer("");
    setEvaluation(null);
    setAnswered(false);
    setSummary(null);
    setError("");
  }


  // ── Render ──────────────────────────────────────────────
  return (
    <div className="app">
      <div className="card">

        {/* Header */}
        <div className="header">
          <h1>🎤 AI Mock Interviewer</h1>
          {screen !== "setup" && (
            <button className="restart-btn" onClick={handleRestart}>
              Start Over
            </button>
          )}
        </div>

        {error && <div className="error">{error}</div>}


        {/* ── Setup Screen ─────────────────────────────── */}
        {screen === "setup" && (
          <form onSubmit={handleStart} className="setup-form">
            <p className="subtitle">
              Upload your resume and select a role to get personalised interview questions.
            </p>

            <label className="field-label">Job Role</label>
            <select
              value={role}
              onChange={e => setRole(e.target.value)}
              className="select"
            >
              {ROLES.map(r => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>

            <label className="field-label">Resume (PDF)</label>
            <div
              className="upload-zone"
              onClick={() => fileRef.current.click()}
            >
              {file ? `✅ ${file.name}` : "Click to upload your resume PDF"}
              <input
                ref={fileRef}
                type="file"
                accept=".pdf"
                hidden
                onChange={e => setFile(e.target.files[0])}
              />
            </div>

            <button
              type="submit"
              className="primary-btn"
              disabled={loading || !file}
            >
              {loading ? "Generating questions..." : "Start Interview →"}
            </button>
          </form>
        )}


        {/* ── Interview Screen ──────────────────────────── */}
        {screen === "interview" && (
          <div className="interview">

            {/* Progress */}
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${((qNumber - 1) / total) * 100}%` }}
              />
            </div>
            <p className="progress-label">
              Question {answered ? qNumber : qNumber} of {total}
            </p>

            {/* Question */}
            <div className="question-box">
              <p className="question-text">
                {answered && evaluation
                  ? /* show current question still */
                    question
                  : question}
              </p>
            </div>

            {/* Answer input — hide after submitting */}
            {!answered && (
              <form onSubmit={handleAnswer}>
                <textarea
                  value={answer}
                  onChange={e => setAnswer(e.target.value)}
                  placeholder="Type your answer here..."
                  rows={5}
                  disabled={loading}
                />
                <button
                  type="submit"
                  className="primary-btn"
                  disabled={loading || !answer.trim()}
                >
                  {loading ? "Evaluating..." : "Submit Answer"}
                </button>
              </form>
            )}

            {/* Evaluation result */}
            {answered && evaluation && (
              <div className="evaluation">
                <div className="score-row">
                  <span className="score-label">Score</span>
                  <span className={`score-value ${
                    evaluation.score >= 7 ? "high" :
                    evaluation.score >= 4 ? "mid"  : "low"
                  }`}>
                    {evaluation.score}/10
                  </span>
                </div>

                <div className="eval-item">
                  <span className="eval-icon">✅</span>
                  <span>{evaluation.good}</span>
                </div>
                <div className="eval-item">
                  <span className="eval-icon">⚠️</span>
                  <span>{evaluation.missing}</span>
                </div>
                <div className="eval-item">
                  <span className="eval-icon">💡</span>
                  <span>{evaluation.tip}</span>
                </div>

                <button className="primary-btn" onClick={handleContinue}>
                  {summary ? "See Final Results →" : "Next Question →"}
                </button>
              </div>
            )}

          </div>
        )}


        {/* ── Summary Screen ────────────────────────────── */}
        {screen === "summary" && summary && (
          <div className="summary">

            {/* Score */}
            <div className="final-score">
              <div className={`grade ${
                summary.percentage >= 80 ? "grade-excellent" :
                summary.percentage >= 60 ? "grade-good"      :
                summary.percentage >= 40 ? "grade-average"   : "grade-poor"
              }`}>
                {summary.grade}
              </div>
              <p className="score-display">
                {summary.total_score}/{summary.max_score}
                <span className="pct"> ({summary.percentage}%)</span>
              </p>
            </div>

            {/* Overall feedback */}
            <div className="feedback-box">
              <p>{summary.feedback}</p>
              <div className="eval-item">
                <span className="eval-icon">💪</span>
                <span><strong>Strength:</strong> {summary.strengths}</span>
              </div>
              <div className="eval-item">
                <span className="eval-icon">📈</span>
                <span><strong>Work on:</strong> {summary.improve}</span>
              </div>
            </div>

            {/* Per question breakdown */}
            <h3 className="breakdown-title">Question Breakdown</h3>
            {summary.breakdown.map((item, i) => (
              <div key={i} className="breakdown-item">
                <div className="breakdown-header">
                  <span className="q-label">Q{i + 1}</span>
                  <span className={`q-score ${
                    item.score >= 7 ? "high" :
                    item.score >= 4 ? "mid"  : "low"
                  }`}>{item.score}/10</span>
                </div>
                <p className="q-text">{item.question}</p>
                <p className="a-text">Your answer: {item.answer}</p>
                <p className="tip-text">💡 {item.tip}</p>
              </div>
            ))}

            <button className="primary-btn" onClick={handleRestart}>
              Try Again
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
