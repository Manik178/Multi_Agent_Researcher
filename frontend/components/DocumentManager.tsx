"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  uploadDocument,
  getDocuments,
  deleteDocument,
} from "@/lib/api";
import {
  Upload,
  FileText,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";

interface UploadState {
  file: File;
  status: "uploading" | "done" | "error";
  message?: string;
  chunks?: number;
}

export function DocumentManager() {
  const [documents, setDocuments] = useState<string[]>([]);
  const [uploads, setUploads] = useState<UploadState[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [deletingFile, setDeletingFile] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch documents on mount
  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    setIsLoading(true);
    try {
      const result = await getDocuments();
      setDocuments(result.documents);
    } catch {
      // Ignore errors
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpload = useCallback(async (files: FileList | File[]) => {
    const fileArray = Array.from(files);
    const allowed = [".pdf", ".txt", ".md"];

    for (const file of fileArray) {
      const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
      if (!allowed.includes(ext)) continue;

      setUploads((prev) => [
        ...prev,
        { file, status: "uploading" },
      ]);

      try {
        const result = await uploadDocument(file);
        setUploads((prev) =>
          prev.map((u) =>
            u.file === file
              ? {
                  ...u,
                  status: "done",
                  message: `${result.chunks_stored} chunks stored`,
                  chunks: result.chunks_stored,
                }
              : u,
          ),
        );
        // Refresh document list
        const updated = await getDocuments();
        setDocuments(updated.documents);
      } catch (err) {
        setUploads((prev) =>
          prev.map((u) =>
            u.file === file
              ? {
                  ...u,
                  status: "error",
                  message:
                    err instanceof Error ? err.message : "Upload failed",
                }
              : u,
          ),
        );
      }
    }
  }, []);

  const handleDelete = async (filename: string) => {
    setDeletingFile(filename);
    try {
      await deleteDocument(filename);
      setDocuments((prev) => prev.filter((d) => d !== filename));
    } catch {
      // Ignore
    } finally {
      setDeletingFile(null);
    }
  };

  const clearUpload = (index: number) => {
    setUploads((prev) => prev.filter((_, i) => i !== index));
  };

  // Drag & drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      handleUpload(e.dataTransfer.files);
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`flex flex-col items-center justify-center gap-3 p-8 rounded-xl border-2 border-dashed cursor-pointer transition-all duration-200 ${
          isDragOver
            ? "border-primary bg-indigo-muted"
            : "border-border bg-surface/30 hover:border-muted-foreground/30 hover:bg-surface/50"
        }`}
      >
        <div
          className={`flex items-center justify-center w-12 h-12 rounded-xl transition-colors ${
            isDragOver ? "bg-primary/20" : "bg-surface"
          }`}
        >
          <Upload
            className={`w-5 h-5 transition-colors ${
              isDragOver ? "text-primary" : "text-muted-foreground"
            }`}
          />
        </div>
        <div className="text-center">
          <p className="text-sm font-medium text-foreground">
            Drop files here or click to browse
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Supports PDF, TXT, and Markdown files
          </p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files) handleUpload(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {/* Upload progress */}
      {uploads.length > 0 && (
        <div className="space-y-2">
          {uploads.map((upload, i) => (
            <div
              key={`${upload.file.name}-${i}`}
              className="flex items-center gap-3 px-4 py-3 rounded-lg border border-border bg-surface/50 animate-fade-in-up"
            >
              {upload.status === "uploading" && (
                <Loader2 className="w-4 h-4 text-primary animate-spin shrink-0" />
              )}
              {upload.status === "done" && (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              )}
              {upload.status === "error" && (
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
              )}

              <div className="flex-1 min-w-0">
                <p className="text-sm text-foreground truncate">
                  {upload.file.name}
                </p>
                {upload.message && (
                  <p
                    className={`text-xs ${
                      upload.status === "error"
                        ? "text-red-400"
                        : "text-muted-foreground"
                    }`}
                  >
                    {upload.message}
                  </p>
                )}
              </div>

              {upload.status !== "uploading" && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    clearUpload(i);
                  }}
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Explainer */}
      <div className="flex items-start gap-2.5 px-4 py-3 rounded-lg bg-primary/5 border border-primary/10">
        <FileText className="w-4 h-4 text-primary shrink-0 mt-0.5" />
        <p className="text-xs text-muted-foreground leading-relaxed">
          Uploaded documents are searched before the web. The research agents
          will prioritize your private documents when answering questions.
        </p>
      </div>

      {/* Document list */}
      <div className="space-y-2">
        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Uploaded Documents ({documents.length})
        </h3>

        {isLoading ? (
          <div className="flex items-center gap-2 py-8 justify-center text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading documents…
          </div>
        ) : documents.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-8 text-center">
            <FileText className="w-8 h-8 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              No documents uploaded yet
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {documents.map((doc) => (
              <div
                key={doc}
                className="flex items-center gap-3 px-4 py-3 rounded-lg border border-border bg-surface/50 group"
              >
                <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
                <span className="flex-1 text-sm text-foreground truncate">
                  {doc}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDelete(doc)}
                  disabled={deletingFile === doc}
                  className="opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 p-0 text-muted-foreground hover:text-red-400"
                >
                  {deletingFile === doc ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="w-3.5 h-3.5" />
                  )}
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
