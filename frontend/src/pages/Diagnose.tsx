import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AlertCircle, AlertTriangle, Info, ChevronDown, ChevronUp } from "lucide-react";
import type { ScanResult, Issue } from "../api/client";
import clsx from "clsx";

const SEVERITY_CONFIG = {
  critical: { icon: AlertCircle, color: "text-red-400", bg: "bg-red-950 border-red-800" },
  warning: { icon: AlertTriangle, color: "text-yellow-400", bg: "bg-yellow-950 border-yellow-800" },
  suggestion: { icon: Info, color: "text-blue-400", bg: "bg-blue-950 border-blue-800" },
};

const PROJECT_TYPE_LABELS: Record<string, string> = {
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

function IssueCard({ issue, approved, onToggle }: {
  issue: Issue & { id: string };
  approved: boolean;
  onToggle: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const cfg = SEVERITY_CONFIG[issue.severity];
  const Icon = cfg.icon;

  return (
    <div className={clsx("border rounded-lg p-4 space-y-3", cfg.bg)}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <Icon className={clsx("w-5 h-5 mt-0.5 flex-shrink-0", cfg.color)} />
          <div>
            <div className="font-semibold">{issue.title}</div>
            <div className="text-sm text-gray-400 mt-1">{issue.description}</div>
            {issue.file && (
              <div className="text-xs text-gray-500 mt-1">
                {issue.file}{issue.line ? `:${issue.line}` : ""}
              </div>
            )}
          </div>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <button
            onClick={onToggle}
            className={clsx(
              "px-3 py-1 rounded text-sm font-medium transition",
              approved
                ? "bg-green-600 text-white"
                : "bg-gray-700 text-gray-300 hover:bg-gray-600"
            )}
          >
            {approved ? "Approved" : "Approve"}
          </button>
          <button
            onClick={onToggle}
            className={clsx(
              "px-3 py-1 rounded text-sm font-medium transition",
              !approved
                ? "bg-gray-600 text-white"
                : "bg-gray-700 text-gray-300 hover:bg-gray-600"
            )}
          >
            Skip
          </button>
        </div>
      </div>

      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-200"
        >
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          Show proposed fix
        </button>
        {expanded && (
          <div className="mt-2 space-y-2">
            <p className="text-sm text-gray-300">{issue.proposed_fix}</p>
            {issue.diff_preview && (
              <pre className="bg-gray-900 rounded p-3 text-xs text-green-300 overflow-x-auto">
                {issue.diff_preview}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function Diagnose() {
  const { state } = useLocation() as { state: { scanResult: ScanResult } };
  const navigate = useNavigate();
  const scan = state?.scanResult;

  const issuesWithIds = scan?.issues.map((issue, i) => ({ ...issue, id: `issue_${i}` })) ?? [];
  const [approvals, setApprovals] = useState<Record<string, boolean>>(
    Object.fromEntries(issuesWithIds.filter(i => i.severity === "critical").map(i => [i.id, true]))
  );

  if (!scan) return <div className="text-white p-8">No scan data. Go back and scan a repo.</div>;

  const toggle = (id: string) => setApprovals(prev => ({ ...prev, [id]: !prev[id] }));

  const proceed = () => {
    navigate("/questionnaire", {
      state: {
        scanResult: scan,
        approvedFixes: Object.entries(approvals).map(([issue_id, approved]) => ({ issue_id, approved })),
      },
    });
  };

  const criticalCount = issuesWithIds.filter(i => i.severity === "critical").length;
  const warningCount = issuesWithIds.filter(i => i.severity === "warning").length;

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Diagnosis</h1>
        <p className="text-gray-400 mt-1 text-sm">{scan.repo_url}</p>
      </div>

      <div className="bg-gray-900 rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-lg font-semibold">{PROJECT_TYPE_LABELS[scan.project_type]}</div>
            <div className="text-sm text-gray-400">
              {Math.round(scan.confidence * 100)}% confidence
            </div>
          </div>
          <div className="flex gap-4 text-sm">
            {criticalCount > 0 && <span className="text-red-400">{criticalCount} critical</span>}
            {warningCount > 0 && <span className="text-yellow-400">{warningCount} warnings</span>}
          </div>
        </div>
        {scan.detected_characteristics.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {scan.detected_characteristics.map(c => (
              <span key={c} className="bg-gray-800 text-gray-300 text-xs px-2 py-1 rounded-full">{c}</span>
            ))}
          </div>
        )}
      </div>

      {issuesWithIds.length === 0 ? (
        <div className="bg-green-950 border border-green-800 rounded-lg p-4 text-green-300">
          No deployment issues detected. Your project looks good to go!
        </div>
      ) : (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Issues Found</h2>
          {issuesWithIds.map(issue => (
            <IssueCard
              key={issue.id}
              issue={issue}
              approved={!!approvals[issue.id]}
              onToggle={() => toggle(issue.id)}
            />
          ))}
        </div>
      )}

      <button
        onClick={proceed}
        className="w-full bg-orange-500 hover:bg-orange-400 text-white font-semibold py-3 rounded-lg text-lg transition"
      >
        Continue to Configuration →
      </button>
    </div>
  );
}
