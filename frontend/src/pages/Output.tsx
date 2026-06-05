import { useState } from "react";
import { useLocation, Link } from "react-router-dom";
import clsx from "clsx";
import type { GeneratedConfig } from "../api/client";

function Stepper() {
  const steps = ["Connect", "Scan", "Diagnose", "Fix", "Configure", "Generate"];
  return (
    <div className="flex items-center gap-0">
      {steps.map((s, i) => (
        <div key={s} className="flex items-center">
          <div className={clsx(
            "w-7 h-7 rounded-full border text-xs font-bold flex items-center justify-center",
            "border-forge-white bg-forge-white text-black"
          )}>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>
          </div>
          <span className="hidden sm:block text-xs mx-1.5 text-forge-muted">{s}</span>
          {i < steps.length - 1 && <div className="w-4 h-px bg-forge-border mx-1" />}
        </div>
      ))}
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={copy}
      className="flex items-center gap-1.5 text-xs text-forge-muted hover:text-forge-light transition-colors px-2.5 py-1.5 rounded-lg hover:bg-forge-surface"
    >
      {copied ? (
        <>
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M2 7l3 3 6-6" stroke="#a8a8a8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
          Copied
        </>
      ) : (
        <>
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><rect x="4.5" y="4.5" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.2"/><path d="M1.5 8.5V2a1 1 0 0 1 1-1h6.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/></svg>
          Copy
        </>
      )}
    </button>
  );
}

function DownloadButton({ name, content }: { name: string; content: string }) {
  const dl = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([content], { type: "text/plain" }));
    a.download = name;
    a.click();
  };
  return (
    <button
      onClick={dl}
      className="flex items-center gap-1.5 text-xs text-forge-muted hover:text-forge-light transition-colors px-2.5 py-1.5 rounded-lg hover:bg-forge-surface"
    >
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M6.5 1v8M3.5 6.5l3 3 3-3M1.5 12h10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>
      Download
    </button>
  );
}

export default function Output() {
  const { state } = useLocation() as { state: { config: GeneratedConfig } };
  const config = state?.config;
  const files = config ? Object.entries(config.files) : [];
  const [active, setActive] = useState(files[0]?.[0] ?? "guide");

  if (!config) {
    return <div className="min-h-screen bg-forge-bg flex items-center justify-center text-forge-text">No config data.</div>;
  }

  const downloadAll = () => {
    files.forEach(([name, content]) => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([content], { type: "text/plain" }));
      a.download = name;
      a.click();
    });
  };

  const activeContent = active === "guide" ? config.deployment_guide : config.files[active];

  return (
    <div className="min-h-screen bg-forge-bg text-forge-white flex flex-col">
      {/* Top bar */}
      <div className="border-b border-forge-border bg-forge-surface/60 backdrop-blur sticky top-0 z-30">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-forge-white flex items-center justify-center">
              <svg width="11" height="11" viewBox="0 0 14 14" fill="none">
                <path d="M2 12L7 2L12 12M4 8.5H10" stroke="#080808" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <span className="font-semibold text-sm text-forge-white">Forge</span>
          </div>
          <Stepper />
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-10 space-y-8 flex-1 w-full">
        {/* Header */}
        <div className="flex items-start justify-between gap-4" style={{ animation: "fadeUp 0.4s ease both" }}>
          <div>
            <div className="text-xs text-forge-muted uppercase tracking-wider mb-1">Step 6 of 6 — Complete</div>
            <h1 className="text-2xl font-bold text-forge-white">Your infrastructure is ready.</h1>
            <p className="text-forge-text text-sm mt-1 capitalize">
              {config.tier.replace("_", " ")} configuration · {files.length} file{files.length > 1 ? "s" : ""} generated
            </p>
          </div>
          <button
            onClick={downloadAll}
            className="forge-btn-primary flex items-center gap-2 py-2.5 px-5 text-sm whitespace-nowrap"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1v8M4 6.5l3 3 3-3M1.5 13h11" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>
            Download all
          </button>
        </div>

        {/* Main panel */}
        <div className="forge-card gradient-border overflow-hidden" style={{ animation: "fadeUp 0.4s ease 0.1s both" }}>
          {/* File tabs */}
          <div className="flex items-center gap-0 border-b border-forge-border overflow-x-auto bg-forge-surface/50">
            {files.map(([name]) => (
              <button
                key={name}
                onClick={() => setActive(name)}
                className={clsx(
                  "flex items-center gap-2 px-5 py-3 text-xs font-mono whitespace-nowrap border-r border-forge-border transition-colors",
                  active === name
                    ? "bg-forge-bg text-forge-white border-b-0"
                    : "text-forge-muted hover:text-forge-text"
                )}
              >
                <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
                  <path d="M2 1.5h4.5L9 4v5.5H2z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/>
                  <path d="M6.5 1.5v3H9" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                {name}
              </button>
            ))}
            <button
              onClick={() => setActive("guide")}
              className={clsx(
                "flex items-center gap-2 px-5 py-3 text-xs whitespace-nowrap transition-colors",
                active === "guide"
                  ? "bg-forge-bg text-forge-white"
                  : "text-forge-muted hover:text-forge-text"
              )}
            >
              <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
                <rect x="1.5" y="1.5" width="8" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.2"/>
                <path d="M3.5 4h4M3.5 6h2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
              </svg>
              Deploy guide
            </button>
          </div>

          {/* File content */}
          <div>
            <div className="flex items-center justify-between px-5 py-2.5 border-b border-forge-border bg-forge-surface/30">
              <span className="text-xs text-forge-muted font-mono">{active}</span>
              <div className="flex items-center">
                <CopyButton text={activeContent} />
                {active !== "guide" && <DownloadButton name={active} content={activeContent} />}
              </div>
            </div>
            <pre className="p-5 text-xs font-mono text-forge-light leading-6 overflow-auto max-h-[520px]">
              {activeContent}
            </pre>
          </div>
        </div>

        {/* Next steps */}
        <div className="forge-card gradient-border p-6" style={{ animation: "fadeUp 0.4s ease 0.2s both" }}>
          <h3 className="text-sm font-semibold text-forge-white mb-4">Next steps</h3>
          <ol className="space-y-3">
            {[
              ["Download all files", "Place them in your project root"],
              ["Set up environment", `Copy .env.example → .env and fill in secrets`],
              ["Start services", "docker compose up -d --build"],
              ["Verify", "curl http://localhost:8000/health → should return {\"status\":\"ok\"}"],
            ].map(([title, desc], i) => (
              <li key={title} className="flex gap-4">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-forge-surface border border-forge-border text-xs font-bold text-forge-muted flex items-center justify-center">
                  {i + 1}
                </span>
                <div>
                  <div className="text-sm font-medium text-forge-light">{title}</div>
                  <div className="text-xs text-forge-muted font-mono mt-0.5">{desc}</div>
                </div>
              </li>
            ))}
          </ol>
        </div>

        {/* Start over */}
        <div className="text-center pb-6">
          <Link to="/app" className="forge-btn-ghost text-sm">
            Scan another repo
          </Link>
        </div>
      </div>
    </div>
  );
}
