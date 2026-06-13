@echo off
timeout /t 2 /nobreak > nul
setlocal enabledelayedexpansion

rem Получаем текущую дату и время
for /f "tokens=1-3 delims= " %%a in ('date /t') do set currentDate=%%a
for /f "tokens=1-2 delims=:" %%a in ('time /t') do set currentTime=%%a:%%b

rem Формируем сообщение коммита
set commitMessage=here !currentDate! !currentTime!

git status
git add .
git commit -m "!commitMessage!"
git push
pause
