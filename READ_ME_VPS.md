# Deploying Manager AI on a VPS (Hostinger Ready)

## Prerequisites
- A VPS (Hostinger Ubuntu 22.04 recommended)
- Python 3.10+
- Nginx
- A domain name (raehub.live or similar)

## 1. Prepare Your VPS
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv nginx git -y
```

## 2. Clone & Setup
```bash
cd /opt
sudo git clone https://github.com/kingnigelpat/manager-ai.git
sudo chown -R $USER:$USER /opt/manager-ai
cd manager-ai

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Configuration (CRITICAL)

### A. Environment Variables
Create a `.env` file:
```bash
nano .env
```
Add these values:
```env
OPENAI_API_KEY=your_openrouter_key
SECRET_KEY=your_generated_random_string
ADMIN_PIN=your_4_digit_pin
CLOUDINARY_CLOUD_NAME=your_name
CLOUDINARY_API_KEY=your_key
CLOUDINARY_API_SECRET=your_secret
FORCE_HTTPS=True
SESSION_COOKIE_SECURE=True
```

### B. Firebase Credentials
1. Upload your `serviceAccountKey.json` to the root folder `/opt/manager-ai/`. 
2. **Frontend Config**: Edit `static/firebase-config.js` and paste your Firebase Web App credentials (API Key, App ID).

## 4. Gunicorn & Systemd (Stay Alive)

1. Create the service file:
```bash
sudo nano /etc/systemd/system/manager-ai.service
```

2. Paste this configuration:
```ini
[Unit]
Description=Gunicorn instance to serve Manager AI
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/opt/manager-ai
Environment="PATH=/opt/manager-ai/venv/bin"
ExecStart=/opt/manager-ai/venv/bin/gunicorn --workers 3 --bind unix:manager-ai.sock -m 007 wsgi:app

[Install]
WantedBy=multi-user.target
```

3. Start Service:
```bash
sudo systemctl daemon-reload
sudo systemctl start manager-ai
sudo systemctl enable manager-ai
```

## 5. Nginx (Secure Proxy)
1. Create Nginx config:
```bash
sudo nano /etc/nginx/sites-available/manager-ai
```
2. Paste:
```nginx
server {
    listen 80;
    server_name manager.raehub.live;

    location / {
        include proxy_params;
        proxy_pass http://unix:/opt/manager-ai/manager-ai.sock;
    }
}
```
3. Enable and Restart:
```bash
sudo ln -s /etc/nginx/sites-available/manager-ai /etc/nginx/sites-enabled
sudo nginx -t
sudo service nginx restart
```

## 6. SSL (HTTPS)
Highly recommended for production:
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d manager.raehub.live
```

---
**Note:** If Nginx is not installed, you can run temporarily on port 8000 using:
`gunicorn --bind 0.0.0.0:8000 wsgi:app`

