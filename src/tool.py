import threading
import queue
import os
import html
from chimerax.core.tools import ToolInstance
from chimerax.core.commands import run

from chimerax.ui import MainToolWindow

# Imported QHBoxLayout, QPushButton, and QInputDialog for the new UI elements
from Qt.QtWidgets import QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QInputDialog
from Qt.QtCore import QTimer

from .api import get_chimerax_command

# The file where the user's API key will be saved locally on their computer
KEY_FILE = os.path.expanduser("~/.chimerax_gemini_key")

class AIChatTool(ToolInstance):
    SESSION_ENDURING = False 

    def __init__(self, session, tool_name, **kw):
        super().__init__(session, tool_name, **kw)
        
        self.display_name = "AI Chat"
        self.tool_window = MainToolWindow(self)
        parent = self.tool_window.ui_area
        
        # --- BUILD THE UI ---
        layout = QVBoxLayout()
        
        # Top Bar: Add the Settings button
        top_layout = QHBoxLayout()
        self.key_button = QPushButton("🔑 Set API Key")
        self.key_button.clicked.connect(self.prompt_for_key)
        top_layout.addStretch() # Pushes the button to the right side
        top_layout.addWidget(self.key_button)
        layout.addLayout(top_layout)
        
        self.history = QTextEdit()
        self.history.setReadOnly(True)
        layout.addWidget(self.history)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("e.g., Color the protein backbone blue...")
        self.input_field.returnPressed.connect(self.process_input)
        layout.addWidget(self.input_field)
        
        parent.setLayout(layout)
        self.tool_window.manage("right")

        # --- SETUP THREADING ---
        self.response_queue = queue.Queue()
        self.timer = QTimer(parent)
        self.timer.timeout.connect(self.check_for_responses)
        self.timer.start(200)

        # --- LOAD API KEY ---
        self.api_key = self.load_key()
        
        if self.api_key:
            self.history.append("<i>Welcome back! Ask me to change the structure.</i>")
        else:
            self.history.append("<i><b>Welcome!</b> Please enter your Gemini API Key to begin.</i>")
            # Wait 0.5 seconds for the UI to draw, then prompt the user
            QTimer.singleShot(500, self.prompt_for_key)

    def load_key(self):
        """Reads the saved API key from the user's home directory."""
        if os.path.exists(KEY_FILE):
            with open(KEY_FILE, "r") as f:
                return f.read().strip()
        return ""

    def save_key(self, key):
        """Saves the API key locally so they aren't prompted again."""
        with open(KEY_FILE, "w") as f:
            f.write(key.strip())
        try:
            os.chmod(KEY_FILE, 0o600)
        except OSError:
            # Best-effort permission hardening on platforms that support it
            pass
        self.api_key = key.strip()

    def prompt_for_key(self):
        """Pops up a dialog box asking for the API key."""
        key, ok = QInputDialog.getText(
            self.tool_window.ui_area, 
            "Gemini API Key", 
            "Enter your Google Gemini API Key:\n(Get one free at aistudio.google.com)"
        )
        if ok and key.strip():
            self.save_key(key)
            self.history.append("<i style='color:green;'>API Key saved successfully!</i>")

    def process_input(self):
        user_text = self.input_field.text()
        if not user_text.strip():
            return
            
        # Stop them if they try to chat without an API key
        if not self.api_key:
            self.prompt_for_key()
            if not self.api_key: # If they canceled the prompt again
                return
                
        safe_user_text = html.escape(user_text)
        self.history.append(f"<br><b style='color:#0078D7;'>You:</b> {safe_user_text}")
        self.input_field.clear()
        
        self.history.append("<i><small style='color:gray;'>Thinking...</small></i>")
        
        # Grab the key safely for the background thread
        current_key = self.api_key 
        
        def fetch_task():
            cmd = get_chimerax_command(user_text, current_key) # Pass the key here!
            self.response_queue.put(cmd)
            
        threading.Thread(target=fetch_task, daemon=True).start()

    def check_for_responses(self):
        try:
            cmd = self.response_queue.get_nowait()
            self._apply_command(cmd)
        except queue.Empty:
            pass 

    def _apply_command(self, cmd):
        if cmd.startswith("error:"):
            safe_error = html.escape(cmd)
            self.history.append(f"<i style='color:red;'>AI Error: {safe_error}</i>")
            return
            
        safe_cmd = html.escape(cmd)
        self.history.append(f"<b style='color:#107C10;'>AI executing:</b> <code>{safe_cmd}</code>")
        try:
            run(self.session, cmd)
        except Exception as e:
            safe_exec_error = html.escape(str(e))
            self.history.append(f"<i style='color:red;'>ChimeraX Error: {safe_exec_error}</i>")
