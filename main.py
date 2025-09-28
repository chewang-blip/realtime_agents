from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import json
import asyncio
import base64
import logging
from typing import Dict, List
from datetime import datetime
from models.personas import PersonaManager, ChatMessage
from services.websocket_manager import ConnectionManager
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Persona Chat API", version="1.0.0")

# Templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize managers
persona_manager = PersonaManager()
connection_manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def get_voice_page(request: Request):
    """Serve the main voice interface page"""
    personas = persona_manager.get_all_personas()
    return templates.TemplateResponse("voice_chat_audioworklet.html", {
        "request": request,
        "personas": personas
    })

@app.get("/api/personas")
async def get_personas():
    """Get all available personas"""
    return {"personas": persona_manager.get_all_personas()}

@app.get("/api/personas/{persona_id}")
async def get_persona(persona_id: str):
    """Get a specific persona by ID"""
    persona = persona_manager.get_persona(persona_id)
    if not persona:
        return {"error": "Persona not found"}, 404
    return {"persona": persona}

@app.get("/api/stats")
async def get_stats():
    """Get current server statistics"""
    return {
        "active_connections": connection_manager.get_connection_count(),
        "connected_clients": connection_manager.get_connected_clients(),
        "available_personas": len(persona_manager.get_all_personas())
    }

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time voice chat with OpenAI Realtime API"""
    await connection_manager.connect(websocket, client_id)

    # Setup response handlers for this client (audio only)
    response_handlers = {
        "audio_delta": lambda event: handle_audio_delta(client_id, event),
        "audio_done": lambda event: handle_audio_done(client_id, event)
    }

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)

            # Process the message
            if message_data["type"] == "select_persona":
                # Set persona for this client
                persona_id = message_data["persona_id"]
                persona = persona_manager.get_persona(persona_id)
                connection_manager.set_client_persona(client_id, persona_id)

                # Send confirmation
                await connection_manager.send_message(client_id, {
                    "type": "persona_selected",
                    "persona": persona,
                    "message": f"Voice chat with {persona['name']} is ready!"
                })

            elif message_data["type"] == "start_conversation":
                # Start continuous conversation mode
                persona_id = connection_manager.get_client_persona(client_id)
                if not persona_id:
                    await connection_manager.send_message(client_id, {
                        "type": "error",
                        "message": "Please select a persona first."
                    })
                    continue

                try:
                    logger.info(f"Starting conversation for client {client_id} with persona {persona_id}")

                    # Initialize conversation with persona
                    result = await persona_manager.start_conversation(
                        persona_id, client_id, response_handlers
                    )

                    logger.info(f"Conversation started result: {result}")

                    await connection_manager.send_message(client_id, {
                        "type": "conversation_started",
                        "message": "Conversation started - speak naturally!"
                    })

                except Exception as e:
                    logger.error(f"Error starting conversation: {e}")
                    await connection_manager.send_message(client_id, {
                        "type": "error",
                        "message": f"Error starting conversation: {str(e)}"
                    })

            elif message_data["type"] == "audio_stream_data":
                # Handle continuous streaming audio data
                persona_id = connection_manager.get_client_persona(client_id)
                if not persona_id:
                    continue

                try:
                    if persona_manager.openai_client and persona_manager.openai_client.is_connected:
                        audio_data = base64.b64decode(message_data["audio_data"])
                        logger.debug(f"Received audio chunk: {len(audio_data)} bytes from client {client_id}")
                        await persona_manager.openai_client.append_audio_data(audio_data)

                        # Send audio data to OpenAI for processing
                        logger.debug(f"Sent {len(audio_data)} bytes to OpenAI")
                    else:
                        logger.warning("OpenAI client not connected when trying to send audio")
                        await connection_manager.send_message(client_id, {
                            "type": "error",
                            "message": "Voice service not connected. Please try again."
                        })

                except Exception as e:
                    logger.error(f"Error processing audio stream: {e}")
                    await connection_manager.send_message(client_id, {
                        "type": "error",
                        "message": f"Audio processing error: {str(e)}"
                    })

            elif message_data["type"] == "commit_audio_input":
                # Manual speech completion - commit audio buffer and trigger response
                if persona_manager.openai_client:
                    try:
                        logger.info(f"Committing audio input for manual speech from client {client_id}")
                        await persona_manager.openai_client.send_event("input_audio_buffer.commit")
                        await persona_manager.openai_client.send_event("response.create", {
                            "response": {
                                "modalities": ["audio"],
                                "instructions": "Respond to what the user just said in a natural, conversational way."
                            }
                        })
                    except Exception as e:
                        logger.error(f"Error committing audio input: {e}")
                        await connection_manager.send_message(client_id, {
                            "type": "error",
                            "message": f"Error processing speech: {str(e)}"
                        })

            elif message_data["type"] == "end_conversation":
                # End continuous conversation
                if persona_manager.openai_client:
                    try:
                        await persona_manager.openai_client.send_event("session.update", {
                            "session": {"turn_detection": None}
                        })
                        await connection_manager.send_message(client_id, {
                            "type": "conversation_ended",
                            "message": "Conversation ended"
                        })
                    except Exception as e:
                        logger.error(f"Error ending conversation: {e}")

    except WebSocketDisconnect:
        await persona_manager.cleanup_client_handlers(client_id)
        connection_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await persona_manager.cleanup_client_handlers(client_id)
        connection_manager.disconnect(client_id)

# Text handlers removed - voice-only application

async def handle_audio_delta(client_id: str, event: Dict):
    """Handle streaming audio response from OpenAI"""
    logger.info(f"Handling audio delta for client {client_id}")
    audio_delta = event.get("delta")
    if audio_delta:
        logger.info(f"Sending audio delta to client: {len(audio_delta)} chars")
        # Send base64 encoded audio chunk
        await connection_manager.send_message(client_id, {
            "type": "audio_delta",
            "audio_data": audio_delta,
            "timestamp": datetime.now().isoformat()
        })
    else:
        logger.warning("No audio delta in event")

async def handle_audio_done(client_id: str, event: Dict):
    """Handle completed audio response from OpenAI"""
    await connection_manager.send_message(client_id, {
        "type": "audio_response_complete",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)