# Deploying Manager AI on a VPS

## Prerequisites
- A VPS (Ubuntu 20.04/22.04 recommended)
- Python 3.8+
- Nginx (optional, but recommended as a reverse proxy)

## Installation Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/kingnigelpat/manager-ai.git
   cd manager-ai
   ```

2. **Set up Virtual Environment**
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Create a `.env` file with your secrets:
   ```bash
   nano .env
   ```
   Paste the following (fill in your keys):
   ```
   OPENAI_API_KEY=your_key_here
   SECRET_KEY=your_random_secret_string
   ADMIN_PIN=your_admin_pin
   ```

5. **Run with Gunicorn (Production Server)**
   Do not use `python app.py` in production. Use Gunicorn:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:8000 app:app
   ```
   - `-w 4`: Uses 4 worker processes.
   - `-b 0.0.0.0:8000`: Binds to port 8000 on all interfaces.

   You can now access your app at `http://your_vps_ip:8000`.

## keeping it Running (Systemd)

To keep the app running after you close the terminal:

1. Create a service file:
   ```bash
   sudo nano /etc/systemd/system/manager-ai.service
   ```

2. Paste this content (adjust paths as needed):
   ```ini
   [Unit]
   Description=Gunicorn instance to serve Manager AI
   After=network.target

   [Service]
   User=root
   Group=www-data
   WorkingDirectory=/root/manager-ai
   Environment="PATH=/root/manager-ai/venv/bin"
   ExecStart=/root/manager-ai/venv/bin/gunicorn --workers 3 --bind unix:manager-ai.sock -m 007 app:app

   [Install]
   WantedBy=multi-user.target
   ```

3. Start and enable the service:
   ```bash
   sudo systemctl start manager-ai
   sudo systemctl enable manager-ai
   ```

## Nginx Setup (Recommended)
If you want to use a domain name and HTTPS:

1. Install Nginx: `sudo apt install nginx`
2. Create config: `sudo nano /etc/nginx/sites-available/manager-ai`
3. Add proxy pass to the unix socket or port 8000.
4. Enable with `ln -s`.
