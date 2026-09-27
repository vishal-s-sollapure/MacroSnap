# MacroSnap - Project Environment Setup

Follow these commands in your terminal to set up the Python virtual environment and install project dependencies.

---

## 🚀 Step-by-Step Setup

### 1️⃣ Open Terminal / Command Prompt
Navigate to your project directory:
```bash
cd path/to/MacroSnap
```

---

### 2️⃣ Create the Virtual Environment

**Windows:**
```powershell
python -m venv venv
```
*(If `python` is not recognized, try `py -m venv venv`)*

**macOS / Linux:**
```bash
python3 -m venv venv
```

---

### 3️⃣ Activate the Virtual Environment

**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt / `cmd`):**
```cmd
venv\Scripts\activate.bat
```

**macOS / Linux (Bash / Zsh):**
```bash
source venv/bin/activate
```

> **Note:** Once activated, you should see `(venv)` prepended to your terminal prompt line.

---

### 4️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## ⚡ Quick One-Click Setup Scripts

Alternatively, run the automated setup script for your OS:

- **Windows (Command Prompt):** Double-click or run `setup_env.bat`
- **Windows (PowerShell):** Run `.\setup_env.ps1`
- **macOS / Linux:** Run `bash setup_env.sh`

---

## 🛑 Deactivating the Environment

When you are done working on the project, deactivate the virtual environment by running:
```bash
deactivate
```
