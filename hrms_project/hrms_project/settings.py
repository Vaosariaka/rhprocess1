import os
from pathlib import Path
from dotenv import load_dotenv
from django.contrib import admin   # ← NOUVELLE LIGNE


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment from .env if present
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'change-me-please')
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'rest_framework',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hrms_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [str(BASE_DIR / 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'hrms_project.wsgi.application'

# Database (PostgreSQL is required)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'hrms'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'sariaka'),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
# Directory where `collectstatic` will gather static files for production or local testing.
# Uses BASE_DIR for a predictable local path.
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ]
}

# Email configuration: default to console backend in DEBUG for easy local testing.
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'no-reply@example.com')
if os.environ.get('DJANGO_EMAIL_BACKEND'):
    EMAIL_BACKEND = os.environ.get('DJANGO_EMAIL_BACKEND')
else:
    # use console backend when debugging or when no backend specified
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend'

# Optional SMTP settings (used when not using console backend)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 25))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', '0') == '1'
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', '0') == '1'

# ----------------------
# HR parameters for payroll calculations
# These can be overridden in environment variables or edited here.
# ----------------------
HR_SECTEUR = os.environ.get('HR_SECTEUR', 'non_agricole')  # 'agricole' or 'non_agricole'
HR_HEURES_NON_AGRICOLE = float(os.environ.get('HR_HEURES_NON_AGRICOLE', '173.33'))
HR_HEURES_AGRICOLE = float(os.environ.get('HR_HEURES_AGRICOLE', '200'))
HR_JOURS_NON_AGRICOLE = float(os.environ.get('HR_JOURS_NON_AGRICOLE', '21.67'))
HR_JOURS_AGRICOLE = float(os.environ.get('HR_JOURS_AGRICOLE', '25'))
# CNaPS ceiling so employee contribution = 1% of up to 1,000,000 Ar (i.e., 10,000 Ar max)
HR_PLAFOND_CNAPS = float(os.environ.get('HR_PLAFOND_CNAPS', '350000'))
HR_TAUX_CNAPS_SALARIE = float(os.environ.get('HR_TAUX_CNAPS_SALARIE', '0.01'))
HR_TAUX_SANITAIRE_SALARIE = float(os.environ.get('HR_TAUX_SANITAIRE_SALARIE', '0.01'))

# Jours fériés (format: MM-DD for recurring holidays or YYYY-MM-DD for specific dates)
# Example: '01-01' (1 Jan), '06-26' (26 Jun). Can be overridden via env var HR_HOLIDAYS
_hr_holidays_env = os.environ.get('HR_HOLIDAYS', '01-01,06-26')
HR_HOLIDAYS = [h.strip() for h in _hr_holidays_env.split(',') if h.strip()]


# settings.py – Cette ligne est la clé de tout
STATICFILES_DIRS = [
    BASE_DIR / "core" / "static",
]

# Et surtout celle-ci :
ADMIN_MEDIA_PREFIX = '/static/admin/'  # pas obligatoire mais propre



