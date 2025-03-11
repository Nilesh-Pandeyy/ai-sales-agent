
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class ConversationLogger:
    def __init__(self):
        self.conversations: Dict[str, Dict] = {}
        # Ensure logs directory exists
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
    def log_call_start(self, call_sid: str, number: str):
        """Log the start of a new call."""
        self.conversations[call_sid] = {
            "start_time": datetime.now().isoformat(),
            "customer_number": number,
            "transcript": []
        }
        # Save immediately to capture the call even if the server crashes
        self._save_to_file(call_sid)
        
    def log_interaction(self, call_sid: str, user_input: str, ai_response: str):
        """Log a single interaction between the user and the AI agent."""
        if call_sid not in self.conversations:
            # If the call wasn't properly started, initialize it now
            self.conversations[call_sid] = {
                "start_time": datetime.now().isoformat(),
                "customer_number": "unknown",
                "transcript": []
            }
            
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user_input,
            "agent": ai_response
        }
        self.conversations[call_sid]["transcript"].append(entry)
        
        # Save after each interaction to preserve data
        self._save_to_file(call_sid)
        
    def log_call_end(self, call_sid: str, status: str):
        """Log the end of a call with its final status."""
        if call_sid not in self.conversations:
            # If we're ending a call that wasn't properly started
            self.conversations[call_sid] = {
                "start_time": datetime.now().isoformat(),
                "customer_number": "unknown",
                "transcript": []
            }
            
        self.conversations[call_sid]["end_time"] = datetime.now().isoformat()
        self.conversations[call_sid]["status"] = status
        self._save_to_file(call_sid)
        
        # Remove from memory after saving
        if call_sid in self.conversations:
            del self.conversations[call_sid]
        
    def _save_to_file(self, call_sid: str):
        """Save the conversation to a JSON file."""
        filename = f"logs/{call_sid}.json"
        try:
            with open(filename, "w") as f:
                json.dump(self.conversations[call_sid], f, indent=2)
        except Exception as e:
            print(f"Error saving conversation log for {call_sid}: {e}")
            
    def get_transcript(self, call_sid: str) -> Optional[Dict]:
        """Get the transcript for a specific call."""
        # First check if it's in memory
        if call_sid in self.conversations:
            return self.conversations[call_sid]
            
        # If not in memory, try to load from file
        filename = f"logs/{call_sid}.json"
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading transcript for {call_sid}: {e}")
                
        return None
        
    def get_all_calls(self, limit: int = 100) -> List[Dict]:
        """Get details for all calls, sorted by start time (newest first)."""
        calls = []
        
        # Get calls from log files
        if os.path.exists('logs'):
            for filename in os.listdir('logs'):
                if filename.endswith('.json'):
                    try:
                        call_sid = filename.replace('.json', '')
                        call_data = self.get_transcript(call_sid)
                        
                        if call_data:
                            # Add call_sid to the data
                            call_data['call_sid'] = call_sid
                            calls.append(call_data)
                    except Exception as e:
                        print(f"Error processing log file {filename}: {e}")
        
        # Sort by start time (newest first)
        calls.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        
        # Return only the requested number
        return calls[:limit]

