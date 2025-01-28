FROM nginx:latest

# Copier les fichiers statiques dans le dossier HTML de Nginx
COPY ./dist /usr/share/nginx/html

# Set proper permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

# Create a custom nginx configuration
COPY ./nginx.conf /etc/nginx/conf.d/default.conf