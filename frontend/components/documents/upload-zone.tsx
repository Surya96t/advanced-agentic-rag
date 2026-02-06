"use client";

import { useCallback, useId } from "react";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
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
  }, [fileInputId]);  return (
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
        "border-2 border-dashed rounded-lg py-2 px-4 text-center transition-all outline-none",
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        isDragging && !disabled
          ? "border-primary bg-primary/5 scale-[1.02]"
          : "border-muted-foreground/25 hover:border-muted-foreground/50 hover:bg-accent/30",
        disabled && "opacity-50 cursor-not-allowed"
      )}
    >
      <Upload
        className={cn(
          "mx-auto h-5 w-5 mb-1 transition-colors",
          isDragging && !disabled ? "text-primary" : "text-muted-foreground"
        )}
      />
      <p className="text-xs font-medium mb-0.5">
        {isDragging && !disabled
          ? "Drop files here"
          : "Drop files or click"}
      </p>
      <p className="text-xs text-muted-foreground mb-2">
        .txt, .md, .pdf • Max 10MB
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
        <Button asChild disabled={disabled} size="sm">
          <span>Choose Files</span>
        </Button>
      </label>
    </div>
  );
}
