#!/bin/bash

# Ajouter srcs au PYTHONPATH
export PYTHONPATH=/app/srcs:$PYTHONPATH

# Appliquer les migrations de la base de données
echo "Applying database migrations..."
python srcs/manage.py migrate


# Collecter les fichiers statiques
echo "Collecting static files..."
python srcs/manage.py collectstatic --noinput

# Créer un superutilisateur pour l'administration Django
echo "Creating superuser..."
python srcs/manage.py createsuperuser --noinput --username $DJANGO_SUPERUSER_USERNAME --email $DJANGO_SUPERUSER_EMAIL || true

# Démarrer le serveur Gunicorn
echo "Starting Gunicorn server..."
cd /app/srcs
exec gunicorn user_managment.wsgi:application \
    --bind 0.0.0.0:8001 \
    --workers 3 \
    --access-logfile - \
    --error-logfile - \
    --log-level debug \
    --capture-output \
    --enable-stdio-inheritance