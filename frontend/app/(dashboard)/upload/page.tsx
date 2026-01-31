"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Upload, FileText, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";

// Generate a simple unique ID
const generateId = () => `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

interface UploadingFile {
  fileId: string;
  file: File;
  progress: number;
  status: "pending" | "uploading" | "success" | "error";
  error?: string;
}

export default function UploadPage() {
  const router = useRouter();
  const [isDragging, setIsDragging] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const uploadFile = async (file: File, fileId: string) => {
    try {
      // Update status to uploading
      setUploadingFiles((prev) =>
        prev.map((f) => (f.fileId === fileId ? { ...f, status: "uploading" as const } : f))
      );

      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("/api/documents", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Upload failed");
      }

      // Simulate progress (since we don't have real progress tracking)
      for (let progress = 0; progress <= 100; progress += 20) {
        setUploadingFiles((prev) =>
          prev.map((f) => (f.fileId === fileId ? { ...f, progress } : f))
        );
        await new Promise((resolve) => setTimeout(resolve, 100));
      }

      // Mark as success
      setUploadingFiles((prev) =>
        prev.map((f) =>
          f.fileId === fileId ? { ...f, status: "success" as const, progress: 100 } : f
        )
      );

      toast.success(`${file.name} uploaded successfully`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Upload failed";
      setUploadingFiles((prev) =>
        prev.map((f) =>
          f.fileId === fileId ? { ...f, status: "error" as const, error: errorMessage } : f
        )
      );
      toast.error(`Failed to upload ${file.name}: ${errorMessage}`);
    }
  };

  const handleFiles = useCallback(async (files: File[]) => {
    const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

    // Validate file types (txt, md, pdf)
    const validFiles = files.filter((file) => {
      const ext = file.name.split(".").pop()?.toLowerCase();
      const validExt = ext === "txt" || ext === "md" || ext === "pdf";
      const validSize = file.size <= MAX_FILE_SIZE;
      return validExt && validSize;
    });

    const rejectedCount = files.length - validFiles.length;
    if (rejectedCount > 0) {
      toast.error(
        "Some files were rejected. Only .txt, .md, and .pdf files under 10MB are allowed."
      );
    }

    if (validFiles.length === 0) return;

    // Initialize uploading state with unique IDs
    const newUploadingFiles: UploadingFile[] = validFiles.map((file) => ({
      fileId: generateId(),
      file,
      progress: 0,
      status: "pending",
    }));

    setUploadingFiles((prev) => [...prev, ...newUploadingFiles]);

    // Upload each file using its unique ID
    for (const uploadingFile of newUploadingFiles) {
      await uploadFile(uploadingFile.file, uploadingFile.fileId);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  }, [handleFiles]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      handleFiles(files);
    }
  }, [handleFiles]);

  const removeFile = (fileId: string) => {
    setUploadingFiles((prev) => prev.filter((f) => f.fileId !== fileId));
  };

  const clearCompleted = () => {
    setUploadingFiles((prev) => prev.filter((f) => f.status !== "success"));
  };

  const viewDocuments = () => {
    router.push("/documents");
  };

  return (
    <div className="container mx-auto py-8 px-4 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Upload Documents</h1>
        <p className="text-muted-foreground">
          Upload API documentation files (.txt, .md, .pdf) to build your knowledge base
        </p>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Drop files here</CardTitle>
          <CardDescription>
            Supported formats: Text (.txt), Markdown (.md), PDF (.pdf)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            className={`
              border-2 border-dashed rounded-lg p-12 text-center transition-colors
              ${
                isDragging
                  ? "border-primary bg-primary/5"
                  : "border-muted-foreground/25 hover:border-muted-foreground/50"
              }
            `}
          >
            <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-medium mb-2">
              Drag and drop files here, or click to browse
            </p>
            <p className="text-sm text-muted-foreground mb-4">
              Maximum file size: 10MB per file
            </p>
            <input
              type="file"
              multiple
              accept=".txt,.md,.pdf"
              onChange={handleFileInput}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload">
              <Button asChild>
                <span>Choose Files</span>
              </Button>
            </label>
          </div>
        </CardContent>
      </Card>

      {uploadingFiles.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Upload Progress</CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={clearCompleted}>
                  Clear Completed
                </Button>
                <Button variant="default" size="sm" onClick={viewDocuments}>
                  View Documents
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {uploadingFiles.map((upload) => (
                <div key={upload.fileId} className="flex items-start gap-3 p-3 border rounded-lg">
                  <FileText className="h-5 w-5 text-muted-foreground mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-medium truncate">{upload.file.name}</p>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => removeFile(upload.fileId)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                    <div className="space-y-1">
                      <Progress value={upload.progress} className="h-2" />
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>
                          {upload.status === "pending" && "Waiting..."}
                          {upload.status === "uploading" && `Uploading... ${upload.progress}%`}
                          {upload.status === "success" && "✓ Complete"}
                          {upload.status === "error" && `✗ ${upload.error}`}
                        </span>
                        <span>{(upload.file.size / 1024).toFixed(1)} KB</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
