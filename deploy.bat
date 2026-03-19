@echo off
cd C:\woozoo
echo GitHub에서 최신 버전 가져오는 중...
git pull origin main
echo.
echo 변경사항 업로드 중...
git add .
git commit -m "update"
git push origin main
echo.
echo 배포 완료!
pause
