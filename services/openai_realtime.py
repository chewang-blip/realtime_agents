import asyncio
import json
import logging
import websockets
import base64
from typing import Dict, List, Optional, Callable
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class OpenAIRealtimeClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
        self.websocket = None
        self.is_connected = False
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.session_config = {
            "modalities": ["text", "audio"],
            "instructions": "",
            "voice": "alloy",
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "input_audio_transcription": {
                "model": "whisper-1"
            },
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.4,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 500
            },
            "tools": [],
            "tool_choice": "none",
            "temperature": 0.85,
            "max_response_output_tokens": 100
        }

    async def connect(self):
        """Connect to OpenAI Realtime API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "OpenAI-Beta": "realtime=v1"
            }

            self.websocket = await websockets.connect(
                self.url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )

            self.is_connected = True
            logger.info("Connected to OpenAI Realtime API")

            # Start listening for events
            asyncio.create_task(self._listen_for_events())

            # Send session configuration
            await self.send_event("session.update", {"session": self.session_config})

        except Exception as e:
            logger.error(f"Failed to connect to OpenAI Realtime API: {e}")
            self.is_connected = False
            raise

    async def disconnect(self):
        """Disconnect from OpenAI Realtime API"""
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
        self.is_connected = False
        logger.info("Disconnected from OpenAI Realtime API")

    async def send_event(self, event_type: str, data: Dict = None):
        """Send an event to the OpenAI Realtime API"""
        if not self.is_connected or not self.websocket:
            raise ConnectionError("Not connected to OpenAI Realtime API")

        # Generate valid event ID (alphanumeric + underscore/dash only)
        timestamp = str(int(datetime.now().timestamp() * 1000000))
        event_id = f"evt_{timestamp}"

        event = {
            "event_id": event_id,
            "type": event_type
        }

        if data:
            event.update(data)

        await self.websocket.send(json.dumps(event))
        logger.debug(f"Sent event: {event_type}")

    async def _listen_for_events(self):
        """Listen for events from OpenAI Realtime API"""
        try:
            async for message in self.websocket:
                try:
                    event = json.loads(message)
                    event_type = event.get("type")

                    if event_type:
                        await self._handle_event(event_type, event)

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.info("OpenAI Realtime API connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error listening for events: {e}")
            self.is_connected = False

    async def _handle_event(self, event_type: str, event: Dict):
        """Handle incoming events from OpenAI Realtime API"""
        logger.info(f"Received OpenAI event: {event_type}")
        logger.debug(f"Event data: {event}")

        handlers = self.event_handlers.get(event_type, [])
        if not handlers:
            logger.warning(f"No handlers registered for event type: {event_type}")

        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")

    def on_event(self, event_type: str, handler: Callable):
        """Register an event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    async def send_text_message(self, text: str, persona_instructions: str = ""):
        """Send a text message with persona instructions"""
        # Update session with persona instructions
        if persona_instructions:
            await self.send_event("session.update", {
                "session": {
                    **self.session_config,
                    "instructions": persona_instructions
                }
            })

        # Create conversation item
        timestamp = str(int(datetime.now().timestamp() * 1000000))
        await self.send_event("conversation.item.create", {
            "item": {
                "id": f"msg_{timestamp}",
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": text
                    }
                ]
            }
        })

        # Create response
        await self.send_event("response.create", {
            "response": {
                "modalities": ["text"],
                "instructions": persona_instructions
            }
        })

    async def send_audio_message(self, audio_data: bytes, persona_instructions: str = ""):
        """Send audio data for processing"""
        # Update session with persona instructions
        if persona_instructions:
            await self.send_event("session.update", {
                "session": {
                    **self.session_config,
                    "instructions": persona_instructions
                }
            })

        # Encode audio data to base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        # Create conversation item with audio
        timestamp = str(int(datetime.now().timestamp() * 1000000))
        await self.send_event("conversation.item.create", {
            "item": {
                "id": f"audio_{timestamp}",
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "audio": audio_base64
                    }
                ]
            }
        })

        # Create response
        await self.send_event("response.create", {
            "response": {
                "modalities": ["text", "audio"],
                "instructions": persona_instructions
            }
        })

    async def start_audio_stream(self):
        """Start streaming audio input"""
        await self.send_event("input_audio_buffer.clear")

    async def append_audio_data(self, audio_data: bytes):
        """Append audio data to the input buffer for continuous conversation"""
        try:
            # Convert audio data to base64 for transmission
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            # Send to OpenAI Realtime API
            await self.send_event("input_audio_buffer.append", {
                "audio": audio_base64
            })

            logger.debug(f"Successfully appended {len(audio_data)} bytes of audio data")

        except Exception as e:
            logger.error(f"Error appending audio data: {e}")
            raise

    async def commit_audio_input(self):
        """Commit the audio input buffer"""
        await self.send_event("input_audio_buffer.commit")

    async def cancel_response(self):
        """Cancel the current response generation"""
        await self.send_event("response.cancel")

    def set_persona_instructions(self, instructions: str):
        """Update the persona instructions"""
        self.session_config["instructions"] = instructions

    def set_voice(self, voice: str):
        """Set the voice for audio responses"""
        self.session_config["voice"] = voice

    def set_temperature(self, temperature: float):
        """Set the response temperature"""
        self.session_config["temperature"] = temperature