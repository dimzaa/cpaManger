# 🚀 How to Run Everything (PowerShell Version)

## 🪟 Windows PowerShell — 3 Easy Steps

### Step 1️⃣: First Time Setup (Run Once)

```powershell
# Open PowerShell in your project folder, then:
.\setup.ps1
```

✅ This will:
- Install Python dependencies
- Install Node modules
- Create `.env` files
- Takes ~2-3 minutes

### Step 2️⃣: Run All Tests

```powershell
.\run_tests.ps1
```

✅ This will:
- Run backend integration tests
- Build frontend
- Show if everything works

### Step 3️⃣: Start Development Servers

```powershell
.\start_servers.ps1
```

✅ This will:
- Open backend in new terminal (port 8000)
- Open frontend in new terminal (port 5173)
- You just go to http://localhost:5173 in browser

---

## If PowerShell Scripts Don't Work...

### Issue: "cannot be loaded because running scripts is disabled"

**Fix:** Run this ONE TIME:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try again:
```powershell
.\setup.ps1
```

---

## If You Get Permission Errors...

**Option 1: Run as Administrator**
1. Right-click PowerShell
2. Select "Run as Administrator"
3. Then run the scripts

**Option 2: Manual Commands**

If scripts still don't work, you can type the commands manually:

```powershell
# Setup
python -m venv backend\venv
backend\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
cd frontend
npm install

# Run tests
cd backend
python test_integration.py
cd ..\frontend
npm run build

# Start servers (each in new terminal)
# Terminal 1:
backend\venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload

# Terminal 2:
cd frontend
npm run dev
```

---

## Where Are These Files?

In your project folder:
```
c:\Users\zahal\OneDrive\cpa\
├── setup.ps1              ← Double-click or .\setup.ps1
├── run_tests.ps1          ← Double-click or .\run_tests.ps1
├── start_servers.ps1      ← Double-click or .\start_servers.ps1
├── backend/
├── frontend/
└── ... (other files)
```

---

## Quick Reference

| Want to... | Run this |
|-----------|----------|
| **Setup first time** | `.\setup.ps1` |
| **Run all tests** | `.\run_tests.ps1` |
| **Start coding** | `.\start_servers.ps1` |
| **Check Python installed** | `python --version` |
| **Check Node installed** | `node --version` |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Scripts won't run | See "PowerShell Scripts Don't Work" section above |
| Python not found | Install from https://python.org (check "Add to PATH") |
| Node not found | Install from https://nodejs.org (LTS version) |
| Port 8000 in use | Change backend port (edit in start_servers.ps1) |
| npm install fails | Delete `frontend\node_modules` folder, try again |

---

## Still Stuck?

Try this simple check:

```powershell
# In PowerShell, type:
python --version    # Should show Python 3.x.x
node --version      # Should show v18.x.x or higher
npm --version       # Should show 8.x.x or higher
```

If any of those don't work, that software isn't installed yet.

**Don't have them?**
- Python: https://python.org
- Node.js: https://nodejs.org (download LTS)
- After installing, restart PowerShell

---

## That's It! 🎉

- `.\setup.ps1` → Install everything
- `.\run_tests.ps1` → Verify it works
- `.\start_servers.ps1` → Start coding

Questions? Check SETUP_GUIDE.md or QUICK_START.md
