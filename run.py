#!/usr/bin/env python3
"""
Simple script to run the AI Persona Chat application
"""

import uvicorn
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Run the FastAPI application"""
    try:
        # Add the current directory to the Python path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

        # Check for OpenAI API key
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("⚠️  WARNING: OPENAI_API_KEY not found in environment variables!")
            print("   Please set your OpenAI API key in a .env file or environment variable.")
            print("   Copy .env.example to .env and add your key.")
            print("   The app will use fallback responses without OpenAI integration.\n")
        else:
            print("✅ OpenAI API key detected - GPT Realtime API enabled!\n")

        print("🚀 Starting AI Voice Personas - Realtime Voice Chat Server...")
        print("📱 Open your browser to: http://localhost:8000")
        print("🔌 WebSocket endpoint: ws://localhost:8000/ws/{client_id}")
        print("📊 API docs available at: http://localhost:8000/docs")
        print("\n🎤 Voice-Only AI Personas:")
        print("   🌟 Gold Astrologer - Mystical voice with cosmic wisdom")
        print("   🍎 Health & Dietitian - Professional wellness guidance")
        print("   💝 Consultant Friend - Warm emotional support")
        print("   🪟 Window Sales Specialist - Confident sales expertise")
        print("   🚗 Car Sales Specialist - Enthusiastic vehicle advice")
        print("   💼 Business Conversationalist - Professional discussions")
        print("\n🗣️ Pure Voice Interaction:")
        print("   • Hold microphone button to speak")
        print("   • Real-time voice-to-voice conversation")
        print("   • Each persona has unique voice and personality")
        print("   • No text interface - 100% voice experience")
        print("   • Press Space bar or hold mic button to talk")
        print("\n⚡ Press Ctrl+C to stop the server\n")

        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped. Thanks for using AI Persona Chat!")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())