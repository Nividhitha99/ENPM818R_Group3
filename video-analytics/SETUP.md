# Video Analytics Dashboard - Team Setup Guide

## Prerequisites

Ensure you have the following installed:
- Docker Desktop (running)
- Git
- PowerShell (Windows) or Terminal (Mac/Linux)

## Quick Start Commands

### 1. Clone/Navigate to Project
```powershell
cd "C:\Users\YourName\Desktop\VirtualizationProject\video-analytics"
```

### 2. Start All Services
```powershell
docker-compose up -d
```

### 3. Check Service Status
```powershell
docker-compose ps
```

### 4. View Logs (if needed)
```powershell
docker-compose logs -f
```

### 5. Stop All Services
```powershell
docker-compose down
```

## Access URLs

Once services are running, access:

- **Frontend Dashboard**: http://localhost:3000
- **Uploader API**: http://localhost:8001/health
- **Analytics API**: http://localhost:8002/health
- **Auth API**: http://localhost:8003/health
- **Gateway API**: http://localhost:8000/health

## Rebuild Services (After Code Changes)

### Rebuild Frontend Only
```powershell
docker-compose build frontend
docker-compose up -d frontend
```

### Rebuild All Services
```powershell
docker-compose build
docker-compose up -d
```

### Rebuild Without Cache (Clean Build)
```powershell
docker-compose build --no-cache
docker-compose up -d
```

## Troubleshooting

### Check if Ports are Available
```powershell
netstat -an | Select-String ":3000"
```

### Restart a Specific Service
```powershell
docker-compose restart frontend
docker-compose restart uploader
docker-compose restart analytics
```

### View Service Logs
```powershell
docker-compose logs frontend
docker-compose logs uploader
docker-compose logs analytics
```

### Remove All Containers and Start Fresh
```powershell
docker-compose down -v
docker-compose up -d --build
```

## Development Workflow

### 1. First Time Setup
```powershell
cd video-analytics
docker-compose up -d --build
```

### 2. Daily Start
```powershell
docker-compose up -d
```

### 3. Daily Stop
```powershell
docker-compose down
```

### 4. After Pulling Code Changes
```powershell
git pull
docker-compose build
docker-compose up -d
```

## Verify Everything is Working

```powershell
# Check all containers are running
docker-compose ps

# Test frontend
Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing

# Test backend APIs
Invoke-WebRequest -Uri "http://localhost:8001/health" -UseBasicParsing
Invoke-WebRequest -Uri "http://localhost:8002/health" -UseBasicParsing
```

## Common Issues

### Port Already in Use
```powershell
# Find process using port 3000
netstat -ano | findstr :3000
# Kill process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

### Docker Desktop Not Running
- Start Docker Desktop application
- Wait for it to fully start (whale icon in system tray)

### Services Not Starting
```powershell
# Check Docker is running
docker ps

# Check logs for errors
docker-compose logs
```

## Project Structure
```
video-analytics/
├── backend/          # Microservices (FastAPI)
├── frontend/         # React Dashboard
├── terraform/        # Infrastructure as Code
├── k8s/              # Kubernetes Manifests
└── docker-compose.yml
```

