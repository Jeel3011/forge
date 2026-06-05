import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { getQuestions, generateConfigs, type ScanResult, type Question } from "../api/client";

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

  if (!state?.scanResult) return <div className="text-white p-8">No scan data.</div>;

  const allAnswered = questions.every(q => answers[q.id]);

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6 max-w-2xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Configure Your Deployment</h1>
        <p className="text-gray-400 mt-1 text-sm">
          Questions tailored to what Forge found in your code
        </p>
      </div>

      {loading ? (
        <div className="text-gray-400">Generating questions...</div>
      ) : (
        <div className="space-y-6">
          {questions.map((q) => (
            <div key={q.id} className="bg-gray-900 rounded-xl p-5 space-y-4">
              <div>
                <div className="font-semibold text-lg">{q.text}</div>
                <div className="text-sm text-gray-400 mt-1">{q.context}</div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {q.options.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setAnswers(prev => ({ ...prev, [q.id]: opt.value }))}
                    className={`p-3 rounded-lg text-sm font-medium border transition text-left ${
                      answers[q.id] === opt.value
                        ? "bg-orange-500 border-orange-500 text-white"
                        : "bg-gray-800 border-gray-700 text-gray-300 hover:border-gray-500"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          ))}

          <div className="bg-gray-900 rounded-xl p-5 space-y-3">
            <div className="font-semibold">Output format</div>
            <div className="grid grid-cols-3 gap-2">
              {[
                { value: "docker_compose", label: "Docker Compose" },
                { value: "kubernetes", label: "Kubernetes" },
                { value: "terraform", label: "Terraform" },
              ].map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setTier(opt.value)}
                  className={`p-3 rounded-lg text-sm font-medium border transition ${
                    tier === opt.value
                      ? "bg-orange-500 border-orange-500 text-white"
                      : "bg-gray-800 border-gray-700 text-gray-300 hover:border-gray-500"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleGenerate}
            disabled={generating}
            className="w-full bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-white font-semibold py-3 rounded-lg text-lg transition"
          >
            {generating ? "Generating..." : "Generate Configs →"}
          </button>
        </div>
      )}
    </div>
  );
}
