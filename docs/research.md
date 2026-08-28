# Research & Références

Base de recherche du projet MoodMirror — papiers académiques, concurrents, état de l'art privacy et collecte.

---

## Papiers académiques

### InsightMe (2022)
- **arXiv 2202.03721** — self-tracking meta app pour mood
- Montre comment les données se relient au bien-être ; dashboard de corrélation mood × facteurs externes
- Lien : https://arxiv.org/pdf/2202.03721

### Frontiers en Psychologie Numérique (2025)
- Méta-analyse des effets psychologiques de la tech digitale ; identifie les entités digitales les plus impactantes
- Lien : https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2025.1560516/full

### Dashboard Social Media Tracking (PMC)
- Essai randomisé pour patients anxieux/dépressifs ; dashboard électronique pour cliniciens
- Lien : https://pmc.ncbi.nlm.nih.gov/articles/PMC12604431/

### Digital Self-control (ACM 2022)
- Bien-être numérique via auto-contrôle digital
- Lien : https://dl.acm.org/doi/full/10.1145/3571810

### Boosting Positivity — ASU (2024)
- Impact du mood tracking sur le bien-être mental ; le tracking motive le changement (comme le tracking calories)
- Lien : https://news.wpcarey.asu.edu/20241101-boosting-positivity-impact-mood-tracking-mental-well-being

---

## 🔴 L'étude qui valide TOUT le projet — Kelly & Sharot, Nature Human Behaviour (nov 2024)

**« Web-browsing patterns reflect and shape mood and mental health »** — UCL + MIT, financé Wellcome, publié dans *Nature Human Behaviour* vol 9 (2025).
- Paper : https://www.nature.com/articles/s41562-024-02065-9 (DOI 10.1038/s41562-024-02065-9)
- Résumé presse : https://www.news-medical.net/news/20241121/Study-finds-link-between-poor-mental-health-and-browsing-negative-online-content.aspx

**4 études, 1 145 participants** — les gens partagent leur historique de navigation réel ; NLP sur la valence émotionnelle des pages visitées.

**Résultats clés :**
- La relation est **causale et bidirectionnelle** (pas juste corrélative).
- Pire santé mentale → on consomme plus de contenu négatif.
- Consommer du contenu négatif → l'humeur se dégrade ensuite (effet causal démontré par manipulation : exposer des participants à des sites négatifs vs neutres, mesurer le mood après).
- Boucle de rétroaction : les gens exposés au contenu négatif choisissent *ensuite* plus de contenu négatif en navigation libre.

**Leur intervention :** un plug-in qui ajoute des **« content labels »** sur les pages web — *comme une étiquette nutritionnelle*, affichant l'impact émotionnel du contenu + sa praticité/informativité, pour aider à faire des choix plus sains.

**Impact pour MoodMirror :** c'est la validation scientifique de la thèse centrale (« ce que tu consommes shape ton humeur ») ET un prototype direct de feature (labels affectifs sur le contenu). À citer dans tout pitch/démo.

---

## Méta-analyses récentes — nuances importantes

- **Lemahieu et al. (mars 2025, Scientific Reports)** — méta-analyse pré-enregistrée : l'abstinence temporaire des réseaux sociaux n'améliore *pas* significativement le bien-être affectif positif/négatif ni la satisfaction de vie (10 études adultes). → **Argument produit** : ce n'est pas « moins d'écran » qui compte, c'est *quels contenus*. MoodMirror ne vend pas de l'abstinence, il vend de la connaissance.
- **Méta-analyse 292 études (ScienceDirect)** — corrélation positive téléphone↔bien-être, négative certains usages → les effets sont hétérogènes selon le type d'usage, ce qui renforce l'intérêt d'une mesure fine par catégorie de contenu.
- **SAGE (sept 2025) « Breaking News, Breaking Moods? »** — lien consommation médiatique × bonheur, rôle de la confiance et des algorithmes.

---

## Concurrents / marché

### Mood Tracking (sans corrélation contenu)
- **Daylio** — mood journal simple
- **Mooda** — tracking + insights basiques
- **Claro** — mood + habits
- **Remente** — mood + journaling
- **Moodflow** (App Store) — insights IA hebdo sur ce qui affecte le bien-être. Le plus proche en marketing, mais c'est un mood journal avec tags manuels, pas de collecte de contenu réel.
- **Moodsy** — mood + habitudes + playlists, insights ML personnalisés.
- **Moodtap** (2026) — wearables IA qui prédisent les shifts d'humeur via HRV/sommeil. Bascule du « log » vers la prédiction biométrique.

### Digital Wellbeing (sans mood)
- **Screen Time** (Apple) — usage apps, limites
- **Digital Wellbeing** (Google) — timers, focus mode
- **One Sec** — friction avant ouverture d'app
- **Feedcutter** et autres 2026 — toutes tournent autour de la réduction du temps d'écran, aucune ne fait la corrélation contenu×mood.

### Marché
- CAGR ~13% 2025→2035 ; tendance dominante = insights IA + auto-management guidé.

### ⚠️ Le gap
Personne ne croise *contenu réellement consommé* × *humeur déclarée* de façon personnalisée et locale, privacy-first. Les mood trackers demandent des tags manuels ; les wellbeing apps comptent du temps sans mood. **MoodMirror reste seul sur ce croisement.**

---

## Privacy tech — état de l'art

- **Google Privacy Sandbox (déc 2025)** : document « Differential privacy semantics for On-Device Personalization » — DP + Federated Compute comme approche de référence pour exposer des patterns sans exposer les données individuelles. ⚠️ Plusieurs technologies Privacy Sandbox sont en cours de phase-out ; ne pas construire dessus, mais le modèle (agrégats on-device → upload anonymisés) est exactement le nôtre et reste valide.
- **Apple** : tout le processing Siri sur données Health se fait on-device — référence de positionnement « processing local par défaut ».
- **Compliance** : les apps de santé mentale naviguent un paysage HIPAA-GDPR hybride ; en EU, GDPR seul + le statut de données de santé (art. 9) impose la minimisation → notre architecture zero-knowledge (jamais d'URL brute au cloud) est l'argument compliance principal.

---

## Collecte macOS — état réel (critique pour Phase 0)

- **knowledgeC.db** (`~/Library/Application Support/Knowledge/knowledgeC.db`) : base SQLite CoreDuet — usage apps, web usage, media, notifications, lock/unlock. Lisible en lecture seule avec **Full Disk Access** accordé à l'app/terminal.
- **Répo de référence** : `iamEvanYT/macos-screen-time` (Bun/TS, zéro dépendance) — lit knowledgeC.db directement, agrégats par app/catégorie/date/heure, résolution de noms via Spotlight. À adapter en Python pour le prototype.
- **⚠️ Migration Biome** : depuis **iOS 16 / macOS 13+**, Apple stocke une partie des stats dans les **Biome activity streams** (fichiers `segb`, protobuf segmentés) au lieu de knowledgeC.db — notamment l'activité Safari fine. Il faut vérifier sur le Mac cible ce qui reste dans knowledgeC.db vs ce qui est parti en Biome, et si les segb sont décryptables/parseables. **Risque technique n°1 de la Phase 0.**
- **Historique navigateur** : fichiers SQLite directs (Chrome: `History`, Safari: `History.db` dans iCloud/Library) — lecture possible avec Full Disk Access ; c'est la source de contenu *la plus riche* pour la valence NLP, et elle ne dépend pas de Screen Time du tout.
- **APIs officielles** : l'API Screen Time d'Apple est réservée aux apps parentales approuvées (MDM/ScreenTime API iOS 15+) — non accessible pour un SaaS tiers normal. La lecture directe des bases est le chemin praticable, mais c'est du private API territory → risque App Store ; sur macOS standalone, c'est acceptable en beta.

---

## Synthèse — ce qui change dans la roadmap

1. **Le pitch scientifique est inattaquable** : Kelly & Sharot (Nat Hum Behav) + méta-analyses 2025. À mettre en tête de toute doc.
2. **Feature « étiquettes affectives »** (labels type nutrition sur le contenu) — validée par l'intervention de l'étude ; candidate pour le MVP plutôt qu'une phase tardive.
3. **Positionnement anti-abstinence** : la méta-analyse Lemahieu 2025 donne l'argument « moins d'écran ≠ mieux-être ; *quels* contenus, c'est ça qui compte ».
4. **Phase 0 à réordonner** : vérifier d'abord le contenu réel de knowledgeC.db + les historiques navigateurs, avant tout code. Le risque Biome est à trancher en jour 1.
