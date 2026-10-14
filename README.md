# 🤖 Recrutia

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![React](https://img.shields.io/badge/React-Frontend-61DAFB)
![AI Agents](https://img.shields.io/badge/AI-Multi--Agent-orange)

**Recrutia** est une plateforme de recrutement de nouvelle génération, propulsée par un écosystème **Multi-Agents** basé sur Mistral AI.

Elle réunit **Recruteurs** et **Étudiants/Candidats** dans une interface conversationnelle unifiée ("Chat-First"), automatisant l'intégralité du pipeline de recrutement et de recherche d'emploi.

> 🚀 **Projet PFA** - Architecture Modulaire & Intelligence Artificielle de Pointe

## 👥 Équipe

- **HAJJI Neyssem**
- **HRAGHI Mohamed Aziz**

---

## 💡 Le Problème
- **Recruteurs** : Perte de temps sur la rédaction d'offres, le tri des CVs et la gestion des emails.
- **Candidats** : Difficulté à trouver des offres pertinentes et à adapter leur CV à chaque poste.

## ✨ La Solution Recrutia

L'application détecte automatiquement votre rôle (via NLP) et active les agents appropriés.

### 👔 Espace Recruteur 
- **✍️ Génération de Contenu** : Création automatique de posts LinkedIn viraux optimisés pour l'engagement.
- **📊 Analyse de Candidatures** : Parsing de CVs, scoring de pertinence et tri automatique.
- **📅 Gestion Automatisée** : Envoi d'emails de convocation ou de refus personnalisés.
- **📝 Formulaires Intelligents** : Création de questionnaires de pré-qualification.


### 🎓 Espace Candidat (Étudiant/Freelance)
*Propulsé par un système Multi-Agents (7 agents spécialisés)*
- **🧠 Analyse de Profil** : Extraction des compétences techniques et soft skills du CV.
- **🕵️ Recherche de Job IA** : Scraping temps réel sur 4 sources majeures :
  - **LinkedIn** (Offres publiques)
  - **RemoteOK** (API JSON)
  - **WeWorkRemotely** (Remote only)
  - **Adzuna** (Agrégateur)
- **🎯 Matching Intelligent** : Calcul de compatibilité (Score %) entre le CV et l'offre.
- **⚡ Optimisation** : Conseils pour améliorer le CV en fonction de l'offre visée.

---

## 🛠️ Stack Technique

| Couche | Technologie |
|--------|-------------|
| **Backend** | [FastAPI](https://fastapi.tiangolo.com/) (Python) |
| **Frontend** | [React](https://react.dev/) + [Vite](https://vite.dev/) |
| **LLM & IA** | Mistral AI |
| **Orchestration** | Architecture modulaire personnalisée |
| **Scraping** | Beautiful Soup 4, python-jobspy, Requests |
| **Base de données** | SQLite (`data/recrutia.db`) |

---

## 🚀 Installation & Lancement

### Prérequis

- **Python 3.9+** → [Télécharger](https://www.python.org/downloads/)
- **Node.js 18+** → [Télécharger](https://nodejs.org/)
- **Git** → [Télécharger](https://git-scm.com/)

### 1. Cloner le projet

```bash
git clone https://github.com/inesCherif/recrutia.git
cd recrutia
```

### 2. Backend (FastAPI)

```bash
# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement virtuel
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# Windows (CMD)
.\venv\Scripts\activate.bat
# Mac/Linux
source venv/bin/activate

# Installer les dépendances Python
pip install -r requirements.txt
```

### 3. Frontend (React + Vite)

```bash
# Dans un nouveau terminal
cd frontend

# Installer les dépendances Node
npm install
```

### 4. Configuration

Créez un fichier `.env` à la racine du projet :

```env
# Clés API requises
MISTRAL_API_KEY=votre_cle_mistral

# Optionnel
HUGGINGFACE_TOKEN=votre_token_hf
```

### 5. Lancer l'application

Vous devez lancer **2 terminaux** :

**Terminal 1 — Backend :**
```bash
# Depuis la racine du projet (avec le venv activé)
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend :**
```bash
# Depuis le dossier frontend
cd frontend
npm run dev
```

L'application sera accessible sur :
- 🖥️ **Frontend** : `http://localhost:5173`
- ⚙️ **API Backend** : `http://localhost:8000`
- 📚 **API Docs** : `http://localhost:8000/docs`

---

## ⚠️ Erreurs Courantes

| Erreur | Solution |
|--------|----------|
| `uvicorn : terme non reconnu` | Activez le venv puis faites `pip install -r requirements.txt` |
| `npm: command not found` | Installez [Node.js](https://nodejs.org/) |
| `Module not found` (Python) | Vérifiez que le venv est activé (`pip list` pour vérifier) |
| `CORS error` dans le navigateur | Assurez-vous que le backend tourne sur le port 8000 |

---

## 🏗️ Architecture des Dossiers

```text
Recrutia/
├── backend/                # API FastAPI
│   ├── main.py             # Point d'entrée FastAPI
│   ├── routes/             # Endpoints API
│   └── ...
├── frontend/               # Application React + Vite
│   ├── src/
│   │   ├── App.jsx         # Composant principal
│   │   ├── pages/          # Pages de l'application
│   │   └── components/     # Composants réutilisables
│   └── package.json
├── agents/                 # Agents IA
│   ├── core/               # Orchestrateur & compréhension
│   ├── entrepreneur/       # Agents Recruteur
│   └── student/            # Agents Candidat
├── config/                 # Configuration (settings.py)
├── models/                 # Schémas de données (Pydantic)
├── services/               # Services (Authentification)
├── utils/                  # Utilitaires (Logger, Clients API)
├── data/                   # Données persistantes
├── scripts/                # Scripts utilitaires
├── tests/                  # Tests unitaires
├── requirements.txt        # Dépendances Python
└── .env                    # Variables d'environnement (non versionné)
```

---

*Développé avec ❤️ pour le PFA*
