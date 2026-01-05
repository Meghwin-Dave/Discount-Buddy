# Discount Buddy – AWS Linux Setup Guide

This guide covers the step-by-step process to deploy and run Discount Buddy on an AWS EC2 Linux instance.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Provision EC2 Instance](#provision-ec2-instance)
3. [Connect to EC2 via SSH](#connect-to-ec2-via-ssh)
4. [System Update & Package Installation](#system-update--package-installation)
5. [Clone the Repository](#clone-the-repository)
6. [Environment Variables Setup](#environment-variables-setup)
7. [Install Application Dependencies](#install-application-dependencies)
8. [Database Setup](#database-setup)
9. [Run the Application](#run-the-application)
10. [Additional Recommendations](#additional-recommendations)
11. [Troubleshooting](#troubleshooting)

---

## 1. Prerequisites
- AWS account with permissions to launch EC2 instances
- SSH key pair for EC2 access
- [GitHub] access permissions to this repository
-  Open ports (e.g., 80/443 for web, 22 for SSH) in the AWS Security Group

## 2. Provision EC2 Instance
1. Go to the AWS Console > EC2 > Launch Instance.
2. Select a Linux AMI (e.g., Ubuntu 22.04 LTS or Amazon Linux 2).
3. Choose instance type (t2.micro for testing, larger as needed).
4. Configure security group (allow SSH (22), HTTP (80), HTTPS (443)).
5. Attach or create a key pair for SSH access.
6. Launch the instance.

## 3. Connect to EC2 via SSH
Get your instance's public DNS/IP. From your terminal:
```bash
ssh -i /path/to/your-key.pem ubuntu@your-ec2-public-dns
# or for Amazon Linux
ssh -i /path/to/your-key.pem ec2-user@your-ec2-public-dns
```

## 4. System Update & Package Installation
Update the system and install required packages (Python, pip, venv, PostgreSQL, Redis, and more):
```bash
sudo apt update && sudo apt upgrade -y # (Ubuntu/Debian)
sudo yum update -y                    # (Amazon Linux)
sudo apt install -y python3 python3-pip python3-venv git postgresql postgresql-contrib redis-server
sudo service postgresql start
sudo service redis-server start
```

## 5. Clone the Repository
```bash
git clone https://github.com/your-username/discount-buddy.git
cd discount-buddy
```

## 6. Environment Variables Setup
Create a `.env` file in your project root directory with the following content:

```env
DJANGO_SECRET_KEY=your-very-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=ec2-your-ip-or-domain,localhost,127.0.0.1

# PostgreSQL setup
DB_ENGINE=postgres
POSTGRES_DB=discountbuddy
POSTGRES_USER=postgres
POSTGRES_PASSWORD=1234
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis (for cache in production)
REDIS_URL=redis://localhost:6379/1
```

Adjust these values as needed for your setup.

## 7. Install Application Dependencies
Depending on the stack:
```bash
# Node.js/JavaScript
npm install
# Python
pip install -r requirements.txt
```

## 8. Database Setup (Switching to PostgreSQL)

The project is configured to use PostgreSQL. If not already installed, install it (see above), and make sure the service is running:

```bash
sudo service postgresql start
```

Create the database and user (these steps require `sudo` access):

```bash
sudo -u postgres psql
```
Inside the PostgreSQL shell, run:
```sql
CREATE DATABASE discountbuddy;
CREATE USER postgres WITH PASSWORD '1234';
GRANT ALL PRIVILEGES ON DATABASE discountbuddy TO postgres;
\q
```

If you already created the DB and user, just ensure your `.env` matches the above credentials.

Apply Django migrations:
```bash
python manage.py migrate
```

## 9. Run the Application
```bash
# Node.js
npm start
# or for production
npm run build && npm run start:prod
# Python
python app.py
```

## 10. Additional Recommendations
- Configure a process manager (pm2, systemd) for auto-restart
- Set up HTTPS with Nginx/Certbot (letsencrypt)
- Enable firewall (ufw, firewalld)

## 11. Troubleshooting
- Check application logs for errors
- Use `curl localhost:PORT` to verify the app is running
- Check AWS EC2 security group rules if the server is not accessible

---

## Contact
If you encounter issues, please contact the maintainer or open a GitHub issue.

