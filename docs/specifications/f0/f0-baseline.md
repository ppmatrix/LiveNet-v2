# LiveNet v2 — F0 Technical Baseline

Status: Working draft
Date: 2026-10-15

## 1. Approved architecture

- New project, independent of LiveNet v1
- Modular monolith
- Agentless-first architecture
- Backend: Flask
- Frontend: React, TypeScript, Vite
- Database: PostgreSQL
- Asynchronous processing: Celery and Redis
- Database migrations: Alembic
- API: REST and Server-Sent Events
- Local deployment: Docker Compose
- CI/CD: GitHub Actions
- Container registry: GitHub Container Registry

## 2. Development environments

- Development: progbox
- Staging: dedicated Proxmox VM
- Production: dedicated VM
- Kubernetes: conditional future adoption

## 3. Scalability

- Initial deployment: fewer than 100 resources
- Architectural preparation: 100–1,000 resources
- Avoid unnecessary complexity and resource consumption

## 4. Roadmap

- F0: Technical Foundation
- F1: Inventory, Integrations and Discovery
- F2: Monitoring and Alerts
- F3: Operations
- F4: Lifecycle
- F5: Consolidation, Security and Production

## 5. Future security monitoring

D-52: Security Monitoring / SIEM

- Architecture must support future integration
- Implementation deferred until after MVP
- No SIEM dependency in the initial MVP

## 6. Pending documentation

- Full verified transcription of D-01 through D-52
- Consolidation of the 16 approved technical chapters
- Preservation of identified technical gaps
- Detailed F0 acceptance criteria
- Verification of module contracts and data model

No implementation decisions may be inferred from missing details.
