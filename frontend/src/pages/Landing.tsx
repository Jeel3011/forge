import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { TerminalDemo } from "../components/TerminalDemo";
import { StepCard } from "../components/StepCard";
import { FeatureRow } from "../components/FeatureRow";
import { useReveal } from "../hooks/useReveal";

// ─── Hero ────────────────────────────────────────────────────────────────────

function Hero() {
  const [url, setUrl] = useState("");
  const heroRef = useRef<HTMLElement>(null);
  const navigate = useNavigate();

  // Subtle parallax on scroll
  useEffect(() => {
    const onScroll = () => {
      if (!heroRef.current) return;
      const y = window.scrollY;
      heroRef.current.style.setProperty("--scroll-y", `${y * 0.25}px`);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <section
      ref={heroRef}
      className="relative min-h-screen flex flex-col items-center justify-center px-6 pt-24 pb-16 overflow-hidden"
    >
      {/* Grid background */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
          transform: "translateY(var(--scroll-y, 0))",
        }}
      />

      {/* Radial vignette */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-10%,rgba(255,255,255,0.04)_0%,transparent_70%)]" />
      <div className="absolute bottom-0 left-0 right-0 h-48 bg-gradient-to-t from-forge-bg to-transparent" />

      <div className="relative z-10 max-w-4xl w-full mx-auto text-center space-y-8">
        {/* Badge */}
        <div
          className="inline-flex items-center gap-2 text-xs font-medium tracking-wider uppercase text-forge-subtle border border-forge-border bg-forge-surface/60 backdrop-blur px-4 py-2 rounded-full"
          style={{ animation: "fadeUp 0.6s ease 0.1s both" }}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-forge-light animate-pulse" />
          AI/ML Deployment Platform
        </div>

        {/* Headline */}
        <h1
          className="text-5xl sm:text-6xl lg:text-7xl font-black text-forge-white leading-[1.05] tracking-tight"
          style={{ animation: "fadeUp 0.6s ease 0.2s both" }}
        >
          Deploy AI projects
          <br />
          <span className="text-forge-light/80">without the guesswork.</span>
        </h1>

        {/* Sub */}
        <p
          className="text-lg sm:text-xl text-forge-text max-w-2xl mx-auto leading-relaxed"
          style={{ animation: "fadeUp 0.6s ease 0.35s both" }}
        >
          Paste a GitHub URL. Forge reads your code, classifies your AI project type,
          diagnoses deployment issues, and generates infrastructure configs — in under 60 seconds.
        </p>

        {/* CTA input */}
        <div
          className="max-w-xl mx-auto space-y-3"
          style={{ animation: "fadeUp 0.6s ease 0.5s both" }}
          id="cta"
        >
          <div className="flex gap-2">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && navigate(url.trim() ? `/app?repo=${encodeURIComponent(url.trim())}` : "/app")}
              placeholder="github.com/you/your-ai-project"
              className="forge-input flex-1"
            />
            <button
              onClick={() => navigate(url.trim() ? `/app?repo=${encodeURIComponent(url.trim())}` : "/app")}
              className="forge-btn-primary whitespace-nowrap"
            >
              Scan free →
            </button>
          </div>
          <p className="text-xs text-forge-muted">No sign-up required · 3 free scans/month</p>
        </div>

        {/* Social proof numbers */}
        <div
          className="flex items-center justify-center gap-8 pt-4"
          style={{ animation: "fadeUp 0.6s ease 0.65s both" }}
        >
          {[
            { n: "8", label: "Project types detected" },
            { n: "10+", label: "Anti-patterns checked" },
            { n: "3", label: "Output tiers" },
          ].map(({ n, label }) => (
            <div key={label} className="text-center">
              <div className="text-2xl font-bold text-forge-white">{n}</div>
              <div className="text-xs text-forge-muted mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Terminal demo */}
      <div
        className="relative z-10 max-w-2xl w-full mx-auto mt-16"
        style={{ animation: "fadeUp 0.7s ease 0.8s both" }}
      >
        <TerminalDemo />
      </div>

      {/* Scroll indicator */}
      <div
        className="relative z-10 mt-16 flex flex-col items-center gap-2 text-forge-muted"
        style={{ animation: "fadeIn 1s ease 1.2s both" }}
      >
        <div className="w-px h-8 bg-gradient-to-b from-transparent to-forge-border" />
        <span className="text-xs tracking-widest uppercase">Scroll</span>
      </div>
    </section>
  );
}

// ─── Logos / trust bar ───────────────────────────────────────────────────────

function TrustBar() {
  const ref = useReveal<HTMLElement>(0.1);
  const labels = ["FastAPI", "LangChain", "PyTorch", "Celery", "Docker", "Kubernetes", "Terraform", "Redis"];

  return (
    <section ref={ref} className="reveal py-12 border-y border-forge-border">
      <div className="max-w-6xl mx-auto px-6">
        <p className="text-xs text-forge-muted text-center tracking-widest uppercase mb-8">
          Detects and configures
        </p>
        <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
          {labels.map((l) => (
            <span key={l} className="text-sm font-medium text-forge-muted hover:text-forge-text transition-colors duration-200 cursor-default">
              {l}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── How it works ────────────────────────────────────────────────────────────

const STEPS = [
  {
    number: "01",
    title: "Connect",
    description: "Paste any GitHub URL — public or private. Same UX as Vercel.",
    detail: "We fetch up to 30 key files: requirements.txt, Dockerfiles, entry points, and config files. Private repos need a GitHub token.",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 2C5.13 2 2 5.13 2 9c0 3.09 2 5.72 4.77 6.65.35.06.48-.15.48-.34v-1.2c-1.94.42-2.35-.94-2.35-.94-.32-.81-.78-1.02-.78-1.02-.64-.43.05-.43.05-.43.7.05 1.07.72 1.07.72.62 1.07 1.63.76 2.03.58.06-.45.24-.76.44-.93-1.55-.18-3.18-.78-3.18-3.46 0-.76.27-1.39.72-1.88-.07-.18-.31-.89.07-1.85 0 0 .59-.19 1.92.72A6.65 6.65 0 0 1 9 5.8c.59 0 1.19.08 1.75.23 1.33-.9 1.92-.72 1.92-.72.38.96.14 1.67.07 1.85.45.49.72 1.12.72 1.88 0 2.69-1.64 3.28-3.2 3.45.25.22.48.65.48 1.31v1.94c0 .19.13.4.48.34A7.003 7.003 0 0 0 16 9c0-3.87-3.13-7-7-7Z"/>
      </svg>
    ),
  },
  {
    number: "02",
    title: "Scan & Classify",
    description: "Two-layer analysis: deterministic dep parsing + Claude AI code reading.",
    detail: "Layer 1 parses package manifests with weighted signals. Layer 2 uses Claude Haiku to detect agent retry loops, streaming patterns, model loading anti-patterns, and more.",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="8" cy="8" r="5.5"/><path d="M12.5 12.5L16 16"/>
      </svg>
    ),
  },
  {
    number: "03",
    title: "Diagnose",
    description: "10+ deployment issue detectors fire against your specific project type.",
    detail: "Each issue comes with severity (critical / warning), a line reference, and a proposed diff. Nothing gets applied without your approval.",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 3v6M9 12v.5M3.5 15.5h11l-5.5-13-5.5 13Z"/>
      </svg>
    ),
  },
  {
    number: "04",
    title: "Fix",
    description: "Approve or skip each proposed fix. You stay in control.",
    detail: "Human-in-the-loop: every fix shows you a diff preview. Approve criticals, skip suggestions you don't need. Platform applies only approved changes.",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 9.5l4 4 8-8"/>
      </svg>
    ),
  },
  {
    number: "05",
    title: "Configure",
    description: "Answer 5–8 questions generated from what's in your code.",
    detail: "Not a generic form. Questions come from real code signals: if Celery is found with retry loops, we ask what max runtime you need. Answers directly set config values.",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 2a7 7 0 1 0 0 14A7 7 0 0 0 9 2Zm0 4v4m0 2v.5"/>
      </svg>
    ),
  },
  {
    number: "06",
    title: "Generate",
    description: "Download Docker Compose, Kubernetes, or Terraform configs.",
    detail: "Three output tiers tuned to your scale. Resource limits, health checks, worker counts, and timeouts are all set from your actual answers — not generic defaults.",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 2v10M5 8l4 4 4-4M3 16h12"/>
      </svg>
    ),
  },
];

function HowItWorks() {
  const headRef = useReveal<HTMLDivElement>();
  const gridRef = useReveal<HTMLDivElement>(0.05);

  return (
    <section id="how" className="py-28 px-6">
      <div className="max-w-6xl mx-auto space-y-16">
        <div ref={headRef} className="reveal text-center space-y-4">
          <span className="section-label">How it works</span>
          <h2 className="text-4xl lg:text-5xl font-bold text-forge-white">
            Six phases. Zero guesswork.
          </h2>
          <p className="text-forge-text text-lg max-w-xl mx-auto">
            From a GitHub URL to downloadable infrastructure configs in under a minute.
          </p>
        </div>

        <div ref={gridRef} className="reveal stagger-children grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {STEPS.map((step) => (
            <StepCard key={step.number} {...step} />
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Feature sections ────────────────────────────────────────────────────────

const DOCKER_EXAMPLE = `# docker-compose.yml — generated for AI Agent
services:
  api:
    build: .
    ports: ["8000:8000"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
    deploy:
      resources:
        limits: { memory: 2G }

  worker:
    build: .
    # --time-limit=1800 set because you said 30-min max runtime
    command: celery -A app.celery worker --concurrency=4 \\
             -Q agent_tasks --time-limit=1800 --soft-time-limit=1740

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 512mb

  qdrant:
    image: qdrant/qdrant:latest
    volumes: [qdrant_data:/qdrant/storage]`;

const DIAGNOSE_EXAMPLE = `[CRITICAL] Model loaded on every request
           main.py:47 — AutoTokenizer.from_pretrained(...)
           This causes 4–8s cold start per request under load.

  Fix: Move to FastAPI lifespan event (startup)
       Estimated impact: removes 6s latency from every request

  [Approve]  [Skip]  [Show diff]

─────────────────────────────────────────────────
[WARNING]  No health check endpoint detected
           Load balancers can't route around failures.

  Fix: Add GET /health → 200 OK
  [Approve]  [Skip]`;

function Features() {
  const r1 = useReveal<HTMLDivElement>();
  const r2 = useReveal<HTMLDivElement>();
  const r3 = useReveal<HTMLDivElement>();

  return (
    <section id="features" className="py-28 px-6 border-t border-forge-border">
      <div className="max-w-6xl mx-auto space-y-32">
        <div ref={r1} className="reveal">
          <FeatureRow
            eyebrow="Config generation"
            title="Infrastructure that knows what you built."
            description="Forge doesn't generate boilerplate. It reads your code, sees your Celery workers with retry loops, and sets --time-limit exactly to what you said your max task runtime is. Every value is derived from evidence."
            code={DOCKER_EXAMPLE}
          />
        </div>

        <div ref={r2} className="reveal">
          <FeatureRow
            reverse
            eyebrow="Human-in-the-loop fixes"
            title="You approve every change before it touches your code."
            description="Each issue has a severity, a line reference, and a diff preview. Critical issues are pre-approved but you can skip any. Nothing ships without your sign-off."
            code={DIAGNOSE_EXAMPLE}
          />
        </div>

        <div ref={r3} className="reveal">
          <ProjectTypesGrid />
        </div>
      </div>
    </section>
  );
}

const PROJECT_TYPES = [
  { name: "LLM Application",      deps: "openai · anthropic · langchain",           infra: "API + optional Redis" },
  { name: "AI Agent",             deps: "celery · redis · tool imports · retry",    infra: "API + worker pool + vector store" },
  { name: "Fine-tuning Pipeline", deps: "torch · transformers · peft · wandb",      infra: "GPU instance + blob storage" },
  { name: "Model Serving",        deps: "onnxruntime · bentoml · torch.predict",    infra: "GPU/CPU inference + autoscaler" },
  { name: "Data Pipeline",        deps: "airflow · prefect · dagster",              infra: "Scheduler + workers + DB" },
  { name: "Computer Vision",      deps: "opencv · PIL · torchvision · ultralytics", infra: "GPU + file storage + queue" },
  { name: "Multi-modal",          deps: "mixed of above",                           infra: "Detected and combined" },
  { name: "Classical ML",         deps: "sklearn · xgboost · lightgbm",             infra: "CPU API + caching layer" },
];

function ProjectTypesGrid() {
  return (
    <div className="space-y-8">
      <div className="text-center space-y-3">
        <span className="section-label">Coverage</span>
        <h3 className="text-3xl font-bold text-forge-white">8 AI project types. All handled.</h3>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {PROJECT_TYPES.map((pt) => (
          <div key={pt.name} className="forge-card gradient-border p-5 group hover:border-forge-line transition-all duration-200">
            <div className="font-semibold text-forge-white text-sm mb-2">{pt.name}</div>
            <div className="text-xs text-forge-muted font-mono mb-3 leading-relaxed">{pt.deps}</div>
            <div className="text-xs text-forge-subtle border-t border-forge-border pt-3">{pt.infra}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Comparison table ─────────────────────────────────────────────────────────

const COLS = ["Vercel", "Railway", "Modal", "SageMaker", "Forge"];
const ROWS = [
  { label: "Understands project type",     vals: [false, false, false, "~", true] },
  { label: "Detects AI-specific issues",   vals: [false, false, false, false, true] },
  { label: "Context-aware questions",      vals: [false, false, false, false, true] },
  { label: "GPU workloads",                vals: [false, "~", true, true, true] },
  { label: "Celery / background workers",  vals: [false, true, true, true, true] },
  { label: "Docker Compose output",        vals: [false, false, false, false, true] },
  { label: "Kubernetes output",            vals: [false, false, false, true, true] },
  { label: "Terraform output",             vals: [false, false, false, "~", true] },
];

function Comparison() {
  const ref = useReveal<HTMLElement>(0.05);

  const cell = (v: boolean | string) => {
    if (v === true) return <span className="text-forge-light font-medium">✓</span>;
    if (v === false) return <span className="text-forge-border">✗</span>;
    return <span className="text-forge-muted">~</span>;
  };

  return (
    <section ref={ref} className="reveal py-28 px-6 border-t border-forge-border">
      <div className="max-w-5xl mx-auto space-y-12">
        <div className="text-center space-y-4">
          <span className="section-label">Comparison</span>
          <h2 className="text-4xl font-bold text-forge-white">Nobody else reads your code.</h2>
          <p className="text-forge-text">The first three rows are the actual gap. No other platform owns them.</p>
        </div>

        <div className="forge-card gradient-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-forge-border">
                <th className="text-left p-4 text-forge-muted font-normal w-56">Feature</th>
                {COLS.map((c) => (
                  <th key={c} className={`p-4 text-center font-semibold ${c === "Forge" ? "text-forge-white" : "text-forge-subtle"}`}>
                    {c}
                    {c === "Forge" && (
                      <div className="text-xs text-forge-muted font-normal mt-0.5">this</div>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row, i) => (
                <tr key={row.label} className={`border-b border-forge-border last:border-0 ${i < 3 ? "bg-forge-surface/30" : ""}`}>
                  <td className="p-4 text-forge-text">{row.label}</td>
                  {row.vals.map((v, j) => (
                    <td key={j} className={`p-4 text-center ${COLS[j] === "Forge" ? "bg-forge-surface/20" : ""}`}>
                      {cell(v)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

// ─── Pricing ──────────────────────────────────────────────────────────────────

const PLANS = [
  {
    name: "Free",
    price: "$0",
    period: "",
    description: "For individuals trying it out.",
    features: [
      "3 scans per month",
      "Public repos only",
      "Docker Compose output",
      "Issue detection",
    ],
    cta: "Start free",
    highlight: false,
  },
  {
    name: "Pro",
    price: "$29",
    period: "/mo",
    description: "For engineers shipping AI products.",
    features: [
      "Unlimited scans",
      "Private repo access",
      "Kubernetes + Terraform output",
      "Deployment guides",
      "Prompt deployment features",
    ],
    cta: "Get Pro",
    highlight: true,
  },
  {
    name: "Team",
    price: "$99",
    period: "/mo",
    description: "For teams moving fast.",
    features: [
      "Everything in Pro",
      "Multiple team members",
      "Scan history & audit trail",
      "Priority support",
    ],
    cta: "Get Team",
    highlight: false,
  },
];

function Pricing() {
  const ref = useReveal<HTMLElement>(0.05);

  return (
    <section id="pricing" ref={ref} className="reveal py-28 px-6 border-t border-forge-border">
      <div className="max-w-5xl mx-auto space-y-14">
        <div className="text-center space-y-4">
          <span className="section-label">Pricing</span>
          <h2 className="text-4xl font-bold text-forge-white">Straightforward.</h2>
          <p className="text-forge-text">Start free. Upgrade when you need more.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-4">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={`forge-card gradient-border p-8 space-y-6 transition-all duration-200 ${
                plan.highlight
                  ? "border-forge-line bg-forge-card"
                  : "hover:border-forge-line"
              }`}
            >
              {plan.highlight && (
                <div className="inline-flex text-xs font-semibold tracking-wider uppercase text-black bg-forge-white px-3 py-1 rounded-full">
                  Popular
                </div>
              )}
              <div>
                <div className="text-forge-subtle text-sm mb-1">{plan.name}</div>
                <div className="flex items-baseline gap-0.5">
                  <span className="text-4xl font-black text-forge-white">{plan.price}</span>
                  <span className="text-forge-muted text-sm">{plan.period}</span>
                </div>
                <p className="text-forge-text text-sm mt-2">{plan.description}</p>
              </div>

              <ul className="space-y-3">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-center gap-2.5 text-sm text-forge-text">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="flex-shrink-0 text-forge-light">
                      <path d="M2.5 7.5l3 3 6-6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    {f}
                  </li>
                ))}
              </ul>

              <Link
                to="/app"
                className={`block text-center py-3 rounded-xl text-sm font-semibold transition-all duration-200 ${
                  plan.highlight
                    ? "bg-forge-white text-black hover:bg-forge-light"
                    : "border border-forge-border text-forge-text hover:border-forge-line hover:text-forge-light"
                }`}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Final CTA ────────────────────────────────────────────────────────────────

function FinalCTA() {
  const ref = useReveal<HTMLElement>();

  return (
    <section ref={ref} className="reveal py-28 px-6 border-t border-forge-border">
      <div className="max-w-2xl mx-auto text-center space-y-8">
        <h2 className="text-4xl lg:text-5xl font-black text-forge-white leading-tight">
          Start in 30 seconds.
          <br />
          <span className="text-forge-subtle">No account required.</span>
        </h2>
        <p className="text-forge-text text-lg">
          Paste a GitHub repo and see your project classified, diagnosed, and ready to deploy.
        </p>
        <Link to="/app" className="forge-btn-primary inline-block text-base px-8 py-4">
          Scan your repo →
        </Link>
      </div>
    </section>
  );
}

// ─── Footer ───────────────────────────────────────────────────────────────────

function Footer() {
  return (
    <footer className="border-t border-forge-border py-10 px-6">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-forge-muted">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-forge-white flex items-center justify-center">
            <svg width="10" height="10" viewBox="0 0 14 14" fill="none">
              <path d="M2 12L7 2L12 12M4 8.5H10" stroke="#080808" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span className="font-medium text-forge-subtle">Forge</span>
          <span>· AI/ML Deployment Platform</span>
        </div>
        <div className="flex items-center gap-6">
          <a href="#how" className="hover:text-forge-text transition-colors">How it works</a>
          <a href="#pricing" className="hover:text-forge-text transition-colors">Pricing</a>
          <a href="https://github.com/Jeel3011/forge" className="hover:text-forge-text transition-colors" target="_blank" rel="noreferrer">GitHub</a>
        </div>
        <span>© 2026 Forge</span>
      </div>
    </footer>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Landing() {
  return (
    <div className="bg-forge-bg">
      <Hero />
      <TrustBar />
      <HowItWorks />
      <Features />
      <Comparison />
      <Pricing />
      <FinalCTA />
      <Footer />
    </div>
  );
}
