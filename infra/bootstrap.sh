#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/ep3-preflop-bootstrap.log) 2>&1
export AWS_DEFAULT_REGION='__REGION__'
export AWS_PAGER=''
dnf install -y docker git python3.12 python3.12-pip nginx
systemctl enable --now docker
mkdir -p /usr/local/lib/docker/cli-plugins /opt/ep3-preflop
curl -fsSL https://github.com/docker/compose/releases/download/v2.39.4/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
git clone https://github.com/vicenteehueichapan-boop/ep3-preflop-sixmax.git /opt/ep3-preflop/source
cd /opt/ep3-preflop/source
python3.12 -m venv /opt/ep3-preflop/tools
/opt/ep3-preflop/tools/bin/pip install --no-cache-dir boto3 certbot==5.4.0
export PATH="/opt/ep3-preflop/tools/bin:$PATH"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
aws logs create-log-group --log-group-name /ep3-preflop/app || test $? -eq 254
aws logs put-retention-policy --log-group-name /ep3-preflop/app --retention-in-days 7
aws ecr describe-repositories --repository-names ep3-preflop >/dev/null 2>&1 || aws ecr create-repository --repository-name ep3-preflop --image-scanning-configuration scanOnPush=true --tags Key=Project,Value=ep3-preflop
aws ecr get-login-password | docker login --username AWS --password-stdin "$ACCOUNT.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com"
docker build --target inference -t "$ACCOUNT.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/ep3-preflop:1" .
docker push "$ACCOUNT.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/ep3-preflop:1"
python infra/cloud.py deploy-model
python - <<'PY'
import os,secrets
db=secrets.token_hex(20);rabbit=secrets.token_hex(20)
values={'APP_ENV':'production','MODEL_BACKEND':'sagemaker','EVENT_TRANSPORT':'rabbitmq',
 'DATABASE_URL':'postgresql+psycopg://preflop:'+db+'@postgres/preflop',
 'DB_PASSWORD':db,'RABBIT_PASSWORD':rabbit,'RABBIT_URL':'amqp://preflop:'+rabbit+'@rabbitmq:5672/%2F',
 'JWT_SECRET':secrets.token_hex(32),'DEMO_USERNAME':'alumno','DEMO_PASSWORD':secrets.token_urlsafe(16),
 'SAGEMAKER_ENDPOINT':'ep3-preflop','AWS_DEFAULT_REGION':os.environ['AWS_DEFAULT_REGION'],'RATE_LIMIT_PER_MINUTE':'1200'}
with open('.env','x') as f:
 for k,v in values.items(): f.write(k+'='+v+'\n')
os.chmod('.env',0o600)
PY
docker compose build api
docker compose up -d
mkdir -p /var/www/acme
cat > /etc/nginx/conf.d/ep3-preflop.conf <<'NGINX'
server {
  listen 80 default_server;
  server_name _;
  location /.well-known/acme-challenge/ { root /var/www/acme; }
  location / { return 301 https://$host$request_uri; }
}
NGINX
# Amazon Linux nginx ships an HTTP default block: remove its default_server token
# only on this NEW dedicated instance, never on another project's host.
sed -i 's/listen       80;/listen       8081;/;s/listen       \[::\]:80;/listen       [::]:8081;/' /etc/nginx/nginx.conf
systemctl enable --now nginx
certbot certonly --non-interactive --agree-tos --register-unsafely-without-email --webroot --webroot-path /var/www/acme --preferred-profile shortlived --ip-address '__PUBLIC_IP__'
cat > /etc/nginx/conf.d/ep3-preflop.conf <<'NGINX'
limit_req_zone $binary_remote_addr zone=ep3_login:10m rate=10r/m;
server {
 listen 80 default_server; server_name _;
 location /.well-known/acme-challenge/ { root /var/www/acme; }
 location / { return 301 https://$host$request_uri; }
}
server {
 listen 443 ssl; server_name __PUBLIC_IP__;
 ssl_certificate /etc/letsencrypt/live/__PUBLIC_IP__/fullchain.pem;
 ssl_certificate_key /etc/letsencrypt/live/__PUBLIC_IP__/privkey.pem;
 ssl_protocols TLSv1.2 TLSv1.3;
 add_header X-Content-Type-Options nosniff always;
 add_header X-Frame-Options DENY always;
 client_max_body_size 32k;
 location /v1/auth/token {
  limit_req zone=ep3_login burst=10 nodelay;
  limit_req_status 429;
  proxy_pass http://127.0.0.1:8000;
  proxy_set_header Host $host;
 }
 location / {
  proxy_pass http://127.0.0.1:8000;
  proxy_set_header Host $host;
  proxy_set_header X-Forwarded-Proto https;
  proxy_read_timeout 60s;
 }
}
NGINX
nginx -t
systemctl reload nginx
printf '%s\n' '#!/bin/sh' 'systemctl reload nginx' > /etc/letsencrypt/renewal-hooks/deploy/nginx.sh
chmod +x /etc/letsencrypt/renewal-hooks/deploy/nginx.sh
bash infra/renewal.sh
echo "EP3_READY https://__PUBLIC_IP__"
