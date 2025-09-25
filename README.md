# Tree Lives Matter - Local Development

This project has a Flask backend and a React (Create React App) frontend.

## Prerequisites Installation (First Time Setup)

If you don't have Python and Node.js installed, use the automated installer:

```powershell
# Right-click and "Run as administrator"
./install.bat
```

This script will automatically install:

- Python 3.11+ (for Flask backend)
- Node.js LTS + npm (for React frontend)

## Quick start (Windows)

After prerequisites are installed, use the batch script at the repo root:

```powershell
# From the project root
./start.bat
```

What it does:

- Creates Python virtual environment in `backend/.venv` if missing
- Installs backend Python dependencies from `backend/requirements.txt`
- Installs frontend npm packages in `frontend/` if `node_modules` is missing
- Starts backend on http://localhost:5000 and frontend on http://localhost:3000
- Opens browser tabs to the API test endpoint and the app

If you prefer manual steps, see `frontend/README.md` for commands.

## Optional keys (only if you want the full "magic")

The app runs without any external keys: alerts can be created on the map and will appear automatically on the Public/User/Admin pages every ~15 seconds.

If you want the extra monitoring pipeline and AI assistant:

- Backend monitoring (optional): copy `backend/.env.example` to `backend/.env` and fill in values you have:
  - SENTINEL_CLIENT_ID, SENTINEL_CLIENT_SECRET (Sentinel Hub)
  - PINATA_API_KEY, PINATA_SECRET_API_KEY (Pinata IPFS)
  - INFURA_URL, ACCOUNT_ADDRESS, PRIVATE_KEY, CONTRACT_ADDRESS (Ethereum Sepolia)
  - All are optional. Missing keys simply skip that step; nothing breaks.
- Frontend AI (optional): open the AI widget, paste your Groq API key (gsk\_...) in the key input; it's stored locally in your browser only.

Where to put keys:

- Backend: `backend/.env` file (never commit it). The script `alert.py` will read it automatically.
- Frontend (Groq): Use the UI input under the AI section; we do not store it server-side.

## Do I need Remix or Solidity?

- Remix (the desktop app) and the Solidity compiler are tools for Ethereum smart contract development. This project does not include any Solidity or blockchain components, so you do not need Remix or a Solidity compiler.
- If you later decide to integrate blockchain features (e.g., recording alerts on-chain), we can revisit and set up the appropriate tooling.

## Troubleshooting

**Missing Prerequisites:**

- Run `install.bat` as administrator to auto-install Python and Node.js
- Manual install: Node.js LTS from https://nodejs.org/ and Python 3.x from https://www.python.org/downloads/

**Runtime Issues:**

- Port conflicts: backend uses 5000, frontend uses 3000. Close other apps occupying these ports or change the ports if needed.
- API test: http://localhost:5000/api/test should return JSON `{ message: "Backend connected successfully!", ... }`
