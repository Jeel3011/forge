import { useEffect, useState } from "react";

const LINES = [
  { text: "$ forge scan github.com/acme/ml-agent", delay: 0,    color: "text-forge-light" },
  { text: "  Fetching repository...",               delay: 800,  color: "text-forge-subtle" },
  { text: "  Parsing dependencies (47 packages)",   delay: 1600, color: "text-forge-subtle" },
  { text: "  Running AI code analysis...",          delay: 2400, color: "text-forge-subtle" },
  { text: "",                                       delay: 3000, color: "" },
  { text: "  Project type:  AI Agent (94%)",        delay: 3200, color: "text-forge-light" },
  { text: "  Dependencies:  celery, redis, langchain, fastapi", delay: 3600, color: "text-forge-text" },
  { text: "",                                       delay: 4000, color: "" },
  { text: "  [CRITICAL] Model loaded on every request (main.py:47)", delay: 4200, color: "text-red-400/80" },
  { text: "  [WARNING]  No health check endpoint",  delay: 4600, color: "text-yellow-400/70" },
  { text: "  [WARNING]  Redis without retry logic", delay: 5000, color: "text-yellow-400/70" },
  { text: "",                                       delay: 5400, color: "" },
  { text: "  Generating docker-compose.yml...",     delay: 5600, color: "text-forge-subtle" },
  { text: "  Generating Dockerfile...",             delay: 6000, color: "text-forge-subtle" },
  { text: "  Generating .env.example...",           delay: 6400, color: "text-forge-subtle" },
  { text: "",                                       delay: 6800, color: "" },
  { text: "  ✓ Done. 3 files ready to download.",  delay: 7000, color: "text-forge-white" },
];

export function TerminalDemo() {
  const [visibleLines, setVisibleLines] = useState(0);

  useEffect(() => {
    const timers = LINES.map((line, i) =>
      setTimeout(() => setVisibleLines(i + 1), line.delay)
    );
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="relative rounded-2xl overflow-hidden border border-forge-border bg-forge-surface">
      {/* Traffic lights */}
      <div className="flex items-center gap-2 px-5 py-4 border-b border-forge-border bg-forge-card">
        <div className="w-3 h-3 rounded-full bg-[#3a3a3a]" />
        <div className="w-3 h-3 rounded-full bg-[#3a3a3a]" />
        <div className="w-3 h-3 rounded-full bg-[#3a3a3a]" />
        <span className="ml-3 text-xs text-forge-muted font-mono">forge — terminal</span>
      </div>

      {/* Scan line effect */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div
          className="absolute left-0 right-0 h-16 opacity-[0.03]"
          style={{
            background: "linear-gradient(180deg, transparent, rgba(255,255,255,0.8), transparent)",
            animation: "scanLine 3s linear infinite",
          }}
        />
      </div>

      <div className="p-5 font-mono text-xs leading-6 min-h-[320px]">
        {LINES.slice(0, visibleLines).map((line, i) => (
          <div key={i} className={`${line.color || "text-transparent"} select-none`}>
            {line.text || " "}
          </div>
        ))}
        {visibleLines < LINES.length && (
          <span className="inline-block w-2 h-4 bg-forge-text cursor-blink align-middle" />
        )}
      </div>
    </div>
  );
}
