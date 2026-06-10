import { ArrowRight } from "lucide-react";

interface FollowUpChipsProps {
  questions: string[];
  onSelect: (question: string) => void;
}

export function FollowUpChips({ questions, onSelect }: FollowUpChipsProps) {
  if (questions.length === 0) return null;

  return (
    <div className="space-y-3 animate-fade-in-up">
      <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
        Related Questions
      </h3>

      <div className="space-y-2">
        {questions.map((q, i) => (
          <button
            key={i}
            onClick={() => onSelect(q)}
            className="group flex items-center gap-3 w-full text-left px-4 py-3 rounded-lg border border-border bg-surface/50 text-sm text-foreground hover:border-primary/30 hover:bg-indigo-muted transition-all duration-200 animate-fade-in-up"
            style={{ animationDelay: `${i * 100}ms` }}
          >
            <span className="flex-1">{q}</span>
            <ArrowRight className="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all duration-200" />
          </button>
        ))}
      </div>
    </div>
  );
}
