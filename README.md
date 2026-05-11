# Custom AI Agent – Architecture ReAct Avancée

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a393.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-State_Graph-orange.svg)
![MongoDB](https://img.shields.io/badge/MongoDB-NoSQL-47A248.svg)

Un assistant virtuel autonome, modulaire et hautement réactif. Construit sur une architecture **ReAct** (Reason + Act), cet agent est capable d'interagir avec le monde extérieur (Web, Emails, Calendrier, Système de fichiers) tout en conservant une mémoire optimisée et un sas de validation humain pour les actions critiques.

---

## Architecture Technique

* **LangGraph** : Moteur de raisonnement basé sur des graphes d'état. Il permet de chaîner des étapes de traitement (logique, appels d’outils, prise de décision) de façon modulaire, cyclique et traçable.
* **FastAPI** : Serveur HTTP asynchrone et typé. Expose les points d’entrée de l’assistant via une API REST robuste, assurant une faible latence et intégrant nativement la documentation OpenAPI.
* **Groq** : Fournisseur de modèles de langage (LLM) offrant des temps d'inférence ultra-rapides, essentiels pour une interaction conversationnelle fluide en temps réel.
* **MongoDB** : Base de données NoSQL orientée document, utilisée pour la persistance des checkpoints LangGraph, le stockage des historiques de session et la gestion asynchrone de la mémoire.

---

## Fonctionnalités & Optimisations

* **Streaming en Temps Réel (SSE)** : Le backend FastAPI et le frontend communiquent via un flux continu (Server-Sent Events). L'affichage mot par mot des tokens générés par le LLM offre une expérience utilisateur ultra-fluide, sans temps d'attente lors de l'exécution des outils complexes.
* **Gestion Autonome de la Mémoire** : Intégration d'un nœud d'auto-compression. Pour prévenir la surcharge du contexte (*Token Limit*) et l'engorgement de la base de données, l'agent résume silencieusement les anciennes conversations en arrière-plan et purge les anciens nœuds MongoDB, tout en conservant le contexte global.
* **Sécurité Anti-Prompt Leaking & Hallucinations** : Le *Prompt Engineering* et les consignes système sont strictement cloisonnés. Des balises de sécurité invisibles empêchent le LLM de divulguer ses instructions internes ou d'inventer des données factuelles (*placeholder data*) sans faire appel à ses outils.
* **Human-in-the-Loop (HITL)** : Sas de sécurité bloquant l'exécution d'outils critiques (envoi d'emails, modifications d'agenda) tant qu'une validation humaine explicite n'a pas été interceptée.

---

## Outils Intégrés

L'agent dispose d'un arsenal d'outils lui permettant d'agir sur son environnement :

| Nom de l'outil | Fonction | Cas d'usage |
|---|---|---|
| `list_directory_contents` | Navigation locale (`ls`) | Vérification instantanée des fichiers présents dans le répertoire courant de l'agent. |
| `search_local_file` | Recherche globale (`find`) | Recherche récursive d'un fichier spécifique sur le système pour récupérer son chemin absolu. |
| `read_local_document` | Lecture de fichiers locaux (.txt, .pdf) | Analyse et extraction de contenu de documents fournis par l’utilisateur. |
| `internet_search` | Recherche web via Tavily | Récupération de données factuelles, actualités en temps réel. |
| `get_current_time` | Horodatage système | Planification, repères temporels pour la création d'événements. |
| `scrape_web_page` | Scraping d’URL spécifique | Extraction du contenu brut d'une page web donnée. |
| `read_recent_emails` | Lecture IMAP de la boîte de réception | Analyse, recherche et résumé des derniers messages reçus. |
| `send_email` | Envoi d'emails via SMTP Google | Rédaction et envoi de courriels (protégé par HITL). |
| `read_upcoming_events` | Lecture via API Google Calendar | Consultation de l'emploi du temps avec authentification OAuth 2.0. |
| `Calendar` | Écriture via API Google Calendar | Ajout d'événements, réunions et rappels (protégé par HITL). |

---

## Principes de Conception

1. **Modularité** : Le découplage des composants (Frontend, API FastAPI, Graphe de raisonnement, Outils) facilite les tests unitaires et la maintenance.
2. **Scalabilité** : L'utilisation de l'asynchrone (`async`/`await`) sur l'ensemble de la pile et la flexibilité de MongoDB permettent une mise à l'échelle aisée.
3. **Sécurité First** : Gestion stricte des intentions (ex: pas d'appel API coûteux pour de simples salutations), protection des secrets via `.env`, et obligation de validation humaine pour les actions impactantes.
4. **Extensibilité** : L'ajout d'une nouvelle capacité à l'agent se fait simplement par la création d'une fonction Python documentée et son injection dans la liste des nœuds LangGraph.

---

## Déploiement & Configuration

### Prérequis
* Python 3.10+
* Docker & Docker Compose (Recommandé pour MongoDB)

### Variables d'environnement (`.env`)
À la racine du projet, créez un fichier `.env` contenant les clés suivantes :

# API Keys
GROQ_API_KEY=votre_cle_groq
TAVILY_API_KEY=votre_cle_tavily

# Base de données
URI_MONGODB=mongodb://localhost:27017

# SMTP / IMAP (Envoi et lecture d'emails)
EMAIL_ADDRESS=votre_email@gmail.com
EMAIL_PASSWORD=votre_mot_de_passe_d_application

### Authentification Google Calendar (OAuth 2.0)

Pour utiliser les outils d'agenda, vous devez configurer un écran de consentement OAuth sur la [Google Cloud Console](https://console.cloud.google.com/) et placer le fichier **`credentials.json`** téléchargé à la racine du projet. Un fichier `token.json` sera généré automatiquement lors de la première connexion. **Attention :** Ces deux fichiers doivent figurer dans votre `.gitignore`.

### Lancement Local

# 1. Démarrer la base de données MongoDB (si utilisation de Docker)
docker-compose up -d

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Lancer le serveur backend
uvicorn api:app --reload

Ce projet suit des normes strictes de développement. Toute modification du graphe d'état doit être accompagnée de tests pour s'assurer que les barrières de sécurité et le compresseur de mémoire restent fonctionnels.