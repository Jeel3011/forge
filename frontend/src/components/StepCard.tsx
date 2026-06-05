interface StepCardProps {
  number: string;
  title: string;
  description: string;
  detail: string;
  icon: React.ReactNode;
}

export function StepCard({ number, title, description, detail, icon }: StepCardProps) {
  return (
    <div className="group relative forge-card gradient-border p-8 hover:border-forge-line transition-all duration-300 hover:-translate-y-1">
      <div className="flex items-start justify-between mb-6">
        <div className="w-11 h-11 rounded-xl bg-forge-surface border border-forge-border flex items-center justify-center text-forge-text group-hover:border-forge-line transition-colors duration-300">
          {icon}
        </div>
        <span className="text-4xl font-black text-forge-border group-hover:text-forge-line transition-colors duration-300 select-none tabular-nums">
          {number}
        </span>
      </div>
      <h3 className="text-lg font-semibold text-forge-white mb-2">{title}</h3>
      <p className="text-sm text-forge-text leading-relaxed mb-4">{description}</p>
      <p className="text-xs text-forge-muted leading-relaxed border-t border-forge-border pt-4">{detail}</p>
    </div>
  );
}
