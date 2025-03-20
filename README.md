# Voice Agent API

A FastAPI application that processes voice input, generates AI responses, and returns spoken output.

## Setup

### Prerequisites
- Python 3.8+
- FFmpeg (for audio processing)

### Installation

1. Clone the repository
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Create a virtual environment
   ```
   python3 -m venv venv
   ```

3. Activate the virtual environment
   ```
   # On macOS/Linux
   source venv/bin/activate
   
   # On Windows
   venv\Scripts\activate
   ```

4. Install dependencies
   ```
   pip install -r requirements.txt
   ```

5. Create a `.env` file for environment variables. Rename .env_template to .env
   ```
   OPENAI_API_KEY=your_openai_api_key
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   ```

## Usage

### Running the application
```
python src/main.py
```

The API will be available at http://localhost:5001

### Endpoints

- Main interface: `GET /`
- Health Check: `GET /health`
- Test Endpoint: `GET /test`
- Voice Processing: `POST /talk`

## Development

### Adding new endpoints
Add new routes in `src/main.py` following the existing pattern with explicit return types.
