# TOPIK OCR Tool - PydanticAI Optimized

🚀 **Hoàn toàn tối ưu hóa với PydanticAI** - Loại bỏ hoàn toàn legacy code, tối ưu performance và cost.

## ✨ Key Features

- **🤖 PydanticAI Integration**: Modern AI framework với type safety
- **⚡ Optimized Workflow**: OCR all images → Single AI call → Structured output
- **🔗 Cross-Image Processing**: Ghép nối câu hỏi từ nhiều ảnh
- **💰 Cost Effective**: Giảm API calls từ N xuống 1
- **🛡️ Type Safety**: Full Pydantic validation
- **🚀 High Performance**: Batch processing optimized

## 📁 Project Structure

```
topik_auto/
├── core/                    # Core processing modules (PydanticAI optimized)
│   ├── __init__.py         # Clean exports
│   ├── ocr_processor.py   # Enhanced PaddleOCR handling
│   └── structurer.py      # PydanticAI structuring (only)
├── api/                    # FastAPI backend (PydanticAI integrated)
│   ├── __init__.py        
│   ├── api.py            # Main FastAPI application
│   ├── endpoints.py      # Route definitions
│   ├── schemas.py        # Pydantic models
│   └── services.py       # Business logic (PydanticAI)
├── processors/            # High-level processors (optimized)
│   └── topik_processor.py # Main processor (PydanticAI only)
├── config/                # Configuration modules
├── database/              # Database managers
├── docker/                # Docker configuration
└── MIGRATION_TO_PYDANTIC_AI.md # Migration guide
```

## 🚀 Quick Start

### With Docker (Recommended)

1. **Environment Setup**
```bash
# Copy environment file
cp .env.example .env

# Edit .env file with your GEMINI_API_KEY
```

2. **Build and Run**
```bash
cd docker
docker-compose up --build
```

3. **Access Applications**
- **Gradio UI**: http://localhost:7866
- **FastAPI Backend**: http://localhost:8888
- **API Docs**: http://localhost:8888/docs

### Development Mode

1. **Backend (FastAPI)**
```bash
pip install -r requirements.txt
uvicorn api.api:app --host 0.0.0.0 --port 8888 --reload
```

2. **Frontend (Gradio)**
```bash
pip install -r requirements-gradio.txt
python app.py
```

## 🏗️ Architecture Overview

### Core Modules (Refactored)

**Before**: Single large `model.py` file
**After**: Modular structure:

- `preprocessor.py`: Image enhancement and preprocessing
- `ocr_processor.py`: PaddleOCR integration with error handling
- `structurer.py`: Gemini AI for data structuring
- `model.py`: Backward compatibility re-exports

### API Layer (MVC Pattern)

**Before**: Monolithic `main.py`
**After**: Clean separation:

- `api.py`: FastAPI app configuration
- `endpoints.py`: Route definitions and request handling
- `services.py`: Business logic and processing
- `schemas.py`: Request/response models

### Frontend (Modern Gradio App)

**Before**: Direct processing in Gradio
**After**: API-first architecture:

- Clean separation between UI and processing
- Async HTTP calls to backend API
- Professional UI with progress tracking
- Docker-native configuration

## 🔧 Key Improvements

### 1. **Modularity**
- Each component has single responsibility
- Easy to test and maintain individual modules
- Clear import structure with `__all__` definitions

### 2. **API Architecture**
- MVC pattern for better organization
- Service layer for business logic
- Proper error handling and status codes
- Swagger documentation auto-generated

### 3. **Docker Integration**
- Backend and frontend as separate containers
- Internal network communication
- Environment-based configuration
- Health checks and proper logging

### 4. **User Experience**
- Modern Gradio interface with custom styling
- Real-time progress tracking
- API health monitoring
- File management interface

## 🔍 API Endpoints

### Health & Status
- `GET /` - Basic health check
- `GET /health` - Detailed health status

### Processing
- `POST /process-images` - Process uploaded images
- `POST /process-zip` - Process ZIP file containing images

### File Management
- `GET /download/{filename}` - Download processed CSV
- `GET /list-outputs` - List available output files
- `DELETE /cleanup` - Clean up old files

## 🧪 Testing

### Test API Health
```bash
curl http://localhost:8888/health
```

### Test Image Processing
```bash
curl -X POST "http://localhost:8888/process-images" \
  -F "files=@test_image.jpg" \
  -F "source_info=Test TOPIK"
```

## 📝 Configuration

### Environment Variables

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional (with defaults)
API_BASE_URL=http://fastapi:8888
GRADIO_HOST=0.0.0.0
GRADIO_PORT=7866
NETWORK_NAME=kor-data-processing
```

### Docker Network

The containers communicate through a Docker network:
- `fastapi` container exposes port 8888
- `gradio-app` connects to `http://fastapi:8888`
- External access via mapped ports

## 🔄 Migration Guide

### From Old Structure

1. **Imports**: Update imports to use new module structure
```python
# Old
from core.model import TOPIKOCRProcessor

# New
from core import TOPIKOCRProcessor
# or
from core.ocr_processor import TOPIKOCRProcessor
```

2. **API**: Use new endpoint structure
```python
# Old
from api.main import app

# New  
from api import app
# or
from api.api import app
```

3. **Configuration**: Update environment variables and Docker setup

## 🐛 Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Check if FastAPI container is running
   - Verify network configuration in docker-compose
   - Check GEMINI_API_KEY is set

2. **OCR Initialization Error**
   - Ensure PaddleOCR dependencies are installed
   - Check available memory (OCR models are large)
   - Review OCR configuration in `config/ocr_config.py`

3. **Gradio UI Not Loading**
   - Verify port mapping in docker-compose
   - Check API_BASE_URL environment variable
   - Ensure gradio-app container can reach fastapi container

### Logs

```bash
# View all container logs
docker-compose logs

# View specific container
docker-compose logs fastapi
docker-compose logs gradio-app
```

## 🤝 Contributing

1. Follow the modular structure
2. Add tests for new functionality
3. Update documentation
4. Ensure Docker builds successfully

## 📄 License

[Your License Here]
