"use client";

import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Document } from "@/lib/document-utils";

interface BulkDeleteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedDocuments: Document[];
  onConfirm: () => void;
  isDeleting?: boolean;
}

/**
 * Confirmation dialog for bulk document deletion
 */
export function BulkDeleteDialog({
  open,
  onOpenChange,
  selectedDocuments,
  onConfirm,
  isDeleting = false,
}: BulkDeleteDialogProps) {
  const count = selectedDocuments.length;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete {count} Document{count !== 1 ? 's' : ''}?</DialogTitle>
          <DialogDescription>
            This action cannot be undone. The following documents and their chunks will be
            permanently deleted.
          </DialogDescription>
        </DialogHeader>

        {/* List of documents to delete */}
        <div className="max-h-60 overflow-y-auto border rounded-lg">
          {selectedDocuments.map((doc) => (
            <div
              key={doc.id}
              className="flex items-start gap-3 p-3 border-b last:border-b-0 bg-muted/30"
            >
              <AlertCircle className="h-5 w-5 text-destructive mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{doc.filename}</p>
                <p className="text-xs text-muted-foreground">
                  {doc.chunk_count !== undefined ? `${doc.chunk_count} chunks` : 'No chunks'}
                </p>
              </div>
            </div>
          ))}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isDeleting}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={isDeleting}
          >
            {isDeleting ? "Deleting..." : `Delete ${count} Document${count !== 1 ? 's' : ''}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
