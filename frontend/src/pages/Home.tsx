import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Zap } from "lucide-react";
import { scanRepo, ScanResult } from "../api/client";

export default function Home() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleScan = async () => {
    setError("");
    setLoading(true);
    try {
      const result: ScanResult = await scanRepo(url);
      navigate("/diagnose", { state: { scanResult: result } });
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Failed to scan repo. Check the URL and try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center px-4">
      <div className="max-w-2xl w-full text-center space-y-8">
        <div className="flex items-center justify-center gap-3">
          <Zap className="w-10 h-10 text-orange-400" />
          <h1 className="text-5xl font-bold tracking-tight">Forge</h1>
        </div>
        <p className="text-xl text-gray-400">
          Paste your GitHub repo. Get deployment-ready infrastructure configs in minutes.
        </p>
        <p className="text-sm text-gray-500">
          Understands your AI project type — fine-tuning pipelines, agent systems, model serving, and more.
        </p>

        <div className="space-y-3">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleScan()}
            placeholder="https://github.com/you/your-ai-project"
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-lg placeholder-gray-600 focus:outline-none focus:border-orange-400 transition"
          />
          <button
            onClick={handleScan}
            disabled={loading || !url.trim()}
            className="w-full bg-orange-500 hover:bg-orange-400 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-lg text-lg transition"
          >
            {loading ? "Scanning..." : "Scan Repo →"}
          </button>
          {error && <p className="text-red-400 text-sm">{error}</p>}
        </div>

        <div className="grid grid-cols-3 gap-4 text-sm text-gray-500 pt-4">
          <div className="bg-gray-900 rounded-lg p-4 text-left">
            <div className="text-orange-400 font-semibold mb-1">Scan & Classify</div>
            Detects your exact AI project type from dependencies and code patterns
          </div>
          <div className="bg-gray-900 rounded-lg p-4 text-left">
            <div className="text-orange-400 font-semibold mb-1">Diagnose Issues</div>
            Finds deployment anti-patterns before they cause production incidents
          </div>
          <div className="bg-gray-900 rounded-lg p-4 text-left">
            <div className="text-orange-400 font-semibold mb-1">Generate Configs</div>
            Docker Compose, Kubernetes, and Terraform — tuned to your project
          </div>
        </div>
      </div>
    </div>
  );
}
