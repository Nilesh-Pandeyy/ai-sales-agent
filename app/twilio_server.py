
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file
from app.agent import SalesAgent
from app.conversation_logger import ConversationLogger
from datetime import datetime
import os
import json
import asyncio
import base64
import io
import hashlib
from twilio.twiml.voice_response import VoiceResponse
from dotenv import load_dotenv
load_dotenv()
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
AUDIO_RESPONSES_DIR = os.path.join(PROJECT_ROOT, 'audio_responses')
LOGS_DIR = os.path.join(PROJECT_ROOT, 'logs')
app = Flask(__name__, template_folder='templates')
agent = SalesAgent()
logger = ConversationLogger()


os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(AUDIO_RESPONSES_DIR, exist_ok=True)

def generate_audio_filename(call_sid, text):
    """Generate a consistent filename for audio responses."""
    # Use a hash of the call_sid and text to create a unique but consistent filename
    filename_hash = hashlib.md5(f"{call_sid}_{text}".encode()).hexdigest()
    return os.path.join(AUDIO_RESPONSES_DIR, f"{call_sid}_{filename_hash}.mp3")

@app.route("/")
def dashboard():
    """Render the dashboard page with call statistics."""
    # Get call statistics
    total_calls = 0
    today_calls = 0
    durations = []
    recent_calls = []
    
    # Iterate through log files
    if os.path.exists('logs'):
        for filename in os.listdir('logs'):
            if filename.endswith('.json'):
                with open(os.path.join('logs', filename), 'r') as f:
                    try:
                        call_data = json.load(f)
                        total_calls += 1
                        
                        # Check if call was today
                        start_time = datetime.fromisoformat(call_data['start_time'])
                        if start_time.date() == datetime.now().date():
                            today_calls += 1
                        
                        # Calculate duration if available
                        if 'end_time' in call_data:
                            end_time = datetime.fromisoformat(call_data['end_time'])
                            duration = (end_time - start_time).total_seconds() / 60  # in minutes
                            durations.append(duration)
                        
                        # Add to recent calls
                        if len(recent_calls) < 10:  # Just show the 10 most recent calls
                            call_sid = os.path.splitext(filename)[0]
                            status = call_data.get('status', 'unknown')
                            
                            # Format duration
                            if 'end_time' in call_data:
                                duration_str = f"{duration:.1f} min"
                            else:
                                duration_str = "In progress"
                            
                            recent_calls.append({
                                'sid': call_sid,
                                'number': call_data['customer_number'],
                                'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                                'duration': duration_str,
                                'status': status
                            })
                    except (json.JSONDecodeError, KeyError) as e:
                        print(f"Error parsing {filename}: {e}")
    
    # Calculate average duration
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    # Count active calls
    active_now = len(agent.active_conversations)
    
    # Sort recent calls by start time (newest first)
    recent_calls.sort(key=lambda x: x['start_time'], reverse=True)
    
    return render_template('dashboard.html', 
                           total_calls=total_calls,
                           today_calls=today_calls,
                           avg_duration=f"{avg_duration:.1f}",
                           active_now=active_now,
                           recent_calls=recent_calls)

@app.route("/transcript/<call_sid>")
def view_transcript(call_sid):
    """Render the transcript page for a specific call."""
    try:
        # Load call data from logs
        with open(f"logs/{call_sid}.json", 'r') as f:
            call_data = json.load(f)
        
        # Format data for template
        start_time = datetime.fromisoformat(call_data['start_time'])
        
        if 'end_time' in call_data:
            end_time = datetime.fromisoformat(call_data['end_time'])
            duration = (end_time - start_time).total_seconds() / 60  # in minutes
            duration_str = f"{duration:.1f} min"
            status = call_data.get('status', 'completed')
        else:
            duration_str = "In progress"
            status = "in-progress"
        
        # Format transcript for display
        transcript = []
        for entry in call_data.get('transcript', []):
            transcript.append({
                'role': 'agent' if 'agent' in entry else 'user',
                'content': entry.get('agent', entry.get('user', '')),
                'timestamp': datetime.fromisoformat(entry['timestamp']).strftime('%H:%M:%S')
            })
        
        call = {
            'sid': call_sid,
            'customer_number': call_data['customer_number'],
            'date': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'duration': duration_str,
            'status': status,
            'transcript': transcript
        }
        
        return render_template('transcript.html', call=call)
    
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        return f"Error loading transcript: {e}", 404

@app.route("/twilio/inbound", methods=["POST"])
def handle_inbound_call():
    """Handle inbound Twilio call."""
    call_sid = request.values.get("CallSid", "")
    from_number = request.values.get("From", "")
    
    # Log the call start
    logger.log_call_start(call_sid, from_number)
    
    # Get a conversation for this call
    conversation = agent.get_conversation(call_sid)
    
    # Generate response with TwiML
    return str(conversation.respond())
@app.route("/twilio/user-input", methods=["POST"])
def handle_user_input():
    """Handle user speech input from Twilio."""
    call_sid = request.values.get("CallSid", "")
    user_input = request.values.get("SpeechResult", "")
    
    # Get the conversation
    conversation = agent.get_conversation(call_sid)
    
    # Log the user input
    logger.log_interaction(call_sid, user_input, "Processing...")
    
    # Create a TwiML response
    response = VoiceResponse()
    
    if user_input:
        # Get AI response (blocking for simplicity)
        ai_response = asyncio.run(conversation.get_response(user_input))
        
        # Log the AI response
        logger.log_interaction(call_sid, user_input, ai_response)
        
        # Generate a consistent audio filename
        audio_file_path = generate_audio_filename(call_sid, ai_response)
        
        # Only generate audio if file doesn't exist
        if not os.path.exists(audio_file_path):
            try:
                # Generate speech asynchronously
                audio_base64 = asyncio.run(conversation.synthesize_with_elevenlabs(ai_response))
                
                if audio_base64:
                    # Save the audio 
                    with open(audio_file_path, "wb") as f:
                        f.write(base64.b64decode(audio_base64))
                else:
                    # Fallback to Twilio's TTS
                    response.say(ai_response)
            except Exception as e:
                print(f"Error generating speech: {e}")
                # Fallback to Twilio's TTS
                response.say(ai_response)
        
        # Play the audio if file exists
        if os.path.exists(audio_file_path):
            # Use relative path from audio_responses directory
            response.play(f"/twilio/audio/{os.path.basename(audio_file_path)}")
        else:
            # Fallback to Twilio's TTS
            response.say(ai_response)
    else:
        # No speech detected
        response.say("I'm sorry, I didn't hear anything. Could you please try again?")
    
    # Add another gather for continuous conversation
    gather = response.gather(
        input="speech",
        action="/twilio/user-input",
        timeout=5,
        speech_timeout="auto"
    )
    
    return str(response)
'''
@app.route("/twilio/audio/<filename>")
def serve_audio(filename):
    """Serve synthesized audio files."""
    try:
        return send_file(f"audio_responses/{filename}", mimetype="audio/mpeg")
    except Exception as e:
        print(f"Error serving audio file: {e}")
        return "", 404
'''
@app.route("/twilio/audio/<filename>")
def serve_audio(filename):
    """Serve synthesized audio files."""
    try:
        # Validate filename to prevent directory traversal
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(AUDIO_RESPONSES_DIR, safe_filename)
        
        if not os.path.exists(file_path):
            print(f"Audio file not found: {file_path}")
            return "", 404
        
        return send_file(file_path, mimetype="audio/mpeg")
    except Exception as e:
        print(f"Error serving audio file: {e}")
        return "", 404
@app.route("/twilio/audio-webhook", methods=["POST"])
def handle_audio_webhook():
    """Handle audio data from Twilio for processing with Deepgram."""
    try:
        call_sid = request.values.get("CallSid", "")
        audio_base64 = request.values.get("RecordingData", "")
        
        if not audio_base64 or not call_sid:
            return jsonify({"error": "Missing required parameters"}), 400
        
        # Get the conversation
        if call_sid not in agent.active_conversations:
            return jsonify({"error": "No active conversation found"}), 404
        
        conversation = agent.active_conversations[call_sid]
        
        # Process the speech
        result = asyncio.run(conversation.process_speech_input(audio_base64))
        
        if not result["success"]:
            return jsonify({"error": "Failed to process speech"}), 500
        
        # Log the interaction
        logger.log_interaction(call_sid, result["transcript"], result["response_text"])
        
        # Return the response
        return jsonify({
            "success": True,
            "transcript": result["transcript"],
            "response_text": result["response_text"],
            "response_audio": result["response_audio"]
        })
    
    except Exception as e:
        print(f"Error handling audio webhook: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/status")
def get_status():
    """Get current status for dashboard updates."""
    active_calls = len(agent.active_conversations)
    
    # Get recent calls for real-time updates
    recent_calls = []
    
    if os.path.exists('logs'):
        log_files = sorted(
            [f for f in os.listdir('logs') if f.endswith('.json')],
            key=lambda x: os.path.getmtime(os.path.join('logs', x)),
            reverse=True
        )[:10]  # Get 10 most recent logs
        
        for filename in log_files:
            with open(os.path.join('logs', filename), 'r') as f:
                try:
                    call_data = json.load(f)
                    call_sid = os.path.splitext(filename)[0]
                    
                    # Calculate duration if available
                    start_time = datetime.fromisoformat(call_data['start_time'])
                    if 'end_time' in call_data:
                        end_time = datetime.fromisoformat(call_data['end_time'])
                        duration = (end_time - start_time).total_seconds() / 60  # in minutes
                        duration_str = f"{duration:.1f} min"
                        status = call_data.get('status', 'completed')
                    else:
                        duration_str = "In progress"
                        status = "in-progress"
                    
                    recent_calls.append({
                        'sid': call_sid,
                        'number': call_data['customer_number'],
                        'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'duration': duration_str,
                        'status': status
                    })
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Error parsing {filename}: {e}")
    
    return jsonify({
        'active_calls': active_calls,
        'recent_calls': recent_calls
    })

@app.route("/outbound-call", methods=["POST"])
def make_outbound_call():
    """Initiate an outbound call."""
    try:
        # Check if request is JSON
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Request must be JSON'}), 400

        data = request.json
        to_phone = data.get('to_phone')
        from_phone = data.get('from_phone')
        
        # Validate phone numbers
        if not to_phone or not from_phone:
            return jsonify({'success': False, 'error': 'Phone numbers are required'}), 400
        
        # Ensure phone numbers are in E.164 format
        if not (to_phone.startswith('+') and from_phone.startswith('+')):
            return jsonify({'success': False, 'error': 'Phone numbers must be in E.164 format (e.g., +1234567890)'}), 400
        
        # Verify Twilio credentials are set
        if not (os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN")):
            return jsonify({'success': False, 'error': 'Twilio credentials are not configured'}), 500
        
        # Update the webhook URL with the actual host
        webhook_base_url = request.host_url.rstrip('/')
        
        # Initiate the call
        try:
            # Validate Twilio client can be imported
            from twilio.rest import Client
            
            conversation = agent.make_outbound_call(to_phone, from_phone, webhook_base_url)
            
            # Log the call start
            logger.log_call_start(conversation.call_sid, to_phone)
            
            return jsonify({
                'success': True, 
                'call_sid': conversation.call_sid,
                'to_phone': to_phone,
                'from_phone': from_phone
            })
        
        except ImportError:
            return jsonify({'success': False, 'error': 'Twilio library not installed'}), 500
        
        except Exception as e:
            print(f"Error making outbound call: {e}")
            return jsonify({
                'success': False, 
                'error': 'Failed to initiate call',
                'details': str(e)
            }), 500
    
    except Exception as e:
        print(f"Unexpected error in outbound call: {e}")
        return jsonify({
            'success': False, 
            'error': 'Unexpected server error',
            'details': str(e)
        }), 500

@app.route("/twilio/outbound-connect", methods=["POST", "GET"])
def handle_outbound_connect():
    """Handle when an outbound call is connected."""
    call_sid = request.values.get("CallSid", "")
    
    # Create TwiML for the outbound call
    response = VoiceResponse()
    
    try:
        # Get the conversation for this call
        conversation = agent.get_conversation(call_sid)
        
        # Get the initial message from the agent
        initial_message = asyncio.run(conversation.agent.get_initial_message())
        
        # Add initial message
        response.say(initial_message or "Hello! This is Jivus AI. How can I assist you today?")
        
        # Add gather to capture user input
        gather = response.gather(
            input="speech",
            action="/twilio/user-input",timeout=5,
            speech_timeout="auto"
        )
        
    except Exception as e:
        print(f"Error in outbound connect: {e}")
        response.say("Hello! There was an issue connecting the call.")
    
    return str(response)

@app.route("/twilio/status", methods=["POST", "GET"])
def handle_status_update():
    """Handle Twilio call status updates."""
    try:
        status = request.values.get("CallStatus", "")
        call_sid = request.values.get("CallSid", "")
        
        print(f"Call {call_sid} status updated to {status}")
        
        if status in ["completed", "failed"]:
            # End the conversation if it's active
            if call_sid in agent.active_conversations:
                # Terminate the conversation
                conversation = agent.active_conversations[call_sid]
                conversation.terminate()
                
                # Remove from active conversations
                del agent.active_conversations[call_sid]
            
            # Log the call end
            logger.log_call_end(call_sid, status)
        
        # Always return a TwiML response for Twilio
        response = VoiceResponse()
        return str(response)
    
    except Exception as e:
        print(f"Error in status update: {e}")
        response = VoiceResponse()
        return str(response)

if __name__ == "__main__":
    # Make sure audio_responses directory exists
    os.makedirs("audio_responses", exist_ok=True)
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=8000)