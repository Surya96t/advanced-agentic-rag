"use client";

import { FileText, FileType, FileCode, Trash2 } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { formatDate, getFileExtension, type Document } from "@/lib/document-utils";

interface DocumentsTableProps {
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
 * Desktop table view for documents with bulk selection
 */
export function DocumentsTable({
  documents,
  selectedIds,
  onToggleSelect,
  onDelete,
  isLoading = false,
}: DocumentsTableProps) {
  if (isLoading) {
    return <DocumentsTableSkeleton />;
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
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12">
              <span className="sr-only">Select</span>
            </TableHead>
            <TableHead>Name</TableHead>
            <TableHead className="hidden sm:table-cell">Upload Date</TableHead>
            <TableHead className="hidden md:table-cell">Chunks</TableHead>
            <TableHead className="text-right w-20">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((doc) => {
            const { icon: Icon, color } = getFileIcon(doc.filename);
            const isSelected = selectedIds.has(doc.id);

            return (
              <TableRow
                key={doc.id}
                className={cn(
                  "hover:bg-muted/50 transition-colors",
                  isSelected && "bg-muted/50"
                )}
              >
                {/* Checkbox */}
                <TableCell>
                  <Checkbox
                    checked={isSelected}
                    onCheckedChange={() => onToggleSelect(doc.id)}
                    aria-label={`Select ${doc.filename}`}
                  />
                </TableCell>

                {/* File name with icon */}
                <TableCell className="font-medium">
                  <div className="flex items-center gap-2">
                    <Icon className={cn("h-4 w-4 shrink-0", color)} />
                    <span className="truncate">{doc.filename}</span>
                  </div>
                </TableCell>

                {/* Upload date */}
                <TableCell className="hidden sm:table-cell text-muted-foreground">
                  {formatDate(doc.upload_date)}
                </TableCell>

                {/* Chunk count */}
                <TableCell className="hidden md:table-cell">
                  {doc.chunk_count !== undefined ? (
                    <Badge variant="secondary" className="font-mono">
                      {doc.chunk_count}
                    </Badge>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>

                {/* Delete button */}
                <TableCell className="text-right">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onDelete(doc)}
                    className="hover:bg-destructive/10 hover:text-destructive"
                    aria-label={`Delete ${doc.filename}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

/**
 * Loading skeleton for table
 */
function DocumentsTableSkeleton() {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12"></TableHead>
            <TableHead>Name</TableHead>
            <TableHead className="hidden sm:table-cell">Upload Date</TableHead>
            <TableHead className="hidden md:table-cell">Chunks</TableHead>
            <TableHead className="text-right w-20">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {Array.from({ length: 5 }).map((_, i) => (
            <TableRow key={i}>
              <TableCell>
                <Skeleton className="h-4 w-4" />
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <Skeleton className="h-4 w-4" />
                  <Skeleton className="h-4 w-48" />
                </div>
              </TableCell>
              <TableCell className="hidden sm:table-cell">
                <Skeleton className="h-4 w-32" />
              </TableCell>
              <TableCell className="hidden md:table-cell">
                <Skeleton className="h-5 w-12" />
              </TableCell>
              <TableCell className="text-right">
                <Skeleton className="h-8 w-8 ml-auto" />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
