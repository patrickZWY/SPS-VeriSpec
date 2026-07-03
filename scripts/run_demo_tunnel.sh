#!/usr/bin/env bash
set -euo pipefail

TUNNEL_NAME="${SPS_AGENT_TUNNEL:-sps-verispec-demo}"
ORIGIN_URL="${SPS_AGENT_ORIGIN:-http://127.0.0.1:8765}"

exec cloudflared tunnel run --url "$ORIGIN_URL" "$TUNNEL_NAME"
