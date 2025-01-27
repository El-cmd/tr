FROM nginx:latest

# Copier les fichiers statiques dans le dossier HTML de Nginx
COPY dist /usr/share/nginx/html

RUN  chown -R www-data:www-data /usr/share/nginx/html
RUN chmod 555 /usr/share/nginx/html