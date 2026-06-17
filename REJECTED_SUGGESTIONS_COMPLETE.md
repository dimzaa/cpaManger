# ✅ REJECTED SUGGESTIONS FEATURE - COMPLETE IMPLEMENTATION

## Overview
Added a complete "הצעות שנדחו" (Rejected Suggestions) feature for employees to view, edit, and resubmit their rejected explanation suggestions.

---

## Backend Changes

### **New Endpoint: GET /api/suggestions/my-rejected**
Location: [backend/routes/suggestions.py](backend/routes/suggestions.py)

**Response Schema:** `RejectedSuggestionResponse`
```python
{
    id: int,
    municipality_name: str,           # Name of municipality
    month: str,                       # YYYY-MM format
    topic_code: str,                  # Budget code (e.g., "3")
    budget_line_name: str,            # Name of budget line
    custom_text: str,                 # Employee's suggested text
    preset_text: str,                 # If from preset library
    review_note: str,                 # CPA's rejection reason
    created_at: datetime,
    updated_at: datetime,
    suggestion_type: str,             # "preset" or "custom"
    preset_id: int
}
```

**Functionality:**
- Returns all REJECTED suggestions for current employee
- Includes municipality name, budget line details, and CPA's rejection reason
- Empty list for non-employee users
- Ordered by most recent first

**Key Code:**
```python
@router.get("/my-rejected", response_model=List[RejectedSuggestionResponse])
async def get_my_rejected_suggestions(
    current_user: User = Depends(require_login),
    db: Session = Depends(get_db)
):
    # Filters by status=REJECTED and suggested_by=current_user
    # Returns enriched data with municipality/budget line names
```

---

## Frontend Changes

### **1. New Hook: useRejectedSuggestionsCount**
File: [frontend/src/hooks/useRejectedSuggestionsCount.js](frontend/src/hooks/useRejectedSuggestionsCount.js)

**Features:**
- Fetches count of rejected suggestions
- Auto-refreshes every 60 seconds
- Returns: `{ count, loading, error, refetch }`
- Used by Sidebar to display badge

### **2. New Page: EmployeeRejectedPage**
File: [frontend/src/pages/EmployeeRejectedPage.jsx](frontend/src/pages/EmployeeRejectedPage.jsx)
Route: `/portal/rejected`

**Features:**
- Shows all rejected suggestions in card layout
- Displays:
  - ❌ Red "REJECTED" badge
  - Municipality name
  - Month and topic code
  - Budget line name
  - Employee's suggested text (blue box)
  - CPA's rejection reason (red box)
  - Date rejected
- "✏️ ערוך והגש מחדש" button to edit and resubmit
- Modal pre-fills with old text for editing
- Empty state message when no rejected suggestions

**Card Layout:**
```
┌─────────────────────────────────────────┐
│ ❌ נדחתה                    עירית X    │
│ מרץ 2026 | קוד 3 | ילדי ח"מ 5י'       │
│                                         │
│ 💡 הההסבר שהגשת:                       │
│ "[employee text]"                       │
│                                         │
│ 🔴 סיבת הדחייה מרואה החשבון:          │
│ "[CPA reason]"                          │
│                                         │
│ [✏️ ערוך והגש מחדש]                   │
└─────────────────────────────────────────┘
```

### **3. Updated Sidebar**
File: [frontend/src/components/layout/Sidebar.jsx](frontend/src/components/layout/Sidebar.jsx)

**Changes:**
- Added `useRejectedSuggestionsCount` hook
- Import `AlertCircle` icon from lucide-react
- Added `employeeItems` array for employee-specific navigation
- Shows "הצעות שנדחו ❌" with red badge showing count
- Only visible for employees (role === 'employee')
- Badge hidden when count = 0

**New Employee Section:**
```jsx
{employeeItems.length > 0 && (
  <>
    <div className="border-t border-slate-700 my-2 pt-2">
      <p className="text-xs text-slate-500 font-hebrew px-4 mb-2">הצעות</p>
    </div>
    {employeeItems.map((item) => (
      <Link to={item.path} className="...">
        <div className="flex items-center gap-3">
          <Icon size={20} />
          <span>{item.label}</span>
        </div>
        {item.badge && (
          <span className="bg-red-600 text-white rounded-full px-2 py-1">
            {item.badge}
          </span>
        )}
      </Link>
    ))}
  </>
)}
```

### **4. Updated App.jsx**
File: [frontend/src/App.jsx](frontend/src/App.jsx)

**Changes:**
- Imported `EmployeeRejectedPage`
- Added route `/portal/rejected`

```jsx
<Route path="/portal" element={<MunicipalityRoute />}>
  <Route index element={<PortalHomePage />} />
  <Route path="budget" element={<PortalBudgetPage />} />
  <Route path="rejected" element={<EmployeeRejectedPage />} />
</Route>
```

### **5. Updated API Service**
File: [frontend/src/services/api.js](frontend/src/services/api.js)

**New Method:**
```javascript
suggestionsAPI = {
  // ... existing methods ...
  
  // Get my rejected suggestions (employee)
  getMyRejected: () =>
    apiClient.get('/api/suggestions/my-rejected'),
}
```

### **6. Enhanced Modal Component**
File: [frontend/src/components/portal/ExplanationSuggestionModal.jsx](frontend/src/components/portal/ExplanationSuggestionModal.jsx)

**New Props:**
- `prefilledText`: Pre-fills custom text field when editing
- `isEdit`: Boolean flag to indicate edit mode

**Changes:**
- Constructor accepts `prefilledText` and `isEdit` props
- `useState` initializes `customText` with `prefilledText`
- When modal opens in edit mode:
  - Pre-fills text in custom field
  - Automatically switches to "custom" tab
  - Employee can modify text before resubmitting

---

## Complete Flow

```
EMPLOYEE REJECTS SUGGESTION
│
├─ CPA reviews suggestion on /admin/approvals
├─ Clicks "❌ דחה" (Reject)
├─ Enters rejection reason
└─ Saves rejection

EMPLOYEE SEES REJECTED SUGGESTION
│
├─ Sidebar shows "הצעות שנדחו ❌ [1]" red badge
├─ Clicks badge → Goes to /portal/rejected
├─ Sees card with:
│  ├─ Original suggested text
│  ├─ CPA's rejection reason
│  └─ "✏️ ערוך והגש מחדש" button

EMPLOYEE EDITS AND RESUBMITS
│
├─ Clicks resubmit button
├─ Modal opens:
│  ├─ Custom tab active
│  ├─ Text pre-filled with original
│  └─ Employee edits text
├─ Clicks "שלח" (Submit)
└─ New suggestion created with PENDING status

BACK TO APPROVAL CYCLE
│
├─ CPA sees new suggestion on /admin/approvals
├─ Old rejection note cleared (new submission)
└─ Can approve or reject again
```

---

## API Endpoints Summary

### Employee Endpoints
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/suggestions` | Submit new suggestion |
| GET | `/api/suggestions/my` | Get my pending/approved suggestions |
| GET | `/api/suggestions/my-rejected` | **NEW:** Get my rejected suggestions |

### Admin Endpoints
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/suggestions/pending` | Get all pending suggestions |
| GET | `/api/suggestions/pending/count` | Get pending count |
| PATCH | `/api/suggestions/{id}/approve` | Approve a suggestion |
| PATCH | `/api/suggestions/{id}/reject` | Reject a suggestion |

---

## Key Features Implemented

✅ **Rejected Suggestions Page:**
- Shows all rejected suggestions with full details
- Displays CPA's rejection reason for context
- Color-coded (red for rejected)

✅ **Sidebar Badge:**
- Red badge showing count of rejected suggestions
- Auto-updates every 60 seconds
- Disappears when count = 0
- Only visible to employees

✅ **Edit & Resubmit:**
- Pre-fills old text in modal
- Allows employee to edit before resubmitting
- Creates new PENDING suggestion
- Clears old rejection note

✅ **Dashboard:**
- Employee can navigate directly from sidebar
- Clear layout with card-based design
- Empty state message when no rejections

---

## Testing Checklist

### Backend Testing
```bash
curl -H "Authorization: Bearer [TOKEN]" \
  http://127.0.0.1:8000/api/suggestions/my-rejected
```

**Expected Response:**
```json
[
  {
    "id": 5,
    "municipality_name": "עיר Y",
    "month": "2026-03",
    "topic_code": "3",
    "budget_line_name": "ילדים חזקי צו",
    "custom_text": "הוספו 2 ילדים חדשים",
    "preset_text": null,
    "review_note": "ההסבר לא מפורט מספיק",
    "suggestion_type": "custom",
    "created_at": "2026-04-03T...",
    "updated_at": "2026-04-03T...",
    "preset_id": null
  }
]
```

### Frontend Testing

1. **Test Sidebar Badge:**
   - Log in as employee
   - Have at least 1 rejected suggestion in DB
   - Sidebar should show "הצעות שנדחו ❌ [count]"
   - Badge should be red

2. **Test Navigation:**
   - Click badge or "הצעות שנדחו ❌"
   - Should navigate to `/portal/rejected`
   - Page should load with all rejected suggestions

3. **Test Edit & Resubmit:**
   - Click "✏️ ערוך והגש מחדש"
   - Modal should open with:
     - "custom" tab active
     - Text pre-filled
   - Edit the text
   - Click "שלח"
   - Suggestion should be resubmitted as PENDING

4. **Test Dashboard Update:**
   - After resubmitting, count should decrease
   - Badge should disappear if count = 0
   - Card should disappear from list

---

## Database

No new tables required! Uses existing:
- `explanation_suggestions` table
- Filters by `status = 'rejected'`

---

## Known Limitations

1. **Edit Modal:** Currently uses the standard modal. Could enhance to show:
   - Old text next to new (side-by-side comparison)
   - Strikethrough old text
   - Color highlighting

2. **Bulk Actions:** No bulk resubmit. Each suggestion must be edited individually.

3. **Answer History:** No history of previous submission attempts. Shows only latest version.

---

## Future Enhancements

💡 Possible improvements:
- Add filters (by municipality, date, type)
- Show rejection history/timeline
- Bulk operations (resubmit multiple)
- Search within rejected suggestions
- Email notification when rejected
- Auto-expire old rejections after 30 days

---

## Files Modified/Created

### Backend
- ✅ [backend/routes/suggestions.py](backend/routes/suggestions.py) - Added endpoint + schema

### Frontend
- ✅ [frontend/src/hooks/useRejectedSuggestionsCount.js](frontend/src/hooks/useRejectedSuggestionsCount.js) - NEW
- ✅ [frontend/src/pages/EmployeeRejectedPage.jsx](frontend/src/pages/EmployeeRejectedPage.jsx) - NEW
- ✅ [frontend/src/services/api.js](frontend/src/services/api.js) - Added method
- ✅ [frontend/src/App.jsx](frontend/src/App.jsx) - Added route
- ✅ [frontend/src/components/layout/Sidebar.jsx](frontend/src/components/layout/Sidebar.jsx) - Added employee items
- ✅ [frontend/src/components/portal/ExplanationSuggestionModal.jsx](frontend/src/components/portal/ExplanationSuggestionModal.jsx) - Enhanced with pre-fill

---

## Ready to Test! 🚀

Both servers running:
- ✅ Backend: `http://127.0.0.1:8000`
- ✅ Frontend: `http://127.0.0.1:3000`

Navigate to `/portal/rejected` or click the sidebar badge to test the feature!
