@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (
    echo Ejecuta primero INICIAR_WINDOWS.bat.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements_modelo.txt
if errorlevel 1 (
    echo No se pudo instalar Sentence-BERT.
    pause
    exit /b 1
)
python -c "from src.motor import cargar_modelo; m=cargar_modelo(); print('Modelo cargado correctamente')"
pause
