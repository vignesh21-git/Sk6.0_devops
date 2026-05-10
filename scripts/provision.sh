#!/bin/bash
# ============================================================
# Sk6.0 — Server Provisioning Script
# Run once on a fresh Ubuntu 22.04 LTS server as root.
# Usage: curl -sSL https://... | bash
#        or: bash scripts/provision.sh
# ============================================================

set -euo pipefail

DEPLOY_USER="deploy"
APP_DIR="/opt/sk6"
BACKUP_DIR="${APP_DIR}/backups"

log() { echo "━━ $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Run as root"

# ── OS Update ───────────────────────────────────────────────
log "Updating OS packages..."
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq
apt-get install -y -qq \
  curl wget git ufw fail2ban \
  apt-transport-https ca-certificates gnupg lsb-release \
  unattended-upgrades jq ncdu htop

# ── Docker ───────────────────────────────────────────────────
log "Installing Docker..."
if ! command -v docker &>/dev/null; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

# Install docker-compose v1 (used by project Makefile and scripts)
if ! command -v docker-compose &>/dev/null; then
  COMPOSE_VERSION="1.29.2"
  curl -fsSL \
    "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
fi

# Configure Docker daemon — structured logging, log rotation
cat > /etc/docker/daemon.json <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  }
}
EOF
systemctl restart docker

# ── Deploy user ──────────────────────────────────────────────
log "Creating deploy user..."
if ! id "${DEPLOY_USER}" &>/dev/null; then
  useradd -m -s /bin/bash -G docker "${DEPLOY_USER}"
fi

mkdir -p "/home/${DEPLOY_USER}/.ssh"
chmod 700 "/home/${DEPLOY_USER}/.ssh"
touch "/home/${DEPLOY_USER}/.ssh/authorized_keys"
chmod 600 "/home/${DEPLOY_USER}/.ssh/authorized_keys"
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "/home/${DEPLOY_USER}/.ssh"

echo ""
echo "  ➜ Paste your public SSH key for the deploy user:"
echo "    echo 'ssh-ed25519 AAAA...' >> /home/${DEPLOY_USER}/.ssh/authorized_keys"
echo ""

# ── SSH Hardening ────────────────────────────────────────────
log "Hardening SSH..."
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sed -i 's/^#*X11Forwarding.*/X11Forwarding no/' /etc/ssh/sshd_config
if ! grep -q "AllowUsers ${DEPLOY_USER}" /etc/ssh/sshd_config; then
  echo "AllowUsers ${DEPLOY_USER}" >> /etc/ssh/sshd_config
fi
systemctl restart sshd

# ── Firewall ─────────────────────────────────────────────────
log "Configuring UFW firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp  comment 'SSH'
ufw allow 80/tcp  comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable

# ── fail2ban ─────────────────────────────────────────────────
log "Configuring fail2ban..."
cat > /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port    = ssh
logpath = %(sshd_log)s

[nginx-limit-req]
enabled  = true
filter   = nginx-limit-req
port     = http,https
logpath  = /var/log/nginx/error.log
maxretry = 10
EOF
systemctl enable fail2ban && systemctl restart fail2ban

# ── Unattended security upgrades ─────────────────────────────
log "Enabling unattended-upgrades..."
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

# ── MinIO Client (mc) — for RustFS backup uploads ────────────
log "Installing mc (MinIO Client)..."
wget -q "https://dl.min.io/client/mc/release/linux-amd64/mc" -O /usr/local/bin/mc
chmod +x /usr/local/bin/mc

# ── App Directory ─────────────────────────────────────────────
log "Setting up app directory..."
mkdir -p "${APP_DIR}" "${BACKUP_DIR}" "${APP_DIR}/nginx/certs"
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${APP_DIR}"

# ── Log rotation for backup logs ─────────────────────────────
cat > /etc/logrotate.d/sk6 <<EOF
/var/log/sk6-*.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
    create 0640 ${DEPLOY_USER} adm
}
EOF

# ── Cron jobs ─────────────────────────────────────────────────
log "Installing cron jobs..."
crontab -u "${DEPLOY_USER}" - <<EOF
# Daily DB backup at 02:00
0 2 * * * /bin/bash ${APP_DIR}/scripts/backup.sh >> /var/log/sk6-backup.log 2>&1

# TLS renewal check at 03:00 and 15:00
0 3,15 * * * docker-compose -f ${APP_DIR}/docker-compose.yml exec -T certbot \
  certbot renew --quiet \
  --deploy-hook "docker-compose -f ${APP_DIR}/docker-compose.yml exec -T nginx nginx -s reload" \
  >> /var/log/sk6-certbot.log 2>&1
EOF

# ── Kernel tuning (high-concurrency TCP) ─────────────────────
log "Applying kernel tuning..."
cat >> /etc/sysctl.d/99-sk6.conf <<'EOF'
# High-concurrency tuning for Sk6.0
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15
fs.file-max = 1000000
EOF
sysctl --system -q

# ── Increase file descriptor limits ──────────────────────────
cat >> /etc/security/limits.d/99-sk6.conf <<'EOF'
*    soft nofile 65535
*    hard nofile 65535
root soft nofile 65535
root hard nofile 65535
EOF

log "Provisioning complete."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Next steps:"
echo ""
echo "  1. Add SSH public key:"
echo "     echo 'ssh-ed25519 ...' >> /home/${DEPLOY_USER}/.ssh/authorized_keys"
echo ""
echo "  2. Clone repo and configure:"
echo "     cd ${APP_DIR}"
echo "     git clone <repo-url> ."
echo "     cp .env.example .env && nano .env"
echo "     cp monitoring/alertmanager/alertmanager.yml.example \\"
echo "        monitoring/alertmanager/alertmanager.yml"
echo "     nano monitoring/alertmanager/alertmanager.yml"
echo ""
echo "  3. Obtain TLS certificate:"
echo "     docker-compose up -d nginx"
echo "     docker-compose run --rm certbot certonly \\"
echo "       --webroot -w /var/www/certbot -d \${DOMAIN}"
echo "     docker-compose restart nginx"
echo ""
echo "  4. Start full stack with monitoring:"
echo "     docker-compose --profile monitoring --profile production up -d"
echo ""
echo "  5. Set up RustFS buckets:"
echo "     mc alias set sk6rustfs http://localhost:9000 \$RUSTFS_ACCESS_KEY \$RUSTFS_SECRET_KEY"
echo "     mc mb sk6rustfs/sk6-static sk6rustfs/sk6-backups"
echo "     mc anonymous set download sk6rustfs/sk6-static"
echo ""
echo "  6. Verify all services healthy:"
echo "     docker-compose ps"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
