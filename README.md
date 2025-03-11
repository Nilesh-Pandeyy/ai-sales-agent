# Jivus AI Voice Agent

## Overview

Jivus AI Voice Agent is an advanced conversational AI platform that enables automated outbound calling with intelligent, context-aware communication. Leveraging cutting-edge AI technologies, this solution provides a powerful tool for sales, customer support, and communication automation.

## 🚀 Features

### AI-Powered Communication
- Intelligent conversation management
- Context-aware responses
- Adaptive communication strategy

### Technical Capabilities
- Outbound call initiation
- Real-time speech transcription
- AI-generated voice responses
- Comprehensive conversation logging
- Web-based dashboard for call monitoring

## 🛠 Technology Stack

### Core Technologies
- Python
- Flask
- Twilio
- Groq AI
- ElevenLabs Text-to-Speech
- Deepgram Speech Recognition

### Key Libraries
- vocode
- groq
- twilio
- pydantic

## 📋 Prerequisites

### Environment Requirements
- Python 3.8+
- Twilio Account
- Groq API Key
- ElevenLabs API Key
- Deepgram API Key

### Required Environment Variables
```
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
GROQ_API_KEY=your_groq_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
ELEVEN_LABS_API_KEY=your_elevenlabs_api_key
```

## 🔧 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Nilesh-Pandeyy/ai-sales-agent.git
cd ai-voice-agent
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Environment Variables
Create a `.env` file in the project root and add your API keys

Update twilio configuration and do setup of every thing like buying phone number and set webhook and save configuration

### 5. Run the Application
```bash
python main.py
```

## 🌐 Dashboard Access
- Navigate to `http://localhost:8000` or  Running on `http://127.0.0.1:8000`
 * Running on  `http:// IP address:8000`( local (private) IP address)
- Monitor calls
- Initiate outbound calls
- View call transcripts and analytics

## 📊 Key Components

### Agent Configuration
- Configurable AI behavior
- Customizable conversation strategies
- Context management

### Conversation Logging
- Full conversation transcripts
- Audio file preservation
- Detailed interaction metadata

### Call Workflow
1. Initiate Outbound Call
2. AI Generates Initial Greeting
3. Adaptive Conversation Flow
4. Comprehensive Logging
5. Call Termination

## 🔒 Security Considerations
- Secure API key management
- Conversation data encryption
- Compliance with telecommunication regulations

## 📈 Scalability
- Designed for horizontal scaling
- Modular architecture
- Easy integration with existing systems

## 🤝 Contributing
1. Fork the Repository
2. Create Feature Branch
3. Commit Changes
4. Push to Branch
5. Open Pull Request



## 🔍 Future Roadmap
- Enhanced AI models
- Multi-language support
- Advanced analytics
- Machine learning model training

---
