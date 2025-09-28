from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
import logging
from services.openai_realtime import OpenAIRealtimeClient

logger = logging.getLogger(__name__)

class ChatMessage(BaseModel):
    message: str
    timestamp: datetime
    sender: str  # "user" or "ai"

class Persona(BaseModel):
    id: str
    name: str
    description: str
    prompt: str
    color: str
    icon: str

class PersonaManager:
    def __init__(self):
        self.openai_client = None
        self.current_response_handlers = {}
        self.personas = {
            "astrologer": Persona(
                id="astrologer",
                name="Gold Astrologer",
                description="Wise and compassionate astrologer offering mystical insights",
                prompt="You are a wise and compassionate astrologer. Speak in a mystical yet reassuring tone, offering insights about zodiac signs, planetary alignments, and life paths. Use metaphors and gentle guidance to make the user feel inspired and hopeful. Keep explanations clear and personalized as if you are reading their stars.",
                color="#FFD700",
                icon="🌟"
            ),
            "health": Persona(
                id="health",
                name="Health & Dietitian",
                description="Certified health and nutrition consultant",
                prompt="You are a certified health and nutrition consultant. Speak in a friendly, practical, and motivating tone. Offer science-based advice on diet, fitness, and lifestyle habits. Adjust recommendations to the user's context, avoiding medical jargon. Encourage progress and small wins while making health feel achievable.",
                color="#4CAF50",
                icon="🍎"
            ),
            "emotional": Persona(
                id="emotional",
                name="Consultant Friend",
                description="Warm emotional support and guidance",
                prompt="You are a warm, non-judgmental consultant friend. Listen actively, validate emotions, and create a safe space where the user can open up. Use empathy, reflective listening, and gentle questions to help them process feelings. Avoid giving hard solutions unless asked; focus on emotional connection and encouragement.",
                color="#FF69B4",
                icon="💝"
            ),
            "windows": Persona(
                id="windows",
                name="Window Sales Specialist",
                description="Expert in aluminum and wooden windows",
                prompt="You are a persuasive yet friendly sales consultant specializing in aluminum and wooden windows. Highlight product benefits like durability, design, and energy efficiency. Tailor pitches to the user's needs (cost, aesthetics, maintenance). Use conversational selling with confidence but never pushy — focus on trust.",
                color="#8B4513",
                icon="🪟"
            ),
            "cars": Persona(
                id="cars",
                name="Car Sales Specialist",
                description="Enthusiastic car sales consultant",
                prompt="You are a car sales consultant. Be enthusiastic, knowledgeable, and approachable. Help the user explore car options, explain features, compare models, and guide them toward the right fit. Emphasize safety, performance, and lifestyle compatibility. Use storytelling and real-world examples to make it engaging.",
                color="#FF4500",
                icon="🚗"
            ),
            "general": Persona(
                id="general",
                name="Business Conversationalist",
                description="Versatile professional conversation partner",
                prompt="You are a versatile conversational partner who can adapt across casual chat, business brainstorming, and light mentorship. Keep the tone professional yet approachable. Engage with curiosity, provide insights when asked, and keep conversations flowing naturally, as if in real life.",
                color="#2196F3",
                icon="💼"
            )
        }

    def get_all_personas(self) -> List[Dict]:
        """Get all personas as dictionaries"""
        return [persona.dict() for persona in self.personas.values()]

    def get_persona(self, persona_id: str) -> Optional[Dict]:
        """Get a specific persona by ID"""
        persona = self.personas.get(persona_id)
        return persona.dict() if persona else None

    async def initialize_openai_client(self):
        """Initialize the OpenAI realtime client"""
        if not self.openai_client:
            try:
                self.openai_client = OpenAIRealtimeClient()
                await self.openai_client.connect()
                self._setup_event_handlers()
                logger.info("OpenAI Realtime client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                raise

    def _setup_event_handlers(self):
        """Setup event handlers for OpenAI realtime events"""
        if not self.openai_client:
            return

# Text handlers removed - voice-only application

        async def handle_audio_delta(event):
            """Handle streaming audio response"""
            logger.info(f"Received audio delta: {len(str(event))} bytes")
            for client_id, handlers in self.current_response_handlers.items():
                if 'audio_delta' in handlers:
                    try:
                        await handlers['audio_delta'](event)
                    except Exception as e:
                        logger.error(f"Error in audio_delta handler: {e}")

        async def handle_audio_done(event):
            """Handle completed audio response"""
            logger.info("Audio response completed")
            for client_id, handlers in self.current_response_handlers.items():
                if 'audio_done' in handlers:
                    try:
                        await handlers['audio_done'](event)
                    except Exception as e:
                        logger.error(f"Error in audio_done handler: {e}")

        async def handle_error(event):
            """Handle API errors"""
            logger.error(f"OpenAI API error: {event}")

        # Register event handlers (audio only)
        self.openai_client.on_event("response.audio.delta", handle_audio_delta)
        self.openai_client.on_event("response.audio.done", handle_audio_done)
        self.openai_client.on_event("error", handle_error)

# Text-based response generation removed - voice-only application

    async def start_conversation(self, persona_id: str, client_id: str = None, response_handlers: Dict = None):
        """Start a continuous conversation session with voice activity detection"""
        persona = self.personas.get(persona_id)
        if not persona:
            return {"error": "Persona not found"}

        if not self.openai_client:
            await self.initialize_openai_client()

        try:
            logger.info(f"Setting up conversation for persona {persona_id}")

            # Set up response handlers for this client
            if client_id and response_handlers:
                self.current_response_handlers[client_id] = response_handlers
                logger.info(f"Set up response handlers for client {client_id}")

            # Configure session for human-like continuous conversation
            session_update = {
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": f"{persona.prompt}\n\nIMPORTANT: You are having a natural voice conversation. Respond conversationally and authentically. Keep responses engaging but concise (1-2 sentences). Always acknowledge what the user says and continue the conversation naturally.",
                    "voice": self._get_persona_voice(persona_id),
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {"model": "whisper-1"},
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.6,  # Less sensitive - wait for clearer speech ending
                        "prefix_padding_ms": 400,  # More padding to catch full speech
                        "silence_duration_ms": 1200  # Wait longer for natural pauses
                    },
                    "temperature": 0.85,  # Natural but consistent responses
                    "max_response_output_tokens": 150,  # Allow slightly longer responses
                    "tool_choice": "none"  # Disable tool calling for faster responses
                }
            }

            logger.info(f"Sending session update for continuous conversation")
            await self.openai_client.send_event("session.update", session_update)

            # Clear input audio buffer and start fresh
            await self.openai_client.send_event("input_audio_buffer.clear")

            # Generate an initial greeting from the persona
            await self._send_initial_greeting(persona_id)

            logger.info("Conversation session configured successfully")
            return {"status": "conversation_started"}

        except Exception as e:
            logger.error(f"Error starting conversation: {e}", exc_info=True)
            return {"error": str(e)}

    async def _send_initial_greeting(self, persona_id: str):
        """Send an initial greeting message to start the conversation"""
        greetings = {
            "astrologer": "Hello, beautiful soul! The stars have guided you here today. I sense positive energy around you. What would you like to explore about your cosmic journey?",
            "health": "Hi there! I'm so excited to help you on your wellness journey today. Whether it's nutrition, fitness, or healthy habits, I'm here to support you. What health goals are you working on?",
            "emotional": "Hello, dear friend. I'm really glad you're here. This is a safe space where you can share whatever is on your heart. How are you feeling today?",
            "windows": "Good day! Thanks for considering us for your window needs. I'm here to help you find the perfect windows that combine beauty, efficiency, and value. What type of project are you working on?",
            "cars": "Hey there! Great to meet you! I'm pumped to help you find the perfect vehicle. Whether you're looking for reliability, performance, or style, we'll find something amazing together. What kind of driving do you do most?",
            "general": "Hello! It's great to connect with you today. I'm here for whatever you'd like to discuss - business ideas, casual conversation, or brainstorming. What's on your mind?"
        }

        greeting = greetings.get(persona_id, "Hello! How can I help you today?")

        # Create a text message to trigger an audio response
        timestamp = str(int(datetime.now().timestamp() * 1000000))
        await self.openai_client.send_event("conversation.item.create", {
            "item": {
                "id": f"greeting_{timestamp}",
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": greeting
                    }
                ]
            }
        })

        # Generate the audio response
        await self.openai_client.send_event("response.create", {
            "response": {
                "modalities": ["audio"],
                "instructions": "Speak this greeting message naturally with the persona's characteristic voice and tone. Be warm and engaging."
            }
        })

        logger.info(f"Sent initial greeting for persona {persona_id}")

    async def generate_audio_response(self, persona_id: str, audio_data: bytes, client_id: str = None, response_handlers: Dict = None):
        """Generate AI voice response from audio input - core voice-to-voice functionality"""
        persona = self.personas.get(persona_id)
        if not persona:
            return {"error": "Persona not found"}

        if not self.openai_client:
            await self.initialize_openai_client()

        try:
            # Set up response handlers for this client
            if client_id and response_handlers:
                self.current_response_handlers[client_id] = response_handlers

            # Configure session for voice-focused with persona characteristics
            await self.openai_client.send_event("session.update", {
                "session": {
                    **self.openai_client.session_config,
                    "modalities": ["audio", "text"],  # Must include both audio and text
                    "instructions": persona.prompt,
                    "voice": "alloy",
                    "input_audio_transcription": {"model": "whisper-1"},
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500
                    }
                }
            })

            # Send audio message with persona instructions
            await self.openai_client.send_audio_message(
                audio_data,
                persona_instructions=persona.prompt
            )

            return {"status": "voice_processing"}

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            return {"error": str(e)}

    def _get_persona_voice(self, persona_id: str) -> str:
        """Get appropriate voice for each persona"""
        voice_mapping = {
            "astrologer": "nova",      # Calm, mystical voice
            "health": "alloy",         # Professional, clear voice
            "emotional": "shimmer",    # Warm, empathetic voice
            "windows": "echo",         # Confident, sales voice
            "cars": "fable",          # Enthusiastic, engaging voice
            "general": "onyx"         # Professional, versatile voice
        }
        return voice_mapping.get(persona_id, "alloy")

    async def _generate_fallback_response(self, persona_id: str, user_message: str) -> str:
        """Generate fallback response when OpenAI is unavailable"""
        responses = {
            "astrologer": self._generate_astrologer_response(user_message),
            "health": self._generate_health_response(user_message),
            "emotional": self._generate_emotional_response(user_message),
            "windows": self._generate_windows_response(user_message),
            "cars": self._generate_cars_response(user_message),
            "general": self._generate_general_response(user_message)
        }

        await asyncio.sleep(1)  # Simulate processing
        return responses.get(persona_id, "I'm here to help! How can I assist you today?")

    async def cleanup_client_handlers(self, client_id: str):
        """Clean up response handlers for a disconnected client"""
        if client_id in self.current_response_handlers:
            del self.current_response_handlers[client_id]

    async def close(self):
        """Close the OpenAI client connection"""
        if self.openai_client:
            await self.openai_client.disconnect()
            self.openai_client = None

    def _generate_astrologer_response(self, message: str) -> str:
        message_lower = message.lower()
        if any(word in message_lower for word in ["horoscope", "zodiac", "sign", "stars"]):
            return "🌟 The stars whisper of great potential in your path. Your celestial energy suggests a time of transformation and growth. What zodiac sign guides your journey, dear soul?"
        elif any(word in message_lower for word in ["future", "prediction", "destiny"]):
            return "✨ The cosmic tapestry reveals that your future holds beautiful possibilities. The planets align to support your dreams, but remember - you are the co-creator of your destiny. Trust in the universe's timing."
        else:
            return "🌙 Welcome, kindred spirit. The universe has guided you here for a reason. Share what weighs on your heart, and let the stars illuminate your path forward."

    def _generate_health_response(self, message: str) -> str:
        message_lower = message.lower()
        if any(word in message_lower for word in ["diet", "food", "eat", "nutrition"]):
            return "🍎 Great question about nutrition! Remember, small sustainable changes make the biggest impact. Focus on adding more whole foods rather than restricting. What specific nutrition goals are you working toward?"
        elif any(word in message_lower for word in ["exercise", "workout", "fitness", "gym"]):
            return "💪 I love that you're thinking about fitness! The best workout is the one you'll actually do consistently. Start with 15-20 minutes of movement you enjoy. What activities make you feel energized?"
        else:
            return "🌟 Hello! I'm here to help you on your wellness journey. Whether it's nutrition, fitness, or healthy habits, we can work together to make health feel achievable and enjoyable. What would you like to focus on today?"

    def _generate_emotional_response(self, message: str) -> str:
        message_lower = message.lower()
        if any(word in message_lower for word in ["stressed", "anxious", "worried", "overwhelmed"]):
            return "💙 I hear you, and what you're feeling is completely valid. It's okay to feel overwhelmed sometimes - it shows you care deeply. Take a deep breath with me. What's weighing most heavily on your heart right now?"
        elif any(word in message_lower for word in ["sad", "down", "depressed", "hurt"]):
            return "🤗 I'm so glad you felt safe enough to share that with me. Your feelings matter, and you don't have to carry this alone. Sometimes just naming what we're feeling can be the first step. I'm here to listen without judgment."
        else:
            return "💝 Hello, dear friend. This is a safe space where you can be completely yourself. I'm here to listen, support, and walk alongside you through whatever you're experiencing. What's on your mind today?"

    def _generate_windows_response(self, message: str) -> str:
        message_lower = message.lower()
        if any(word in message_lower for word in ["aluminum", "aluminium", "metal"]):
            return "🪟 Excellent choice considering aluminum windows! They offer outstanding durability and virtually zero maintenance. Plus, modern aluminum frames provide superior energy efficiency with thermal breaks. What's your primary focus - longevity, aesthetics, or energy savings?"
        elif any(word in message_lower for word in ["wood", "wooden", "timber"]):
            return "🌳 Wooden windows bring such warmth and character to a home! They offer natural insulation properties and can be customized to match any architectural style. While they need some maintenance, the beauty and value they add is incomparable. Are you drawn to a traditional or contemporary wood design?"
        else:
            return "🏠 Welcome! I'm excited to help you find the perfect windows for your space. Whether you're drawn to the sleek durability of aluminum or the timeless beauty of wood, we'll find something that matches your style, budget, and performance needs. What's your vision for your windows?"

    def _generate_cars_response(self, message: str) -> str:
        message_lower = message.lower()
        if any(word in message_lower for word in ["suv", "family", "kids", "space"]):
            return "🚗 A family vehicle - now that's an exciting decision! SUVs offer incredible versatility, safety features, and that commanding road view. Whether it's weekend adventures or daily school runs, the right SUV becomes your family's trusted companion. What size family are we planning for?"
        elif any(word in message_lower for word in ["sedan", "car", "fuel", "economy"]):
            return "🌟 Sedans are fantastic - smooth ride, excellent fuel economy, and perfect for daily commuting! Modern sedans pack surprising amounts of tech and safety features too. Are you looking for something sporty and fun, or more focused on comfort and efficiency?"
        else:
            return "🚙 Hey there! I'm thrilled to help you find your next perfect ride. Every car has a story, and I'm here to help you find the one that fits yours. Whether it's your first car, an upgrade, or something completely different - let's discover what gets you excited! What brings you car shopping today?"

    def _generate_general_response(self, message: str) -> str:
        message_lower = message.lower()
        if any(word in message_lower for word in ["business", "work", "professional", "career"]):
            return "💼 That's a great professional topic! I'd love to explore this with you. Business success often comes down to understanding people, solving real problems, and building genuine relationships. What specific aspect would you like to dive into?"
        elif any(word in message_lower for word in ["idea", "brainstorm", "creative", "innovation"]):
            return "💡 I love brainstorming sessions! The best ideas often come from combining unexpected perspectives. Let's think creatively and explore possibilities together. What's the challenge or opportunity you're working with?"
        else:
            return "👋 Great to connect with you! I enjoy engaging conversations across all kinds of topics - whether it's business strategy, creative projects, or just exploring interesting ideas together. What's capturing your interest these days?"