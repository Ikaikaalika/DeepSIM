# DeepSim Deployment Guide

## Quick Start (Local Development)

### 1. Using Docker Compose (Recommended)
```bash
# Clone and navigate to project
git clone <your-repo-url>
cd DeepSIM

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# Database UI: http://localhost:8080
```

### 2. Manual Setup
```bash
# Backend
cd backend
pip install -r requirements.txt
python main.py

# Frontend (new terminal)
cd frontend
npm install
npm start
```

## Production Deployment Options

### Option 1: Vercel + Railway
**Best for**: Quick deployment, minimal configuration

**Frontend (Vercel):**
```bash
npm install -g vercel
cd frontend
vercel deploy --prod
```

**Backend (Railway):**
1. Connect your GitHub repo to Railway
2. Deploy the `backend/` directory
3. Set environment variables:
   - `THUNDER_ENDPOINT`
   - `THUNDER_API_KEY`

### Option 2: AWS ECS + S3
**Best for**: Enterprise deployment, high availability

**Infrastructure:**
```bash
# Deploy using AWS CLI
aws ecs create-cluster --cluster-name deepsim-cluster
aws s3 mb s3://deepsim-frontend-bucket
```

**Backend:** Deploy container to ECS
**Frontend:** Static hosting on S3 + CloudFront

### Option 3: DigitalOcean App Platform
**Best for**: Balanced cost and features

1. Connect GitHub repository
2. Configure build settings:
   - Backend: Docker, port 8000
   - Frontend: Node.js, npm run build
3. Set environment variables
4. Deploy

### Option 4: Self-Hosted (VPS)
**Best for**: Full control, custom requirements

```bash
# On your server
git clone <repo-url>
cd DeepSIM

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Deploy
docker-compose up -d

# Setup reverse proxy (nginx)
sudo apt install nginx
# Configure nginx for domains
```

## Environment Variables

Create `.env` files:

**Backend (`backend/.env`):**
```
THUNDER_ENDPOINT=https://your-thunder-endpoint.com
THUNDER_API_KEY=your-api-key
DATABASE_URL=sqlite:///data/database.sqlite
API_HOST=0.0.0.0
API_PORT=8000
```

**Frontend (`frontend/.env`):**
```
REACT_APP_API_URL=https://your-api-domain.com
```

## Thunder Compute Integration

### 1. Setup Thunder Account
```bash
# Install Thunder CLI
pip install thunder-cli
thunder login
```

### 2. Deploy LLM Model
```bash
cd llm_finetune
python train_deepseek_thunder.py --config training_config.json
```

### 3. Setup Inference Endpoint
```bash
# Deploy model to Thunder
thunder deploy --model deepsim_deepseek_lora --name deepsim-llm
```

## Scaling Considerations

### Database
- **Development:** SQLite (included)
- **Production:** PostgreSQL or MySQL
  ```python
  # Update backend/main.py
  DATABASE_URL=postgresql://user:pass@host:5432/deepsim
  ```

### Load Balancing
```nginx
upstream deepsim_backend {
    server backend1:8000;
    server backend2:8000;
}

server {
    location /api/ {
        proxy_pass http://deepsim_backend;
    }
}
```

### Monitoring
```yaml
# docker-compose.yml additions
services:
  prometheus:
    image: prom/prometheus
  grafana:
    image: grafana/grafana
```

## Security Checklist

- [ ] Configure CORS properly for production domains
- [ ] Use HTTPS certificates (Let's Encrypt)
- [ ] Set up authentication if needed
- [ ] Configure rate limiting
- [ ] Secure environment variables
- [ ] Enable logging and monitoring

## Cost Estimates

### Vercel + Railway
- Frontend (Vercel): Free tier / $20/month
- Backend (Railway): $5-20/month
- **Total: $5-40/month**

### AWS
- ECS + RDS: $30-100/month
- S3 + CloudFront: $5-20/month
- **Total: $35-120/month**

### DigitalOcean
- App Platform: $12-25/month
- **Total: $12-25/month**

### Self-hosted VPS
- DigitalOcean Droplet: $6-20/month
- **Total: $6-20/month**

## Troubleshooting

### Common Issues
1. **Port conflicts**: Change ports in docker-compose.yml
2. **Memory issues**: Increase Docker memory limits
3. **CORS errors**: Update backend CORS settings
4. **Build failures**: Check Node.js/Python versions

### Logs
```bash
# Docker logs
docker-compose logs backend
docker-compose logs frontend

# Application logs
tail -f backend/app.log
```

## Support

- GitHub Issues: Report bugs and feature requests
- Documentation: Check README.md for API details
- Discord: Community support (link to be added)