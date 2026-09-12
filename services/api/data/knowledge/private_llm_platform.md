# Private LLM Platform

Private LLM Platform est une plateforme privée de gestion, déploiement,
benchmarking et supervision de modèles LLM.

## Composants
- Frontend React.
- API backend FastAPI.
- Ollama pour l'inférence locale.
- vLLM pour les environnements GPU.
- Kubernetes pour l'orchestration.
- Prometheus pour les métriques.
- Grafana pour la visualisation.
- Alertmanager pour les alertes.
- GitHub Actions pour la CI/CD.
- GHCR pour les images de conteneurs.
- Assistant documentaire RAG.

## RAG
L'assistant recherche d'abord des passages ou enregistrements pertinents
dans la base documentaire locale. Le contexte retrouvé est ensuite transmis
au modèle Ollama pour produire une réponse accompagnée de sources.

## DevOps
La contribution DevOps comprend Docker, Kubernetes, stockage persistant,
Ingress, RBAC, Secrets, NetworkPolicies, HPA, PDB, monitoring,
CI/CD et validation des manifests.
