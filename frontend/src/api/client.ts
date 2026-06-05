import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "/api",
  timeout: 60000,
});

export interface ScanResult {
  repo_url: string;
  project_type: string;
  confidence: number;
  l1_confidence: number;
  ai_reasoning: string;
  detected_dependencies: string[];
  detected_characteristics: string[];
  files_scanned: number;
  issues: Issue[];
}

export interface Issue {
  severity: "critical" | "warning" | "suggestion";
  title: string;
  description: string;
  file?: string;
  line?: number;
  proposed_fix: string;
  diff_preview?: string;
}

export interface Question {
  id: string;
  text: string;
  context: string;
  options: { value: string; label: string }[];
  allows_custom: boolean;
}

export interface GeneratedConfig {
  tier: string;
  files: Record<string, string>;
  deployment_guide: string;
}

export const scanRepo = (repoUrl: string) =>
  api.post<ScanResult>("/scan", { repo_url: repoUrl }).then((r) => r.data);

export const getQuestions = (scanResult: ScanResult) =>
  api.post<Question[]>("/questions", scanResult).then((r) => r.data);

export const generateConfigs = (payload: {
  scan_result: ScanResult;
  approved_fixes: { issue_id: string; approved: boolean }[];
  questionnaire_answers: Record<string, string>;
  output_tier: string;
}) => api.post<GeneratedConfig>("/generate", payload).then((r) => r.data);
