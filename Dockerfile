FROM python:3.11-slim

# System deps for GUI (Tkinter), VNC/noVNC, and scanning tools
RUN apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
     python3-tk \
     xvfb x11vnc fluxbox \
     novnc websockify \
     nmap \
     ca-certificates curl \
     supervisor \
  && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:0 \
    NO_VNC_PORT=6080 \
    VNC_PORT=5900 \
    SCREEN_W=1280 \
    SCREEN_H=800 \
    SCREEN_D=24

WORKDIR /app

# Install Python deps first for better caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Supervisor config and start script
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/start-app.sh /usr/local/bin/start-app.sh
RUN chmod +x /usr/local/bin/start-app.sh

# Expose noVNC (web) and VNC ports
EXPOSE 6080 5900

# Default volumes for persistent data/config
VOLUME ["/app/modules/cve/nvd_data", "/app/backups"]

# Start all services (Xvfb, fluxbox, x11vnc, websockify, then the app)
CMD ["/usr/bin/supervisord", "-n"]
