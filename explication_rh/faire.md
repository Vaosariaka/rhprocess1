### 1. Fonctionnalités essentielles (Base RH)

A. Gestion du personnel
- [x] Fiche employé complète (identité, contact, poste, photo, etc.) — `Employee` model, champs et `photo`.
- [x] Suivi du contrat de travail (type, durée, période d'essai, renouvellement) — `Contract` model + helpers (renew/convert/terminate).
- [x] Historique des postes, promotions, mobilités — `PositionHistory` model.
- [x] Gestion des documents RH (CIN, diplômes, attestations, etc.) — `Document` model (upload + validité).

B. Gestion des absences et congés
- [x] Suivi des soldes de congés (payés, maladie, exceptionnels) — `LeaveBalance` + `employee_available_leave()`.
- [x] Workflow de demande et validation hiérarchique — `LeaveRequest` model avec approbations dept/hr et méthode `approve_by_hr()`.
- [x] Intégration avec le calendrier de l'entreprise — ICS export + simple FullCalendar page (`/planner/calendar/`) ajoutée.
- [x] Alertes automatiques pour congés non validés ou absences répétées — création d'`Alerte` dans validations/flows.

C. Gestion du temps et des présences
- [x] Feuille de temps / pointage (manuel ou automatique) — `Presence` model (time_in/time_out, minutes_late, etc.).
- [x] Heures supplémentaires, retards, pauses — champs et calculs pris en compte dans `core/payroll.py`.
- [x] Génération automatique du relevé de présence — helper `_presence_summary()` présent.
- [x] Interface d'intégration avec la paie — `compute_payroll_for_employee()` lit `Presence`/`Absence`.

D. Gestion de la paie (base)
- [x] Fiches de paie mensuelles (salaire brut, retenues, net à payer) — `Payroll` model + exporters (`export_employee_fiche`, `export_payroll_pdf`).
- [x] Paramétrage des taux CNAPS, OSTIE, IRSA, etc. — configurables via `core/payroll.py` defaults and `PayrollCalculator` usage.
- [x] Gestion des primes, avances, heures supplémentaires, absences — heures sup & absences gérées; primes/avances peuvent être stockées en `notes` ou champs additionnels.
- [x] Export vers format comptable ou PDF — XLSX/PDF/ZIP exporters implémentés.

### 2. Fonctionnalités avancées (RH numériques / intelligentes)

A. Tableaux de bord et indicateurs RH
- [x] Statistiques sur les effectifs (par genre, âge, service, contrat, etc.) — endpoints `stats_*` et vues SQL.
- [x] Taux de turnover, absentéisme, ancienneté moyenne — endpoints et helpers présents.
- [x] Alertes de fin de contrat, congés non pris, dépassement de budget formation — système d'`Alerte` pour signaler événements.
- [x] Visualisation graphique — page de graphiques basique ajoutée (consomme les endpoints `stats_*`).

B. Gestion des performances

- [x] Évaluations périodiques automatisées (scoring) — implémenté partiellement : management command `compute_performance_scores` exists and an API trigger `/api/performance/run/` was added to run it on demand. Scheduling (cron or Celery) and heuristic tuning remain as follow-ups.
- [x] Génération de rapports de performance — implémenté : the command writes CSV reports into `exports/reports/` and creates `Report` records; a simple reports UI is available at `/reports/`.

C. Gestion des compétences

- [x] Cartographie des compétences de l'entreprise — API + UI basique ajoutées (`/api/competency/cartography/`, template `competency_cartography.html`). -> a corriger
- [x] Matching automatique profil / poste à pourvoir — API `/api/competency/match/` + simple matching UI (`match_candidates.html`) implemented (simple TF / competency score).
- [x] Suggestion de formations — API `/api/competency/suggest-trainings/` + UI (`training_suggestions.html`) and generation command available. ->a corriger

D. Self-Service Employé (Espace employé)

- [x] Mise à jour personnelle des informations — espace self-service (/employees/self-service/profile/) avec formulaire sécurisé et API `employees/me/`.
- [x] Consultation bulletins de paie, solde de congés — exports et helpers (`export_employee_fiche`, `employee_available_leave`).
- [x] Soumission de demandes (attestations, congés, remboursements) — `LeaveRequest` existant pour congés; autres demandes à définir.
- [x] Système de messagerie RH — messagerie web (`/planner/messages/`) connectée aux APIs `messages/inbox`, `messages/send`, `messages/recipients`.

E. Portail Manager

- [x] Validation des demandes de son équipe — vue `approve_leave` + `user_is_manager`. -> a corriger
- [x] Suivi des performances et absences — données présentes; UI dédiée limitée.
- [ ] Tableaux de bord spécifiques par departement — backend data disponible; dashboards front-end

F. Automatisation et Intelligence artificielle ->a corriger

- [x] Chatbot RH pour répondre aux questions fréquentes (congés, paie, etc.) — `chatbot_view` implémenté.
- [x] Génération automatique de documents RH (contrat, attestation, etc.) — exports et templates partiels disponibles.
- [x] Prédiction de turnover (analyse de données) — management command `predict_turnover` added; writes CSV reports and creates Report rows.
- [x] Détection d'anomalies sur les heures ou la paie — management command `detect_payroll_anomalies` added; writes CSV anomaly reports.
- [x] Recommandation de candidats (matching CV ↔ poste) — basic matching implemented via `/api/competency/match/` (competency score + text-similarity fallback).

G. Conformité et audit

- [x] Journalisation des actions (traces d'audit) — `AuditLog` model.
- [x] Gestion des autorisations par rôle (employé, manager, RH, admin) — checks via groups and `user_is_manager`.
- [x] Sauvegarde et archivage légal des documents RH — `Document` model + backups folder present (project-level), infra/legal archiving depends on deployment.


