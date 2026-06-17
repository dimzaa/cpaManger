# CPA Budget System - Notification/Suggestions System Investigation

**Date:** April 3, 2026  
**Status:** CRITICAL ISSUES FOUND - Data Integrity Problems

---

## EXECUTIVE SUMMARY

The suggestions system has **critical data integrity issues** that prevent the approval workflow from functioning correctly. 4 out of 5 suggestions in the database have NULL `custom_text` fields despite being marked as "custom" type. This is caused by a **frontend-backend mismatch** in field naming conventions.

---

## TASK 1: DATABASE INVESTIGATION

### 1.1 explanation_suggestions Table Schema

```
id                  INTEGER (Primary Key)
budget_line_id      INTEGER (FK to budget_lines)
municipality_id     INTEGER (FK to municipalities)
month               VARCHAR(7)          # YYYY-MM format
topic_code          VARCHAR(10)         # Budget code (3, 19, 33, etc.)
suggestion_type     VARCHAR(20)         # "preset" or "custom"
preset_id           INTEGER             # FK to preset_explanations (nullable)
custom_text         VARCHAR(500)        # Employee's custom text (nullable)
suggested_by        INTEGER             # FK to users
status              VARCHAR(20)         # "pending", "approved", "rejected"
reviewed_by         INTEGER             # FK to users (nullable)
review_note         VARCHAR(500)        # Rejection reason or approval note (nullable)
created_at          DATETIME            
updated_at          DATETIME            
```

### 1.2 approved_explanations Table Schema

```
id                  INTEGER (Primary Key)
budget_line_id      INTEGER (FK to budget_lines)
municipality_id     INTEGER (FK to municipalities)
month               VARCHAR(7)          # YYYY-MM format
topic_code          VARCHAR(10)         # Budget code
final_text          VARCHAR(1000)       # THE TEXT SHOWN TO MUNICIPALITY
approved_by         INTEGER (FK to users)
source              VARCHAR(20)         # "auto", "preset", "custom", "suggestion"
suggestion_id       INTEGER             # FK to explanation_suggestions (nullable)
created_at          DATETIME            
updated_at          DATETIME            
```

### 1.3 Sample Data from Database

**Row 1 - CRITICAL ISSUE:**
```
id:               1
budget_line_id:   254
municipality_id:  4
month:            2026-03
topic_code:       33
suggestion_type:  "custom"
preset_id:        None
custom_text:      ❌ NULL (INVALID - custom suggestion without text!)
suggested_by:     9
status:           pending
reviewed_by:      None
review_note:      None
created_at:       2026-04-02 18:37:45
```

**Row 2 - OK:**
```
id:               2
budget_line_id:   261
municipality_id:  4
month:            2026-03
topic_code:       0
suggestion_type:  "preset"
preset_id:        6
custom_text:      None (correct - preset type doesn't use custom_text)
suggested_by:     16
status:           approved
reviewed_by:      1
review_note:      "Approved by test. Good explanation."
created_at:       2026-04-02 20:06:53
```

**Row 3 - CRITICAL ISSUE:**
```
id:               3
budget_line_id:   233
municipality_id:  4
month:            2026-03
topic_code:       19
suggestion_type:  "custom"
preset_id:        None
custom_text:      ❌ NULL (INVALID - custom suggestion without text!)
suggested_by:     9
status:           pending
reviewed_by:      None
review_note:      None
created_at:       2026-04-02 20:09:10
```

### 1.4 Data Statistics

```
Total Suggestions:                  5
  - custom type, PENDING:           4  ❌ ALL HAVE NULL CUSTOM_TEXT
  - preset type, APPROVED:          1  ✅ Properly formed
```

### 1.5 Data Integrity Issues

| Issue | Count | Severity | Impact |
|-------|-------|----------|--------|
| Custom suggestions with NULL custom_text | 4 | CRITICAL | Cannot be approved; invalid state |
| Preset suggestions with NULL preset_id | 0 | OK | None found |

---

## TASK 2: BACKEND API RESPONSE CHECK

### 2.1 GET /api/suggestions/pending Endpoint Analysis

**Location:** [backend/routes/suggestions.py](backend/routes/suggestions.py#L135-L180)

**Code Flow:**
```python
@router.get("/pending", response_model=List[SuggestionDetailResponse])
async def get_pending_suggestions(
    municipality_id: Optional[int] = Query(None),
    employee_id: Optional[int] = Query(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # 1. Query PENDING suggestions from database
    query = db.query(ExplanationSuggestion).filter(
        ExplanationSuggestion.status == SuggestionStatus.PENDING
    )
    
    # 2. Apply optional filters
    if municipality_id:
        query = query.filter(ExplanationSuggestion.municipality_id == municipality_id)
    if employee_id:
        query = query.filter(ExplanationSuggestion.suggested_by == employee_id)
    
    suggestions = query.order_by(ExplanationSuggestion.created_at.desc()).all()
    
    # 3. Enrich with related data
    result = []
    for s in suggestions:
        detail = SuggestionDetailResponse.model_validate(s)
        
        # Add suggester name
        if s.suggester:
            suggester_name = f"{s.suggester.first_name or ''} {s.suggester.last_name or ''}".strip()
        detail.suggester_name = suggester_name or "Unknown"
        
        # Add preset text (if applicable)
        if s.preset:
            detail.preset_text = s.preset.preset_text
        
        result.append(detail)
    
    return result
```

### 2.2 Response Schema

**SuggestionDetailResponse:**
```python
class SuggestionDetailResponse(SuggestionResponse):
    """Extended response with related data."""
    suggester_name: Optional[str] = None          # Added by endpoint
    reviewer_name: Optional[str] = None           # NOT populated (bug!)
    preset_text: Optional[str] = None             # Populated from preset.preset_text
```

**Base SuggestionResponse includes:**
```python
id: int
budget_line_id: int
municipality_id: int
month: str
topic_code: str
suggestion_type: str                # "preset" or "custom"
preset_id: Optional[int] = None     
custom_text: Optional[str] = None   # ❌ WILL BE NULL IF SUBMITTED WITH NULL
suggested_by: int
status: str                         # "pending", "approved", "rejected"
reviewed_by: Optional[int] = None
review_note: Optional[str] = None
created_at: datetime
updated_at: datetime
```

### 2.3 Response Issues Found

**Issue #1: Null Fields in Response**
- When a custom suggestion is created with NULL `custom_text`, the response includes `custom_text: null`
- API correctly returns what's in the database (truthful), but the data is invalid

**Issue #2: Missing reviewer_name**
- The endpoint sets `suggester_name` ✅
- But does NOT set `reviewer_name` when suggestion is approved ❌
- Frontend may show "Unknown" or null for reviewer

**Issue #3: No Validation on Retrieval**
- The endpoint doesn't validate that custom suggestions have text
- Returns invalid suggestions without warning

### 2.4 Frontend receives this (Example for Row 1):

```json
{
  "id": 1,
  "budget_line_id": 254,
  "municipality_id": 4,
  "month": "2026-03",
  "topic_code": "33",
  "suggestion_type": "custom",
  "preset_id": null,
  "custom_text": null,                    // ❌ EMPTY!
  "suggested_by": 9,
  "status": "pending",
  "reviewed_by": null,
  "review_note": null,
  "created_at": "2026-04-02T18:37:45",
  "updated_at": "2026-04-02T18:37:45",
  "suggester_name": "John Doe",
  "reviewer_name": null,
  "preset_text": null
}
```

---

## TASK 3: APPROVE ENDPOINT ANALYSIS

### 3.1 PATCH /api/suggestions/{id}/approve Endpoint

**Location:** [backend/routes/suggestions.py](backend/routes/suggestions.py#L240-L295)

**Code:**
```python
@router.patch("/{suggestion_id}/approve", response_model=SuggestionResponse)
async def approve_suggestion(
    suggestion_id: int,
    data: SuggestionApprove,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Approve a suggestion and make it the official explanation (admin only).
    This creates an ApprovedExplanation record that municipalities will see.
    """
    # Find suggestion
    suggestion = db.query(ExplanationSuggestion).filter(
        ExplanationSuggestion.id == suggestion_id
    ).first()
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    if suggestion.status != SuggestionStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Can only approve pending suggestions, this is {suggestion.status}")
    
    # ❌ CRITICAL: Determine the final text
    if suggestion.suggestion_type == "preset" and suggestion.preset:
        final_text = suggestion.preset.preset_text
    else:
        final_text = suggestion.custom_text  # ❌ THIS CAN BE NULL!
    
    # Update suggestion
    suggestion.status = SuggestionStatus.APPROVED
    suggestion.reviewed_by = current_user.id
    suggestion.review_note = data.review_note
    
    # ❌ CRITICAL: Create approved explanation record
    approved = ApprovedExplanation(
        budget_line_id=suggestion.budget_line_id,
        municipality_id=suggestion.municipality_id,
        month=suggestion.month,
        topic_code=suggestion.topic_code,
        final_text=final_text,  # ❌ CAN BE NULL - VIOLATES NOT NULL CONSTRAINT!
        approved_by=current_user.id,
        source=ApprovedExplanationSource.SUGGESTION,
        suggestion_id=suggestion.id
    )
    
    db.add(approved)
    db.commit()  # ❌ DATABASE ERROR: "NOT NULL constraint failed: approved_explanations.final_text"
    db.refresh(suggestion)
    
    logger.info(f"Suggestion {suggestion_id} approved by {current_user.email}")
    
    return suggestion
```

### 3.2 Critical Issues in Approve Endpoint

| Issue | Line | Severity | Description |
|-------|------|----------|-------------|
| **NULL final_text** | 266 | 🔴 CRITICAL | `else: final_text = suggestion.custom_text` doesn't check if NULL |
| **No validation** | 266 | 🔴 CRITICAL | Endpoint doesn't validate that final_text will be non-NULL |
| **Database constraint violation** | 278-286 | 🔴 CRITICAL | ApprovedExplanation.final_text is NOT NULL, but code passes NULL |
| **No error handling** | 290 | 🔴 CRITICAL | db.commit() will crash with database error instead of graceful HTTP error |

### 3.3 What Happens When User Approves a Broken Suggestion

**Scenario:** User tries to approve suggestion ID 1 (custom with NULL custom_text)

1. **API receives request:** `PATCH /api/suggestions/1/approve`
2. **Final text determination:** 
   ```
   suggestion.suggestion_type == "preset"? No (it's "custom")
   suggestion.preset? Irrelevant
   → final_text = suggestion.custom_text
   → final_text = None  ❌
   ```
3. **Create ApprovedExplanation:** Sets `final_text = None`
4. **Database commit:** 
   ```
   ERROR: NOT NULL constraint failed: approved_explanations.final_text
   ```
5. **User receives:** HTTP 500 Internal Server Error (not a helpful error message)

---

## ROOT CAUSE: Frontend-Backend Mismatch

### 3.4 How Bad Data Gets Into Database

**Chain of Events:**

1. **Modal creates suggestion object:** [PortalBudgetPage.jsx Line 120-130]
   ```javascript
   const handleSuggestionSubmit = async (suggestionData) => {
     // suggestionData is from ExplanationSuggestionModal
     // For custom: { 
     //   reason_id: null,
     //   suggestion_type: 'custom',
     //   explanation_text: 'User typed text...' ❌ WRONG FIELD NAME!
     // }
     
     await suggestionsAPI.submit({
       budget_line_id: selectedBudgetLine.id,
       municipality_id: selectedMunicipality,
       month: selectedMonth,
       topic_code: selectedBudgetLine.topic_code,
       ...suggestionData  // ❌ Spreads explanation_text into payload
     });
   }
   ```

2. **Backend receives request:**
   ```python
   # Incoming data from frontend:
   {
     "budget_line_id": 254,
     "municipality_id": 4,
     "month": "2026-03",
     "topic_code": "33",
     "suggestion_type": "custom",
     "reason_id": null,
     "explanation_text": "Some text...",  # ❌ Backend doesn't recognize this field
     # custom_text is MISSING!
   }
   ```

3. **Pydantic schema validation:** [suggestions.py Line 29-35]
   ```python
   class SuggestionCreate(BaseModel):
       budget_line_id: int
       municipality_id: int
       month: str
       topic_code: str
       suggestion_type: str
       preset_id: Optional[int] = None
       custom_text: Optional[str] = None  # ❌ Expects this field
       # Doesn't expect: explanation_text, reason_id
   ```
   - Pydantic ignores unknown fields (`reason_id`, `explanation_text`)
   - `custom_text` not provided → defaults to None

4. **Suggestion created with NULL custom_text:**
   ```python
   suggestion = ExplanationSuggestion(
       custom_text=data.custom_text if data.suggestion_type == "custom" else None,
       # data.custom_text is None → stored as NULL
   )
   ```

---

## SUMMARY TABLE

### Database Schema ✅

| Table | Columns | Status |
|-------|---------|--------|
| explanation_suggestions | 14 columns properly defined | ✅ Correct |
| approved_explanations | 11 columns properly defined | ✅ Correct |
| Constraints | final_text NOT NULL | ✅ Enforced |

### Sample Data ❌

| Issue | Details |
|-------|---------|
| Invalid custom Suggestions | 4/5 suggestions (IDs 1,3,4,5) have NULL custom_text despite `suggestion_type='custom'` |
| Data Integrity | Database allows this invalid state to be created |

### API Response Structure ⚠️

| Endpoint | Response | Issues |
|----------|----------|--------|
| GET /api/suggestions/pending | Returns full suggestion data | ✅ Returns correct data, but data itself is invalid |
| Fields included | All fields including custom_text | ❌ custom_text is NULL in invalid suggestions |
| Validation | Only checks suggestion exists | ❌ No validation that custom suggestions have text |

### Approve Endpoint 🔴

| Aspect | Issue | Consequence |
|--------|-------|-------------|
| final_text determination | `final_text = suggestion.custom_text` without NULL check | Crashes on NULL |
| ApprovedExplanation creation | Passes potentially NULL final_text | Database constraint violation |
| Error handling | No try-catch for db.commit() | HTTP 500 instead of HTTP 400 |
| All fields validated | source, suggestion_id, approved_by all required | ❌ These are correct; only final_text is problem |

---

## ISSUES & FIXES NEEDED

### HIGH PRIORITY (Blocking Approval Workflow)

**Issue 1: Frontend sends wrong field name**
- **Current:** Modal sends `explanation_text`
- **Expected:** Backend expects `custom_text`
- **Fix:** Rename field in [ExplanationSuggestionModal.jsx](frontend/src/components/portal/ExplanationSuggestionModal.jsx#L160)

**Issue 2: Backend doesn't validate NULL custom_text on approval**
- **Current:** `final_text = suggestion.custom_text` (can be NULL)
- **Fix:** Add validation before creating ApprovedExplanation:
  ```python
  if suggestion.suggestion_type == "custom":
      if not suggestion.custom_text:
          raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail="Cannot approve custom suggestion without text"
          )
      final_text = suggestion.custom_text
  elif suggestion.suggestion_type == "preset":
      if not suggestion.preset:
          raise HTTPException(status_code=404, detail="Preset not found")
      final_text = suggestion.preset.preset_text
  else:
      raise HTTPException(status_code=400, detail=f"Unknown suggestion type: {suggestion.suggestion_type}")
  ```

**Issue 3: Existing bad data in database**
- **Current:** 4 suggestions with NULL custom_text are stuck pending
- **Fix:** Migrate these to "rejected" status with system note, or manually add text

### MEDIUM PRIORITY (Missing Features)

**Issue 4: Reviewer name not included in response**
- **Current:** `reviewer_name` field always NULL
- **Fix:** Populate in get_pending_suggestions():
  ```python
  if s.reviewer:
      detail.reviewer_name = f"{s.reviewer.first_name} {s.reviewer.last_name}".strip()
  ```

**Issue 5: No database constraint on suggestion data**
- **Current:** Database allows NULL custom_text for custom suggestions
- **Fix:** Add database-level validation or check in ORM

### LOW PRIORITY (Code Quality)

**Issue 6: Error message doesn't show reason**
- **Current:** "Can only approve pending suggestions, this is {status}"
- **Improvement:** More specific messages for different failure modes

---

## VERIFICATION QUERIES

### Check for broken suggestions:
```sql
SELECT id, status, suggestion_type, custom_text 
FROM explanation_suggestions 
WHERE suggestion_type = 'custom' AND custom_text IS NULL;
```
**Current Result:** 4 rows (IDs 1, 3, 4, 5)

### Check approved explanations with NULL final_text:
```sql
SELECT id, final_text, source, suggestion_id 
FROM approved_explanations 
WHERE final_text IS NULL;
```
**Current Result:** 0 rows (none yet because approvals fail)

---

## RECOMMENDATIONS

1. **URGENT:** Fix frontend field name (`explanation_text` → `custom_text`)
2. **URGENT:** Add validation in approve endpoint before creating ApprovedExplanation
3. **URGENT:** Fix bad data in database (4 broken suggestions)
4. **IMPORTANT:** Add reviewer_name to response
5. **IMPORTANT:** Add database-level constraints to prevent future issues
6. **NICE-TO-HAVE:** Better error messages for validation failures

---

## FILES TO MODIFY

1. **[frontend/src/components/portal/ExplanationSuggestionModal.jsx](frontend/src/components/portal/ExplanationSuggestionModal.jsx#L160)**
   - Change `explanation_text` → `custom_text`

2. **[backend/routes/suggestions.py](backend/routes/suggestions.py#L240-L295)**
   - Add NULL validation in approve_suggestion endpoint
   - Add reviewer_name population in get_pending_suggestions

3. **[backend/models/explanation_suggestion.py](backend/models/explanation_suggestion.py)**
   - Consider adding CheckConstraint for custom suggestions

4. **Database Migration Script**
   - Handle 4 existing broken suggestions

---

**Investigation completed by: System Analysis  
Timestamp: 2026-04-03  
Status: Ready for implementation**
