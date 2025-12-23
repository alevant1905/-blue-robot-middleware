@echo off
echo ========================================
echo Restarting Blue with Fresh Code
echo ========================================
echo.

echo Step 1: Clearing Python cache...
FOR /d /r . %%d IN (__pycache__) DO @IF EXIST "%%d" rd /s /q "%%d"
del /s /q *.pyc 2>nul
echo   Done!
echo.

echo Step 2: Verifying settings...
python -c "import bluetools; s = bluetools._settings; print('  USE_STRICT_TOOL_FORCING:', s.USE_STRICT_TOOL_FORCING); print('  MAX_ITERATIONS:', s.MAX_ITERATIONS)"
echo.

echo Step 3: Starting Blue...
echo.
python run.py
