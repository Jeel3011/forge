import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import clsx from "clsx";
import { getQuestions, generateConfigs, type ScanResult, type Question } from "../api/client";

function Stepper({ step }: { step: number }) {
  const steps = ["Connect", "Scan", "Diagnose", "Fix", "Configure", "Generate"];
  return (
    <div className="flex items-center gap-0">
      {steps.map((s, i) => (
        <div key={s} className="flex items-center">
          <div className={clsx(
            "w-7 h-7 rounded-full border text-xs font-bold flex items-center justify-center transition-all",
            i < step ? "border-forge-white bg-forge-white text-black" :
            i === step ? "border-forge-light text-forge-light" :
            "border-forge-border text-forge-border"
          )}>
            {i < step ? (
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>
            ) : i + 1}
          </div>
          <span className={clsx("hidden sm:block text-xs mx-1.5", i === step ? "text-forge-light" : "text-forge-border")}>{s}</span>
          {i < steps.length - 1 && <div className="w-4 h-px bg-forge-border mx-1" />}
        </div>
      ))}
    </div>
  );
}

function QuestionBlock({
  question,
  answer,
  onSelect,
  index,
}: {
  question: Question;
  answer: string | undefined;
  onSelect: (v: string) => void;
  index: number;
}) {
  return (
    <div
      className="forge-card gradient-border p-6 space-y-5"
      style={{ animation: `fadeUp 0.4s ease ${index * 0.08}s both` }}
    >
      <div className="space-y-1.5">
        <div className="text-xs text-forge-muted font-mono uppercase tracking-wider">Question {index + 1}</div>
        <h3 className="text-base font-semibold text-forge-white leading-snug">{question.text}</h3>
        <p className="text-xs text-forge-subtle leading-relaxed">{question.context}</p>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {question.options.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onSelect(opt.value)}
            className={clsx(
              "p-3.5 rounded-xl text-sm font-medium text-left transition-all duration-150 border",
              answer === opt.value
                ? "bg-forge-white text-black border-forge-white"
                : "bg-forge-surface border-forge-border text-forge-text hover:border-forge-line hover:text-forge-light"
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

const TIERS = [
  {
    value: "docker_compose",
    label: "Docker Compose",
    desc: "1–3 services · up to ~100 users",
    badge: "Recommended",
  },
  {
    value: "kubernetes",
    label: "Kubernetes",
    desc: "Multiple services · 100–10k users",
    badge: null,
  },
  {
    value: "terraform",
    label: "Terraform",
    desc: "Cloud-native · production-grade",
    badge: null,
  },
];

export default function Questionnaire() {
  const { state } = useLocation() as {
    state: { scanResult: ScanResult; approvedFixes: { issue_id: string; approved: boolean }[] };
  };
  const navigate = useNavigate();

  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [tier, setTier] = useState("docker_compose");

  useEffect(() => {
    if (!state?.scanResult) return;
    getQuestions(state.scanResult)
      .then(setQuestions)
      .finally(() => setLoading(false));
  }, [state]);

  if (!state?.scanResult) {
    return <div className="min-h-screen bg-forge-bg flex items-center justify-center text-forge-text">No scan data.</div>;
  }

  const answered = questions.length === 0 || questions.every((q) => answers[q.id]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const result = await generateConfigs({
        scan_result: state.scanResult,
        approved_fixes: state.approvedFixes ?? [],
        questionnaire_answers: answers,
        output_tier: tier,
      });
      navigate("/output", { state: { config: result } });
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-forge-bg text-forge-white">
      {/* Top bar */}
      <div className="border-b border-forge-border bg-forge-surface/60 backdrop-blur sticky top-0 z-30">
        <div className="max-w-3xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-forge-white flex items-center justify-center">
              <svg width="11" height="11" viewBox="0 0 14 14" fill="none">
                <path d="M2 12L7 2L12 12M4 8.5H10" stroke="#080808" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <span className="font-semibold text-sm text-forge-white">Forge</span>
          </div>
          <Stepper step={4} />
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        <div style={{ animation: "fadeUp 0.4s ease both" }}>
          <div className="text-xs text-forge-muted uppercase tracking-wider mb-1">Step 5 of 6</div>
          <h1 className="text-2xl font-bold text-forge-white">Configure your deployment</h1>
          <p className="text-forge-text text-sm mt-1">
            Questions generated from what Forge found in your code — not a generic form.
          </p>
        </div>

        {loading ? (
          <div className="flex items-center gap-3 text-forge-subtle py-12 justify-center">
            <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity=".2" strokeWidth="2.5"/>
              <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
            </svg>
            Generating questions…
          </div>
        ) : (
          <div className="space-y-4">
            {questions.map((q, i) => (
              <QuestionBlock
                key={q.id}
                question={q}
                answer={answers[q.id]}
                onSelect={(v) => setAnswers((p) => ({ ...p, [q.id]: v }))}
                index={i}
              />
            ))}
          </div>
        )}

        {/* Tier selector */}
        {!loading && (
          <div
            className="forge-card gradient-border p-6 space-y-4"
            style={{ animation: `fadeUp 0.4s ease ${questions.length * 0.08 + 0.1}s both` }}
          >
            <div className="space-y-1">
              <div className="text-xs text-forge-muted uppercase tracking-wider">Output format</div>
              <h3 className="text-base font-semibold text-forge-white">What scale are you targeting?</h3>
            </div>
            <div className="grid sm:grid-cols-3 gap-3">
              {TIERS.map((t) => (
                <button
                  key={t.value}
                  onClick={() => setTier(t.value)}
                  className={clsx(
                    "relative p-4 rounded-xl text-left border transition-all duration-150",
                    tier === t.value
                      ? "border-forge-white bg-forge-card"
                      : "border-forge-border bg-forge-surface hover:border-forge-line"
                  )}
                >
                  {t.badge && (
                    <div className="absolute top-3 right-3 text-[9px] font-bold uppercase tracking-wider bg-forge-white text-black px-1.5 py-0.5 rounded">
                      {t.badge}
                    </div>
                  )}
                  <div className={clsx("text-sm font-semibold mb-1", tier === t.value ? "text-forge-white" : "text-forge-light")}>
                    {t.label}
                  </div>
                  <div className="text-xs text-forge-muted">{t.desc}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Generate */}
        {!loading && (
          <div style={{ animation: `fadeUp 0.4s ease ${questions.length * 0.08 + 0.25}s both` }}>
            <button
              onClick={handleGenerate}
              disabled={generating || !answered}
              className="forge-btn-primary w-full py-4 text-base flex items-center justify-center gap-2"
            >
              {generating ? (
                <>
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity=".25" strokeWidth="2.5"/>
                    <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
                  </svg>
                  Generating configs…
                </>
              ) : "Generate infrastructure configs →"}
            </button>
            {!answered && (
              <p className="text-xs text-center text-forge-muted mt-2">Answer all questions to continue</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
