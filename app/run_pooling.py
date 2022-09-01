import os, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portobello.settings')
django.setup()

from bot.dispatcher import run_pooling

if __name__ == "__main__":
    run_pooling()