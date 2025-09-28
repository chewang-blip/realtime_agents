from fastapi import WebSocket
from typing import Dict, List, Optional
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.client_personas: Dict[str, str] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        """Remove a client connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.client_personas:
            del self.client_personas[client_id]
        print(f"Client {client_id} disconnected")

    async def send_message(self, client_id: str, message: dict):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                print(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast(self, message: dict, exclude_client: Optional[str] = None):
        """Broadcast a message to all connected clients"""
        disconnected_clients = []

        for client_id, websocket in self.active_connections.items():
            if exclude_client and client_id == exclude_client:
                continue

            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                print(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    def set_client_persona(self, client_id: str, persona_id: str):
        """Set the persona for a specific client"""
        self.client_personas[client_id] = persona_id

    def get_client_persona(self, client_id: str) -> Optional[str]:
        """Get the current persona for a client"""
        return self.client_personas.get(client_id)

    def get_connected_clients(self) -> List[str]:
        """Get list of all connected client IDs"""
        return list(self.active_connections.keys())

    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)