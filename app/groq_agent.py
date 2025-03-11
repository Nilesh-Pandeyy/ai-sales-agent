from os import getenv
from groq import Groq
from vocode.streaming.agent.base_agent import BaseAgent
from vocode.streaming.models.agent import AgentConfig
from typing import Optional, AsyncGenerator, List
from pydantic import Field
from vocode.streaming.models.message import BaseMessage

class GroqAgentConfig(AgentConfig):
    model_name: str = Field(default="mixtral-8x7b-32768")
    temperature: float = Field(default=0.3)
    prompt_preamble: str = Field(default="You are a professional sales agent")

class GroqSalesAgent(BaseAgent):
    def __init__(self, config: GroqAgentConfig):
        super().__init__(config)
        self.groq_client = Groq(api_key=getenv("GROQ_API_KEY"))
        self.model_name = config.model_name
        self.temperature = config.temperature
        self.conversation_history = []
        self.initial_message = config.initial_message
        self.prompt_preamble = """Act as a concise and efficient sales representative. Your key goals are:
        1. Ask targeted, brief questions to understand customer needs
        2. Listen more than you speak
        3. Provide very brief, value-focused responses
        4. Guide the conversation with short, impactful statements
        5. Aim to speak no more than 15-20 words per response
        6. Encourage the customer to share more about their requirements"""
    
    async def respond(
        self, human_input: str, conversation_id: str = None, is_interrupt: bool = False
    ) -> AsyncGenerator[str, None]:
        """Generate a concise response to the human input."""
        # Add human message to conversation history
        self.conversation_history.append({"role": "user", "content": human_input})
        
        # Prepare system message with prompt preamble
        system_message = {"role": "system", "content": self.prompt_preamble}
        
        # Combine system message with conversation history
        messages = [system_message] + self.conversation_history
        
        # Generate response from Groq
        completion = self.groq_client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=50,  # Limit response length
            stream=True
        )
        
        # Process the streamed response
        full_response = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield content
        
        # Add assistant response to conversation history
        self.conversation_history.append({"role": "assistant", "content": full_response})
    
    async def get_initial_message(self) -> Optional[str]:
        """Return a very brief initial message to start the conversation."""
        if self.initial_message:
            # Keep the initial message short and engaging
            return self.initial_message.text[:50] + "..."
        return "Hello! I'd like to understand how I can help you today."
        
    def reset(self):
        """Reset the conversation history."""
        self.conversation_history = []