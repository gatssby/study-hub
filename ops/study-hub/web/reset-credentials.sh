#!/bin/bash
# Rotate the Study Hub Basic Auth credential on oracle-vps. Run ON the VPS:
#   sudo bash /home/ubuntu/study-hub/ops/study-hub/web/reset-credentials.sh
# The new password is generated locally on the VPS, never placed in argv or logs, and
# stored only in /root/study-hub-web-credentials (0600 root). Read it with:
#   sudo cat /root/study-hub-web-credentials
set -euo pipefail
umask 077
[ "$(id -u)" = 0 ] || { echo "run with sudo" >&2; exit 1; }
USER_NAME=${1:-gatsby}
[[ "$USER_NAME" =~ ^[a-z][a-z0-9_-]{0,31}$ ]] || { echo "invalid user" >&2; exit 2; }
p=$(openssl rand -base64 30 | tr -d '\n/+=' | cut -c1-32)
h=$(printf '%s' "$p" | openssl passwd -6 -stdin)
printf 'user=%s\npassword=%s\ncreated=%s\n' "$USER_NAME" "$p" "$(date -u +%FT%TZ)" > /root/study-hub-web-credentials.new
printf '%s:%s\n' "$USER_NAME" "$h" > /etc/nginx/study-hub-web.htpasswd.new
unset p h
chown root:www-data /etc/nginx/study-hub-web.htpasswd.new; chmod 0640 /etc/nginx/study-hub-web.htpasswd.new
mv /root/study-hub-web-credentials.new /root/study-hub-web-credentials
mv /etc/nginx/study-hub-web.htpasswd.new /etc/nginx/study-hub-web.htpasswd
# nginx reads auth_basic_user_file per request; no reload needed.
echo "rotated; read with: sudo cat /root/study-hub-web-credentials"
