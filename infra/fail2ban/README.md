# Fail2ban — системная установка

Используется **fail2ban на хосте**, а не в Docker. Логи nginx пишутся в `infra/nginx-logs/` (volume из docker-compose), поэтому хост видит их по пути `/var/opt/sinodik/infra/nginx-logs/access.log`.

## Установка на хост (Debian/Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y fail2ban
```

## Подключение джоба для Синодика

1. Убедитесь, что nginx уже хотя бы раз запускался (чтобы на хосте появился лог-файл):
   ```bash
   cd /var/opt/sinodik
   docker compose up -d nginx
   ```
2. Скопируйте джоб и перезапустите fail2ban:
   ```bash
   sudo cp infra/fail2ban/jail.d/sinodik-nginx-auth.local /etc/fail2ban/jail.d/
   sudo systemctl restart fail2ban
   ```

## Проверка

```bash
sudo fail2ban-client status sinodik-nginx-auth
```

После 5 неудачных попыток Basic Auth за 10 минут IP блокируется на 1 час (http/https).
