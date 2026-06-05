interface FeatureRowProps {
  eyebrow: string;
  title: string;
  description: string;
  code: string;
  reverse?: boolean;
}

export function FeatureRow({ eyebrow, title, description, code, reverse }: FeatureRowProps) {
  return (
    <div className={`flex flex-col ${reverse ? "lg:flex-row-reverse" : "lg:flex-row"} gap-12 lg:gap-20 items-center`}>
      <div className="flex-1 space-y-5">
        <span className="section-label">{eyebrow}</span>
        <h3 className="text-3xl font-bold text-forge-white leading-tight">{title}</h3>
        <p className="text-forge-text leading-relaxed text-lg">{description}</p>
      </div>
      <div className="flex-1 w-full">
        <div className="forge-card gradient-border overflow-hidden">
          <div className="flex items-center gap-2 px-5 py-3.5 border-b border-forge-border bg-forge-surface">
            <div className="w-2.5 h-2.5 rounded-full bg-forge-muted" />
            <div className="w-2.5 h-2.5 rounded-full bg-forge-muted" />
            <div className="w-2.5 h-2.5 rounded-full bg-forge-muted" />
            <span className="ml-2 text-xs text-forge-muted font-mono">output</span>
          </div>
          <pre className="p-5 text-xs font-mono text-forge-text leading-6 overflow-x-auto">
            <code>{code}</code>
          </pre>
        </div>
      </div>
    </div>
  );
}
