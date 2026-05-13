@echo off
cd /d "C:\Users\ohashai\Documents\Claude\claude code Projects\SolarDomainHunter"

echo.
echo What did you change? (this becomes your commit message)
echo.
set /p MSG="Message: "

git add app.py requirements.txt README.md PROJECT_PLAN.md batch_scan.py
git commit -m "%MSG%"
git push

echo.
echo Done! Your code is on GitHub. Streamlit will update in ~60 seconds.
echo https://domainhunterai.streamlit.app
echo.
pause
