#!/bin/bash
cd "$(dirname "$0")"

# Inicia el servidor en segundo plano
python3 -m http.server 8000 &

# Guarda el PID del servidor
SERVER_PID=$!

# Da un pequeño tiempo para que arranque
sleep 1

# Abre el navegador en localhost
if command -v open &> /dev/null; then
    open "http://localhost:8000"
elif command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:8000"
fi

# Mantiene el script activo mientras el servidor corre
wait $SERVER_PID