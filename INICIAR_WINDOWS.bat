@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -m venv .venv
) else (
    python -m venv .venv
)
if errorlevel 1 (
    echo No se pudo crear el entorno. Instala Python 3.11 o 3.12.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Error al instalar dependencias. Comprueba Internet.
    pause
    exit /b 1
)
python -m streamlit run app.py
pause
