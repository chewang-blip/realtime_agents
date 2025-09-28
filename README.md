# AI Voice Personas - Pure Voice-to-Voice Chat

A real-time voice-only application with 6 different AI personas, built with FastAPI, WebSockets, and OpenAI's GPT Realtime API for seamless voice-to-voice conversations.

## Features

🌟 **6 Unique AI Personas:**
- **Gold Astrologer** - Mystical insights and celestial guidance
- **Health & Dietitian** - Science-based nutrition and wellness advice
- **Consultant Friend** - Warm emotional support and validation
- **Window Sales Specialist** - Expert in aluminum and wooden windows
- **Car Sales Specialist** - Enthusiastic vehicle recommendations
- **Business Conversationalist** - Professional and social discussions

🎤 **Pure Voice-to-Voice Experience:**
- **No text interface** - 100% voice interaction
- Real-time voice-to-voice conversation with GPT Realtime API
- Streaming audio responses
- Push-to-talk and space bar controls
- Voice activity detection
- Mute and volume controls
- Each persona has unique voice characteristics

🗣️ **Voice Features:**
- Hold microphone button to speak
- Real-time audio processing and streaming
- Instant voice responses
- Persona voice switching
- Background noise suppression
- Echo cancellation and auto-gain control

## Installation

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up OpenAI API Key:**
   ```bash
   # Copy the example environment file
   cp .env.example .env

   # Edit .env and add your OpenAI API key
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **Run the Application:**
   ```bash
   python run.py
   ```

4. **Open Your Browser:**
   Navigate to: `http://localhost:8000`

**Note:** The application will work without an OpenAI API key but will use fallback responses instead of GPT Realtime API.

## API Endpoints

### REST API
- `GET /` - Main chat interface
- `GET /api/personas` - List all available personas
- `GET /api/personas/{persona_id}` - Get specific persona details
- `GET /api/stats` - Server statistics
- `GET /docs` - API documentation (Swagger UI)

### WebSocket
- `WS /ws/{client_id}` - Real-time chat connection

## Project Structure

```
agentApp/
├── main.py                 # FastAPI application
├── run.py                  # Startup script
├── requirements.txt        # Python dependencies
├── models/
│   ├── __init__.py
│   └── personas.py         # Persona definitions and logic
├── services/
│   ├── __init__.py
│   └── websocket_manager.py # WebSocket connection management
└── templates/
    └── chat.html           # Frontend interface
```

## Usage

1. **Start the Server:**
   ```bash
   python run.py
   ```

2. **Select a Persona:**
   - Click on any persona card in the sidebar
   - Each persona has a unique communication style

3. **Start Voice Conversation:**
   - **Select a Persona**: Click on any persona card to begin
   - **Hold to Speak**: Hold the microphone button or press Space bar
   - **Release to Send**: Release button/key to send your voice message
   - **Listen**: Receive instant voice responses from your AI persona
   - **Controls**: Use mute/volume buttons in bottom-right corner

## WebSocket Message Format

### Client to Server:
```json
{
  "type": "select_persona",
  "persona_id": "astrologer"
}

{
  "type": "chat_message",
  "message": "Hello, how are you?"
}
```

### Server to Client:
```json
{
  "type": "persona_selected",
  "persona": {...},
  "message": "You are now chatting with Gold Astrologer!"
}

{
  "type": "ai_response",
  "message": "🌟 The stars whisper of great potential...",
  "timestamp": "2024-01-15T10:30:00"
}
```

## Customization

### Adding New Personas
Edit `models/personas.py` to add new personas with:
- Unique ID and name
- Descriptive prompt for AI behavior
- Custom response generation logic
- Icon and color styling

### Styling
Modify `templates/chat.html` to customize:
- UI colors and layout
- Persona card designs
- Chat message appearance
- Responsive breakpoints

## Development

**Enable Debug Mode:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**API Documentation:**
Visit `http://localhost:8000/docs` for interactive API documentation.

## Requirements

- Python 3.7+
- FastAPI
- Uvicorn
- WebSockets
- Pydantic

## License

MIT License - Feel free to modify and distribute!