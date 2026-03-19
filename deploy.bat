@echo off
cd C:\woozoo
git pull origin main
git add .
git commit -m "update"
git push origin main
echo.
echo Done!
pause
