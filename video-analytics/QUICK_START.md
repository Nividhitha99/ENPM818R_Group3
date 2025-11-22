# Quick Start Commands for Team

## Windows PowerShell Commands

### Initial Setup (First Time)
```powershell
# Navigate to project
cd "C:\Users\YourName\Desktop\VirtualizationProject\video-analytics"

# Build and start all services
docker-compose up -d --build

# Verify services are running
docker-compose ps
```

### Daily Usage
```powershell
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart
```

### After Code Changes
```powershell
# Rebuild and restart
docker-compose build
docker-compose up -d
```

### Access Frontend
Open browser: **http://localhost:3000**

### Check Logs
```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs frontend
docker-compose logs uploader
```

### Troubleshooting
```powershell
# Restart specific service
docker-compose restart frontend

# Remove everything and start fresh
docker-compose down -v
docker-compose up -d --build

# Check if Docker is running
docker ps
```

