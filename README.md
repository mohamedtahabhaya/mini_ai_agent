# Présentation du projet

## Architecture

- **LangGraph** : moteur de raisonnement basé sur des graphes de flux, permettant de chaîner des étapes de traitement (ex. logique, appels d’outils, prise de décision) de façon modulaire et traçable.
- **FastAPI** : serveur HTTP ultra‑rapide, asynchrone et typé, qui expose les points d’entrée de l’assistant (API REST) tout en assurant validation, documentation OpenAPI et haute performance.
- **Groq** : modèle de génération de texte à la pointe, utilisé comme moteur de génération de réponses. Il offre des temps de latence très faibles, idéal pour des interactions en temps réel.
- **MongoDB** : base de données NoSQL document‑oriented, stocke les historiques de conversations, les configurations utilisateur et tout autre artefact persistant du système.

## Outils intégrés

| Outil | Fonction | Usage dans le projet |
|-------|----------|----------------------|
| `internet_search` | Recherche d’informations récentes sur le web via l’API Tavily | Récupération de données factuelles, dates d’événements, actualités, etc. |
| `read_local_document` | Lecture de fichiers texte ou PDF locaux | Extraction de contenu de documents fournis par l’utilisateur (ex. PDF de confirmation) |
| `get_current_time` | Obtention de la date et de l’heure exactes | Gestion des horodatages, réponses dépendant du temps, planification |
| `scrape_web_page` | Scraping d’une page web à partir d’une URL | Extraction de texte brut depuis des pages web spécifiques lorsque l’utilisateur fournit un lien |

## Principes de conception

- **Modularité** : chaque composant (graphes de raisonnement, API, stockage) est découplé, facilitant les tests unitaires et les évolutions futures.
- **Scalabilité** : FastAPI gère la concurrence grâce à `async`, tandis que MongoDB assure une persistance horizontale.
- **Sécurité** : les appels aux outils sont strictement contrôlés (ex. pas de recherche internet pour les simples salutations) afin de limiter les coûts et les risques.
- **Extensibilité** : la couche LangGraph permet d’ajouter de nouveaux nœuds (ex. appel à un service de traduction) sans toucher au reste du code.

## Déploiement

1. **Docker** (optionnel) – conteneuriser FastAPI, MongoDB et les dépendances Python.
2. **CI/CD** – pipelines automatisés pour les tests, le linting et le déploiement sur un environnement cloud.
3. **Configuration** – variables d’environnement pour les clés API (Groq, Tavily, etc.) et les paramètres de connexion MongoDB.

---

*Ce README décrit l’architecture actuelle et les outils mis à disposition de l’assistant. Toute modification ou extension doit suivre les bonnes pratiques de documentation et de tests.*