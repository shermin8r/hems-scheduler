# HEMS Education Scheduler - Railway Deployment

## Quick Railway Deployment Guide

### Step 1: Upload to GitHub
1. Create a new repository on GitHub (name it `hems-scheduler`)
2. Upload all files from this folder to the repository
3. Make sure the repository is public or accessible to Railway

### Step 2: Deploy to Railway
1. Go to [railway.app](https://railway.app) and log in
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your `hems-scheduler` repository
5. Railway will automatically detect it's a Python Flask app
6. Click "Deploy"

### Step 3: Configure Custom Domain (shermerautomation.com)
1. In your Railway project dashboard, go to "Settings"
2. Click "Domains" 
3. Click "Custom Domain"
4. Enter: `hems.shermerautomation.com` (or your preferred subdomain)
5. Railway will provide DNS records to add to Squarespace

### Step 4: Configure DNS in Squarespace
1. Log into your Squarespace account
2. Go to Settings > Domains > shermerautomation.com
3. Click "DNS Settings"
4. Add the CNAME record provided by Railway:
   - **Type**: CNAME
   - **Host**: hems (or your chosen subdomain)
   - **Points to**: [Railway will provide this URL]

### Step 5: Test Your Deployment
- Your HEMS scheduler will be available at: `https://hems.shermerautomation.com`
- Admin login: `admin` / `admin123`
- Change the password after first login!

## System Features
- ✅ Prevents double-booking automatically
- ✅ Three time slots per quarter (9-10, 10-11, 11-12)
- ✅ Speaker self-registration
- ✅ Admin dashboard for management
- ✅ Export functionality for contact lists
- ✅ Mobile responsive design

## Default Admin Credentials
- **Username**: admin
- **Password**: admin123
- **⚠️ IMPORTANT**: Change these credentials after first login!

## Support
- Railway hosting: ~$5/month for reliable performance
- Much faster than free hosting solutions
- 99.9% uptime guarantee
- Professional hosting for your medical team

## File Structure
```
├── main.py              # Main Flask application
├── requirements.txt     # Python dependencies
├── Procfile            # Railway deployment config
├── models/             # Database models
├── routes/             # API routes
├── static/             # Frontend files (React build)
└── database/           # SQLite database (auto-created)
```

The system is production-ready and optimized for Railway deployment!

