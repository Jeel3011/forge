import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import type { ScanResult, Issue } from "../api/client";
import clsx from "clsx";

const PROJECT_LABELS: Record<string, string> = {
  ai_agent: "AI Agent",
  llm_application: "LLM Application",
  fine_tuning: "Fine-tuning Pipeline",
  model_serving: "Model Serving",
  data_pipeline: "Data Pipeline",
  computer_vision: "Computer Vision",
  multimodal: "Multi-modal",
  classical_ml: "Classical ML",
  unknown: "Unknown",
};

const SEV_CONFIG = {
  critical:   { label: "Critical",   dot: "bg-red-500",    text: "text-red-400",    ring: "border-red-900/40 bg-red-950/20" },
  warning:    { label: "Warning",    dot: "bg-yellow-500", text: "text-yellow-400", ring: "border-yellow-900/40 bg-yellow-950/10" },
  suggestion: { label: "Suggestion", dot: "bg-blue-500",   text: "text-blue-400",   ring: "border-blue-900/40 bg-blue-950/10" },
};

function IssueCard({
  issue,
  index,
  approved,
  onApprove,
  onSkip,
}: {
  issue: Issue & { id: string };
  index: number;
  approved: boolean | null;
  onApprove: () => void;
  onSkip: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const cfg = SEV_CONFIG[issue.severity];

  return (
    <div
      className={clsx(
        "forge-card border transition-all duration-200",
        approved === true  && "border-forge-line",
        approved === false && "opacity-40",
        approved === null  && cfg.ring,
      )}
      style={{ animation: `fadeUp 0.4s ease ${index * 0.07}s both` }}
    >
      <div className="p-5 space-y-4">
        {/* Header row */}
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 mt-0.5">
            <span className={clsx("inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border", cfg.text,
              issue.severity === "critical"   ? "border-red-900/50 bg-red-950/30" :
              issue.severity === "warning"    ? "border-yellow-900/50 bg-yellow-950/20" :
              "border-blue-900/50 bg-blue-950/20"
            )}>
              <span className={clsx("w-1.5 h-1.5 rounded-full", cfg.dot)} />
              {cfg.label}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-semibold text-forge-white text-sm leading-snug">{issue.title}</div>
            {issue.file && (
              <div className="text-xs font-mono text-forge-muted mt-0.5">
                {issue.file}{issue.line ? `:${issue.line}` : ""}
              </div>
            )}
          </div>
          {/* Approve / skip */}
          <div className="flex gap-2 flex-shrink-0">
            <button
              onClick={onApprove}
              className={clsx(
                "h-8 px-3.5 rounded-lg text-xs font-semibold transition-all duration-150",
                approved === true
                  ? "bg-forge-white text-black"
                  : "border border-forge-border text-forge-subtle hover:border-forge-line hover:text-forge-light"
              )}
            >
              Approve
            </button>
            <button
              onClick={onSkip}
              className={clsx(
                "h-8 px-3.5 rounded-lg text-xs font-semibold transition-all duration-150",
                approved === false
                  ? "bg-forge-card border border-forge-line text-forge-white"
                  : "border border-forge-border text-forge-subtle hover:border-forge-line hover:text-forge-light"
              )}
            >
              Skip
            </button>
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-forge-text leading-relaxed pl-0">{issue.description}</p>

        {/* Expandable fix */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 text-xs text-forge-muted hover:text-forge-text transition-colors duration-150"
        >
          <svg
            width="12" height="12" viewBox="0 0 12 12" fill="none"
            className={clsx("transition-transform duration-200", expanded && "rotate-180")}
          >
            <path d="M2.5 4.5L6 8L9.5 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          {expanded ? "Hide" : "Show"} proposed fix
        </button>

        {expanded && (
          <div className="space-y-3 pt-1" style={{ animation: "fadeUp 0.25s ease both" }}>
            <p className="text-sm text-forge-text">{issue.proposed_fix}</p>
            {issue.diff_preview && (
              <div className="forge-card border-forge-line overflow-hidden">
                <div className="px-4 py-2 border-b border-forge-border bg-forge-surface">
                  <span className="text-xs text-forge-muted font-mono">diff</span>
                </div>
                <pre className="p-4 text-xs font-mono text-forge-light leading-6 overflow-x-auto">
                  {issue.diff_preview}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Progress stepper
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

export default function Diagnose() {
  const { state } = useLocation() as { state: { scanResult: ScanResult } };
  const navigate = useNavigate();
  const scan = state?.scanResult;

  const issues = scan?.issues.map((issue, i) => ({ ...issue, id: `issue_${i}` })) ?? [];
  const [decisions, setDecisions] = useState<Record<string, boolean | null>>(
    Object.fromEntries(issues.map((i) => [i.id, i.severity === "critical" ? true : null]))
  );

  if (!scan) {
    return (
      <div className="min-h-screen bg-forge-bg flex items-center justify-center text-forge-text">
        No scan data — <a href="/app" className="underline ml-1">go back</a>.
      </div>
    );
  }

  const criticals = issues.filter((i) => i.severity === "critical").length;
  const warnings = issues.filter((i) => i.severity === "warning").length;
  const approved = Object.values(decisions).filter(Boolean).length;

  const proceed = () => {
    navigate("/questionnaire", {
      state: {
        scanResult: scan,
        approvedFixes: Object.entries(decisions).map(([issue_id, a]) => ({ issue_id, approved: !!a })),
      },
    });
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
          <Stepper step={2} />
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {/* Summary card */}
        <div className="forge-card gradient-border p-6 space-y-4" style={{ animation: "fadeUp 0.4s ease both" }}>
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <div className="text-xs text-forge-muted uppercase tracking-wider">Detected project type</div>
              <div className="text-2xl font-bold text-forge-white">{PROJECT_LABELS[scan.project_type]}</div>
              <div className="text-sm text-forge-subtle font-mono">{scan.repo_url}</div>
            </div>
            <div className="text-right flex-shrink-0">
              <div className="text-3xl font-black text-forge-white">{Math.round(scan.confidence * 100)}%</div>
              <div className="text-xs text-forge-muted">confidence</div>
            </div>
          </div>

          {scan.detected_characteristics.length > 0 && (
            <div className="flex flex-wrap gap-2 pt-2 border-t border-forge-border">
              {scan.detected_characteristics.map((c) => (
                <span key={c} className="text-xs px-2.5 py-1 rounded-full bg-forge-surface border border-forge-border text-forge-text font-mono">
                  {c}
                </span>
              ))}
            </div>
          )}

          <div className="flex gap-4 text-sm pt-1 border-t border-forge-border">
            {criticals > 0 && (
              <span className="flex items-center gap-1.5 text-red-400">
                <span className="w-2 h-2 rounded-full bg-red-500" />{criticals} critical
              </span>
            )}
            {warnings > 0 && (
              <span className="flex items-center gap-1.5 text-yellow-400/80">
                <span className="w-2 h-2 rounded-full bg-yellow-500" />{warnings} warning{warnings > 1 ? "s" : ""}
              </span>
            )}
            {issues.length === 0 && (
              <span className="text-forge-subtle">No issues detected</span>
            )}
          </div>
        </div>

        {/* Issues */}
        {issues.length > 0 ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-forge-white">Issues found</h2>
              <span className="text-xs text-forge-muted">{approved} approved</span>
            </div>
            {issues.map((issue, i) => (
              <IssueCard
                key={issue.id}
                issue={issue}
                index={i}
                approved={decisions[issue.id] ?? null}
                onApprove={() => setDecisions((p) => ({ ...p, [issue.id]: true }))}
                onSkip={() => setDecisions((p) => ({ ...p, [issue.id]: false }))}
              />
            ))}
          </div>
        ) : (
          <div className="forge-card border-forge-line p-6 text-center space-y-2" style={{ animation: "fadeUp 0.4s ease 0.1s both" }}>
            <div className="text-2xl">✓</div>
            <div className="text-forge-white font-semibold">No deployment issues detected</div>
            <div className="text-forge-text text-sm">Your project looks clean. Continue to configuration.</div>
          </div>
        )}

        {/* CTA */}
        <div className="pt-2">
          <button
            onClick={proceed}
            className="forge-btn-primary w-full py-4 text-base"
          >
            Continue to Configuration →
          </button>
          <p className="text-xs text-center text-forge-muted mt-3">
            {approved > 0 ? `${approved} fix${approved > 1 ? "es" : ""} will be applied` : "No fixes selected — continuing with original code"}
          </p>
        </div>
      </div>
    </div>
  );
}
