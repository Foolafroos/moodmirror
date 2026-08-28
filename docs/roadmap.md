# Roadmap & Tasks

## Phase 0 — Prototype local (MAINTENANT)
- [ ] Prototype Python + SQLite pour valider la collecte
- [ ] Explorer APIs macOS (ScreenTime, browser history)
- [ ] Définir schéma de données
- [ ] Valider le pipeline : collecte → agrégation → visualisation

**Durée estimée** : 1-2 semaines

> ⚠️ La collecte macOS passe par `knowledgeC.db` (Full Disk Access requis). Depuis macOS 13+, une partie des stats migre vers les streams Biome (`segb`). À valider sur le Mac cible en premier. Voir [research.md](research.md) → Collecte macOS.

## Phase 1 — Backend SaaS
- [ ] FastAPI + PostgreSQL (Supabase/Neon)
- [ ] Row-Level Security activée
- [ ] Auth utilisateur (Clerk ou Supabase Auth)
- [ ] API REST pour sync des agrégats

**Durée estimée** : 2-3 semaines

## Phase 2 — Frontend Dashboard
- [ ] Next.js 14 + Tailwind + shadcn/ui
- [ ] Dashboard : heatmaps, corrélations, trends
- [ ] Graphiques avec Recharts/Visx
- [ ] Onboarding utilisateur

**Durée estimée** : 3-4 semaines

## Phase 3 — Collecte (extension / app)
- [ ] Extension browser (Chrome/Firefox) pour capture URLs
- [ ] App macOS pour usage apps + mood input
- [ ] Traitement on-device (catégorisation, diff privacy)
- [ ] Sync cloud des agrégats anonymisés

**Durée estimée** : 2-3 semaines

## Phase 4 — Privacy Layer
- [ ] Differential Privacy (Opacus / TF Privacy)
- [ ] Hash URLs côté client
- [ ] Audit sécurité + compliance GDPR
- [ ] Documentation privacy transparente

**Durée estimée** : 2 semaines

## Phase 5 — Lancement
- [ ] Beta fermée (invite-only)
- [ ] Stripe integration (pricing tiers)
