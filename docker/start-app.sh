#!/usr/bin/env bash
set -euo pipefail

# Small wait to ensure Xvfb is up
sleep 1

# Optionally update config from env var if provided
if [[ -n "${NVD_API_KEY:-}" ]]; then
  if [[ -f /app/config.json ]]; then
    # inject/replace nvd_api_key in config.json (simple jq-free sed approach)
    if grep -q '"nvd_api_key"' /app/config.json; then
      sed -i "s/\(\"nvd_api_key\"\)\s*:\s*\".*\"/\1: \"${NVD_API_KEY}\"/" /app/config.json || true
    else
      # insert key before last closing brace
      sed -i "s/}\s*$/  ,\n  \"nvd_api_key\": \"${NVD_API_KEY}\"\n}/" /app/config.json || true
    fi
  fi
fi

exec python app.py
