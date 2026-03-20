@echo off
chcp 65001 > nul
cls
echo ============================================================
echo   Woozoo Deploy
echo ============================================================
echo.

cd C:\woozoo

echo [1/3] Git Add...
git add .
echo Done
echo.

echo [2/3] Git Commit...
git commit -m "Update"
echo Done
echo.

echo [3/3] Git Push...
git push origin main
if errorlevel 1 (
    echo.
    echo Error: Push Failed
    pause
    exit /b 1
)
echo Done
echo.

echo ============================================================
echo   Deploy Complete!
echo   Vercel auto-build started (1-2 min)
echo ============================================================
echo.
pause
