
import tkinter as tk
from tkinter import ttk
import pyautogui
import time
import os
import platform
import tempfile
import threading
import base64
from PIL import Image, ImageTk
from io import BytesIO
from datetime import datetime
import json
import uuid
import re
from itertools import cycle
import logging
import asyncio
import socketio  
import threading
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
            print("Logging error to Socket.IO")
        except Exception as e:
            logging.error(f"Error logging through Socket.IO: {str(e)}")
            return None
    
