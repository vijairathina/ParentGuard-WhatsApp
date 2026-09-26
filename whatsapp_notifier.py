import os
import json
import time
import state_manager

# --- Configuration ---
OUTBOX_FILE = "whatsapp_outbox.json"

def start_whatsapp_service():
    """
    Deprecated: The service is now started by run_all.py as a standalone process.
    This function is kept for compatibility but does nothing.
    """
    pass

def get_whatsapp_qr():
    """
    Retrieves the QR code from the shared state manager.
    The standalone service updates this state.
    """
    state = state_manager.get_state()
    return state.get('whatsapp_qr')

def is_whatsapp_connected():
    """
    Checks connection status from shared state.
    """
    state = state_manager.get_state()
    return state.get('whatsapp_status') == "Connected"

def send_whatsapp_message(phone, message):
    """
    Queues a message to be sent by the standalone WhatsApp service.
    Writes to whatsapp_outbox.json.
    """
    try:
        # Load existing outbox
        if os.path.exists(OUTBOX_FILE):
            with open(OUTBOX_FILE, 'r', encoding='utf-8') as f:
                try:
                    outbox = json.load(f)
                except json.JSONDecodeError:
                    outbox = []
        else:
            outbox = []

        # clean phone number
        clean_phone = phone.strip().replace('+', '').replace(' ', '')
        
        # Append new message
        outbox.append({
            'target': clean_phone,
            'message': message,
            'timestamp': time.time()
        })

        # Save back to file
        with open(OUTBOX_FILE, 'w', encoding='utf-8') as f:
            json.dump(outbox, f, indent=2)
            
        print(f"✅ Queued WhatsApp message to {clean_phone}")
        return True
    except Exception as e:
        print(f"❌ Error queuing WhatsApp message: {e}")
        return False

def get_recent_contacts():
    """
    Reads the contacts file maintained by the standalone service.
    """
    CONTACTS_FILE = "whatsapp_contacts.json"
    if os.path.exists(CONTACTS_FILE):
        try:
            with open(CONTACTS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error reading WhatsApp contacts: {e}")
            return []
    return []
