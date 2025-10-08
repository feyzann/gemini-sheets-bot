# Gemini Sheets Bot

FastAPI backend for n8n integration with Gemini 2.5 Flash and Google Sheets. This service provides a single `/chat` endpoint that processes user messages, looks up person information from Google Sheets, and generates personalized responses using Gemini AI.

## Features

- **Person Lookup**: Finds people by phone number (exact match) or name (fuzzy matching)
- **Google Sheets Integration**: Reads person data from a "People" sheet with 60-second TTL caching
- **Gemini AI Integration**: Uses Gemini 2.5 Flash with structured JSON output
- **Deterministic Responses**: Always returns standardized JSON response format
- **Production Ready**: Comprehensive logging, error handling, and health checks

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Google Cloud Service Account with Sheets API access
- Gemini API key

### 2. Installation

```bash
# Clone the repository
git clone <repository-url>
cd gemini-sheets-bot

# Install dependencies
pip install -e .

# Copy environment file
cp env.example .env

# Add your service account file (download from Google Cloud Console)
# Place your service-account.json file in the root directory
```

### 3. Environment Configuration

Edit `.env` file with your credentials:

```env
# Server Configuration
PORT=8080

# Gemini Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Google Sheets Configuration
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
SHEET_ID=1xxxxxxxxxxxxx
RANGE_PEOPLE=People!A2:K

# Application Configuration
DEFAULT_LOCALE=tr-TR
CACHE_TTL_MS=60000

# Logging
LOG_LEVEL=INFO
```

### 4. Google Sheets Setup

#### 4.1 Create Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Sheets API
4. Go to "Credentials" → "Create Credentials" → "Service Account"
5. Download the JSON key file and save as `service-account.json`

#### 4.2 Share Your Google Sheet

1. Open your Google Sheet
2. Click "Share" button
3. Add the service account email (from the JSON file) as "Viewer"
4. Copy the Sheet ID from the URL (between `/d/` and `/edit`)

#### 4.3 Prepare People Sheet

Create a sheet named "People" with the following structure:

| Column | Header | Description |
|--------|--------|-------------|
| A | person_id | Unique identifier |
| B | full_name | Full name |
| C | preferred_name | Preferred name |
| D | school | School name |
| E | department | Department |
| F | email | Email address |
| G | phone | Phone number (E.164 format) |
| H | locale | Locale (e.g., tr-TR) |
| I | profile_doc_id | Profile document ID |
| J | profile_text | Profile description |
| K | last_updated | Last updated date (YYYY-MM-DD) |

**Example data:**
```
person_id | full_name | preferred_name | school | department | email | phone | locale | profile_doc_id | profile_text | last_updated
1 | Ahmet Yılmaz | Ahmet | İTÜ | Bilgisayar Mühendisliği | ahmet@itu.edu.tr | +905551234567 | tr-TR | | Ahmet bilgisayar mühendisliği öğrencisi | 2024-01-15
```

### 5. Run the Application

```bash
# Development mode
uvicorn app.main:app --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

The API will be available at:
- API: http://localhost:8080
- Docs: http://localhost:8080/docs
- Health: http://localhost:8080/health

## API Usage

### Chat Endpoint

**POST** `/api/v1/chat`

#### Request Body

```json
{
  "message": "Merhaba, iade süreci nedir?",
  "user": {
    "name": "Feyza",
    "phone": "+905551234567",
    "locale": "tr-TR"
  }
}
```

#### Response

```json
{
  "answer_text": "Merhaba Feyza! İade süreci hakkında size yardımcı olabilirim...",
  "intent": "bilgi",
  "confidence": 0.95,
  "references": [
    {
      "source": "People",
      "person_id": "1"
    }
  ],
  "meta": {
    "locale_used": "tr-TR"
  }
}
```

### Test with cURL

```bash
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Merhaba",
    "user": {
      "phone": "+905551234567",
      "name": "Feyza",
      "locale": "tr-TR"
    }
  }'
```

## Person Finding Logic

The service finds people using the following priority:

1. **Phone Match**: Exact match on phone number (normalized to E.164 format)
2. **Name Match**: Fuzzy matching on `full_name` and `preferred_name` fields
3. **Message Extraction**: Extracts names from messages using regex patterns

### Phone Normalization

- `+905551234567` → `+905551234567` (E.164)
- `05551234567` → `+905551234567` (Turkish local)
- `90 555 123 45 67` → `+905551234567` (spaces removed)

### Name Matching

Uses `difflib.SequenceMatcher` with 85% similarity threshold:
- "Ahmet Yılmaz" matches "Ahmet Yilmaz" (missing dot)
- "Fatma Demir" matches "Fatma" (preferred name)

## Error Handling

### Person Not Found

When no person is found, the service returns a helpful message:

```json
{
  "answer_text": "Numaranızla eşleşen kayıt bulamadım; ad-soyad ve okul/bölüm bilgisini paylaşır mısınız?",
  "intent": "genel",
  "confidence": 0.3,
  "references": [],
  "meta": {
    "locale_used": "tr-TR",
    "person_not_found": true
  }
}
```

### Technical Errors

For internal errors (Sheets API, Gemini API), the service returns:

```json
{
  "answer_text": "Şu an teknik bir sorun oluştu. Lütfen daha sonra tekrar dener misiniz?",
  "intent": "genel",
  "confidence": 0.0,
  "references": []
}
```

## Logging

The application uses structured logging with request IDs:

```
2024-01-15 10:30:45 | INFO     | app.routes.chat:chat_endpoint:89 | [abc12345] Chat request received: Merhaba, iade süreci nedir?...
2024-01-15 10:30:45 | INFO     | app.routes.chat:chat_endpoint:95 | [abc12345] Retrieved 150 people records in 45.2ms
2024-01-15 10:30:45 | INFO     | app.routes.chat:chat_endpoint:120 | [abc12345] Found person: Ahmet Yılmaz (ID: 1)
2024-01-15 10:30:46 | INFO     | app.routes.chat:chat_endpoint:140 | [abc12345] Response generated in 1250.3ms (sheets: 45.2ms, llm: 1180.1ms) - Intent: bilgi, Confidence: 0.95
```

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

## Project Structure

```
.
├── pyproject.toml          # Dependencies and project config
├── env.example             # Environment variables template
├── README.md               # This file
├── app/
│   ├── main.py             # FastAPI app and health check
│   ├── routes/
│   │   └── chat.py         # Chat endpoint handler
│   ├── core/
│   │   ├── config.py       # Environment configuration
│   │   └── logging.py      # Loguru setup
│   ├── sheets/
│   │   └── client.py       # Google Sheets client with caching
│   ├── people/
│   │   └── find.py         # Person finding logic
│   ├── llm/
│   │   └── gemini.py       # Gemini AI client
│   └── models/
│       ├── request.py      # Request models
│       └── response.py     # Response models
└── tests/
    └── test_find.py        # Person finding tests
```

## Production Deployment

### Docker (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Environment Variables

Ensure all required environment variables are set:
- `GEMINI_API_KEY`: Your Gemini API key
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account JSON
- `SHEET_ID`: Your Google Sheet ID
- Other variables as needed

### Health Monitoring

The service provides health check endpoints:
- `GET /health`: Basic health status
- `GET /`: Service information

## Troubleshooting

### Common Issues

1. **Sheets API Error**: Check service account permissions and sheet sharing
2. **Gemini API Error**: Verify API key and model name
3. **Person Not Found**: Check phone format and name spelling
4. **Cache Issues**: Restart the application to clear cache

### Debug Mode

Set `LOG_LEVEL=DEBUG` in `.env` for detailed logging.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

[Add your license here]
