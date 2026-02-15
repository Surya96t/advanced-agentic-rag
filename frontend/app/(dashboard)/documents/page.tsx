"use client";

import { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { toast } from "sonner";
import { UploadZone } from "@/components/documents/upload-zone";
import { ActiveUploads, type UploadingFile } from "@/components/documents/active-uploads";
import { DocumentsTable } from "@/components/documents/documents-table";
import { DocumentsMobileCards } from "@/components/documents/documents-mobile-cards";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AlertCircle } from "lucide-react";
import {
  type Document,
  type SortField,
  type SortOrder,
  validateFile,
  generateFileId,
  searchDocuments,
  sortDocuments,
  formatDate,
} from "@/lib/document-utils";

// Lazy-load bulk delete dialog (only used when deleting multiple documents)
const BulkDeleteDialog = dynamic(
  () => import("@/components/documents/bulk-delete-dialog").then(mod => ({ default: mod.BulkDeleteDialog })),
  { ssr: false }
);

export default function DocumentsPage() {
  // Documents state
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  // Upload state
  const [isDragging, setIsDragging] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);

  // Selection state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Search/Sort state (keep for filtering even without toolbar)
  const [searchQuery] = useState("");
  const [sortBy] = useState<SortField>("date");
  const [sortOrder] = useState<SortOrder>("desc");

  // Dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);

  // Fetch documents on mount
  useEffect(() => {
    fetchDocuments();
  }, []);

  /**
   * Fetch documents from API
   */
  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const response = await fetch("/api/documents");

      if (!response.ok) {
        throw new Error("Failed to fetch documents");
      }

      const data = await response.json();
      setDocuments(data.documents || []);
    } catch (error) {
      console.error("Error fetching documents:", error);
      toast.error("Failed to load documents");
    } finally {
      setLoading(false);
    }
  };

  /**
   * Upload a single file
   */
  const uploadFile = useCallback(async (file: File, fileId: string) => {
    try {
      // Update status to uploading (indeterminate state - no fake progress)
      setUploadingFiles((prev) =>
        prev.map((f) => (f.fileId === fileId ? { ...f, status: "uploading", progress: undefined } : f))
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

      // Mark as success (set progress to 100 for completed state)
      setUploadingFiles((prev) =>
        prev.map((f) =>
          f.fileId === fileId ? { ...f, status: "success", progress: 100 } : f
        )
      );

      toast.success(`${file.name} uploaded successfully`);

      // Refresh documents list
      await fetchDocuments();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Upload failed";
      setUploadingFiles((prev) =>
        prev.map((f) =>
          f.fileId === fileId ? { ...f, status: "error", error: errorMessage } : f
        )
      );
      toast.error(`Failed to upload ${file.name}`, {
        description: errorMessage,
      });
    }
  }, []);

  /**
   * Handle file selection from upload zone
   */
  const handleFilesSelected = useCallback(async (files: File[]) => {
    // Validate and filter files
    const validatedFiles: UploadingFile[] = [];
    const rejectedFiles: string[] = [];

    files.forEach((file) => {
      const validation = validateFile(file);
      if (validation.valid) {
        validatedFiles.push({
          fileId: generateFileId(),
          file,
          progress: 0,
          status: "pending",
        });
      } else {
        rejectedFiles.push(`${file.name}: ${validation.error}`);
      }
    });

    // Show rejection errors
    if (rejectedFiles.length > 0) {
      toast.error(`${rejectedFiles.length} file(s) rejected`, {
        description: rejectedFiles[0],
      });
    }

    if (validatedFiles.length === 0) return;

    // Add to uploading state
    setUploadingFiles((prev) => [...prev, ...validatedFiles]);

    // Upload each file
    for (const uploadingFile of validatedFiles) {
      await uploadFile(uploadingFile.file, uploadingFile.fileId);
    }
  }, [uploadFile]);

  /**
   * Remove file from upload list
   */
  const handleRemoveUpload = (fileId: string) => {
    setUploadingFiles((prev) => prev.filter((f) => f.fileId !== fileId));
  };

  /**
   * Clear completed uploads
   */
  const handleClearCompleted = () => {
    setUploadingFiles((prev) => prev.filter((f) => f.status !== "success"));
  };

  /**
   * Toggle document selection
   */
  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  /**
   * Open single delete dialog
   */
  const handleDeleteClick = (doc: Document) => {
    setDocumentToDelete(doc);
    setDeleteDialogOpen(true);
  };

  /**
   * Confirm single delete
   */
  const handleDeleteConfirm = async () => {
    if (!documentToDelete) return;

    try {
      setDeleting(true);
      const response = await fetch(`/api/documents/${documentToDelete.id}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to delete document");
      }

      toast.success(`${documentToDelete.filename} deleted successfully`);
      setDocuments((prev) => prev.filter((doc) => doc.id !== documentToDelete.id));
      setDeleteDialogOpen(false);
      setDocumentToDelete(null);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to delete";
      toast.error(errorMessage);
    } finally {
      setDeleting(false);
    }
  };

  /**
   * Open bulk delete dialog
   */
  const handleBulkDeleteClick = () => {
    setBulkDeleteDialogOpen(true);
  };

  /**
   * Confirm bulk delete
   */
  const handleBulkDeleteConfirm = async () => {
    const selectedDocuments = documents.filter((doc) => selectedIds.has(doc.id));
    
    try {
      setBulkDeleting(true);

      // Delete all selected documents with proper error checking
      const deletePromises = selectedDocuments.map((doc) =>
        fetch(`/api/documents/${doc.id}`, { method: "DELETE" })
          .then(async (res) => {
            if (!res.ok) {
              const error = await res.json().catch(() => ({ error: "Delete failed" }));
              throw new Error(error.error || `Failed to delete ${doc.filename}`);
            }
            return { success: true, docId: doc.id };
          })
      );

      const results = await Promise.allSettled(deletePromises);

      // Separate successful and failed deletions
      const successful = results
        .filter((r): r is PromiseFulfilledResult<{ success: true; docId: string }> => 
          r.status === "fulfilled"
        )
        .map((r) => r.value.docId);

      const failures = results.filter((r) => r.status === "rejected");

      // Remove only successfully deleted documents from state
      if (successful.length > 0) {
        setDocuments((prev) => prev.filter((doc) => !successful.includes(doc.id)));
        setSelectedIds((prev) => {
          const next = new Set(prev);
          successful.forEach((id) => next.delete(id));
          return next;
        });
      }

      // Show appropriate feedback
      if (failures.length === 0) {
        toast.success(`${successful.length} document(s) deleted successfully`);
        setBulkDeleteDialogOpen(false);
      } else if (successful.length > 0) {
        toast.warning(
          `${successful.length} deleted, ${failures.length} failed`,
          {
            description: "Some documents could not be deleted. Please try again.",
          }
        );
      } else {
        throw new Error(`Failed to delete all ${failures.length} document(s)`);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to delete";
      toast.error(errorMessage);
    } finally {
      setBulkDeleting(false);
    }
  };

  // Apply search and sort
  const filteredAndSortedDocuments = sortDocuments(
    searchDocuments(documents, searchQuery),
    sortBy,
    sortOrder
  );

  // Get selected documents for bulk delete
  const selectedDocuments = documents.filter((doc) => selectedIds.has(doc.id));

  return (
    <div className="w-full max-w-6xl mx-auto px-6 py-12">
      {/* Upload section - Two column layout */}
      <div className="mb-4 pb-6 border-b">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
          <div>
            <h1 className="text-4xl font-semibold tracking-tight mb-3">Documents</h1>
            <p className="text-muted-foreground text-base">
              Upload and manage your documentation knowledge base. Supported formats include text files, markdown, and PDFs.
            </p>
          </div>
          <UploadZone
            onFilesSelected={handleFilesSelected}
            isDragging={isDragging}
            onDragStateChange={setIsDragging}
            disabled={uploadingFiles.some((f) => f.status === "uploading")}
          />
        </div>
      </div>

      {/* Active uploads (conditional) */}
      {uploadingFiles.length > 0 && (
        <div className="mb-8">
          <ActiveUploads
            uploads={uploadingFiles}
            onRemove={handleRemoveUpload}
            onClearCompleted={handleClearCompleted}
          />
        </div>
      )}

      {/* Documents table (desktop) / cards (mobile) */}
      <div className="hidden md:block">
        <DocumentsTable
          documents={filteredAndSortedDocuments}
          selectedIds={selectedIds}
          onToggleSelect={handleToggleSelect}
          onDelete={handleDeleteClick}
          isLoading={loading}
        />
      </div>

      <div className="md:hidden">
        <DocumentsMobileCards
          documents={filteredAndSortedDocuments}
          selectedIds={selectedIds}
          onToggleSelect={handleToggleSelect}
          onDelete={handleDeleteClick}
          isLoading={loading}
        />
      </div>

      {/* Single delete dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Document</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this document? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {documentToDelete && (
            <div className="flex items-start gap-3 p-3 border rounded-lg bg-muted/50">
              <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">{documentToDelete.filename}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Uploaded {formatDate(documentToDelete.created_at)}
                </p>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
              disabled={deleting}
            >
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteConfirm} disabled={deleting}>
              {deleting ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk delete dialog */}
      <BulkDeleteDialog
        open={bulkDeleteDialogOpen}
        onOpenChange={setBulkDeleteDialogOpen}
        selectedDocuments={selectedDocuments}
        onConfirm={handleBulkDeleteConfirm}
        isDeleting={bulkDeleting}
      />
    </div>
  );
}
