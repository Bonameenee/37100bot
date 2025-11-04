#!/bin/bash
# ==============================================
# Script per aggiornare e riavviare il bot 37100
# ==============================================

# Cartella del progetto
cd /opt/37100bot || exit 1

# Log dell’operazione
echo "=== $(date '+%Y-%m-%d %H:%M:%S') - Aggiornamento bot ===" >> /var/log/37100bot_cron.log

# Esegui il pull dal branch main
git pull origin main >> /var/log/37100bot_cron.log 2>&1

# Riavvia il servizio systemd
systemctl restart 37100bot.service >> /var/log/37100bot_cron.log 2>&1

echo "✅ Bot aggiornato e riavviato correttamente" >> /var/log/37100bot_cron.log
