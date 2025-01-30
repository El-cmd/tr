FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r srcs/requirements.txt

# Create static directory and collect static files
RUN mkdir -p /app/srcs/static && \
    mkdir -p /app/srcs/staticfiles && \
    python /app/srcs/manage.py collectstatic --noinput

# Make port 80 available to the world outside this container
EXPOSE 8001

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT [ "/app/entrypoint.sh" ]