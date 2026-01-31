"use client";

import { Search, ArrowUpDown, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SortField, SortOrder } from "@/lib/document-utils";

interface DocumentsToolbarProps {
  // Search
  searchQuery: string;
  onSearchChange: (query: string) => void;
  
  // Sort
  sortBy: SortField;
  sortOrder: SortOrder;
  onSortChange: (field: SortField, order: SortOrder) => void;
  
  // Bulk actions
  selectedCount: number;
  totalCount: number;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  onBulkDelete: () => void;
  
  // State
  isLoading?: boolean;
}

/**
 * Toolbar for document search, sorting, and bulk actions
 */
export function DocumentsToolbar({
  searchQuery,
  onSearchChange,
  sortBy,
  sortOrder,
  onSortChange,
  selectedCount,
  totalCount,
  onSelectAll,
  onDeselectAll,
  onBulkDelete,
  isLoading = false,
}: DocumentsToolbarProps) {
  const hasSelection = selectedCount > 0;
  const allSelected = selectedCount === totalCount && totalCount > 0;

  // Toggle sort order for current field
  const toggleSortOrder = () => {
    onSortChange(sortBy, sortOrder === 'asc' ? 'desc' : 'asc');
  };

  return (
    <div className="space-y-4">
      {/* Main toolbar */}
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => onSearchChange(e.target.value)}
            className="pl-9"
            disabled={isLoading}
          />
        </div>

        {/* Sort */}
        <div className="flex gap-2">
          <Select
            value={sortBy}
            onValueChange={(value: string) => onSortChange(value as SortField, sortOrder)}
            disabled={isLoading}
          >
            <SelectTrigger className="w-36">
              <SelectValue placeholder="Sort by..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="name">Name</SelectItem>
              <SelectItem value="date">Date</SelectItem>
              <SelectItem value="chunks">Chunks</SelectItem>
            </SelectContent>
          </Select>

          <Button
            variant="outline"
            size="icon"
            onClick={toggleSortOrder}
            disabled={isLoading}
            aria-label={`Sort ${sortOrder === 'asc' ? 'descending' : 'ascending'}`}
          >
            <ArrowUpDown className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Selection toolbar (shows when items selected) */}
      {hasSelection && (
        <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium">
              {selectedCount} of {totalCount} selected
            </span>
            <div className="flex gap-2">
              {!allSelected && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onSelectAll}
                  disabled={isLoading}
                >
                  Select All
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={onDeselectAll}
                disabled={isLoading}
              >
                Deselect All
              </Button>
            </div>
          </div>

          <Button
            variant="destructive"
            size="sm"
            onClick={onBulkDelete}
            disabled={isLoading}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete Selected
          </Button>
        </div>
      )}

      {/* Document count */}
      {!hasSelection && totalCount > 0 && (
        <div className="text-sm text-muted-foreground">
          {totalCount} document{totalCount !== 1 ? 's' : ''} total
        </div>
      )}
    </div>
  );
}
