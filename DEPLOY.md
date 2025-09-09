# Deployment Guide

This document provides step-by-step instructions for deploying the Chemical Supplier Discovery API to production.

## Overview

The system is designed as a FastAPI application that can be deployed using several approaches:
- **Docker** (Recommended for production)
- **Local Python** (For development)
- **Cloud Platforms** (AWS, GCP, Azure)
- **Container Orchestration** (Kubernetes, Docker Swarm)

## Prerequisites

### Required
- Python 3.11+
- SerpAPI key (sign up at https://serpapi.com)
- Internet access for web scraping

### Optional
- Cohere API key (for advanced reranking)
- Docker & Docker Compose
- Load balancer (for production scale)

## Environment Variables

Create a `.env` file with the following variables:

```bash
# Required
SERPAPI_KEY=your_serpapi_key_here

# Optional
COHERE_API_KEY=your_cohere_key_here
PORT=8000
TOKENIZERS_PARALLELISM=false
```

## Deployment Options

### 1. Docker Deployment (Recommended)

**Step 1: Build and run with Docker Compose**
```bash
# Clone the repository
git clone <repository_url>
cd vald

# Create environment file
cp env.example .env
# Edit .env with your API keys

# Build and start the service
docker-compose up -d

# Check service health
curl http://localhost:8000/health
```

**Step 2: Test the API**
```bash
# Test basic endpoint
curl http://localhost:8000/

# Test supplier search
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "chemical_name": "Eucalyptol",
    "cas_number": "470-82-6",
    "limit": 5
  }'
```

### 2. Local Python Deployment

**Step 1: Install dependencies**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install chromium
```

**Step 2: Start the server**
```bash
# Development server (with auto-reload)
uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# Production server
gunicorn api:app --host 0.0.0.0 --port 8000 --workers 2 --worker-class uvicorn.workers.UvicornWorker --timeout 300
```

you can goto localhost:8000/docs

click on post/search

click try it out and paste this in

#### Search for all Suppliers
```bash
{
  "chemical_name": "CHECMICAL NAME HERE",
  "cas_number": "CAS NUMBER HERE",
  "limit": 10,
  "excluded_countries": [
    
  ],
  "allowed_countries": [
    
  ]
}
```

for an all search

## Example API Usage

### Search for Suppliers
```bash
curl -X POST "http://your-domain:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "chemical_name": "N-Methyl-2-pyrrolidone",
    "cas_number": "872-50-4",
    "limit": 10,
    "excluded_countries": ["China", "India"]
  }'
```


### Filter by Allowed Countries Only
```bash
curl -X POST "http://your-domain:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "chemical_name": "Acetone",
    "cas_number": "67-64-1",
    "limit": 5,
    "allowed_countries": ["United States", "Germany", "United Kingdom"]
  }'
```

### Common Issues

**1. Playwright Browser Not Found**
```bash
# Inside container or local environment
python -m playwright install chromium
```

**2. Memory Issues**
```bash
# Increase Docker memory limit
docker run -m 4g your-image

# Or update docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 4G
```

**3. SerpAPI Rate Limits**
- Monitor SerpAPI usage in dashboard
- Implement request queuing for high-volume scenarios
- Consider upgrading SerpAPI plan

**4. Slow Response Times**
- Enable model caching
- Use faster hardware (SSD storage)
- Implement result caching with Redis

### Logs and Debugging

**View Docker logs**
```bash
docker-compose logs -f api
```

**Check service health**
```bash
curl http://localhost:8000/health
```

**Test specific endpoints**
```bash
# Get supported countries
curl http://localhost:8000/countries

# Get example chemicals
curl http://localhost:8000/examples
```

## Security Checklist

- [ ] API keys stored securely (not in code)
- [ ] CORS configured for specific domains
- [ ] Rate limiting implemented
- [ ] HTTPS enabled (use reverse proxy like nginx)
- [ ] Input validation and sanitization
- [ ] Error messages don't expose sensitive information
- [ ] Regular security updates for dependencies
- [ ] Network security groups configured (cloud deployments)

## Maintenance

### Regular Tasks
- Monitor API usage and costs
- Update dependencies (monthly)
- Review and rotate API keys (quarterly)
- Monitor disk space and logs
- Backup configuration and any persistent data

### Updates and Rollbacks
```bash
# Rolling update with zero downtime
docker-compose pull
docker-compose up -d

# Rollback to previous version
docker tag your-image:latest your-image:rollback
docker-compose down
docker-compose up -d
```

## Support

For deployment issues:
1. Check logs for error details
2. Verify environment variables are set correctly
3. Ensure all dependencies are installed
4. Check network connectivity and firewall settings
5. Review resource usage (CPU, memory, disk)

For API-specific issues, refer to the interactive documentation at `/docs` endpoint.
