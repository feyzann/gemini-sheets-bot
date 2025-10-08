#!/usr/bin/env python3
"""Demo script to run the server with test configuration."""

import os
import uvicorn

# Set test environment variables
os.environ['GEMINI_API_KEY'] = 'test-key-replace-with-real'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './service-account.json'
os.environ['SHEET_ID'] = 'test-sheet-id-replace-with-real'
os.environ['RANGE_PEOPLE'] = 'People!A2:K'
os.environ['DEFAULT_LOCALE'] = 'tr-TR'
os.environ['CACHE_TTL_MS'] = '60000'
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['PORT'] = '8081'

# Import app after setting env vars
from app.main import app

if __name__ == "__main__":
    print("🚀 Starting Gemini Sheets Bot Demo Server...")
    print("📝 Note: This is running with test configuration.")
    print("🔧 To use real data, update the environment variables in this file.")
    print("📚 API Docs: http://localhost:8081/docs")
    print("❤️  Health Check: http://localhost:8081/health")
    print("💬 Chat Endpoint: POST http://localhost:8081/api/v1/chat")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8081,
        reload=False,
        log_level="info"
    )
