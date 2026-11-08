@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.13 -m venv .venv
  if errorlevel 1 python -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
  echo No se pudo crear el entorno. Instala Python 3.13 y vuelve a intentar.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo No se completaron las dependencias. Revisa tu conexion a Internet.
  pause
  exit /b 1
)
echo Abre http://127.0.0.1:5000 en tu navegador.
echo Deja esta ventana abierta mientras usas Nexo Lab.
start "" http://127.0.0.1:5000
".venv\Scripts\python.exe" app.py
pause
