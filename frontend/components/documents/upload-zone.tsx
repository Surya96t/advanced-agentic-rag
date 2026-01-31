"use client";

import { useState, useCallback, useId } from "react";
import { Upload, ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface UploadZoneProps {
  onFilesSelected: (files: File[]) => void;
  isDragging: boolean;
  onDragStateChange: (isDragging: boolean) => void;
  disabled?: boolean;
}

/**
 * Collapsible file upload zone with drag & drop support
 */
export function UploadZone({
  onFilesSelected,
  isDragging,
  onDragStateChange,
  disabled = false,
}: UploadZoneProps) {
  const fileInputId = useId();
  const [isExpanded, setIsExpanded] = useState(true);

  const handleDragEnter = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) {
        onDragStateChange(true);
      }
    },
    [disabled, onDragStateChange]
  );

  const handleDragLeave = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      onDragStateChange(false);
    },
    [onDragStateChange]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      onDragStateChange(false);

      if (disabled) return;

      const allowedExtensions = ['.txt', '.md', '.pdf'];
      const files = Array.from(e.dataTransfer.files);
      const validFiles = files.filter((file) => 
        allowedExtensions.some((ext) => file.name.toLowerCase().endsWith(ext))
      );
      if (validFiles.length > 0) {
        onFilesSelected(validFiles);
      }
    },
    [disabled, onFilesSelected, onDragStateChange]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && !disabled) {
        const files = Array.from(e.target.files);
        onFilesSelected(files);
        // Reset input so the same file can be selected again
        e.target.value = '';
      }
    },
    [disabled, onFilesSelected]
  );

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      document.getElementById(fileInputId)?.click();
    }
  }, [fileInputId]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <CardTitle>Upload Documents</CardTitle>
            <CardDescription>
              Drop files here or click to browse (.txt, .md, .pdf • Max 10MB)
            </CardDescription>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            aria-label={isExpanded ? "Collapse upload zone" : "Expand upload zone"}
          >
            {isExpanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent>
          <div
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onKeyDown={handleKeyDown}
            tabIndex={disabled ? -1 : 0}
            role="button"
            aria-label="Upload files"
            className={cn(
              "border-2 border-dashed rounded-lg p-12 text-center transition-all outline-none",
              "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              isDragging && !disabled
                ? "border-primary bg-primary/5 scale-[1.02]"
                : "border-muted-foreground/25 hover:border-muted-foreground/50",
              disabled && "opacity-50 cursor-not-allowed"
            )}
          >
            <Upload
              className={cn(
                "mx-auto h-12 w-12 mb-4 transition-colors",
                isDragging && !disabled ? "text-primary" : "text-muted-foreground"
              )}
            />
            <p className="text-lg font-medium mb-2">
              {isDragging && !disabled
                ? "Drop files here"
                : "Drag and drop files here, or click to browse"}
            </p>
            <p className="text-sm text-muted-foreground mb-4">
              Supported formats: Text (.txt), Markdown (.md), PDF (.pdf)
            </p>
            <input
              type="file"
              multiple
              accept=".txt,.md,.pdf"
              onChange={handleFileInput}
              className="hidden"
              id={fileInputId}
              disabled={disabled}
            />
            <label htmlFor={fileInputId}>
              <Button asChild disabled={disabled}>
                <span>Choose Files</span>
              </Button>
            </label>
          </div>
        </CardContent>
      )}
    </Card>
  );
}
