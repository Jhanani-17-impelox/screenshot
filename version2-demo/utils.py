
import tkinter as tk
from tkinter import ttk
import requests
from PIL import Image, ImageTk
from io import BytesIO
from datetime import datetime
import re
from itertools import cycle
import logging

class MarkdownText(tk.Text):
    """A Text widget with improved Markdown rendering capabilities"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configure text tags for styling
        self.tag_configure("bold", font=("Arial", 12, "bold"))
        self.tag_configure("italic", font=("Arial", 11, "italic"))
        self.tag_configure("regular", font=("Arial", 11))
        self.tag_configure("engine_issue", foreground="red", font=("Arial", 12, "bold"))
        self.tag_configure("section_title", font=("Arial", 12, "bold"), foreground="#4a6baf")
        self.tag_configure("subsection", font=("Arial", 11, "bold"), foreground="#7986cb")
        self.tag_configure("code", background="#f0f0f0", font=("Courier", 10), wrap="none")
        self.tag_configure("bullet", lmargin1=20, lmargin2=30)
        
        # Disable scrollbar by default for streaming display
        self.config(yscrollcommand=None)
    
    def insert_markdown(self, text):
        """Parse and insert markdown text with custom format handling"""
        # Clear content if requested
        if not text:
            return
            
        # Process the text by lines for easier section handling
        lines = text.split('\n')
        i = 0
        in_code_block = False
        current_section = None
        
        while i < len(lines):
            line = lines[i]
            
            # Handle code blocks with triple backticks
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                if in_code_block:
                    # Start of code block
                    code_block_content = []
                    i += 1
                    while i < len(lines) and not lines[i].strip().startswith('```'):
                        code_block_content.append(lines[i])
                        i += 1
                    # Insert the code block
                    self.insert(tk.END, '\n'.join(code_block_content) + '\n', "code")
                i += 1
                continue
                
            # Skip empty lines but preserve spacing
            if not line.strip():
                self.insert(tk.END, '\n')
                i += 1
                continue
                
            # Handle section headers (bold with **)
            bold_section_match = re.match(r'\*\*(.*?):\*\*', line.strip())
            engine_issue_match = re.match(r'<<<\*\*(.*?):\*\*>>>', line.strip())
                
            if engine_issue_match:
                # Special handling for engine issue section
                current_section = "engine_issue"
                section_title = engine_issue_match.group(1)
                self.insert(tk.END, f"Engine Issue Detected: ", "engine_issue")
                i += 1
                continue
            elif bold_section_match:
                # Regular section header
                current_section = "regular"
                section_title = bold_section_match.group(1)
                self.insert(tk.END, section_title, "section_title")
                self.insert(tk.END, ":\n")
                i += 1
                continue
                
            # Handle bullet points
            if line.strip().startswith('- ') or line.strip().startswith('* '):
                bullet_text = line.strip()[2:]
                self.insert(tk.END, "• " + bullet_text + "\n", "bullet")
                i += 1
                continue
                
            # Handle regular text with inline formatting
            if current_section == "engine_issue":
                # Check if this line is part of engine issue section
                if i+1 < len(lines) and (
                    re.match(r'\*\*(.*?):\*\*', lines[i+1].strip()) or 
                    re.match(r'<<<\*\*(.*?):\*\*>>>', lines[i+1].strip())):
                    # Next line is a new section, so this is the end of engine issue
                    current_section = None
                    self.insert(tk.END, line + "\n", "engine_issue")
                else:
                    # Still in engine issue section
                    self.insert(tk.END, line + "\n", "engine_issue")
            else:
                # Regular text
                self.process_inline_formatting(line)
                self.insert(tk.END, "\n")
                
            i += 1

    def process_inline_formatting(self, line):
        """Process inline markdown formatting like bold and italic"""
        # Process the line to handle bold and italic
        segments = []
        current_pos = 0
        
        # Find all bold text (**text**)
        bold_pattern = r'\*\*(.*?)\*\*'
        for match in re.finditer(bold_pattern, line):
            # Add text before the match
            if match.start() > current_pos:
                segments.append(("regular", line[current_pos:match.start()]))
            
            # Add the bold text without the ** markers
            segments.append(("bold", match.group(1)))
            current_pos = match.end()
        
        # Add any remaining text
        if current_pos < len(line):
            segments.append(("regular", line[current_pos:]))
        
        # If no formatting found, just add the whole line as regular text
        if not segments:
            self.insert(tk.END, line, "regular")
            return
            
        # Insert all segments with appropriate tags
        for tag, text in segments:
            self.insert(tk.END, text, tag)



def configure_styles(self):
        style = ttk.Style()
        style.theme_use('clam')  # Use clam theme as base
        
        # Configure button style
        style.configure('TButton', 
                        font=('Arial', 10, 'bold'),
                        background=self.colors["primary"],
                        foreground=self.colors["text_light"])
        
        style.map('TButton',
                 background=[('active', self.colors["secondary"])],
                 foreground=[('active', self.colors["text_light"])])
                 
        # Configure label style
        style.configure('TLabel', 
                        font=('Arial', 10),
                        background=self.colors["bg_light"],
                        foreground=self.colors["text_dark"])
                        
        # Configure frame style
        style.configure('TFrame', background=self.colors["bg_light"])
        
        # Configure labelframe style
        style.configure('TLabelframe', 
                        background=self.colors["bg_light"],
                        foreground=self.colors["primary"])
                        
        style.configure('TLabelframe.Label', 
                        font=('Arial', 11, 'bold'),
                        background=self.colors["bg_light"],
                        foreground=self.colors["primary"])


def setup_icon(self):
        try:
            icon = Image.new('RGB', (16, 16), color=self.colors["primary"])
            photo = ImageTk.PhotoImage(icon)
            self.root.iconphoto(False, photo)
        except Exception as e:    
            logging.error(f"Error setting up icon: {str(e)}")

def log_error(self, payload):
        try:
            
            # url = "http://localhost:8001/v1/conversations/log-error"
            url = "https://taroapi.impelox.com/v1/conversations/log-error"

            
            headers = {
                "Content-Type": "application/json",
                'x-api-key': 'demomUwuvZaEYN38J74JVzidgPzGz49h4YwoFhKl2iPzwH4uV5Jm6VH9lZvKgKuO'
            }

            response = requests.post(url, json=payload, headers=headers)
            print(response)


        except Exception as e:
            logging.error(f"Error in API call: {str(e)}")
            self.log_error({
  "occured_while": "insert in error log api",
  "error_message": str(e),
  "occured_in": "front-end"
})
            self.update_status(f"API Error: {str(e)}", "error")
            return None
        

def create_rounded_rectangle(canvas, x1, y1, x2, y2, radius=25, **kwargs):
    """Helper function to create a rounded rectangle on a canvas"""
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)

def draw_toggle(self):
        """Draw the toggle switch based on current state"""
        self.toggle_canvas.delete("all")
        
        # Draw background
        if self.connection_var.get():
            bg_color = self.colors["primary"]
        else:
            bg_color = "gray70"
            
        # Create rounded rectangle for background
        create_rounded_rectangle(
            self.toggle_canvas,
            2, 2, 58, 22,
            radius=24,
            fill=bg_color,
            outline=""
        )
        
        # Draw toggle circle
        circle_x = 40 if self.connection_var.get() else 16
        self.toggle_canvas.create_oval(
            circle_x - 8, 4,
            circle_x + 8, 20,
            fill="white",
            outline=""
        )
def toggle_connection(self):
        """Handle connection toggle between REST and WebSocket"""
        self.use_websocket = self.connection_var.get()
        print(f"Switching to {'WebSocket' if self.use_websocket else 'REST API'}",self.use_websocket)
        if self.use_websocket:
            # Switch to WebSocket
            if not self.is_connected:
                try:
                    self.connect_socketio()
                    self.update_status("Switched to low latency", "success")
                except Exception as e:
                    self.update_status("Failed to connect to WebSocket", "error")
                    self.connection_var.set(False)
                    self.use_websocket = False
        else:
            # Switch to REST API
            if self.is_connected:
                try:
                    self.sio.disconnect()
                    self.is_connected = False
                    self.update_status("Switched to high accuracy", "success")
                except Exception as e:
                    logging.error(f"Error disconnecting from WebSocket: {str(e)}")
                    self.update_status("Error disconnecting from WebSocket", "error")

     
def create_connection_toggle(self):
        """Create a toggle button for switching between REST and WebSocket"""
        toggle_frame = ttk.Frame(self.root)
        toggle_frame.place(relx=1.0, rely=0, anchor="ne", x=-10, y=10)
        
         # Create label for toggle
        self.toggle_label = ttk.Label(
            toggle_frame,
            text="Fast(beta)",
            background=self.colors["bg_light"],
            foreground=self.colors["primary"]
        )
        self.toggle_label.pack(side=tk.RIGHT, padx=(0, 5))
        # Create canvas for custom toggle
        self.toggle_canvas = tk.Canvas(
            toggle_frame,
            width=60,
            height=24,
            bg=self.colors["bg_light"],
            highlightthickness=0
        )
        self.toggle_canvas.pack(side=tk.RIGHT, padx=5)
        
       
        
        # Initialize toggle state
        self.connection_var = tk.BooleanVar(value=False)
        draw_toggle(self)
        
        # Bind click event
        self.toggle_canvas.bind("<Button-1>", self.on_toggle_click)
      