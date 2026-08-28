# Architecture Technique — Stack SaaS

## Frontend
- **Next.js 14+ (App Router)** — React, SSR/SSG, déploiement Vercel
- **Tailwind CSS + shadcn/ui** — UI pro rapide
- **Recharts** ou **Visx** — graphiques (heatmaps, corrélations, trends)

## Backend
- **Python + FastAPI** — async, rapide, écosystème data science (pandas, scikit-learn)
- Alternative : Node.js si tout TypeScript

## Database
- **PostgreSQL** (Supabase ou Neon)
- **Row-Level Security (RLS)** — chaque user ne voit que ses données. Critique pour SaaS bien-être.

## Privacy Layer (cœur du produit)
- **Differential Privacy** — bruit mathématique sur les agrégats. Librairies : Opacus (PyTorch) ou TensorFlow Privacy.
- **On-device processing** — données brutes restent sur l'appareil. Seuls les agrégats remontent.
- **Zero-knowledge architecture** — le cloud ne stocke jamais le contenu brut. Catégories + scores uniquement.

## Infrastructure
- **Vercel** (frontend) + **Railway** ou **Render** (backend Python)
- **Stripe** — paiements
- **Clerk** ou **Supabase Auth** — auth utilisateur

## Mobile (Phase 2)
- **React Native** / **Expo** — réutilise la logique React

## Modèle de données anonymisées

```
┌─ Appareil User ───────────────────┐
│                                  │
│  Données brutes :                │
│  • Humeur (2x/jour)              │
│  • URLs visitées                 │
│  • Usage apps (durée, fréquence) │
│  • Notifications reçues          │
│                                  │
│  TRAITEMENT ON-DEVICE            │
│  ────────────────────            │
│  1. Catégorisation des contenus  │
│     (NLP local : valence, topic) │
│  2. Agrégation par catégorie/jour│
│  3. Differential Privacy         │
│     (bruit Laplacien sur scores) │
│                                  │
└──────────────┬───────────────────┘
               │ Seuls les agrégats
               ▼
┌─ Cloud ──────────────────────────┐
│  Agrégats anonymisés :           │
│  • {catégorie, durée, score}     │
│  • jamais d'URL brute            │
│  • jamais de mood brut           │
│                                  │
│  → Benchmark population          │
│  → "Les gens qui lisent X        │
│    rapportent Y % plus de        │
│    fatigue le soir"              │
└──────────────────────────────────┘
```

## Collecte macOS (Phase 0) — points d'attention

- **knowledgeC.db** (`~/Library/Application Support/Knowledge/knowledgeC.db`) : base SQLite CoreDuet, lisible en lecture seule avec Full Disk Access. Usage apps, web usage, media, notifications.
- **Référence** : `iamEvanYT/macos-screen-time` (lit knowledgeC.db directement). À adapter en Python.
- **⚠️ Migration Biome** : depuis iOS 16 / macOS 13+, une partie des stats migre vers les Biome activity streams (`segb`, protobuf). À trancher sur le Mac cible en jour 1 — c'est le risque technique n°1 de la Phase 0.
- **Historique navigateur** : fichiers SQLite directs (Chrome `History`, Safari `History.db`) — source de contenu la plus riche pour la valence NLP, indépendante de Screen Time.
- **APIs officielles** : l'API Screen Time d'Apple est réservée aux apps parentales approuvées — non accessible pour un SaaS tiers normal. La lecture directe des bases est du private API territory → risque App Store ; acceptable en beta macOS standalone.
