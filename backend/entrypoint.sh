#!/bin/sh
set -e

# Esperar a que Qdrant esté disponible antes de continuar
python manage.py shell -c "
import socket, time, os
host = os.getenv('QDRANT_HOST', 'qdrant')
port = int(os.getenv('QDRANT_PORT', '6333'))
print(f'Esperando a Qdrant en {host}:{port}...')
for i in range(30):
    try:
        with socket.create_connection((host, port), timeout=2):
            print('Qdrant disponible.')
            break
    except (OSError, ConnectionRefusedError):
        time.sleep(2)
else:
    print('No se pudo conectar a Qdrant.')
    exit(1)
"

echo "Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

echo "Indexando documentos predeterminados..."
python manage.py index_default_documents

echo "Iniciando servidor de desarrollo de Django..."
exec python manage.py runserver 0.0.0.0:8000
