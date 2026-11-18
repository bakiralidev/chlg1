# HTTPS (Let's Encrypt / Certbot) Sozlash Qo'llanmasi

Dev rejimda `nginx/nginx.conf` (sertifikatsiz HTTP) ishlatiladi. Production domenga ulanganda `nginx/nginx.ssl.conf` ga o'tiladi.

## 1. Sertifikat olish (Certbot)

```bash
sudo certbot certonly --webroot \
  -w /var/www/certbot \
  -d your-domain.uz \
  --email admin@your-domain.uz \
  --agree-tos --no-eff-email
```

## 2. Docker Compose ga ulash

`docker-compose.yml` dagi `nginx` xizmatiga sertifikat papkalarini ulang:

```yaml
    volumes:
      - ./nginx/nginx.ssl.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - /var/www/certbot:/var/www/certbot:ro
```

`nginx.ssl.conf` ichidagi `/etc/letsencrypt/live/pychallenge/` yo'lini domeningiz nomiga moslang, so'ngra qayta ishga tushiring:

```bash
docker compose up -d nginx
```

## 3. Avtomatik yangilash (Cron)

```bash
0 3 * * * certbot renew --quiet && docker compose exec nginx nginx -s reload
```
