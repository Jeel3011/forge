import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { scanRepo, ScanResult } from "../api/client";

const EXAMPLES = [
  "github.com/langchain-ai/langchain",
  "github.com/run-llama/llama_index",
  "github.com/huggingface/transformers",
];

export default function Home() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [placeholder, setPlaceholder] = useState(EXAMPLES[0]);
  const navigate = useNavigate();
  const [params] = useSearchParams();

  // Pre-fill from landing page URL param
  useEffect(() => {
    const repo = params.get("repo");
    if (repo) setUrl(repo);
  }, [params]);

  // Cycle placeholder text
  useEffect(() => {
    let i = 0;
    const id = setInterval(() => {
      i = (i + 1) % EXAMPLES.length;
      setPlaceholder(EXAMPLES[i]);
    }, 3000);
    return () => clearInterval(id);
  }, []);

  const handleScan = async () => {
    if (!url.trim()) return;
    setError("");
    setLoading(true);
    try {
      const rawUrl = url.startsWith("http") ? url : `https://${url}`;
      const result: ScanResult = await scanRepo(rawUrl);
      navigate("/diagnose", { state: { scanResult: result } });
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Failed to scan repo. Check the URL and try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-forge-bg flex flex-col items-center justify-center px-6 relative">
      {/* Grid */}
      <div className="absolute inset-0 pointer-events-none" style={{
        backgroundImage: "linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)",
        backgroundSize: "40px 40px",
      }} />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_50%_50%,rgba(255,255,255,0.03)_0%,transparent_70%)] pointer-events-none" />

      <div className="relative z-10 w-full max-w-xl space-y-10" style={{ animation: "fadeUp 0.5s ease both" }}>
        {/* Header */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 mb-2">
            <div className="w-8 h-8 rounded-xl bg-forge-white flex items-center justify-center">
              <svg width="15" height="15" viewBox="0 0 14 14" fill="none">
                <path d="M2 12L7 2L12 12" stroke="#080808" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M4 8.5H10" stroke="#080808" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </div>
            <span className="font-bold text-lg text-forge-white tracking-tight">Forge</span>
          </div>
          <h1 className="text-3xl font-bold text-forge-white">Scan a repository</h1>
          <p className="text-forge-text">Paste a GitHub URL and get deployment-ready infrastructure configs.</p>
        </div>

        {/* Input card */}
        <div className="forge-card gradient-border p-6 space-y-4">
          <div className="space-y-2">
            <label className="text-xs font-medium text-forge-subtle uppercase tracking-wider">Repository URL</label>
            <input
              type="text"
              value={url}
              autoFocus
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleScan()}
              placeholder={placeholder}
              className="forge-input"
            />
          </div>

          <button
            onClick={handleScan}
            disabled={loading || !url.trim()}
            className="forge-btn-primary w-full py-3.5 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity=".25" strokeWidth="2.5"/>
                  <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
                </svg>
                Scanning…
              </>
            ) : (
              <>Scan repository <span className="opacity-60 ml-1">→</span></>
            )}
          </button>

          {error && (
            <div className="text-xs text-red-400/80 bg-red-950/20 border border-red-900/30 rounded-lg px-4 py-3">
              {error}
            </div>
          )}
        </div>

        {/* Phase indicators */}
        <div className="flex items-center justify-between text-xs text-forge-muted">
          {["Connect", "Scan", "Diagnose", "Fix", "Configure", "Generate"].map((phase, i) => (
            <div key={phase} className="flex items-center gap-2">
              <div className={`w-5 h-5 rounded-full border flex items-center justify-center text-[9px] font-bold transition-colors ${i === 0 ? "border-forge-light text-forge-light" : "border-forge-border text-forge-border"}`}>
                {i + 1}
              </div>
              <span className={i === 0 ? "text-forge-subtle" : "hidden sm:block"}>{phase}</span>
              {i < 5 && <div className="w-3 h-px bg-forge-border hidden sm:block" />}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
