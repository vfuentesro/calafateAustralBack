"""
Django settings for Backedn_Calafate_Austral project.

Generated by 'django-admin startproject' using Django 5.2.3.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

from pathlib import Path
import os
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Inicializar django-environ
env = environ.Env(
    DEBUG=(bool, False)
)
# Leer el archivo .env si existe
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'Tienda',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Backedn_Calafate_Austral.urls'

# --- CSRF y SESSION para cross-domain con subdominios ---
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_DOMAIN = '.calafateaustral.cl'
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_DOMAIN = '.calafateaustral.cl'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Backedn_Calafate_Austral.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# Configuración de base de datos compatible con Railway y variables individuales
#if env('DATABASE_URL', default=None):
 #   DATABASES = {
 #       'default': env.db(),  # Toma DATABASE_URL automáticamente
 #   }
#else:
  #  DATABASES = {
   #     'default': {
    #        'ENGINE': 'django.db.backends.mysql',
     ##      'USER': env('MYSQLUSER', default='root'),
       #     'PASSWORD': env('MYSQLPASSWORD', default=''),
        #    'HOST': env('MYSQLHOST', default='localhost'),
         #   'PORT': env('MYSQLPORT', default='3306'),
          #  'OPTIONS': {
           #     'charset': 'utf8mb4',
    #        },
    #    }
    #}

# Configuración de base de datos para entorno local
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_NAME', default='calafate'),
        'USER': env('DB_USER', default='root'),
        'PASSWORD': env('DB_PASSWORD', default='4dm1n1str4d0r'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

# Configuración de Email para Desarrollo
# Los correos se imprimirán en la consola donde se ejecuta el servidor.
# Para producción, reemplazar con un backend real como SMTP, SendGrid, etc.
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='Calafate Austral <no-responder@calafateaustral.com>')
ADMIN_EMAIL = env('ADMIN_EMAIL', default='admin@calafateaustral.com') # Email del admin para recibir notificaciones
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env('EMAIL_PORT', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=False)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configuración de correo electrónico para desarrollo (imprime en consola)
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# La configuración SMTP se puede mantener comentada para uso futuro en producción
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'calafateaustral@gmail.com'
# EMAIL_HOST_PASSWORD = 'your_app_password'

# Correo del administrador
# ADMIN_EMAIL = 'admin@calafateaustral.cl'

# Configuración de Getnet (SANDBOX)
GETNET_API_URL = env('GETNET_API_URL')
GETNET_AUTH_URL = env('GETNET_AUTH_URL')
GETNET_LOGIN = env('GETNET_LOGIN')
GETNET_SECRET_KEY = env('GETNET_SECRET_KEY')
GETNET_MERCHANT_ID = env('GETNET_MERCHANT_ID')


# Correos de Chile settings (valores de ejemplo)
CORREOS_CHILE_API_URL = env('CORREOS_CHILE_API_URL')
CORREOS_CHILE_USER = env('CORREOS_CHILE_USER')
CORREOS_CHILE_PASSWORD = env('CORREOS_CHILE_PASSWORD')

# Chilexpress settings
CHILEXPRESS_API_KEY = env('CHILEXPRESS_API_KEY')
CHILEXPRESS_API_URL = env('CHILEXPRESS_API_URL')

# URL base del sitio (para webhooks y redirecciones)
BASE_URL = env('BASE_URL', default='https://calafateaustralback-production.up.railway.app')  # Cambiar en producción

# Configuración de logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'Tienda': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Crear directorio de logs si no existe
logs_dir = BASE_DIR / 'logs'
if not logs_dir.exists():
    logs_dir.mkdir(exist_ok=True)

# --- CORS ---
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "https://calafateaustral.cl",
    "https://www.calafateaustral.cl",
    "https://calafate-austral.web.app",
    "https://calafate-austral.firebaseapp.com"
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://localhost:\d+$",
]
CORS_TRUSTED_ORIGINS = [
    "https://calafateaustral.cl",
    "https://www.calafateaustral.cl",
    "https://calafate-austral.web.app",
    "https://calafate-austral.firebaseapp.com"
]
CSRF_TRUSTED_ORIGINS = [
    "https://calafateaustral.cl",
    "https://www.calafateaustral.cl",
    "https://api.calafateaustral.cl",
    "https://calafate-austral.web.app",
    "https://calafate-austral.firebaseapp.com"
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAdminUser',
    ],
}

# If you want to allow all origins (less secure, good for initial development)
# CORS_ALLOW_ALL_ORIGINS = True

# Password hashing: usar Argon2 como principal para máxima seguridad
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

AUTH_USER_MODEL = 'Tienda.Usuario'

LOGIN_URL = '/compra/login/'
