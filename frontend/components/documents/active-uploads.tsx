"use client";

import { FileText, X, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import { formatFileSize } from "@/lib/document-utils";

export type UploadStatus = "pending" | "uploading" | "success" | "error";

export interface UploadingFile {
  fileId: string;
  file: File;
  progress: number | undefined; // undefined = indeterminate/spinner state during upload
  status: UploadStatus;
  error?: string;
}

interface ActiveUploadsProps {
  uploads: UploadingFile[];
  onRemove: (fileId: string) => void;
  onClearCompleted: () => void;
}

/**
 * Get status icon and color based on upload status
 */
function getStatusConfig(status: UploadStatus) {
  switch (status) {
    case "pending":
      return {
        icon: Loader2,
        color: "text-muted-foreground",
        label: "Waiting...",
        animate: "animate-spin",
      };
    case "uploading":
      return {
        icon: Loader2,
        color: "text-blue-500",
        label: "Uploading...",
        animate: "animate-spin",
      };
    case "success":
      return {
        icon: CheckCircle2,
        color: "text-green-500",
        label: "Complete",
        animate: "",
      };
    case "error":
      return {
        icon: AlertCircle,
        color: "text-destructive",
        label: "Failed",
        animate: "",
      };
  }
}

/**
 * Display active file uploads with progress tracking
 */
export function ActiveUploads({ uploads, onRemove, onClearCompleted }: ActiveUploadsProps) {
  if (uploads.length === 0) return null;

  const hasCompleted = uploads.some((upload) => upload.status === "success");

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Active Uploads ({uploads.length})</CardTitle>
          {hasCompleted && (
            <Button 
              variant="outline" 
              size="sm" 
              onClick={onClearCompleted}
              aria-label="Clear completed uploads"
            >
              Clear Completed
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {uploads.map((upload) => {
            const statusConfig = getStatusConfig(upload.status);
            const StatusIcon = statusConfig.icon;

            return (
              <div
                key={upload.fileId}
                className={cn(
                  "flex items-start gap-3 p-3 border rounded-lg transition-colors",
                  upload.status === "success" && "bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-900",
                  upload.status === "error" && "bg-destructive/5 border-destructive/20"
                )}
              >
                <FileText className="h-5 w-5 text-muted-foreground mt-0.5 shrink-0" />
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-medium truncate pr-2">{upload.file.name}</p>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 shrink-0"
                      onClick={() => onRemove(upload.fileId)}
                      aria-label={`Remove ${upload.file.name}`}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>

                  {/* Progress bar or spinner for indeterminate state */}
                  {upload.status !== "error" && (
                    <>
                      {upload.progress !== undefined ? (
                        <Progress
                          value={upload.progress}
                          className={cn(
                            "h-2 mb-1",
                            upload.status === "success" && "*:bg-green-500"
                          )}
                        />
                      ) : (
                        // Indeterminate state during actual upload
                        <div className="h-2 mb-1 bg-muted rounded-full overflow-hidden">
                          <div className="h-full bg-primary animate-pulse" style={{ width: "100%" }} />
                        </div>
                      )}
                    </>
                  )}

                  {/* Status and file size */}
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5">
                      <StatusIcon
                        className={cn("h-3.5 w-3.5", statusConfig.color, statusConfig.animate)}
                      />
                      <span className={statusConfig.color}>
                        {upload.status === "uploading" && (upload.progress !== undefined ? `${upload.progress}%` : "Uploading...")}
                        {upload.status === "pending" && statusConfig.label}
                        {upload.status === "success" && statusConfig.label}
                        {upload.status === "error" && upload.error}
                      </span>
                    </div>
                    <span className="text-muted-foreground">
                      {formatFileSize(upload.file.size)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
