@echo off
REM ==========================================================
REM  Short Factory - iniciar o BACKEND (API + motor de render)
REM  Basta dar duplo-clique neste arquivo.
REM ==========================================================
cd /d "%~dp0backend"

where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo.
  echo [ATENCAO] ffmpeg nao encontrado no PATH.
  echo   Instale com:  winget install ffmpeg
  echo   e FECHE e ABRA este arquivo de novo.
  echo.
  pause
  exit /b 1
)

if not exist ".venv" (
  echo Criando ambiente Python (.venv)...
  python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Instalando/atualizando dependencias do backend...
pip install -q -r requirements.txt

echo.
echo ================================================================
echo  Backend rodando em  http://localhost:8000
echo  Deixe esta janela ABERTA. Feche-a para parar o backend.
echo ================================================================
echo.
uvicorn main:app --port 8000
pause
