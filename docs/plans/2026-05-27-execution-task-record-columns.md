# Execution Task Record Columns Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show both sample name and sample ID in the execution task list so users can distinguish replay sources more easily.

**Architecture:** Keep the backend contract unchanged and derive display text in the admin web from the already loaded record list. Update only the execution task table columns and related frontend tests.

**Tech Stack:** React, TypeScript, Vite, Vitest, Testing Library.

---

### Task 1: Define the expected table behavior in tests

**Files:**
- Modify: `admin/web/src/App.test.tsx`

**Step 1: Write the failing test**

- Update the execution task list test to expect two columns: `样本名称` and `样本 ID`.
- Assert the row renders the record name and the `#ID` separately.

**Step 2: Run test to verify it fails**

Run: `npm test -- --run App.test.tsx -t "renders execution tasks in a list table and shows results in a result table"`

Expected: FAIL because the page still renders a single `来源样本` column.

### Task 2: Implement the new table columns

**Files:**
- Modify: `admin/web/src/App.tsx`

**Step 1: Write minimal implementation**

- Build a `recordById` lookup from the already loaded `records`.
- Replace the execution task column header `来源样本` with `样本名称` and `样本 ID`.
- Render the resolved record name in one cell and `#${source_ref_id}` in the adjacent cell.
- Keep fallback behavior for missing record rows.

**Step 2: Run test to verify it passes**

Run: `npm test -- --run App.test.tsx -t "renders execution tasks in a list table and shows results in a result table"`

Expected: PASS

### Task 3: Run regression checks

**Files:**
- No code changes

**Step 1: Run the frontend suite**

Run: `npm test -- --run App.test.tsx`

Expected: PASS

**Step 2: Run production build**

Run: `npm run build`

Expected: PASS
