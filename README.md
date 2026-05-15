# Mini Agent IA - Orchestration Multi-Agents avec LangGraph

Ce projet est un système d'Intelligence Artificielle **Multi-Agents** modulaire, réactif et autonome. Construit avec **LangGraph** et propulsé par l'API **Groq**, il orchestre une équipe d'agents spécialisés capables d'interagir avec le système local, d'effectuer des recherches sur le web, de gérer des e-mails/calendriers et de maintenir une conversation fluide avec l'utilisateur.

## Fonctionnalités Clés

* **Orchestration Intelligente (Le Superviseur) :** Un agent routeur qui analyse les requêtes et délègue les tâches au bon expert (Système, Web ou Général), avec un système **Anti-Boucle (Anti-Loop Shield)** robuste codé en Python pour éviter les plantages de l'IA.
* **🛠️ Séparation des Responsabilités (Experts) :**
  * **System Agent :** Spécialiste de l'ordinateur local (lecture/écriture de fichiers, exécution de commandes terminal, ouverture de liens/applications).
  * **Web Agent :** Spécialiste externe (recherches internet, e-mails, agenda).
  * **General Agent :** "Concierge" de l'application chargé de l'accueil et des bavardages.
* **Gestion Avancée de la Mémoire :**
  * **Persistance :** Sauvegarde des conversations dans une base de données **MongoDB** (Thread ID).
  * **Compresseur de Mémoire (Garbage Collector) :** Un nœud spécifique (`summarizer`) qui résume automatiquement les anciennes conversations pour économiser les tokens et éviter les crashs (Rate Limits) lors de l'analyse de gros fichiers.
* **⚡ Interface Temps Réel :** Un backend **FastAPI** qui stream les réponses des agents en direct (SSE - Server-Sent Events) vers l'interface utilisateur.

## Architecture du Projet

Le flux de travail (StateGraph) est modélisé comme suit :
1. L'utilisateur envoie un message (via FastAPI).
2. Le **Superviseur** analyse la demande et décide du prochain agent (`next_agent`).
3. L'expert désigné (`system_agent`, `web_agent`, ou `general_agent`) réfléchit. S'il a besoin d'outils, il passe par la **Tool Room** (Salle des machines) et récupère les résultats.
4. Une fois la tâche terminée, le dossier retourne au Superviseur.
5. Si tout est fini, le Superviseur choisit `FINISH`. Le graphe passe alors par le **Summarizer** (si la conversation est longue) avant de terminer la boucle.

### Structure des fichiers

* `state.py` : Définit la mémoire partagée (`AgentState`) entre les agents.
* `graph.py` : Le cœur du réacteur. Contient les prompts des agents, les règles de routage, le bouclier anti-boucle et la définition du graphe LangGraph.
* `tools.py` : Les fonctions Python exécutables par les IA (Recherche web, Terminal, Fichiers, etc.).
* `api.py` : Le serveur FastAPI qui gère les requêtes Web, la base de données MongoDB et le streaming.
* `index.html` : L'interface utilisateur (Frontend) pour discuter avec l'agent.

## Prérequis et Installation

### 1. Variables d'environnement
Créez un fichier `.env` à la racine du projet en vous basant sur le fichier `.env.example`. Vous aurez besoin de :
* Clé API Groq (`GROQ_API_KEY`)
* Clé API Tavily pour la recherche web (`TAVILY_API_KEY`)
* URI de votre base de données MongoDB (`URI_MONGODB`)

### 2. Installation des dépendances
Il est recommandé d'utiliser `uv` pour installer les dépendances du projet :
```bash
uv init
source .venv/bin/activate
uv pip install fastapi uvicorn langchain langchain-groq langgraph pymongo python-dotenv pydantic
# Lancement Local

docker-compose up -d

pip install -r requirements.txt

uvicorn api:app --reload