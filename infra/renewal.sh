#!/bin/bash
set -euo pipefail
mkdir -p /etc/letsencrypt/renewal-hooks/deploy
printf '%s\n' '#!/bin/sh' 'systemctl reload nginx' > /etc/letsencrypt/renewal-hooks/deploy/nginx.sh
chmod +x /etc/letsencrypt/renewal-hooks/deploy/nginx.sh
cat > /etc/systemd/system/ep3-cert-renew.service <<'UNIT'
[Unit]
Description=Renovar exclusivamente el certificado de la demo EP3
After=network-online.target
[Service]
Type=oneshot
ExecStart=/opt/ep3-preflop/tools/bin/certbot renew --quiet
UNIT
cat > /etc/systemd/system/ep3-cert-renew.timer <<'UNIT'
[Unit]
Description=Renovacion de certificado EP3 cada seis horas
[Timer]
OnCalendar=*-*-* 00,06,12,18:00:00
Persistent=true
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now ep3-cert-renew.timer
