# Phase 5 — Explanations Engine — Testing Guide

## 🎯 Test Overview

Phase 5 adds auto-generated explanations for each budget line, with CPA override capability.

---

## ✅ Manual Testing Steps

### Test 1: Auto-Generated Explanations (Municipality View)

**Setup:**
1. Start backend & frontend
2. Login as municipality user
3. Navigate to Budget Page
4. Select a month with data

**Verify:**
- [ ] Each budget line shows explanation indicator (📝 הצג הסבר)
- [ ] Click to expand shows blue explanation box
- [ ] Explanation text is in Hebrew
- [ ] Explanation matches the budget topic
  - For topic 101: Mentions kindergarten/ממלא/תשלום
  - For topic 202: Mentions special education/חינוך מיוחד
  - For topic 303: Mentions teacher hours/שעות נוסף
  - For topic 404: Mentions learning issues/ליקויי למידה
  - For topic 505: Mentions student transport/נסיעות תלמידים
- [ ] Different explanation for different line types:
  - Regular: Standard explanation
  - Retro: Includes month information (e.g., "עבור חודש דצמבר")
  - Shortage: Mentions shortfall amount
  - Adjustment: Explains adjustment reason
- [ ] Click to collapse hides explanation
- [ ] No edit pencil visible (municipalities are read-only)

### Test 2: Custom Explanations (CPA Admin View)

**Setup:**
1. Login as admin
2. Navigate to Municipality Page
3. Select a municipality and month
4. Look at any budget line

**Verify:**
- [ ] Budget line has explanation if data exists
- [ ] Hover over explanation shows pencil icon
- [ ] Click pencil → textarea appears
- [ ] Current explanation text appears in textarea
- [ ] Can edit the text
- [ ] Click "שמור" (Save) button
- [ ] Explanation saves and closes
- [ ] Badge "✏️ מותאם אישית" (Custom) appears
- [ ] Reloading page shows the custom explanation persists
- [ ] Delete custom explanation option available (or delete via API)

### Test 3: Retro Explanations

**Setup:**
1. Upload test data with retro payment (line_type = "retro")
2. View in portal
3. View in admin dashboard

**Verify:**
- [ ] Retro explanation includes the period month it covers
- [ ] Format: "תשלום רטרוספקטיבי עבור [month]"
- [ ] Row has yellow background (retro color)
- [ ] Can override with custom explanation
- [ ] Custom explanation displays properly

### Test 4: Shortage Explanations

**Setup:**
1. Upload test data with shortage (line_type = "shortage")
2. View in portal and admin

**Verify:**
- [ ] Shortage explanation includes amount shortfall
- [ ] Format: "חוסר בתשלום [$amount]"
- [ ] Row has red background (shortage color)
- [ ] Amount displays in NIS (₪)
- [ ] Can override with custom text

### Test 5: Adjustment Explanations

**Setup:**
1. Upload test data with adjustment (line_type = "adjustment")
2. View in both interfaces

**Verify:**
- [ ] Adjustment explanation explains the adjustment
- [ ] Row has blue background (adjustment color)
- [ ] Text is clear about what was adjusted

### Test 6: API Endpoints

**Test GET /explanations/{municipality_id}/{month}**
```bash
# Check that custom explanations return correctly
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/explanations/1/2024-03
```

Expected Response:
```json
{
  "101": {
    "custom_text": "התשלום לגנים דרש התאמה...",
    "id": 1,
    "created_at": "2024-03-30T10:00:00",
    "updated_at": "2024-03-30T10:00:00"
  }
}
```

**Test POST /explanations/{municipality_id}/{month}/{topic_code}**
```bash
# Create/update custom explanation
curl -X POST -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{"custom_text": "הסבר חדש וזה טוב"}' \
  http://localhost:8000/explanations/1/2024-03/101
```

Expected: 201 Created with explanation object

**Test DELETE /explanations/{municipality_id}/{month}/{topic_code}**
```bash
# Delete custom explanation (reverts to auto)
curl -X DELETE -H "Authorization: Bearer {admin_token}" \
  http://localhost:8000/explanations/1/2024-03/101
```

Expected: 204 No Content

### Test 7: Authorization

**Admin Access:**
- [ ] Admin user CAN edit explanations
- [ ] Admin user CAN create custom explanations
- [ ] Admin user CAN delete custom explanations

**Municipality Access:**
- [ ] Municipality user CAN view explanations
- [ ] Municipality user CANNOT edit explanations
- [ ] Municipality user CANNOT see edit button/pencil
- [ ] Municipality user sees read-only explanation
- [ ] If they try to POST to /explanations → 403 Forbidden

**Non-Authenticated:**
- [ ] GET without token → 401 Unauthorized
- [ ] POST without token → 401 Unauthorized

### Test 8: Database Verification

**Check custom_explanations table:**
```sql
SELECT * FROM custom_explanations;
```

Expected:
- [ ] Table exists
- [ ] Columns: id, municipality_id, month, topic_code, custom_text, created_at, updated_at
- [ ] Custom explanations saved after admin saves
- [ ] Foreign key to municipality_id works
- [ ] Unique constraint on (municipality_id, month, topic_code)

### Test 9: Hebrew Text Handling

- [ ] Explanation text displays correctly in RTL
- [ ] No mojibake (garbled characters like ???)
- [ ] Special Hebrew characters display: שׁ, שׂ, ״, ׳
- [ ] Copy-paste of explanation text works
- [ ] Export to Excel/CSV preserves Hebrew

### Test 10: Mobile Responsiveness

**On iPhone (Safari):**
- [ ] Explanation box displays without overflow
- [ ] Edit pencil is accessible
- [ ] Textarea expands properly
- [ ] Save button is tappable
- [ ] RTL layout is correct

**On Android (Chrome):**
- [ ] Same checks as iPhone
- [ ] Text input works smoothly
- [ ] No layout shifts

### Test 11: Edge Cases

**Empty Explanation:**
- [ ] If no budget line custom explanation → shows auto-generated
- [ ] If custom explanation is empty string → shows auto-generated

**Very Long Explanation:**
- [ ] Can save very long explanations (1000+ characters)
- [ ] Display wraps properly
- [ ] No truncation

**Special Characters:**
- [ ] Save explanation with quotes: "הסבר"
- [ ] Save with punctuation: הסבר, הסבר!
- [ ] Save with emojis: הסבר 💰
- [ ] All display correctly

**Multiple Municipalities:**
- [ ] Admin can set different custom explanations for each municipality
- [ ] Each municipality only sees their own custom explanations

---

## 📊 Expected Behavior Summary

### For Regular Budget Lines:
```
Auto-explanation: "תשלום סטנדרטי לנושא: [topic]"
Custom override: User can enter anything
Delete: Reverts to auto
Result: Clean, editable text
```

### For Retro Lines:
```
Auto-explanation: "תשלום רטרוספקטיבי עבור [month]"
Identifier: Yellow background, "רטרו" badge
Custom override: Can enhance with context
Result: Explains why payment is late
```

### For Shortage Lines:
```
Auto-explanation: "חוסר בתשלום בסך ₪[amount]"
Identifier: Red background, "חוסר" badge
Custom override: Can explain why shortage happened
Result: Clear about the problem
```

### For Adjustment Lines:
```
Auto-explanation: "התאמה לתשלום"
Identifier: Blue background, "התאמה" badge
Custom override: Can explain reason for adjustment
Result: Context for the change
```

---

## 🔄 Test Data Requirements

For comprehensive Phase 5 testing, ensure test data includes:

```python
# Sample budget lines needed:
test_lines = [
  # Regular payment
  { "topic_code": "101", "amount": 50000, "line_type": "regular" },
  # Retro from previous month
  { "topic_code": "202", "amount": 30000, "line_type": "retro", "period_month": "2024-02" },
  # Shortage (payment less than expected)
  { "topic_code": "303", "amount": -5000, "line_type": "shortage" },
  # Adjustment
  { "topic_code": "404", "amount": 2000, "line_type": "adjustment" },
  # Another topic
  { "topic_code": "505", "amount": 15000, "line_type": "regular" },
]
```

---

## 🚀 Sign-Off Checklist

- [ ] Auto-explanations generate for all 5 budget topics
- [ ] Explanations match the correct topic descriptions
- [ ] All 4 line types generate appropriate explanations
- [ ] Admin can create custom explanations
- [ ] Custom explanations persist in database
- [ ] Municipality users see final explanation (custom or auto)
- [ ] Municipality users cannot edit explanations
- [ ] Delete custom reverts to auto
- [ ] Hebrew text displays correctly
- [ ] API endpoints work with proper authorization
- [ ] Mobile displays correctly
- [ ] All edge cases handled

**When all checks pass:**
```
✅ Phase 5 — Explanations Engine — VERIFIED & READY FOR DEPLOYMENT
```
