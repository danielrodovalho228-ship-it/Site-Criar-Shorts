@echo off
REM ==========================================================
REM  Short Factory - iniciar o FRONTEND (o site / wizard)
REM  Basta dar duplo-clique neste arquivo (com o backend ja aberto).
REM ==========================================================
cd /d "%~dp0frontend"

where npm >nul 2>nul
if errorlevel 1 (
  echo.
  echo [ATENCAO] Node.js/npm nao encontrado.
  echo   Instale com:  winget install OpenJS.NodeJS.LTS
  echo   e FECHE e ABRA este arquivo de novo.
  echo.
  pause
  exit /b 1
)

if not exist "node_modules" (
  echo Instalando dependencias do frontend (so na primeira vez)...
  call npm install
)

echo.
echo ================================================================
echo  Frontend rodando em  http://localhost:5173
echo  Abra esse endereco no navegador.
echo  Deixe esta janela ABERTA. Feche-a para parar o site.
echo ================================================================
echo.
call npm run dev
pause
