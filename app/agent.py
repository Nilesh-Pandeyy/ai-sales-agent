from vocode.streaming.models.agent import AgentConfig
from vocode.streaming.models.message import BaseMessage
from vocode.streaming.models.synthesizer import ElevenLabsSynthesizerConfig
from vocode.streaming.models.transcriber import DeepgramTranscriberConfig
from .groq_agent import GroqSalesAgent, GroqAgentConfig
import os
import asyncio
import requests
import json
import base64
from typing import Dict, Optional, List, Any

class SalesAgent:
    def __init__(self):
        # Check for required environment variables
        required_env_vars = [
            "GROQ_API_KEY",
            "DEEPGRAM_API_KEY", 
            "ELEVEN_LABS_API_KEY",
            "TWILIO_ACCOUNT_SID", 
            "TWILIO_AUTH_TOKEN"
        ]
        
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Configure the agent with GroqSalesAgent
        self.agent_config = GroqAgentConfig(
            initial_message=BaseMessage(
                text="Hello! Welcome to Jivus AI. How can I assist you today?"
            ),
            model_name="llama3-70b-8192",
            temperature=0.3,
            prompt_preamble="""Act as an experienced sales representative. Your goals are:
            1. Build rapport with customers
            2. Identify pain points through questions
            3. Present solutions naturally
            4. Handle objections professionally"""
        )
        
        # Configure Deepgram for speech recognition with required parameters
        self.deepgram_config = DeepgramTranscriberConfig(
            model_name="nova-2",
            language="en-US",
            tier="enhanced",
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            # Required parameters
            sampling_rate=8000,  # Standard for telephony
            audio_encoding="linear16",  # Using string instead of enum
            chunk_size=1024
        )
        
        # Configure ElevenLabs for voice synthesis with required parameters
        self.elevenlabs_config = ElevenLabsSynthesizerConfig(
            api_key=os.getenv("ELEVEN_LABS_API_KEY"),
            voice_id="EXAVITQu4vr4xnSDxMaL",  # Default voice ID
            model_id="eleven_turbo_v2",
            # Required parameters
            sampling_rate=22050,  # ElevenLabs default
            audio_encoding="linear16"  # Using string instead of enum
        )
        
        # Keep track of active conversations
        self.active_conversations = {}
    
    def get_conversation(self, call_sid):
        """Get or create a conversation for the given call SID."""
        if call_sid in self.active_conversations:
            return self.active_conversations[call_sid]
        
        # Create the GroqSalesAgent instance
        agent = GroqSalesAgent(self.agent_config)
        
        # Create an enhanced conversation with Deepgram and ElevenLabs integration
        conversation = EnhancedConversation(
            agent=agent,
            deepgram_config=self.deepgram_config,
            elevenlabs_config=self.elevenlabs_config
        )
        conversation.call_sid = call_sid
        
        # Store the conversation
        self.active_conversations[call_sid] = conversation
        return conversation
    
    def make_outbound_call(self, to_phone, from_phone, webhook_base_url=""):
        """Make an outbound call to the specified phone number."""
        # Import Twilio client
        from twilio.rest import Client
        
        # Get Twilio credentials from environment variables
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        
        client = Client(account_sid, auth_token)
        
        # Set up webhook URLs
        if not webhook_base_url:
            webhook_base_url = "http://your-server-url"  # Default fallback
            print(f"Warning: Using default webhook URL: {webhook_base_url}")
            print("Please provide your actual server URL for webhooks to work properly.")
        
        # Create the call
        call = client.calls.create(
            to=to_phone,
            from_=from_phone,
            url=f"{webhook_base_url}/twilio/outbound-connect",
            status_callback=f"{webhook_base_url}/twilio/status"
        )
        
        # Create a conversation
        conversation = self.get_conversation(call.sid)
        
        return conversation


class EnhancedConversation:
    """An enhanced conversation that integrates Deepgram and ElevenLabs."""
    
    def __init__(self, agent, deepgram_config, elevenlabs_config):
        self.agent = agent
        self.deepgram_config = deepgram_config
        self.elevenlabs_config = elevenlabs_config
        self.call_sid = None
        self.is_active = True
        
        # Store API keys for direct access
        self.deepgram_api_key = deepgram_config.api_key
        self.elevenlabs_api_key = elevenlabs_config.api_key
        self.elevenlabs_voice_id = elevenlabs_config.voice_id
        self.elevenlabs_model_id = elevenlabs_config.model_id
    
    async def transcribe_with_deepgram(self, audio_data_base64):
        """Transcribe audio using Deepgram API directly."""
        try:
            # Decode base64 audio data
            audio_data = base64.b64decode(audio_data_base64)
            
            # Set up Deepgram API request
            url = "https://api.deepgram.com/v1/listen"
            headers = {
                "Authorization": f"Token {self.deepgram_api_key}",
                "Content-Type": "audio/wav"  # Adjust based on your audio format
            }
            params = {
                "model": self.deepgram_config.model_name,
                "language": self.deepgram_config.language,
                "tier": self.deepgram_config.tier,
                "punctuate": True,
                "diarize": False
            }
            
            # Make the API request
            response = requests.post(url, headers=headers, params=params, data=audio_data)
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            # Extract the transcript
            if "results" in result and "channels" in result["results"]:
                transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
                return transcript
            
            return ""
        
        except Exception as e:
            print(f"Error transcribing with Deepgram: {e}")
            return ""
    
    async def synthesize_with_elevenlabs(self, text):
        """Synthesize speech using ElevenLabs API directly."""
        try:
            # Set up ElevenLabs API request
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}"
            headers = {
                "xi-api-key": self.elevenlabs_api_key,
                "Content-Type": "application/json"
            }
            data = {
                "text": text,
                "model_id": self.elevenlabs_model_id,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
            
            # Make the API request
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            # Get the audio data
            audio_data = response.content
            
            # Return as base64
            return base64.b64encode(audio_data).decode('utf-8')
        
        except Exception as e:
            print(f"Error synthesizing with ElevenLabs: {e}")
            return None
    
    async def get_response(self, user_input):
        """Get a response from the agent for the given user input."""
        full_response = ""
        async for chunk in self.agent.respond(user_input, self.call_sid):
            full_response += chunk
        return full_response
    
    async def process_speech_input(self, audio_data_base64):
        """Process speech input: transcribe, get response, and synthesize."""
        # Step 1: Transcribe with Deepgram
        transcript = await self.transcribe_with_deepgram(audio_data_base64)
        
        if not transcript:
            # If transcription failed, return a default response
            return {
                "success": False,
                "transcript": "",
                "response_text": "I'm sorry, I couldn't understand that. Could you please try again?",
                "response_audio": None
            }
        
        # Step 2: Get response from agent
        response_text = await self.get_response(transcript)
        
        # Step 3: Synthesize speech with ElevenLabs
        response_audio = await self.synthesize_with_elevenlabs(response_text)
        
        return {
            "success": True,
            "transcript": transcript,
            "response_text": response_text,
            "response_audio": response_audio
        }
    
    def terminate(self):
        """Terminate the conversation."""
        self.is_active = False
        self.agent.reset()
    
    # Add these attributes to mimic the expected interface
    @property
    def input_device(self):
        return SimpleDevice()
    
    @property
    def output_device(self):
        return SimpleDevice()
    
    def respond(self):
        """Generate TwiML for Twilio to respond to the call."""
        from twilio.twiml.voice_response import VoiceResponse
        
        response = VoiceResponse()
        
        # Get initial message from agent
        initial_message = None
        try:
            initial_message = asyncio.run(self.agent.get_initial_message())
        except:
            pass
        
        # Add a simple greeting message
        response.say(initial_message or "Hello! Welcome to Jivus AI. How can I assist you today?")
        
        # Add a gather to capture user input
        gather = response.gather(
            input="speech",
            action="/twilio/user-input",
            timeout=5,
            speech_timeout="auto"
        )
        
        return response


class SimpleDevice:
    """A simple mock device that does nothing but satisfies the interface."""
    
    def start(self, form_data=None):
        """Mock start method."""
        pass
    
    def receive_audio(self, audio_data):
        """Mock method to receive audio."""
        pass