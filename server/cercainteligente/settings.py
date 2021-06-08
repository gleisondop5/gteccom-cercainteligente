from pathlib import Path

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = Path(__file__).resolve().parent.parent
#BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '2zelj=rh=t27qr@#euylfnrht^e+kscwpb#%ky*gy@i*55belp'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    # django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    #3rd party 
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    "crispy_forms",
    # local apps
    'monitor.apps.MonitorConfig', 
    'channels'
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

ROOT_URLCONF = 'cercainteligente.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR/"monitor"/"templates"/"monitor"],
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

WSGI_APPLICATION = 'cercainteligente.wsgi.application'
ASGI_APPLICATION = 'cercainteligente.asgi.application'


# Channels

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
        }
    }
}

# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'cercainteligente',
        'USER': 'cercainteligente',
        'PASSWORD': 'qwert',
        'HOST': '127.0.0.1',
        'PORT': '5432'
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_URL = '/static/'

# django-allauth

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1
# altera o direcionamento apos o login para raiz
LOGIN_REDIRECT_URL = "/monitoramento"
ACCOUNT_SESSION_REMEMBER = True
#confirma o email pelo terminal. Em produção o usuário receberia um email de confirmação
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
# Só precisa digitar a senha uma vez
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = False
# Não precisa de username
ACCOUNT_USERNAME_REQUIRED = False
# Método de autenticação: email
ACCOUNT_AUTHENTICATION_METHOD = "email"
# Email obrigatório
ACCOUNT_EMAIL_REQUIRED = True
# Email único
ACCOUNT_UNIQUE_EMAIL = True


# django-crispy-forms
CRISPY_TEMPLATE_PACK = "bootstrap4"