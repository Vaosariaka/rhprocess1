# DO.md — Documentation opérationnelle du projet HR/MS

Date: 3 novembre 2025

Ce document rassemble une vue d'ensemble des fonctionnalités, de l'architecture, des points d'entrée (endpoints), et des tâches en cours pour le projet HR / Paie présent dans le dépôt.

## 1) Objectif du projet
Un système RH / paie simple développé en Django (DRF) pour gérer : employés, contrats, congés, présences, alertes, calculs de paie, import d'"ETAT DE PAIE" Excel, et export de fiches de paie (XLSX / PDF).

## 2) Fonctionnalités principales
- Gestion des employés (CRUD via admin et API) — modèle `Employee`.
- Gestion des catégories / fonctions (`Category`).
- Gestion des contrats (`Contract`) et historique des contrats (`ContractHistory`).
- Gestion des congés (`Leave`) avec workflow d'approbation (page d'approbation, notifications optionnelles) et historique (`LeaveHistory`).
- Présences et absences (`Presence`, `Absence`).
- Alertes (`Alerte`) et journal `Historique` pour traces diverses.
- Calcul de paie (module `core/payroll.py`) : calculer salaire brut/net, déductions CNAPS/OSTIE, majorations, etc.
- Import des états de paie depuis Excel via la commande management `import_payroll` et l'interface upload (`import_payroll_upload`).
- Exports :
  - Génération de fiches de paie individuelles en XLSX (`export_employee_fiche`) et en lot (`export_all_fiches`).
  - Vue PDF par paie (`export_payroll_pdf`) : tente WeasyPrint / xhtml2pdf puis bascule vers l'export XLSX si pas de backend PDF.
  - Export listes : employés (`export_employees_xlsx`), congés (`export_leaves_xlsx`).
- Endpoints statistiques (JSON) : workforce by gender, avg age, avg seniority, turnover, absenteeism monthly, unused leave summary (vues DB optionnelles).

## 3) Organisation des fichiers clés
- `manage.py` — script Django.
- `core/` — application principale :
  - `models.py` — définitions de `Employee`, `Payroll`, `Leave`, `Contract`, `LeaveHistory` etc.
  - `views.py` — vues DRF et vues web (upload, exports, statistiques, UI d'approbation).
  - `admin.py` — configuration admin (liste paies avec bouton "Exporter PDF", historiques en lecture seule).
  - `serializers.py` — serializers DRF.
  - `management/commands/import_payroll.py` — import des états de paie Excel.
  - `payroll.py` — logique de calcul de la paie.
  - `templates/core/` — templates HTML, notamment `fiche_pdf.html`.
  - `migrations/` — migrations Django.

Fichiers présents à la racine du workspace (exemples fournis) :
- `FICHE DE PAIE .xlsx` (modèle Excel de fiche, utilisé si présent)
- `ETAT DE PAIE MAJ.xlsx` / `FICHE DE PAIE .xlsx` — fichiers de données fournis par l'utilisateur.

## 4) Endpoints et routes importantes
- Pages/UI
  - `/` — dashboard (`home`)
  - `/leaves/<pk>/approval/` — page d'approbation pour managers
  - `/import/payroll/` — upload et exécution de l'import
- Exports (web)
  - `/export/fiche/<employee_pk>/?year=YYYY&month=M` — télécharge XLSX fiche (utilise le template Excel si présent)
  - `/export/all-fiches/` — export XLSX toutes fiches (un onglet par salarié)
  - `/export/payroll/<payroll_pk>/pdf/` — export PDF d'une paie (prefers HTML->PDF backends, fallback XLSX)
  - `/export/employees.xlsx` — export liste employés
  - `/export/leaves.xlsx` — export congés
- API (DRF)
  - `/api/employees/` — CRUD employés
  - `/api/payrolls/` — CRUD paies (généralement écrites via import/génération)
  - `/stats/*` — endpoints statistiques JSON

## 5) Comportement d'export / génération de PDF
- Le système essaie d'abord d'utiliser un moteur HTML->PDF (WeasyPrint recommandé). Si absent, tente `xhtml2pdf`. Si les deux échouent, l'endpoint PDF redirige vers l'export XLSX correspondant.
- Pour obtenir une correspondance visuelle exacte avec le modèle Excel, l'approche recommandée est :
  - Générer d'abord l'XLSX à partir du template (`FICHE DE PAIE .xlsx`) puis convertir en PDF via LibreOffice en mode headless (`soffice --headless --convert-to pdf`).
  - Cette option (XLSX→PDF via LibreOffice) n'est pas encore implémentée automatiquement dans le code — elle est listée comme TODO.

## 6) Sécurité et UI admin
- Les modèles d'historique (`ContractHistory`, `LeaveHistory`, `Historique`) ont été rendus en lecture seule dans l'admin (pas d'ajout/suppression/modification depuis l'admin) afin de préserver l'intégrité des logs.
- L'approbation des congés est restreinte aux utilisateurs `is_staff` ou membres du groupe `Manager` (fonction `user_is_manager`).

## 7) Comment lancer le projet en dev
1. Créez un environnement Python 3.10+ et installez dépendances (exemples) :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Exécuter migrations et lancer le serveur (script helper présent) :

```bash
# depuis le répertoire contenant manage.py
./bin/dev.sh
# ou
python3 manage.py migrate
python3 manage.py runserver
```

3. Accédez à l'admin : http://127.0.0.1:8000/admin/ (créez superuser si nécessaire)

Notes : `bin/dev.sh` automatise migrate + runserver. Si l'application PDF doit générer des PDF via LibreOffice, installez `libreoffice` sur l'hôte.

## 8) Dépendances optionnelles
- `weasyprint` (pour HTML->PDF) — recommandé pour rendu propre
- `xhtml2pdf` (fallback)
- `openpyxl` (obligatoire pour manipulation XLSX)
- `pandas` (optionnel, accélère les exports et conversions)
- `libreoffice` (soffice) — optionnel, utile pour conversion XLSX→PDF fidèle

## 9) Tests & qualité
- Il n'y a pas (encore) de batterie complète de tests unitaires. TODO : ajouter tests pour :
  - endpoint `export_employee_fiche` (XLSX generation, template substitution)
  - endpoint `export_payroll_pdf` (fallbacks)
  - import payroll management command (dry-run + apply)

## 10) Tâches en cours / TODO prioritaires
- Améliorer la fidélité PDF : implémenter XLSX→PDF via LibreOffice (option recommandée pour correspondance avec le modèle Excel).
- Ajouter des tests automatiques pour les exports et l'import.
- Peaufiner `core/templates/core/fiche_pdf.html` pour un rendu PDF plus complet (si on choisit la voie HTML->PDF).
- Mettre en place un petit job ou script pour générer des fiches en masse et les archiver.

## 11) Points d'architecture & décisions prises
- L'import des états de paie est fait via une commande management pour garder la logique isolée et testable.
- Les exports XLSX utilisent `openpyxl` et, si présent, `pandas` pour simplifier l'écriture des feuilles.
- Les vues statistiques s'appuient sur des vues matérialisées ou vues SQL dans la base (nommées dans le code : `workforce_by_gender`, `avg_age`, `turnover_12m`, `absenteeism_monthly`, `unused_leave_summary`). Le code est défensif si ces vues sont absentes.

## 12) Où je peux aider ensuite
- Implémenter la conversion XLSX→PDF automatisée (LibreOffice). Je peux coder cela et gérer les fichiers temporaires et les permissions.
- Ou, si vous préférez une solution sans dépendance à LibreOffice, développer une version HTML du modèle de fiche et améliorer `fiche_pdf.html` pour inclure toutes les sections (IRSA, CNAPS, majorations, avances, préavis, etc.).

