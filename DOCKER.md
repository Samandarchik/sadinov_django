# Sadinov Store — Docker bilan ishga tushirish

## Tezkor start

```bash
cd sadinov_django

# 1) Environment'ni sozlash
cp .env.example .env
nano .env   # FERNET_KEY, ESKIZ_PASSWORD, ADMIN_PASSWORD ni to'ldiring

# 2) Mavjud SQLite bazasini volume joyiga ko'chirish (faqat birinchi marta)
mkdir -p data
cp ../store.db data/store.db    # bor bo'lsa

# 3) Build va ishga tushirish
docker compose up -d --build

# 4) Loglar
docker compose logs -f

# 5) To'xtatish
docker compose down
```

Backend `http://your-host:8001` da ishlay boshlaydi.

---

## Yo'q'lash / yangilash

```bash
# Kodni yangilab, qayta build
git pull
docker compose up -d --build

# Konteynerni qayta ishga tushirish
docker compose restart

# Bazaga konsoldan tegish
docker compose exec backend python manage.py shell
```

---

## Production (Nginx + HTTPS)

`docker-compose.yml`'ga proxy qatlam qo'shing yoki host'dagi nginx orqali:

```nginx
server {
    listen 443 ssl http2;
    server_name sayfullayevdev.uz;

    ssl_certificate     /etc/letsencrypt/live/sayfullayevdev.uz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sayfullayevdev.uz/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Fayllar ro'yxati

| Fayl | Tavsif |
|------|--------|
| `Dockerfile` | Python 3.13 + gunicorn |
| `docker-compose.yml` | Bir konteyner, port 8001, volume |
| `.dockerignore` | Image hajmini kichraytirish |
| `.env.example` | Maxfiy o'zgaruvchilar namunasi |
| `requirements.txt` | Python bog'liqliklar |

---

## Backup

```bash
# DB nusxasini olish
docker compose cp backend:/app/data/store.db ./backup-$(date +%F).db

# Restore
docker compose down
cp backup-2026-05-11.db ./data/store.db
docker compose up -d
```
