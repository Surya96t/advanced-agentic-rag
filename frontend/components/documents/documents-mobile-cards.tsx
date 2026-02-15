"use client";

import { FileText, FileType, FileCode, Trash2 } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { formatDate, getFileExtension, type Document } from "@/lib/document-utils";

interface DocumentsMobileCardsProps {
  documents: Document[];
  selectedIds: Set<string>;
  onToggleSelect: (id: string) => void;
  onDelete: (doc: Document) => void;
  isLoading?: boolean;
}

/**
 * Get file icon and color based on extension
 */
function getFileIcon(filename: string) {
  const ext = getFileExtension(filename);
  
  switch (ext) {
    case "pdf":
      return { icon: FileType, color: "text-red-500" };
    case "md":
      return { icon: FileCode, color: "text-blue-500" };
    case "txt":
      return { icon: FileText, color: "text-gray-500" };
    default:
      return { icon: FileText, color: "text-muted-foreground" };
  }
}

/**
 * Mobile card view for documents (responsive alternative to table)
 */
export function DocumentsMobileCards({
  documents,
  selectedIds,
  onToggleSelect,
  onDelete,
  isLoading = false,
}: DocumentsMobileCardsProps) {
  if (isLoading) {
    return <DocumentsCardsSkeleton />;
  }

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center border rounded-lg">
        <FileText className="h-12 w-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">No documents found</h3>
        <p className="text-muted-foreground">
          Upload your first document to get started
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {documents.map((doc) => {
        const { icon: Icon, color } = getFileIcon(doc.filename);
        const isSelected = selectedIds.has(doc.id);

        return (
          <Card
            key={doc.id}
            className={cn(
              "p-4 transition-colors",
              isSelected && "bg-muted/50 border-primary"
            )}
          >
            <div className="flex items-start gap-3">
              {/* Checkbox */}
              <Checkbox
                checked={isSelected}
                onCheckedChange={() => onToggleSelect(doc.id)}
                aria-label={`Select ${doc.filename}`}
                className="mt-1"
              />

              {/* File icon */}
              <Icon className={cn("h-5 w-5 shrink-0 mt-0.5", color)} />

              {/* Content */}
              <div className="flex-1 min-w-0">
                <h3 className="font-medium text-sm truncate mb-1">{doc.filename}</h3>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>{formatDate(doc.created_at)}</span>
                  {doc.chunk_count !== undefined && (
                    <>
                      <span>•</span>
                      <Badge variant="secondary" className="font-mono text-xs px-1.5 py-0">
                        {doc.chunk_count} chunks
                      </Badge>
                    </>
                  )}
                </div>
              </div>

              {/* Delete button */}
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onDelete(doc)}
                className="shrink-0 hover:bg-destructive/10 hover:text-destructive"
                aria-label={`Delete ${doc.filename}`}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </Card>
        );
      })}
    </div>
  );
}

/**
 * Loading skeleton for mobile cards
 */
function DocumentsCardsSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <Card key={i} className="p-4">
          <div className="flex items-start gap-3">
            <Skeleton className="h-4 w-4 mt-1" />
            <Skeleton className="h-5 w-5 mt-0.5" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
            <Skeleton className="h-8 w-8" />
          </div>
        </Card>
      ))}
    </div>
  );
}
