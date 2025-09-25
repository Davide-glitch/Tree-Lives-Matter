@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Project root
set ROOT=%~dp0
pushd "%ROOT%"

echo ============================================
echo  Tree Lives Matter - Dev Startup (Windows)
echo ============================================

echo [1/6] Setting up environment and backend...

REM Optional: Set blockchain/monitoring keys here (leave empty to skip those features)
REM Uncomment and fill these lines if you want to enable blockchain logging:
REM set INFURA_URL=https://sepolia.infura.io/v3/YOUR_INFURA_PROJECT_ID
REM set ACCOUNT_ADDRESS=0xYourEthereumAddress
REM set PRIVATE_KEY=your_private_key_here
REM set CONTRACT_ADDRESS=0xYourContractAddress
REM set SENTINEL_CLIENT_ID=your_sentinel_client_id
REM set SENTINEL_CLIENT_SECRET=your_sentinel_client_secret
REM set PINATA_API_KEY=your_pinata_api_key
REM set PINATA_SECRET_API_KEY=your_pinata_secret_key

cd backend
if not exist .venv (
  echo Creating Python virtual environment...
  where py >nul 2>&1 && (
    py -3 -m venv .venv
  ) || (
    where python >nul 2>&1 && (
      python -m venv .venv
    ) || (
      echo ERROR: Python 3 not found. Install from https://www.python.org/downloads/ and add to PATH.
      pause
      exit /b 1
    )
  )
)
if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
  set "PIP=.venv\Scripts\pip.exe"
) else (
  echo ERROR: Could not find Python venv interpreter.
  echo Please ensure the venv was created successfully.
  pause
  exit /b 1
)

"%PY%" -m pip install --upgrade pip >nul 2>&1
"%PIP%" install -r requirements.txt || (
  echo Failed to install backend requirements.
  pause
  exit /b 1
)

popd

echo [2/6] Ensuring Node.js and frontend deps...
cd frontend
where npm >nul 2>&1 || (
  echo ERROR: npm is not installed or not on PATH. Install Node.js LTS from https://nodejs.org/
  pause
  exit /b 1
)
if not exist node_modules (
  echo Installing npm packages...
  npm install || (
    echo npm install failed.
    pause
    exit /b 1
  )
) else (
  echo node_modules already present. Skipping npm install.
)
cd ..

echo [3/6] Starting backend (Flask) on port 5000...
start "Backend" cmd /k "cd /d "%ROOT%backend" && .venv\Scripts\python.exe run.py"

echo [4/6] Waiting 3 seconds for backend to boot...
PING -n 4 127.0.0.1 >nul

echo [5/6] Starting frontend (CRA) on port 3000...
start "Frontend" cmd /k "cd /d "%ROOT%frontend" && npm start"

echo [6/6] Opening browser tabs...
start "" http://localhost:5000/api/test
start "" http://localhost:3000

echo All set. Two console windows were opened for backend and frontend.
endlocal
exit /b 0
