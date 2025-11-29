HRMS - Minimal Django HR example

But: this is a small starter template implementing basic HR models (Category, Employee, Leave, Payroll) with Django + DRF and PostgreSQL.

Quickstart
1. Create a Python virtualenv and install dependencies (local, without Docker):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. PostgreSQL (required)

This project is configured to use PostgreSQL as the database. Before running the app, create a database and a user. Example commands for a local Postgres server:

```bash
# as a system user with postgres privileges
sudo -u postgres psql -c "CREATE USER hrms_user WITH PASSWORD 'sariaka';"
sudo -u postgres psql -c "CREATE DATABASE hrms OWNER hrms_user;"

# or set POSTGRES_USER=postgres and POSTGRES_PASSWORD=sariaka in .env if you prefer to use the 'postgres' superuser
```

3. Create `.env` (copy `.env.example`) and adjust variables if needed. Example `.env` for local Postgres:

```
DJANGO_SECRET_KEY=change-me-please
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
POSTGRES_DB=hrms
POSTGRES_USER=postgres
POSTGRES_PASSWORD=sariaka
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

4. Apply migrations and create a superuser:

```bash
source .venv/bin/activate
export $(grep -v '^#' .env | xargs) || true
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

5. API endpoints (when server runs):
   - /api/employees/
   - /api/leaves/
   - /api/payrolls/
   - /api/categories/

Admin: /admin/

Notes
- This project requires PostgreSQL.
- For production, set `DEBUG=0`, configure `ALLOWED_HOSTS` and a strong `SECRET_KEY`, and use a managed Postgres instance.

Importer des fichiers Excel
---------------------------

Une commande management permet d\'importer un fichier Excel d\'état de paie et de créer les employés et fiches de paie correspondantes:

```bash
# dry-run (ne modifie pas la base, affiche un résumé)
python manage.py import_payroll --payroll-file '../ETAT DE PAIE MAJ.xlsx' --dry-run

# exécution réelle (persiste les enregistrements)
python manage.py import_payroll --payroll-file '../ETAT DE PAIE MAJ.xlsx'

# options utiles:
# --sheet "SHEETNAME"  -> forcer la feuille à lire
# --month 6 --year 2025 -> forcer mois/année si la colonne DATE est absente
```

La commande tente de détecter automatiquement la ligne d\'en-tête (recherche `matricule`, `NOM`, `SALAIRE`, `NET`, `DATE`) et supporte des formats numériques avec des virgules ou espaces. En cas de doute, exécutez d\'abord en `--dry-run`.

Synchronisation automatique depuis l'interface CRUD
-------------------------------------------------

Les modifications faites via l'interface CRUD (ajout/modification/suppression) sont automatiquement écrites dans les fichiers Excel du workspace :

- `FICHE DE PAIE .xlsx` reçoit la feuille `FICHE` mise à jour avec la liste des employés.
- `ETAT DE PAIE MAJ.xlsx` reçoit/contient les feuilles `Payrolls` et `Leaves` (respectivement fiches paie et congés).

La synchronisation est effectuée via des signaux Django (post_save/post_delete). Si vous préférez déclencher la mise à jour manuellement, utilisez les endpoints d'export dans l'interface web (Employees / Leaves → Exporter (Excel)).
