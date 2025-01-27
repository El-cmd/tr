#!/bin/bash

# Appliquer les migrations de la base de données
echo "Applying database migrations..."
python manage.py migrate


# Collecter les fichiers statiques
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Créer un superutilisateur pour l'administration Django
echo "Creating superuser..."
python manage.py createsuperuser --noinput --username $DJANGO_SUPERUSER_USERNAME --email $DJANGO_SUPERUSER_EMAIL || true

# Démarrer le serveur Gunicorn
echo "Starting Gunicorn server..."
exec gunicorn auth.wsgi:application --bind 0.0.0.0:8001 --workers 3