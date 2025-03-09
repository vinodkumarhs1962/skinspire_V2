# Redis Setup and Usage Guide for Windows Development

## 1. WSL Installation and Setup

### 1.1 Install WSL
Open PowerShell as Administrator and run:
```powershell
wsl --install
```
This command:
- Enables WSL and Virtual Machine Platform features
- Downloads and installs the latest Linux kernel
- Sets WSL 2 as the default
- Downloads and installs Ubuntu Linux distribution

### 1.2 System Restart
- Restart your computer to complete the WSL installation
- After restart, Ubuntu will automatically start and ask you to:
  - Create a username
  - Set a password
  - These credentials are for your Linux environment

### 1.3 Verify Installation
```powershell
# Check WSL version
wsl --version

# List installed distributions
wsl --list --verbose
```

## 2. Redis Installation in WSL

### 2.1 Update Package Repository
```bash
# Add Redis repository key
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg

# Add Redis repository to sources
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list

# Update package list
sudo apt-get update
```

### 2.2 Install Redis
```bash
sudo apt-get install redis
```

## 3. Running Redis

### 3.1 Start Redis Server
```bash
# Start Redis service
sudo service redis-server start

# Check Redis service status
sudo service redis-server status
```

### 3.2 Test Redis Connection
```bash
# Open Redis CLI
redis-cli

# Test connection with ping
127.0.0.1:6379> ping
# Should return: PONG

# Exit Redis CLI
127.0.0.1:6379> exit
```

## 4. Using Redis with Your Application

### 4.1 Environment Configuration
Update your .env file with Redis connection settings:
```
DEV_REDIS_URL=redis://localhost:6379/0
TEST_REDIS_URL=redis://localhost:6379/1
PROD_REDIS_URL=redis://localhost:6379/2  # if needed
```

### 4.2 Daily Usage

#### Starting Redis (Every Time You Need It)
1. Open WSL terminal (Windows Terminal or PowerShell):
```powershell
wsl
```

2. Start Redis server:
```bash
sudo service redis-server start
```

#### Stopping Redis
```bash
sudo service redis-server stop
```

#### Checking Redis Status
```bash
sudo service redis-server status
```

### 4.3 Common Redis CLI Commands
```bash
# Start Redis CLI
redis-cli

# List all keys
keys *

# Get value for a key
get keyname

# Set a value
set keyname value

# Delete a key
del keyname

# Clear all data
flushall

# Show server info
info
```

## 5. Troubleshooting

### 5.1 Redis Service Won't Start
```bash
# Check Redis logs
sudo tail -f /var/log/redis/redis-server.log

# Restart Redis service
sudo service redis-server restart

# Check if Redis port is in use
sudo netstat -nlp | grep 6379
```

### 5.2 Connection Issues
```bash
# Check if Redis is running
ps aux | grep redis

# Check Redis binding
sudo nano /etc/redis/redis.conf
# Look for 'bind 127.0.0.1' line

# Test network connectivity
telnet localhost 6379
```

## 6. Important Notes

1. **WSL Access**: Redis runs inside WSL but is accessible from Windows through localhost
2. **Persistence**: Redis data persists between WSL sessions but not system restarts by default
3. **Memory**: Monitor WSL memory usage if running other services
4. **Security**: Development setup - not configured for production security

## 7. Next Steps

1. Configure your Python application to use Redis:
```python
# Example Redis connection in Python
import redis

redis_client = redis.from_url('redis://localhost:6379/0')
redis_client.ping()  # Should return True
```

2. Test session management:
```python
# Example session storage
redis_client.set('session:123', 'user_data')
redis_client.get('session:123')  # Retrieve session
```

3. Monitor Redis in production scenarios:
```bash
# Memory usage
redis-cli info memory

# Connected clients
redis-cli info clients
```