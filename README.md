# UEX Market Manager 


![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?style=for-the-badge&logo=discord&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)


# ✨ Description



**UEX Market Manager** is a Discord bot designed to manage and deliver UEX marketplace notifications in a secure, organized, and user-friendly way.

The bot receives **real-time notifications via webhooks** directly from the UEX platform.
Each user is assigned a **personal webhook endpoint**, allowing the system to correctly route events such as:

* Negotiation Started
* Chat Messages
* Negotiation Completion by Buyer
* Negotiation Completion by Seller

Every user has their own **private Discord thread**, accessible only to them, where all notifications are delivered in an organized and readable format.

All sensitive data (API keys, secrets, user sessions) is **securely stored and encrypted in the database**, ensuring complete privacy and data protection.

Users can **reply directly from Discord** to any negotiation message.
Thanks to the official UEX APIs, the bot automatically sends replies back to the UEX platform, enabling **seamless two-way communication** without leaving Discord.

The bot also supports an **automatic welcome reply system**:

* Customizable per user
* Can be enabled or disabled at any time
* Automatically sent when a new negotiation starts

A built-in **automatic translation system** supports **9 languages:**
**it, en, es, fr, de, pl, ru, zh, pt,** ensuring a smooth experience for international users.

The entire infrastructure is **fully Dockerized**, making deployment, updates, and maintenance simple and reliable.
The system uses:

* **PostgreSQL** for data persistence
* **Nginx** for internal routing and SSL termination
* **Certbot** for automatic HTTPS certificate management and renewal (configurable by the user)
* **custom watchdog service** that monitors the bot’s health and automatically restarts it in case of crashes or blocks

Additionally, the bot can **notify administrators via Discord webhooks** about system events, crashes, or restarts.

The architecture is **modular, scalable, and easily extendable**, allowing future expansion without major refactoring.

---

# 🧰 Tech Stack

| Component                  | Technology                 |
| -------------------------- | -------------------------- |
| **Language**               | Python 3.11+               |
| **Discord SDK**            | discord.py v2.5+           |
| **Async HTTP**             | aiohttp                    |
| **Database**               | PostgreSQL 15 (asyncpg)    |
| **Webhook Server**         | aiohttp (internal service) |
| **Reverse Proxy**          | Nginx                      |
| **HTTPS**                  | Certbot (Let's Encrypt)    |
| **Security**               | HMAC SHA256                |
| **Environment Management** | python-dotenv              |
| **Containerization**       | Docker + Docker Compose    |

---


# 🚀 Project Evolution

**UEX Market Manager Bot** is the natural evolution of my previous project:

🔗 Original Project:
https://github.com/Passluk00/UEX-Market

While the original version focused on basic notification delivery, this **new iteration** has been **completely redesigned and expanded** to offer a **production-ready, scalable, and secure platform**.


---

# ⚙️ Installation & Deployment Guide (Docker Compose)

 This guide explains how to deploy **UEX Market Manager Bot** using **Docker Compose** for a fast, reliable, and production-ready setup.

* ## Prerequisites
    Make sure the following tools are already installed on your system:
    * **"Docker"**
    * **"Docker Compose"**
    * **"Python 3.11+"**

* ## 🧱 Step 1 — Clone the Repository
    Clone the project repository and move into the project directory:

    ```
    git clone https://github.com/Passluk00/UEX-Market.git
    cd UEX-Market
    ```

* ## 🔐 Step 2 — Environment Configuration (.env)
    Create a `.env` file in the root directory:

    ```
    cp .env.example .env
    ```
    
    Edit the `.env` file and configure the following variables:
    
    ```
    # --- DISCORD CONFIGURATION ---
    DISCORD_TOKEN="Token"                       # Your Discord Bot Token from the Discord Developer Portal
    WEBHOOK_MONITORING_URL="https://..."        # Discord Webhook URL for bot status and heartbeat monitoring
    SYSTEM_LANGUAGE="en"                        # Default system language ( e.g., en, it, fr )

    # --- NETWORK CONFIGURATION ---
    TUNNEL_URL="https://your-domain.ddns.net"   # Your public DNS domain or IP (used for Webhook callbacks)
    PORT=20187                                  # Internal port where the Python webserver will listen

    # --- DATABASE CONFIGURATION ---
    DB_HOST="postgres"                          # Hostname of the database service (matches docker-compose service name)
    DB_PORT=5432                                # Port for PostgreSQL (default is 5432)
    DB_NAME="uexbot"                            # Name of the PostgreSQL database
    DB_USER="uexuser"                           # Username for database authentication
    DB_PASSWORD="superstrongpassword"           # Strong password for database authentication
    ENCRYPTION_KEY = "KEY"                      # Strong ENCRYPTION KEY

    # --- LOGGING ---
    LOG_PATH="./bot.log"                        # Path where the bot will store its execution logs
    ```
    ### ⚠️ Important
    * The `BASE_WEBHOOK_URL` must be publicly accessible.
    * `HTTPS` is strongly recommended for webhook security.
    * For the `ENCRYPTION_KEY` use the KeyGenerator.py


* ## 🗄 Step 3 — PostgreSQL Configuration

    PostgreSQL is automatically initialized via Docker.

    The database will:

    * **Store encrypted user credentials**    
    * **Store session data**
    * **Manage negotiation link mapping**

    No manual setup is required if environment variables are correct.

* ## 🌐 Step 4 — Nginx Configuration

    Edit the file:

    ```
    nginx/conf.d/default.conf
    ```
    
    Example configuration:
    
    ```
    server {
        listen 80;
        server_name **YOUR DOMAIN** ;    # change with your domain or ip

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$host$request_uri;
        }
    }

    # HTTPS
    server {
        listen 443 ssl;
        server_name **YOUR DOMAIN** ;        # change with your domain or ip

        ssl_certificate /etc/letsencrypt/live/ **YOUR DOMAIN** /fullchain.pem;    # change with your domain or ip
        ssl_certificate_key /etc/letsencrypt/live/ **YOUR DOMAIN** /privkey.pem;  # change with your domain or ip

        ssl_protocols TLSv1.2 TLSv1.3;

        # Landing page
        root /usr/share/nginx/html;
        index index.html;

        location / {
            try_files $uri $uri/ = 404;
        }

        # API bot
        location /health {
            proxy_pass http://python:20187/health;   # if you changed the port in the .env change it here too 
            proxy_set_header Host $host;
        }

        location /webhook {
            proxy_pass http://python:20187/webhook;  # if you changed the port in the .env change it here too 
            proxy_set_header Host $host;
        }
    }
    ```
    Replace:

    * `YOUR DOMAIN` with your real domain or public IP

    After SSL is enabled, port 443 will be automatically handled by Certbot.


* ## 🔒 Step 5 — SSL Certificates (Certbot)

    Certbot automatically:

    * Issues SSL certificates
    * Renews them on a scheduled interval (configurable)
    * Reloads Nginx without downtime

    No manual intervention is required once configured.


* ## 🔧 Step 6 — Docker-Compose Setup

    Edit the file:

    ```
    docker-compose.yml
    ```
    
    Example configuration:
    
    ```
    services:

        # Python Bot
        python:
            build: ./bot
            container_name: python
            restart: always
            volumes:
            - ./bot:/app
            expose:
            - "20187" # change this if you change the server port
            networks:
            - backend
            env_file:
            - .env
            depends_on:
            - postgres

        # Nginx Web Server
        nginx:
            image: nginx:alpine
            container_name: nginx
            restart: always
            ports:
            - "80:80"
            - "443:443"
            volumes:
            - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
            - ./nginx/conf.d:/etc/nginx/conf.d:ro
            - ./nginx/html:/usr/share/nginx/html:ro
            - ./certbot/www:/var/www/certbot
            - ./certbot/conf:/etc/letsencrypt
            depends_on:
            - python
            networks:
            - backend

        # Certbot for SSL Certificates
        certbot:
            image: certbot/certbot
            container_name: certbot
            volumes:
            - ./certbot/conf:/etc/letsencrypt
            - ./certbot/www:/var/www/certbot
            # Command changed to not attempt infinite renewal if it fails
            command: >
            certonly --webroot
            --webroot-path=/var/www/certbot
            --email test@gmail.com            # Change with your email for the cert
            --agree-tos
            --no-eff-email
            -d YOUR DOMAIN                    # Cahange with Your domain                
            

        # Watchdog Service
        watchdog:
            build: ./watchdog
            container_name: watchdog
            restart: always
            networks:
            - backend
            volumes:
            - /var/run/docker.sock:/var/run/docker.sock
            depends_on:
            - python

        # PostgreSQL Database
        postgres:
            image: postgres:16-alpine
            container_name: postgres
            restart: always
            env_file: 
            - .env
            environment:
            POSTGRES_DB: ${DB_NAME}
            POSTGRES_USER: ${DB_USER}
            POSTGRES_PASSWORD: ${DB_PASSWORD}
            volumes:
            - postgres_data:/var/lib/postgresql/data
            networks:
            - backend

        volumes:
        postgres_data:

        networks:
        backend:
            driver: bridge
    ```

    Replace:
    
    
    * Where you see a comment with `#` change them with the necessary data
    



* ## 🐳 Step 7 — Build & Start the Stack

    Run the following command from the project root:

    ```
    docker-compose up -d --build
    ```

    This will:

    * **Build all services**
    * **Create Docker networks**
    * **Start PostgreSQL, Nginx, Webhook server, Bot, Watchdog**
    * **Enable automatic restarts on failure**

    Check logs to verify everything is running:

    ```
    docker-compose logs -f
    ```

* ## ✅ Step 8 — Verify the Deployment

    Once the stack is running:

    * The Discord bot should appear **online**
    * Webhook endpoint should be reachable at:

    ```
    https://your-domain.com/webhook/<event>/<user_id>
    ```

    * PostgreSQL should initialize automatically
    * SSL certificates should be issued within a few seconds/minutes

    You can check the status of the bot by visiting url:
    
    ```
    https://your-domain.com/
    ```

* ## 🛡 Step 9 — Watchdog & Monitoring

    The built-in watchdog:
    * Monitors bot health
    * Restarts services on crash
    * Sends notifications to a management Discord webhook

    No additional configuration is required unless you want custom alerts.

* ## 🎛 Step 10 — Discord Bot Setup

    **1.** Invite the bot to your Discord server

    **2.** Use the management command to create the entry point button:
    ```
    /add channel:#uex-market	
    ```

    **3.** Users can now:

    * Open their private thread
    * Insert API credentials
    * Receive notifications
    * Reply directly from Discord

* ## 🚀 Ready to Go

Your **UEX Market Manager Bot** is now fully deployed, secure, and production-ready.

If you need to scale, add new features, or customize workflows, the Docker-based architecture makes expansion easy and safe.