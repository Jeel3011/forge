import { useState } from "react";
import { useLocation } from "react-router-dom";
import { Copy, Download, Check } from "lucide-react";
import type { GeneratedConfig } from "../api/client";

function FileTab({ name, content }: { name: string; content: string }) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const download = () => {
    const blob = new Blob([content], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.click();
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="font-mono text-sm text-orange-300">{name}</span>
        <div className="flex gap-2">
          <button onClick={copy} className="p-1.5 bg-gray-800 hover:bg-gray-700 rounded transition">
            {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-gray-400" />}
          </button>
          <button onClick={download} className="p-1.5 bg-gray-800 hover:bg-gray-700 rounded transition">
            <Download className="w-4 h-4 text-gray-400" />
          </button>
        </div>
      </div>
      <pre className="bg-gray-900 rounded-lg p-4 text-sm text-gray-300 overflow-x-auto max-h-96 font-mono">
        {content}
      </pre>
    </div>
  );
}

export default function Output() {
  const { state } = useLocation() as { state: { config: GeneratedConfig } };
  const config = state?.config;
  const [activeFile, setActiveFile] = useState<string | null>(
    config ? Object.keys(config.files)[0] ?? null : null
  );
  const [showGuide, setShowGuide] = useState(false);

  if (!config) return <div className="text-white p-8">No config data.</div>;

  const downloadAll = () => {
    Object.entries(config.files).forEach(([name, content]) => {
      const blob = new Blob([content], { type: "text/plain" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = name;
      a.click();
    });
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Your Infrastructure</h1>
          <p className="text-gray-400 mt-1 text-sm capitalize">{config.tier.replace("_", " ")} configuration</p>
        </div>
        <button
          onClick={downloadAll}
          className="flex items-center gap-2 bg-orange-500 hover:bg-orange-400 text-white px-4 py-2 rounded-lg font-medium transition"
        >
          <Download className="w-4 h-4" />
          Download All
        </button>
      </div>

      {/* File tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {Object.keys(config.files).map(name => (
          <button
            key={name}
            onClick={() => setActiveFile(name)}
            className={`px-3 py-1.5 rounded-lg text-sm font-mono whitespace-nowrap transition ${
              activeFile === name
                ? "bg-orange-500 text-white"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            {name}
          </button>
        ))}
        <button
          onClick={() => setShowGuide(!showGuide)}
          className={`px-3 py-1.5 rounded-lg text-sm whitespace-nowrap transition ${
            showGuide
              ? "bg-orange-500 text-white"
              : "bg-gray-800 text-gray-400 hover:bg-gray-700"
          }`}
        >
          Deployment Guide
        </button>
      </div>

      {showGuide ? (
        <div className="bg-gray-900 rounded-xl p-6 prose prose-invert max-w-none">
          <pre className="whitespace-pre-wrap text-sm text-gray-300 font-sans">{config.deployment_guide}</pre>
        </div>
      ) : activeFile && config.files[activeFile] ? (
        <div className="bg-gray-900 rounded-xl p-6">
          <FileTab name={activeFile} content={config.files[activeFile]} />
        </div>
      ) : null}

      <div className="bg-gray-900 rounded-xl p-5">
        <div className="text-sm font-semibold mb-2">Next steps</div>
        <ol className="text-sm text-gray-400 space-y-1 list-decimal list-inside">
          <li>Download all files and place them in your project root</li>
          <li>Copy <code className="bg-gray-800 px-1 rounded">.env.example</code> to <code className="bg-gray-800 px-1 rounded">.env</code> and fill in your secrets</li>
          <li>Run <code className="bg-gray-800 px-1 rounded">docker compose up -d --build</code></li>
          <li>Verify with <code className="bg-gray-800 px-1 rounded">curl http://localhost:8000/health</code></li>
        </ol>
      </div>
    </div>
  );
}
