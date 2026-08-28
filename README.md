# MoodMirror

> **Le "SEO de l'âme."** Un SaaS *privacy-first* qui mesure l'impact réel du contenu que tu consumes sur ton humeur — et t'apprend à faire des choix plus sains.

MoodMirror découvre *pourquoi* ton humeur varie en fonction de ce que tu lis, regardes et consommes. Les données brutes restent **sur ton appareil**. Seuls des agrégats anonymisés remontent au cloud pour le benchmark population.

**Value prop :** *« Sachez ce qui vous draine — sans qu'on sache ce que vous lisez. »*

---

## Pourquoi ça tient scientifiquement

La thèse centrale — *ce que tu consommes shape ton humeur* — n'est plus une intuition. Elle est validée :

- **Kelly & Sharot, *Nature Human Behaviour* (2024/2025)** — « Web-browsing patterns reflect and shape mood and mental health ». 4 études, 1 145 participants partageant leur historique de navigation réel. La relation contenu ↔ humeur est **causale et bidirectionnelle**, démontrée par manipulation. Leur intervention (des *content labels* façon étiquette nutritionnelle sur les pages) est un prototype direct de feature pour MoodMirror.
- **Méta-analyses 2025** — l'abstinence des réseaux sociaux n'améliore *pas* significativement le bien-être (Lemahieu et al., *Scientific Reports*). Les effets dépendent du **type d'usage**, pas de la quantité d'écran. → MoodMirror ne vend pas « moins d'écran », il vend de la **connaissance**.

📄 Références complètes : [docs/research.md](docs/research.md)

---

## Le gap (ce que personne ne fait)

| Catégorie | Ce qu'elles font | Ce qu'elles manquent |
|---|---|---|
| Mood trackers (Daylio, Moodsy…) | Journal d'humeur, tags manuels | Aucune collecte de contenu réel |
| Digital Wellbeing (Screen Time, One Sec…) | Comptent du temps, limites | Aucun mood, aucune corrélation |

**Personne ne croise *contenu réellement consommé* × *humeur déclarée*, en local, privacy-first.** C'est exactement MoodMirror.

---

## Architecture — privacy by design

- **On-device processing** : catégorisation (NLP local : valence, topic), agrégation, differential privacy. Les données brutes ne quittent jamais l'appareil.
- **Zero-knowledge cloud** : le serveur ne stocke **jamais** d'URL brute ni de mood brut — seulement `{catégorie, durée, score}` anonymisés.
- **Differential Privacy** : bruit mathématique (Laplacien) sur les agrégats avant remontée.
- **PostgreSQL + Row-Level Security** : chaque utilisateur ne voit que ses données.

```
┌─ Appareil User ────────────────┐
│  Données brutes :              │
│  • Humeur (2x/jour)            │
│  • URLs visitées               │
│  • Usage apps                  │
│                                │
│  TRAITEMENT ON-DEVICE          │
│  1. Catégorisation NLP local   │
│  2. Agrégation cat/jour        │
│  3. Differential Privacy       │
└───────────────┬────────────────┘
                │ Seuls les agrégats
                ▼
┌─ Cloud ────────────────────────┐
│  • {catégorie, durée, score}   │
│  • jamais d'URL brute          │
│  • jamais de mood brut         │
│  → Benchmark population        │
└────────────────────────────────┘
```

📄 Détail complet : [docs/architecture.md](docs/architecture.md)

---

## Stack

- **Frontend** : Next.js 14+ (App Router), Tailwind + shadcn/ui, Recharts/Visx
- **Backend** : Python + FastAPI
- **Database** : PostgreSQL (Supabase / Neon) + RLS
- **Privacy** : Opacus / TensorFlow Privacy (differential privacy)
- **Infra** : Vercel (front) + Railway/Render (back), Stripe, Clerk/Supabase Auth

---

## Roadmap

1. **Phase 0** — Prototype local Python + SQLite (collecte macOS, validation pipeline)
2. **Phase 1** — Backend SaaS (FastAPI + Postgres + RLS + auth)
3. **Phase 2** — Frontend dashboard (corrélations, heatmaps, trends)
4. **Phase 3** — Collecte (extension browser + app macOS, on-device processing)
5. **Phase 4** — Privacy layer (differential privacy, hash URLs client-side, audit GDPR)
6. **Phase 5** — Lancement (beta fermée, Stripe)

📄 Détail : [docs/roadmap.md](docs/roadmap.md)

---

## Status

🟢 **En développement** — Phase architecture SaaS.

> ⚠️ *Projet concept / recherche. Les données de bien-être relèvent d'un cadre réglementaire strict (GDPR art. 9, HIPAA aux US). L'architecture zero-knowledge est l'argument compliance central.*
