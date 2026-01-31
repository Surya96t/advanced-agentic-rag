# 📋 UNIFIED DOCUMENTS & UPLOAD PAGE - IMPLEMENTATION PLAN

## 🎯 Project Goal

Combine `/upload` and `/documents` pages into a single unified page at `/documents` with enhanced features including upload zone, active uploads tracking, search/filter, bulk actions, and responsive design.

---

## 📐 Architecture Decisions

### **Design Choices:**

1. ✅ **Collapsible upload zone** - Can be collapsed to save space when not uploading
2. ✅ **Extract navigation to component** - Better separation of concerns
3. ✅ **Client-side search/filter** - Fast, simple, backend enhancement later
4. ✅ **Client-side sorting** - Instant feedback for users
5. ✅ **Phase-by-phase execution** - Review after each phase before continuing

---

## 🗂️ File Structure Plan

### **Files to CREATE:**

1. `frontend/components/layout/dashboard-nav.tsx` - Extracted navigation component
2. `frontend/components/documents/upload-zone.tsx` - Collapsible file upload area
3. `frontend/components/documents/active-uploads.tsx` - Upload progress tracking
4. `frontend/components/documents/documents-toolbar.tsx` - Search, filter, sort controls
5. `frontend/components/documents/documents-table.tsx` - Enhanced table with bulk selection
6. `frontend/components/documents/documents-mobile-cards.tsx` - Mobile card view
7. `frontend/components/documents/bulk-delete-dialog.tsx` - Bulk delete confirmation
8. `frontend/lib/document-utils.ts` - Utility functions (search, sort, filter)

### **Files to MODIFY:**

1. layout.tsx - Use new nav component
2. page.tsx - Complete rewrite with all features

### **Files to DELETE:**

1. page.tsx - No longer needed

---

## 📅 Phase-by-Phase Execution Plan

---

### **PHASE 1: Navigation Refactor & Basic Setup**

**Goal:** Extract navigation, prepare structure, no feature changes yet

#### Step 1.1: Create Navigation Component

- **File:** `frontend/components/layout/dashboard-nav.tsx`
- **Content:** Extract navigation from layout, keep same functionality
- **Features:**
  - Same 3 links (Documents, Upload, Chat)
  - Active link highlighting
  - Icons and styling preserved

#### Step 1.2: Update Layout to Use New Component

- **File:** layout.tsx
- **Changes:**
  - Import new `DashboardNav` component
  - Replace inline nav with `<DashboardNav />`
  - Clean up unused imports

#### Step 1.3: Verification

- Test that navigation still works
- All links functional
- No visual changes

**🛑 STOP - Get approval before Phase 2**

---

### **PHASE 2: Core Upload Zone Components**

**Goal:** Build reusable upload components, test in isolation

#### Step 2.1: Create Upload Zone Component

- **File:** `frontend/components/documents/upload-zone.tsx`
- **Features:**
  - Drag & drop area (from current upload page)
  - File input button
  - Collapsible state (ChevronDown icon)
  - File type validation
  - Visual feedback for drag state
  - Compact when collapsed (just header bar)
  - Expanded shows full drop zone

#### Step 2.2: Create Active Uploads Component

- **File:** `frontend/components/documents/active-uploads.tsx`
- **Features:**
  - List of uploading files with progress
  - Color-coded status (pending=gray, uploading=blue, success=green, error=red)
  - File size display (formatted KB/MB)
  - Individual remove buttons
  - "Clear Completed" button
  - Only renders when uploadingFiles.length > 0

#### Step 2.3: Create Upload Utilities

- **File:** `frontend/lib/document-utils.ts`
- **Functions:**
  - `formatFileSize(bytes: number): string` - Convert bytes to KB/MB
  - `validateFile(file: File): { valid: boolean, error?: string }` - Validate type and size
  - `generateFileId(): string` - Generate unique IDs

**🛑 STOP - Get approval before Phase 3**

---

### **PHASE 3: Documents Toolbar & Search/Filter**

**Goal:** Add search, sorting, and filtering controls

#### Step 3.1: Create Documents Toolbar Component

- **File:** `frontend/components/documents/documents-toolbar.tsx`
- **Features:**
  - Search input (filters by filename)
  - Sort dropdown (Name, Date, Chunks - asc/desc)
  - Document count display
  - Bulk delete button (only shows when items selected)
  - "Select All" / "Deselect All" buttons (when in selection mode)

#### Step 3.2: Add Search/Sort/Filter Functions

- **File:** `frontend/lib/document-utils.ts`
- **Functions:**
  - `searchDocuments(docs: Document[], query: string): Document[]`
  - `sortDocuments(docs: Document[], sortBy: SortField, order: SortOrder): Document[]`
  - `filterDocuments(docs: Document[], filters: FilterOptions): Document[]`

**🛑 STOP - Get approval before Phase 4**

---

### **PHASE 4: Enhanced Documents Table**

**Goal:** Build responsive table with bulk selection

#### Step 4.1: Create Desktop Table Component

- **File:** `frontend/components/documents/documents-table.tsx`
- **Features:**
  - Checkbox column for selection
  - File type icons (PDF=red, MD=blue, TXT=gray with lucide icons)
  - Status badges (if available from backend)
  - Formatted dates
  - Chunk count display
  - Individual delete buttons
  - Sortable column headers (clickable)
  - Hover effects
  - Empty state component

#### Step 4.2: Create Mobile Cards Component

- **File:** `frontend/components/documents/documents-mobile-cards.tsx`
- **Features:**
  - Card layout for each document
  - Checkbox for selection
  - File icon and name
  - Date and chunk count
  - Delete button
  - Stacked layout
  - Touch-friendly spacing

#### Step 4.3: Create Bulk Delete Dialog

- **File:** `frontend/components/documents/bulk-delete-dialog.tsx`
- **Features:**
  - Shows count of selected items
  - Lists selected document names
  - Confirm/Cancel buttons
  - Warning message
  - Loading state during deletion

**🛑 STOP - Get approval before Phase 5**

---

### **PHASE 5: Unified Documents Page**

**Goal:** Combine everything into the main documents page

#### Step 5.1: Rewrite Documents Page

- **File:** page.tsx
- **Structure:**
  ```
  - UploadZone (collapsible at top)
  - ActiveUploads (conditional render)
  - DocumentsToolbar (search/sort/bulk actions)
  - DocumentsTable (desktop) / MobileCards (mobile)
  - DeleteDialog (single item)
  - BulkDeleteDialog (multiple items)
  ```
- **State Management:**
  - Upload state (files, dragging, progress)
  - Documents state (list, loading)
  - Selection state (selectedIds Set)
  - Search/sort state (query, sortBy, sortOrder)
  - Dialog state (delete, bulkDelete)
- **Features:**
  - Auto-refresh documents after successful upload
  - Responsive breakpoints (mobile/tablet/desktop)
  - Loading skeletons
  - Error boundaries
  - Toast notifications

#### Step 5.2: Add Responsive Styling

- Use Tailwind breakpoints:
  - `sm:` (640px+) - Tablet adjustments
  - `md:` (768px+) - Switch to table view
  - `lg:` (1024px+) - Full desktop layout

**🛑 STOP - Get approval before Phase 6**

---

### **PHASE 6: Navigation Update & Cleanup**

**Goal:** Update navigation links and remove old upload page

#### Step 6.1: Update Navigation Component

- **File:** `frontend/components/layout/dashboard-nav.tsx`
- **Changes:**
  - Remove "Upload" link
  - Keep "Documents" link (now includes upload)
  - Update "Documents" link label to "Documents & Upload" or just "Documents"
  - Consider adding tooltip: "Upload and manage documents"

#### Step 6.2: Delete Old Upload Page

- **File:** page.tsx
- **Action:** DELETE entirely

#### Step 6.3: Update Redirects (if any)

- Check if `/upload` needs redirect to `/documents`
- Add middleware rule if needed

**🛑 STOP - Get approval before Phase 7**

---

### **PHASE 7: Polish & Final Touches**

**Goal:** Animations, loading states, accessibility

#### Step 7.1: Add Loading Skeletons

- Replace spinners with skeleton loaders
- Skeleton for table rows
- Skeleton for upload zone
- Use shadcn/ui Skeleton component

#### Step 7.2: Add Success Animations

- Checkmark animation on successful upload
- Fade-out animation for completed uploads
- Smooth transitions for collapsible sections
- Highlight newly added documents briefly

#### Step 7.3: Accessibility Improvements

- ARIA labels for all interactive elements
- Keyboard navigation for upload zone (Enter to open file picker)
- Focus management for dialogs
- Screen reader announcements for status changes
- Proper heading hierarchy

#### Step 7.4: Final Testing

- Test all features on mobile/tablet/desktop
- Test keyboard navigation
- Test with screen reader
- Test error scenarios
- Test with no documents (empty state)
- Test with many documents (performance)

**🛑 STOP - Final review**

---

## 📊 Summary Statistics

### **New Files:** 8

- 1 navigation component
- 5 document components
- 1 utility file
- 1 unified page (rewrite)

### **Modified Files:** 2

- Layout (use new nav)
- Documents page (complete rewrite)

### **Deleted Files:** 1

- Old upload page

### **Total Phases:** 7

- Each phase ends with approval gate
- Iterative, reversible approach
- Test after each phase

---

## ✅ Ready for Approval

**Next Steps:**

1. Review this plan
2. Approve to start Phase 1
3. I'll implement Phase 1, show you the changes
4. Get your approval before moving to Phase 2
5. Repeat for each phase

**Questions/Changes needed?** Let me know and I'll update the plan!
