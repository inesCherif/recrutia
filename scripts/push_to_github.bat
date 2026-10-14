@echo off
echo ==========================================
echo 🚀 Recrutia - Automation GitHub
echo ==========================================

:: 1. Initialisation
if not exist .git (
    echo [1/5] Initialisation du depot Git...
    git init
) else (
    echo [1/5] Depot Git deja initialise via .git
)

:: 2. Ajout des fichiers
echo.
echo [2/5] Ajout des fichiers...
git add .

:: 3. Commit
echo.
echo [3/5] Creation du commit...
set /p commit_msg="Entrez le message du commit (defaut: 'Mise a jour Recrutia'): "
if "%commit_msg%"=="" set commit_msg=Mise a jour Recrutia
git commit -m "%commit_msg%"

:: 4. Configuration du Remote
echo.
echo [4/5] Configuration du Remote...
git remote -v > nul 2>&1
if %errorlevel% neq 0 (
    echo Configuration de l'URL distant...
    git remote add origin https://github.com/inesCherif/recrutia.git
) else (
    echo Remote 'origin' deja configure.
)

:: 5. Push
echo.
echo [5/5] Envoi vers GitHub...
git branch -M main
git push -u origin main

echo.
echo ✅ Termine !
pause
