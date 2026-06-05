import { useEffect, useRef, useState } from "react";

interface Line {
  text: string;
  color: string;
  delay: number;
  typewriter?: boolean;
}

const SEQUENCES: Line[][] = [
  // Sequence 1 — AI Agent
  [
    { text: "$ forge scan github.com/acme/ml-agent",        delay: 0,    color: "text-forge-white",    typewriter: true },
    { text: "  Fetching 28 files from repository...",        delay: 900,  color: "text-forge-subtle" },
    { text: "  Parsing dependencies (47 packages)",          delay: 1700, color: "text-forge-subtle" },
    { text: "  Running AI code analysis...",                 delay: 2500, color: "text-forge-subtle" },
    { text: "",                                              delay: 3100, color: "" },
    { text: "  ● Project type    AI Agent            94%",  delay: 3300, color: "text-forge-light" },
    { text: "  ● Stack           celery · redis · langchain", delay: 3650, color: "text-forge-text" },
    { text: "",                                              delay: 4000, color: "" },
    { text: "  [CRITICAL]  Model loaded on every request    main.py:47", delay: 4200, color: "text-red-400" },
    { text: "  [WARNING]   No health check endpoint",       delay: 4700, color: "text-yellow-400/80" },
    { text: "  [WARNING]   Redis without retry logic",      delay: 5100, color: "text-yellow-400/80" },
    { text: "",                                              delay: 5500, color: "" },
    { text: "  Generating docker-compose.yml    ✓",         delay: 5700, color: "text-forge-subtle" },
    { text: "  Generating Dockerfile            ✓",         delay: 6100, color: "text-forge-subtle" },
    { text: "  Generating .env.example          ✓",         delay: 6500, color: "text-forge-subtle" },
    { text: "",                                              delay: 6900, color: "" },
    { text: "  ✓ Done — 3 files · save 2–5 days DevOps",   delay: 7100, color: "text-forge-white" },
  ],
  // Sequence 2 — Fine-tuning Pipeline
  [
    { text: "$ forge scan github.com/lab/finetune-llm",      delay: 0,    color: "text-forge-white",    typewriter: true },
    { text: "  Fetching 19 files from repository...",        delay: 900,  color: "text-forge-subtle" },
    { text: "  Parsing dependencies (31 packages)",          delay: 1700, color: "text-forge-subtle" },
    { text: "  Detecting training patterns...",              delay: 2500, color: "text-forge-subtle" },
    { text: "",                                              delay: 3100, color: "" },
    { text: "  ● Project type    Fine-tuning Pipeline  89%", delay: 3300, color: "text-forge-light" },
    { text: "  ● Stack           torch · peft · wandb · hf", delay: 3650, color: "text-forge-text" },
    { text: "",                                              delay: 4000, color: "" },
    { text: "  [CRITICAL]  No GPU base image configured",   delay: 4200, color: "text-red-400" },
    { text: "  [CRITICAL]  Secrets hardcoded in train.py:12", delay: 4600, color: "text-red-400" },
    { text: "  [WARNING]   No checkpoint storage configured", delay: 5100, color: "text-yellow-400/80" },
    { text: "",                                              delay: 5500, color: "" },
    { text: "  Generating Dockerfile (cuda:12.1)    ✓",     delay: 5700, color: "text-forge-subtle" },
    { text: "  Generating docker-compose.yml         ✓",    delay: 6100, color: "text-forge-subtle" },
    { text: "  Generating deployment guide           ✓",    delay: 6500, color: "text-forge-subtle" },
    { text: "",                                              delay: 6900, color: "" },
    { text: "  ✓ Done — GPU-ready config in 58 seconds",    delay: 7100, color: "text-forge-white" },
  ],
  // Sequence 3 — Model Serving
  [
    { text: "$ forge scan github.com/org/inference-api",     delay: 0,    color: "text-forge-white",    typewriter: true },
    { text: "  Fetching 22 files from repository...",        delay: 900,  color: "text-forge-subtle" },
    { text: "  Parsing dependencies (24 packages)",          delay: 1700, color: "text-forge-subtle" },
    { text: "  Profiling inference patterns...",             delay: 2500, color: "text-forge-subtle" },
    { text: "",                                              delay: 3100, color: "" },
    { text: "  ● Project type    Model Serving        91%",  delay: 3300, color: "text-forge-light" },
    { text: "  ● Stack           onnxruntime · fastapi · redis", delay: 3650, color: "text-forge-text" },
    { text: "",                                              delay: 4000, color: "" },
    { text: "  [CRITICAL]  4.2 GB model — no GPU configured", delay: 4200, color: "text-red-400" },
    { text: "  [WARNING]   No request batching detected",   delay: 4700, color: "text-yellow-400/80" },
    { text: "  [WARNING]   Sync file I/O in async handler", delay: 5100, color: "text-yellow-400/80" },
    { text: "",                                              delay: 5500, color: "" },
    { text: "  Generating deployment.yaml             ✓",   delay: 5700, color: "text-forge-subtle" },
    { text: "  Generating hpa.yaml (autoscaler)       ✓",   delay: 6100, color: "text-forge-subtle" },
    { text: "  Generating service.yaml                ✓",   delay: 6500, color: "text-forge-subtle" },
    { text: "",                                              delay: 6900, color: "" },
    { text: "  ✓ Done — K8s manifests · p95 < 200ms target", delay: 7100, color: "text-forge-white" },
  ],
];

const LOOP_PAUSE = 2200; // ms pause at end before restarting

export function TerminalDemo() {
  const [seqIndex, setSeqIndex] = useState(0);
  const [visibleLines, setVisibleLines] = useState(0);
  const [typedChars, setTypedChars] = useState(0);
  const [phase, setPhase] = useState<"typing" | "revealing" | "done">("typing");
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const sequence = SEQUENCES[seqIndex];
  const firstLine = sequence[0];

  const clearTimers = () => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  };

  const addTimer = (fn: () => void, delay: number) => {
    timersRef.current.push(setTimeout(fn, delay));
  };

  useEffect(() => {
    clearTimers();
    setVisibleLines(0);
    setTypedChars(0);
    setPhase("typing");

    // Phase 1: typewriter the first line
    const full = firstLine.text;
    let charIndex = 0;
    const typeInterval = setInterval(() => {
      charIndex++;
      setTypedChars(charIndex);
      if (charIndex >= full.length) {
        clearInterval(typeInterval);
        setPhase("revealing");
      }
    }, 38);
    timersRef.current.push(typeInterval as unknown as ReturnType<typeof setTimeout>);

    return clearTimers;
  }, [seqIndex]);

  useEffect(() => {
    if (phase !== "revealing") return;
    clearTimers();

    // Show first line fully
    setVisibleLines(1);

    // Schedule remaining lines
    sequence.slice(1).forEach((line, i) => {
      addTimer(() => setVisibleLines(i + 2), line.delay);
    });

    // Pause then loop to next sequence
    const lastDelay = sequence[sequence.length - 1].delay;
    addTimer(() => {
      setPhase("done");
      addTimer(() => {
        setSeqIndex((s) => (s + 1) % SEQUENCES.length);
      }, LOOP_PAUSE);
    }, lastDelay + 400);

    return clearTimers;
  }, [phase]);

  const currentLines = sequence.slice(0, visibleLines);
  const allDone = visibleLines >= sequence.length;

  return (
    <div className="relative rounded-2xl overflow-hidden border border-forge-border bg-[#0a0a0a] shadow-2xl">
      {/* Title bar */}
      <div className="flex items-center gap-2 px-5 py-3.5 border-b border-forge-border bg-forge-card/80 backdrop-blur">
        <span className="w-3 h-3 rounded-full bg-[#ff5f57]" />
        <span className="w-3 h-3 rounded-full bg-[#febc2e]" />
        <span className="w-3 h-3 rounded-full bg-[#28c840]" />
        <span className="ml-3 text-xs text-forge-muted font-mono tracking-wide">forge — terminal</span>
        {/* Sequence indicator dots */}
        <div className="ml-auto flex gap-1.5">
          {SEQUENCES.map((_, i) => (
            <span
              key={i}
              className={`w-1.5 h-1.5 rounded-full transition-all duration-500 ${
                i === seqIndex ? "bg-forge-light scale-125" : "bg-forge-border"
              }`}
            />
          ))}
        </div>
      </div>

      {/* CRT scanline */}
      <div className="pointer-events-none absolute inset-0 z-10"
        style={{
          background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px)",
        }}
      />

      {/* Moving highlight */}
      <div
        className="pointer-events-none absolute left-0 right-0 h-24 z-10"
        style={{
          background: "linear-gradient(180deg, transparent, rgba(255,255,255,0.018), transparent)",
          animation: "scanLine 4s ease-in-out infinite",
        }}
      />

      <div className="p-5 font-mono text-xs leading-[1.75] min-h-[300px] overflow-hidden">
        {/* Typewriter first line */}
        {phase === "typing" && (
          <div className={firstLine.color}>
            {firstLine.text.slice(0, typedChars)}
            <span className="inline-block w-[7px] h-[13px] bg-forge-light align-middle ml-[1px] cursor-blink" />
          </div>
        )}

        {/* Revealed lines */}
        {phase !== "typing" && currentLines.map((line, i) => (
          <div
            key={`${seqIndex}-${i}`}
            className={`${line.color || "opacity-0 select-none"} transition-opacity duration-150`}
            style={{ animation: i > 0 ? "fadeUp 0.25s ease both" : undefined }}
          >
            {line.text || " "}
          </div>
        ))}

        {/* Blinking cursor while revealing */}
        {phase === "revealing" && !allDone && (
          <span className="inline-block w-[7px] h-[13px] bg-forge-subtle align-middle cursor-blink" />
        )}

        {/* Done — show restart hint */}
        {phase === "done" && (
          <div className="mt-3 text-forge-border text-[10px] tracking-wider animate-pulse">
            — scanning next project —
          </div>
        )}
      </div>
    </div>
  );
}
