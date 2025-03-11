import os
import sys
from dotenv import load_dotenv
from app.twilio_server import app

# Make sure we're loading environment variables
load_dotenv()

# Check required environment variables
required_vars = [
    "GROQ_API_KEY",
    "DEEPGRAM_API_KEY", 
    "ELEVEN_LABS_API_KEY",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN"
]

missing_vars = [var for var in required_vars if not os.environ.get(var)]
if missing_vars:
    print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please check your .env file and ensure all required variables are set.")
    sys.exit(1)

if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    # Create templates directory if it doesn't exist
    template_dir = os.path.join('app', 'templates')
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
        
    # Print startup message
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting Jivus AI Voice Agent on port {port}")
    print("Dashboard will be available at http://localhost:{port}")
    print("Ctrl+C to quit")
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=port)