import { DocumentManager } from "@/components/DocumentManager";
import { FileText } from "lucide-react";

export default function DocumentsPage() {
  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary/10 border border-primary/20">
          <FileText className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-foreground">Documents</h1>
          <p className="text-sm text-muted-foreground">
            Upload documents for the agents to reference during research.
          </p>
        </div>
      </div>

      <DocumentManager />
    </div>
  );
}
