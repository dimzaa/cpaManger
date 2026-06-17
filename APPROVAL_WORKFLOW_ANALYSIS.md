# Approval Workflow Analysis

## Overview
The approval workflow manages how employee-submitted explanations for budget line changes get reviewed and approved by CPA administrators before being shown to municipalities.

---

## 1. EMPLOYEE SUBMISSION ENDPOINTS

### Endpoint: `POST /api/suggestions`
**Purpose:** Employee submits an explanation suggestion for a budget line

**Access Control:**
- Only employees (`EMPLOYEE` role) and admins (`ADMIN` role) can submit
- Employees can only submit for municipalities they're assigned to
- Admins can submit for any municipality

**Request Schema: `SuggestionCreate`**
```python
{
    "budget_line_id": int,           # Which budget line this is for
    "municipality_id": int,           # Which municipality
    "month": str,                     # YYYY-MM format
    "topic_code": str,                # Budget code (e.g., "3", "19", "33")
    "suggestion_type": str,           # "preset" or "custom"
    "preset_id": Optional[int],       # Required if suggestion_type="preset"
    "custom_text": Optional[str]      # Required if suggestion_type="custom" (max 500 chars)
}
```

**Response: `SuggestionResponse`**
```python
{
    "id": int,
    "budget_line_id": int,
    "municipality_id": int,
    "month": str,
    "topic_code": str,
    "suggestion_type": str,
    "preset_id": Optional[int],
    "custom_text": Optional[str],
    "suggested_by": int,              # User ID of suggester
    "status": str,                    # Always "pending" on creation
    "reviewed_by": Optional[int],
    "review_note": Optional[str],
    "created_at": datetime,
    "updated_at": datetime
}
```

**Logic:**
- Creates an `ExplanationSuggestion` record with `status=PENDING`
- Validates budget line exists
- Validates municipality exists and employee is assigned
- Two types of suggestions supported:
  - **Preset:** Employee selects from CPA-created templates
  - **Custom:** Employee writes their own explanation

---

## 2. CPA APPROVAL/REJECTION ENDPOINTS

### Endpoint: `GET /api/suggestions/pending`
**Purpose:** CPA admin views all pending suggestions awaiting approval

**Access Control:** Admin only (`ADMIN` role)

**Query Parameters:**
- `municipality_id` (optional): Filter by municipality
- `employee_id` (optional): Filter by employee who submitted

**Response: `List[SuggestionDetailResponse]`**
```python
[
    {
        "id": int,
        "budget_line_id": int,
        "municipality_id": int,
        "month": str,
        "topic_code": str,
        "suggestion_type": str,
        "preset_id": Optional[int],
        "custom_text": Optional[str],
        "suggested_by": int,
        "status": str,                # "pending"
        "reviewed_by": Optional[int],
        "review_note": Optional[str],
        "created_at": datetime,
        "updated_at": datetime,
        
        # Extended fields:
        "suggester_name": str,        # First and last name of employee
        "reviewer_name": Optional[str],
        "preset_text": Optional[str]  # If preset is used
    }
]
```

---

### Endpoint: `PATCH /api/suggestions/{suggestion_id}/approve`
**Purpose:** CPA admin approves a suggestion and makes it the official explanation

**Access Control:** Admin only

**Request Schema: `SuggestionApprove`**
```python
{
    "review_note": Optional[str]  # Optional note from CPA (max 500 chars)
}
```

**Response: `SuggestionResponse`**

**Side Effects:**
1. Updates `ExplanationSuggestion`:
   - `status` → `"approved"`
   - `reviewed_by` → current admin's ID
   - `review_note` → provided note (if any)

2. Creates `ApprovedExplanation` record:
   - `budget_line_id` → from suggestion
   - `municipality_id` → from suggestion
   - `month` → from suggestion
   - `topic_code` → from suggestion
   - `final_text` → preset text OR custom text (from suggestion)
   - `approved_by` → current admin's ID
   - `source` → `"suggestion"` (ApprovedExplanationSource enum)
   - `suggestion_id` → link back to the suggestion

**Logic:**
- Only pending suggestions can be approved
- If suggestion type is "preset", uses the preset's text
- If suggestion type is "custom", uses the custom_text from suggestion
- Creates an approved explanation that municipalities will see
- Marks suggestion as approved with current admin as reviewer

---

### Endpoint: `PATCH /api/suggestions/{suggestion_id}/reject`
**Purpose:** CPA admin rejects a suggestion with feedback for the employee

**Access Control:** Admin only

**Request Schema: `SuggestionReject`**
```python
{
    "review_note": str  # Required rejection reason (max 500 chars)
}
```

**Response: `SuggestionResponse`**

**Side Effects:**
1. Updates `ExplanationSuggestion`:
   - `status` → `"rejected"`
   - `reviewed_by` → current admin's ID
   - `review_note` → rejection reason (required)

2. **No `ApprovedExplanation` created**
3. Employee can revise and resubmit

**Logic:**
- Only pending suggestions can be rejected
- Employee sees the rejection reason and can submit a new suggestion
- No approved explanation is created for the municipality

---

### Endpoint: `GET /api/suggestions/my`
**Purpose:** Employee views their own submitted suggestions and their status

**Access Control:** All logged-in users, but meaningful for employees

**Response: `List[SuggestionDetailResponse]`**
- Shows all suggestions submitted by current user
- Includes rejection reasons (if rejected)
- Shows reviewer name and dates

**Logic:**
- Employees see their own suggestions to check if approved/rejected
- Admins receive empty list (they use `/pending` instead)

---

## 3. DATABASE MODELS

### Model: `ExplanationSuggestion`
**Table:** `explanation_suggestions`

**Columns:**
```python
id                  Integer         Primary Key
budget_line_id      Integer         FK → budget_lines.id
municipality_id     Integer         FK → municipalities.id
month               String(7)       YYYY-MM format
topic_code          String(10)      Budget code (e.g., "3", "19")

# Suggestion content (one is populated based on type):
suggestion_type     String(20)      "preset" or "custom"
preset_id           Integer         FK → preset_explanations.id (nullable)
custom_text         String(500)     Employee's written text (nullable)

# Submission tracking:
suggested_by        Integer         FK → users.id (employee/admin who submitted)
status              String(20)      "pending", "approved", or "rejected"
reviewed_by         Integer         FK → users.id (nullable, admin who reviewed)
review_note         String(500)     Rejection reason or CPA notes (nullable)

# Timestamps:
created_at          DateTime        When submitted
updated_at          DateTime        Last modification
```

**Relationships:**
- `budget_line` → BudgetLine (which budget line)
- `municipality` → Municipality
- `suggester` → User (employee who submitted)
- `reviewer` → User (admin who reviewed)
- `preset` → PresetExplanation (template text if preset type)

---

### Model: `ApprovedExplanation`
**Table:** `approved_explanations`

**Columns:**
```python
id                  Integer         Primary Key
budget_line_id      Integer         FK → budget_lines.id
municipality_id     Integer         FK → municipalities.id
month               String(7)       YYYY-MM format
topic_code          String(10)      Budget code

# Final explanation:
final_text          String(1000)    The explanation municipalities see

# Approval tracking:
approved_by         Integer         FK → users.id (CPA admin)
source              String(20)      "suggestion", "preset", "custom", or "auto"
suggestion_id       Integer         FK → explanation_suggestions.id (nullable)

# Timestamps:
created_at          DateTime        When approved
updated_at          DateTime        Last update
```

**Relationships:**
- `budget_line` → BudgetLine
- `municipality` → Municipality
- `approver` → User (who approved)
- `suggestion` → ExplanationSuggestion (if approved from suggestion)

**Notes:**
- This is what municipalities actually see in their budget portal
- Multiple source origins tracked (employee suggestion, preset, custom CPA override, auto-generated)

---

### Model: `PresetExplanation`
**Table:** `preset_explanations`

**Columns:**
```python
id                  Integer         Primary Key
topic_code          String(10)      Budget code (e.g., "3", "19", "general")
preset_text         String(500)     Hebrew explanation template
category            String(50)      "retro", "increase", "decrease", "correction", "new_position", "other"

# Audit:
created_by          Integer         FK → users.id (admin who created)
is_active           Boolean         Available for use?

# Timestamps:
created_at          DateTime
updated_at          DateTime
```

**Purpose:**
- CPA admins create preset templates that employees can choose from
- Reduces need for custom writing
- Ensures consistency in explanations

---

### Model: `BudgetLine`
**Table:** `budget_lines`

**Key Columns:**
```python
id                  Integer         Primary Key
run_id              Integer         FK → monthly_runs.id
municipality_id     Integer         FK → municipalities.id
topic_code          String(10)      Budget code
amount              Float           Amount in shekels
period_month        String(7)       Which month this is FOR (YYYY-MM)
current_month       String(7)       Which month this was PAID in (YYYY-MM)
is_retro            Boolean         True if period_month != current_month
```

**Purpose:**
- Represents individual budget items
- One row per topic per municipality per monthly run
- Employees/admins submit explanations for budget lines that need them

---

## 4. APPROVAL WORKFLOW STATES

### Suggestion Status Enum: `SuggestionStatus`
```python
PENDING   = "pending"    # Awaiting CPA review (initial state)
APPROVED  = "approved"   # CPA approved, now shown to municipality
REJECTED  = "rejected"   # CPA rejected, employee can revise
```

**State Machine:**
```
┌─────────────┐
│  PENDING    │ ← Created on submission
├─────────────┤
│             │
├──→ APPROVED │ ← Admin calls /approve, creates ApprovedExplanation
│             │
├──→ REJECTED │ ← Admin calls /reject, employee can resubmit
│
└─────────────┘
```

---

## 5. COMPLETE WORKFLOW SEQUENCE

### Scenario: Budget line needs explanation

```
STEP 1: EMPLOYEE SUBMISSION
├─ Employee logs in (must have EMPLOYEE role)
├─ Views pending budget line for their municipality
├─ Chooses explanation approach:
│  ├─ Option A: Select from presets (API: GET /api/presets?topic_code=3)
│  └─ Option B: Write custom text
├─ Submits suggestion (API: POST /api/suggestions)
└─ Receives SuggestionResponse with status="pending"

STEP 2: PENDING IN QUEUE
├─ Suggestion stored with status="pending"
├─ Created timestamp recorded
├─ Links: employee → budget_line → municipality

STEP 3: CPA REVIEW
├─ CPA/Admin logs in
├─ Views pending suggestions (API: GET /api/suggestions/pending)
├─ Views list with:
│  - Employee name (suggester_name)
│  - Suggestion type and text
│  - Budget line details
│  - Submission date
└─ Two options:

STEP 4A: APPROVAL PATH
├─ Admin reviews suggestion text
├─ Clicks "Approve" (API: PATCH /api/suggestions/{id}/approve)
├─ Optionally adds review note
├─ System actions:
│  ├─ Updates ExplanationSuggestion.status = "approved"
│  ├─ Updates ExplanationSuggestion.reviewed_by = admin_id
│  ├─ Creates ApprovedExplanation record with:
│  │  ├─ final_text = preset_text OR custom_text
│  │  ├─ source = "suggestion"
│  │  ├─ suggestion_id = link back
│  │  └─ approved_by = admin_id
│  └─ Commits to database
├─ Employee sees status="approved" (API: GET /api/suggestions/my)
└─ Municipality sees approved explanation in budget portal

STEP 4B: REJECTION PATH
├─ Admin reviews suggestion text
├─ Finds issue (unclear, incomplete, incorrect)
├─ Clicks "Reject" (API: PATCH /api/suggestions/{id}/reject)
├─ Provides rejection reason (required)
├─ System actions:
│  ├─ Updates ExplanationSuggestion.status = "rejected"
│  ├─ Updates ExplanationSuggestion.reviewed_by = admin_id
│  ├─ Updates ExplanationSuggestion.review_note = reason
│  ├─ NO ApprovedExplanation created
│  └─ Commits to database
├─ Employee sees status="rejected" with reason
├─ Employee can revise and resubmit (new POST /api/suggestions call)
└─ Cycle repeats with PENDING status for new suggestion

STEP 5: MUNICIPAL VIEW
├─ Municipality accesses budget portal
├─ System queries ApprovedExplanation records
├─ Shows final_text from approved explanations
├─ Displays only explanations with corresponding ApprovedExplanation record
└─ Cities see professional, CPA-approved explanations
```

---

## 6. KEY DESIGN POINTS

### Separation of Concerns
1. **ExplanationSuggestion** = Workflow state and submission data
2. **ApprovedExplanation** = Final approved explanation for municipalities
3. **PresetExplanation** = Template library for consistency

### Access Control
- **Admins** can: view pending, approve, reject, create presets
- **Employees** can: submit suggestions for assigned municipalities, view their own suggestions
- **Municipalities** can: view approved explanations only (read-only)

### Two-Stage System
1. **Suggestions** = Internal workflow (pending/approved/rejected)
2. **Approved Explanations** = What municipalities see

This separation allows:
- Rejection and resubmission without confusion
- Audit trail of suggestions
- Clear finality when something is approved

### Audit Trail
- `suggested_by` → tracks who submitted
- `reviewed_by` → tracks who approved/rejected
- `review_note` → captures feedback
- Timestamps → track workflow progression

---

## 7. API SUMMARY TABLE

| Method | Endpoint | Access | Purpose | Creates Record |
|--------|----------|--------|---------|-----------------|
| POST | `/api/suggestions` | Employee/Admin | Submit explanation | ExplanationSuggestion (pending) |
| GET | `/api/suggestions/pending` | Admin | View pending suggestions | None |
| GET | `/api/suggestions/my` | All users | View own suggestions | None |
| PATCH | `/api/suggestions/{id}/approve` | Admin | Approve suggestion | ApprovedExplanation |
| PATCH | `/api/suggestions/{id}/reject` | Admin | Reject with reason | None |
| GET | `/api/presets` | All users | View available templates | None |
| POST | `/api/presets` | Admin | Create new template | PresetExplanation |

---

## 8. EXPLANATION SOURCE TYPES

When an `ApprovedExplanation` is created, the `source` field indicates its origin:

```python
class ApprovedExplanationSource(str, Enum):
    AUTO = "auto"             # Auto-generated fallback (SmartExplanationEngine)
    PRESET = "preset"         # CPA selected a template 
    CUSTOM = "custom"         # CPA/employee wrote custom text
    SUGGESTION = "suggestion" # Approved from employee suggestion
```

Current workflow uses `"suggestion"` when approving from `/approve` endpoint.

---

## Summary

The approval workflow is a **two-stage** system:

1. **Employee Submission Stage**: Employees submit suggestions for budget explanations (either from presets or custom)
2. **CPA Review Stage**: Admins review pending suggestions and either approve (creating ApprovedExplanation) or reject (with feedback)

The system ensures:
- ✅ Accountability (tracks who did what and when)
- ✅ Quality control (admin approval before municipalities see)
- ✅ Consistency (presets available)
- ✅ Flexibility (custom submissions allowed)
- ✅ Iteration (rejected suggestions can be revised)
- ✅ Separation (internal workflow ≠ municipal view)
