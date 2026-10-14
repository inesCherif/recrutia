#!/bin/bash

echo "=========================================="
echo "🚀 Recrutia - Automation GitHub"
echo "=========================================="

# 1. Initialisation
if [ ! -d ".git" ]; then
    echo "[1/5] Initialisation du dépôt Git..."
    git init
else
    echo "[1/5] Dépôt Git déjà initialisé."
fi

# 2. Ajout des fichiers
echo ""
echo "[2/5] Ajout des fichiers..."
git add .

# 3. Commit
echo ""
echo "[3/5] Création du commit..."
read -p "Entrez le message du commit (défaut: 'Mise à jour Recrutia'): " commit_msg
commit_msg=${commit_msg:-"Mise à jour Recrutia"}
git commit -m "$commit_msg"

# 4. Configuration du Remote
echo ""
echo "[4/5] Configuration du Remote..."
if ! git remote | grep -q origin; then
    echo "Configuration de l'URL distant..."
    git remote add origin https://github.com/inesCherif/recrutia.git
else
    echo "Remote 'origin' déjà configuré."
fi

# 5. Push
echo ""
echo "[5/5] Envoi vers GitHub..."
git branch -M main
git push -u origin main

echo ""
echo "✅ Terminé !"
