
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
import requests
import re
from itertools import cycle
import logging

# Configure logging
logging.basicConfig(
    filename='screenshot_app.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Create a logger object
logger = logging.getLogger(__name__)

# Add these imports at the top of your file
import webbrowser
from tkhtmlview import HTMLLabel, HTMLScrolledText, RenderHTML


class DisplayTextManager:
    """Manages the display text storage and updates for streaming responses"""
    def __init__(self):
        self.display_texts = []  # List of screenshot text entries
        self.current_index = 0   # Index of the current text being updated
    
    def insert_text(self, screenshot, text=""):
        """Insert a new text entry for a screenshot"""
        self.display_texts.insert(0, {
            "screenshot": screenshot,
            "text": text
        })
        self.current_index = 0
        return 0  # Return the index of the new entry
    
    def update_text(self, index, text, is_new_text=False):
        """Update the text at the specified index"""
        if index < 0 or index >= len(self.display_texts):
            return False
            
        if is_new_text:
            self.display_texts[index]["text"] = text
        else:
            self.display_texts[index]["text"] += text
        
        return True
    
    def get_text(self, index):
        """Get the text at the specified index"""
        if index < 0 or index >= len(self.display_texts):
            return None
        return self.display_texts[index]["text"]
    
    def get_screenshot(self, index):
        """Get the screenshot at the specified index"""
        if index < 0 or index >= len(self.display_texts):
            return None
        return self.display_texts[index]["screenshot"]
    
    def clear(self):
        """Clear all display texts"""
        self.display_texts = []
        self.current_index = 0

def parse_engine_issue(markdown_text):
    """Parse the markdown text to identify engine issues"""
    # Check for engine issue pattern
    engine_issue_match = re.search(r'<<<\*\*Engine Description:\*\*>>>(.*?)(?=\n\n\*\*|\Z)', 
                                  markdown_text, re.DOTALL)
    
    if engine_issue_match:
        # Engine issue found
        engine_text = engine_issue_match.group(1).strip()
        return True, engine_text
    
    return False, None

def animate_analyzing_label(label):
    """Animate the analyzing label with moving dots"""
    current_text = label.cget("text").rstrip('.')
    dot_count = (label.cget("text").count('.') + 1) % 4
    label.config(text=f"{current_text}{'.' * dot_count}")
    
    # Return True to keep the animation running
    return True

def update_streaming_layout(parent, text_manager, index):
    """Update the entire streaming layout with the latest text"""
    # Get the current text
    current_text = text_manager.get_text(index)
    
    # Update the markdown display
    if hasattr(parent, 'markdown_text'):
        parent.markdown_text.config(state=tk.NORMAL)
        parent.markdown_text.delete(1.0, tk.END)
        
        # Process the text with enhanced markdown formatting
        has_engine_issue, engine_text = parse_engine_issue(current_text)
        
        if has_engine_issue:
            # Split by the engine issue marker
            parts = current_text.split("<<<**Engine Description:**>>>")
            
            # Insert the first part normally
            parent.markdown_text.insert_markdown(parts[0])
            
            # Insert the engine issue marker in red
            parent.markdown_text.insert(tk.END, "Engine Issue Detected: ", "engine_issue")
            
            # Find where the next section begins
            next_section = re.search(r'\n\n\*\*', parts[1])
            
            if next_section:
                # Insert engine details in red
                engine_details = parts[1][:next_section.start()]
                parent.markdown_text.insert(tk.END, engine_details.strip(), "engine_issue")
                
                # Insert the rest of the text normally
                remaining_text = parts[1][next_section.start():]
                parent.markdown_text.insert_markdown(remaining_text)
            else:
                # Just insert the engine part in red
                parent.markdown_text.insert(tk.END, parts[1].strip(), "engine_issue")
        else:
            # No engine issue, just insert the whole text
            parent.markdown_text.insert_markdown(current_text)
        
        parent.markdown_text.config(state=tk.DISABLED)
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
class ScreenshotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Taro ")
        self.root.geometry("1024x768")
        self.root.resizable(True, True)

        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.payload_file = os.path.join(self.script_dir, "payload.json")

        # Define color scheme for a more colorful UI
        self.colors = {
            "primary": "#4a6baf",
            "secondary": "#7986cb",
            "accent": "#ffab40",
            "success": "#66bb6a",
            "error": "#ef5350",
            "bg_light": "#f5f7fa",
            "bg_dark": "#e1e5eb",
            "text_dark": "#263238",
            "text_light": "#ffffff"
        }

        # Configure ttk styles for a beautiful UI
        self.configure_styles()
        self.setup_icon()
        
        self.root.configure(bg=self.colors["bg_light"])
        
        self.screenshots = []
        self.is_capturing = False
        self.drag_started = False  # To track if we're dragging
        self.status_message = ""
        self.status_type = "info"
        
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.temp_dir = os.path.join(tempfile.gettempdir(), f"es_screenshots_{self.timestamp}")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        self.create_main_layout()
        self.create_floating_button()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)




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

    def save_payload_to_file(self, payload):
        """Save the payload to a JSON file in the script directory"""
        try:
            with open(self.payload_file, 'w') as f:
                json.dump(payload, f, indent=2)
            self.update_status(f"Payload saved to {self.payload_file}", "success")
        except Exception as e:
            logging.error(f"Error saving payload: {str(e)}") 
            self.log_error({
  "occured_while": "save_payload_to_file",
  "error_message": str(e),
  "occured_in": "front-end"
})
            self.update_status(f"Error saving payload: {str(e)}", "error")

    def setup_icon(self):
        try:
            icon = Image.new('RGB', (16, 16), color=self.colors["primary"])
            photo = ImageTk.PhotoImage(icon)
            self.root.iconphoto(False, photo)

        except Exception as e:
            
            logging.error(f"Error setting up icon: {str(e)}")
    
    def create_main_layout(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(
            main_frame, 
            text="Taro ", 
            font=("Arial", 18, "bold"),
            foreground=self.colors["primary"]
        )
        title_label.pack(pady=(0, 10))
        
        self.status_frame = ttk.Frame(main_frame)
        self.status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(
            self.status_frame,
            text="Ready to capture screenshots. Press the button.",
            foreground=self.colors["text_dark"],
            background=self.colors["bg_dark"],
            padding=10
        )
        self.status_label.pack(fill=tk.X)
        
        screenshots_frame = ttk.LabelFrame(main_frame, text="Captured Screenshots", padding=10)
        screenshots_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(screenshots_frame, bg="#f0f0f0")
        self.scrollbar = ttk.Scrollbar(screenshots_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.screenshots_container = ttk.Frame(self.canvas)
        self.screenshots_container_id = self.canvas.create_window(
            (0, 0), 
            window=self.screenshots_container, 
            anchor=tk.NW
        )
        
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.screenshots_container.bind("<Configure>", self.on_frame_configure)

        # Bind mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)

    def on_canvas_configure(self, event):
        """Adjust the canvas width to match the container"""
        self.canvas.itemconfig(self.screenshots_container_id, width=event.width)

    def on_frame_configure(self, event):
        """Update the scroll region to encompass the entire frame"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_mouse_wheel(self, event):
        """Scroll the canvas vertically when the mouse wheel is used"""
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def create_floating_button(self):
        self.button_window = tk.Toplevel(self.root)
        self.button_window.overrideredirect(True)
        self.button_window.attributes('-topmost', True)
        button_frame = tk.Frame(
            self.button_window,
            bg="black", 
            bd=4  
        )
        button_frame.pack(fill=tk.BOTH, expand=True)
        inner_frame = tk.Frame(button_frame, bg=self.colors["accent"])
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        try:
            image_path = "capture.png"
            if os.path.exists(image_path):
                original_img = Image.open(image_path)
                button_size = 40
                button_img = original_img.resize((button_size, button_size), Image.LANCZOS)
                self.button_photo = ImageTk.PhotoImage(button_img)
                
                capture_button = tk.Button(
                    inner_frame,
                    image=self.button_photo,
                    bg=self.colors["accent"],
                    relief=tk.RAISED,
                    command=self.handle_capture
                )
            else:
                capture_button = tk.Button(
                    inner_frame,
                    text="📷",
                    font=("Arial", 14, "bold"),
                    bg=self.colors["accent"],
                    fg=self.colors["text_light"],
                    width=3,
                    height=1,
                    relief=tk.RAISED,
                    command=self.handle_capture
                )
        except Exception as e:
            logging.error(f"Error creating capture button: {str(e)}")
            self.log_error({
  "occured_while": "create_floating_button",
  "error_message": str(e),
  "occured_in": "front-end"
})
            capture_button = tk.Button(
                inner_frame,
                text="📷",
                font=("Arial", 14, "bold"),
                bg=self.colors["accent"],
                fg=self.colors["text_light"],
                width=3,
                height=1,
                relief=tk.RAISED,
                command=self.handle_capture
            )
        
        capture_button.pack(padx=5, pady=5)
        
        self.position_floating_button()
        button_frame.bind("<ButtonPress-1>", self.start_move)
        button_frame.bind("<ButtonRelease-1>", self.stop_move)
        button_frame.bind("<B1-Motion>", self.do_move)
        inner_frame.bind("<ButtonPress-1>", self.start_move)
        inner_frame.bind("<ButtonRelease-1>", self.stop_move)
        inner_frame.bind("<B1-Motion>", self.do_move)
        capture_button.bind("<ButtonPress-1>", self.button_press)
        capture_button.bind("<ButtonRelease-1>", self.button_release)

    def position_floating_button(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        button_width = 70
        button_height = 70        
        x_position = screen_width - button_width - 40
        y_position = screen_height - button_height - 40        
        self.button_window.geometry(f"{button_width}x{button_height}+{x_position}+{y_position}")

    def start_move(self, event):
        self.x = event.x
        self.y = event.y
        self.drag_started = True  # We're always dragging when using the border

    def stop_move(self, event):
        self.x = None
        self.y = None
        self.drag_started = False

    def do_move(self, event):
        if self.is_capturing:
            return            
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.button_window.winfo_x() + deltax
        y = self.button_window.winfo_y() + deltay
        self.button_window.geometry(f"+{x}+{y}")

    def button_press(self, event):
        """Handle button press event separately from drag start"""
        self.drag_started = False
        self.x = event.x
        self.y = event.y

    def button_release(self, event):
        """Handle button release to differentiate clicks from drags"""
        if not self.drag_started and not self.is_capturing:
            self.handle_capture()
        self.x = None
        self.y = None

    def handle_capture(self):
        if self.is_capturing:
            return            
        capture_thread = threading.Thread(target=self.capture_active_window)
        capture_thread.daemon = True
        capture_thread.start()
    
    def create_loader(self, parent):
        """Create a localized loader overlay with a spinning animation centered on the screen"""
        self.loader_frame = tk.Frame(parent, bg="#2D617F", relief="solid", bd=2)
        self.loader_frame.place(relx=0.5,  anchor="center", width=100, height=100)
        self.spinner_label = ttk.Label(self.loader_frame, background="#2D617F")
        self.spinner_label.pack(expand=True)
        self.spinner_images = [
            ImageTk.PhotoImage(Image.new("RGB", (50, 50), (255, 255, 255)).rotate(angle))
            for angle in range(0, 360, 30)
        ]
        self.spinner_cycle = cycle(self.spinner_images)
        self.animate_spinner()

    def animate_spinner(self):
        """Animate the spinner"""
        if hasattr(self, "spinner_label"):
            self.spinner_label.config(image=next(self.spinner_cycle))
            self.spinner_label.after(100, self.animate_spinner)
    def show_loader(self):
        """Show a loading animation while waiting for API response"""
        loader_window = tk.Toplevel(self.root)
        loader_window.overrideredirect(True)
        loader_window.attributes('-topmost', True)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 150
        window_height = 100
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2        
        loader_window.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")      
        frame = tk.Frame(loader_window, bg=self.colors["bg_light"], relief="solid", bd=2)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add a label
        label = tk.Label(
            frame, 
            text="Analyzing...", 
            font=("Arial", 12, "bold"),
            fg=self.colors["primary"],
            bg=self.colors["bg_light"]
        )
        label.pack(pady=(20, 10))
        
        # Create a progress bar
        progress = ttk.Progressbar(
            frame, 
            mode="indeterminate", 
            length=100
        )
        progress.pack(pady=10)
        progress.start(10)
        
        # Store references
        self.loader_window = loader_window
        self.loader_progress = progress

    def hide_loader(self):
        """Hide and destroy the loader window"""
        if hasattr(self, 'loader_window') and self.loader_window:
            self.loader_progress.stop()
            self.loader_window.destroy()
            self.loader_window = None
            self.loader_progress = None



    

    def get_window_info(self):
        system = platform.system()
        
        if system == 'Windows':
            try:
                import ctypes
                from ctypes.wintypes import RECT
                
                user32 = ctypes.windll.user32
                foreground_window = user32.GetForegroundWindow()
                
                length = user32.GetWindowTextLengthW(foreground_window)
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(foreground_window, buff, length + 1)
                title = buff.value
                
                rect = RECT()
                user32.GetWindowRect(foreground_window, ctypes.byref(rect))
                bounds = (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
                
                return title, bounds
            except Exception as e:
                logging.error(f"Error getting window info on Windows: {e}")
                self.log_error({
  "occured_while": "get_window_info",
  "error_message": str(e),
  "occured_in": "front-end"
})
                return f"Window_{datetime.now().strftime('%H%M%S')}", None
        
        elif system == 'Darwin':  # macOS
            try:
                import subprocess
                
                title_cmd = """osascript -e 'tell application "System Events" to get name of first process whose frontmost is true'"""
                title = subprocess.check_output(title_cmd, shell=True).decode('utf-8').strip()
                
                bounds_script = """
                osascript -e '
                tell application "System Events"
                    set frontApp to first application process whose frontmost is true
                    set frontAppName to name of frontApp
                    tell process frontAppName
                        set appWindow to first window
                        set {x, y} to position of appWindow
                        set {width, height} to size of appWindow
                        return x & "," & y & "," & width & "," & height
                    end tell
                end tell
                '
                """
                
                result = subprocess.check_output(bounds_script, shell=True).decode('utf-8').strip()
                bounds = tuple(int(val) for val in result.split(','))
                
                return title, bounds
            except Exception as e:
                logging.error(f"Error getting window info on macOS: {e}")
                return f"Window_{datetime.now().strftime('%H%M%S')}", None
        
        elif system == 'Linux':
            try:
                import subprocess
                
                win_id = subprocess.check_output(["xdotool", "getactivewindow"]).decode('utf-8').strip()
                title = subprocess.check_output(["xdotool", "getwindowname", win_id]).decode('utf-8').strip()
                
                geo_output = subprocess.check_output(["xdotool", "getwindowgeometry", win_id]).decode('utf-8')
                
                pos_line = next(line for line in geo_output.split('\n') if "Position" in line)
                pos_parts = pos_line.split(":")[1].strip().split(",")
                x = int(pos_parts[0])
                y = int(pos_parts[1])
                
                size_line = next(line for line in geo_output.split('\n') if "Geometry" in line)
                size_parts = size_line.split(":")[1].strip().split("x")
                width = int(size_parts[0])
                height = int(size_parts[1])
                
                return title, (x, y, width, height)
            except Exception as e:
                logging.error(f"Error getting window info on Linux: {e}")
                return f"Window_{datetime.now().strftime('%H%M%S')}", None
        
        # Default fallback for unknown systems
        return f"Window_{datetime.now().strftime('%H%M%S')}", None 
    def capture_active_window(self):
        start_time = time.time()
        self.is_capturing = True

        try:
            self.root.withdraw()
            self.button_window.withdraw()
            
            window_info_start = time.time()
            window_title, window_bounds = self.get_window_info()

            if "Taro " in window_title or not window_title:
                self.root.deiconify()
                self.button_window.deiconify()
                self.update_status("No active window detected or captured our own app", "info")
                self.is_capturing = False
                return

            screenshot_start = time.time()
            screenshot = None
            capture_type = ""
            if window_bounds:
                x, y, width, height = window_bounds

                if width <= 0 or height <= 0:
                    self.root.deiconify()
                    self.button_window.deiconify()
                    self.update_status("Invalid window dimensions detected", "error")
                    self.is_capturing = False
                    return

                screenshot = pyautogui.screenshot(region=(x, y, width, height))
                capture_type = "active window"
            else:
                # Platform-specific fallback for Windows
                if platform.system() == 'Windows':
                    try:
                        import win32gui
                        import win32ui
                        from ctypes import windll
                        from PIL import Image

                        hwnd = win32gui.GetForegroundWindow()
                        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                        width = right - left
                        height = bottom - top

                        hwndDC = win32gui.GetWindowDC(hwnd)
                        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
                        saveDC = mfcDC.CreateCompatibleDC()

                        saveBitMap = win32ui.CreateBitmap()
                        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
                        saveDC.SelectObject(saveBitMap)

                        windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 0)

                        bmpinfo = saveBitMap.GetInfo()
                        bmpstr = saveBitMap.GetBitmapBits(True)
                        screenshot = Image.frombuffer(
                            'RGB',
                            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                            bmpstr, 'raw', 'BGRX', 0, 1)

                        # Cleanup resources
                        win32gui.DeleteObject(saveBitMap.GetHandle())
                        saveDC.DeleteDC()
                        mfcDC.DeleteDC()
                        win32gui.ReleaseDC(hwnd, hwndDC)

                        capture_type = "active window"
                    except Exception as e:
                        logging.error(f"Error capturing active window on Windows: {e}")
                        screenshot = pyautogui.screenshot()
                        capture_type = "full screen (fallback)"
                else:
                    logger = logging.getLogger(__name__) # Assuming you have logging configured
                    logger.warning("Falling back to full screen capture.")
                    screenshot = pyautogui.screenshot()
                    capture_type = "full screen (fallback)"

            self.root.deiconify()
            self.button_window.deiconify()

            sanitized_title = ''.join(c for c in window_title if c.isalnum() or c in ' -_')[:30]
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"screenshot_{timestamp}_{sanitized_title}.png"
            file_path = os.path.join(self.temp_dir, filename)

            compressed_img = self.compress_image(screenshot)

            buffered = BytesIO()
            compressed_img.save(buffered, format="PNG", optimize=True)
            img_str_raw = base64.b64encode(buffered.getvalue()).decode()

            session_id = str(uuid.uuid4())
            self.update_status("Analyzing screenshot...", "analyzing")

            payload_json = {
                "session_id": session_id,
                "user_message": {
                    "type": "image",
                    "image": [img_str_raw],
                },
                "conversation_history": [
                    {
                        "role": "user",
                        "content": "get only the Inspector's Notes,Engine description and Fault parts and precautions accident from this image",
                        "attachments": [
                            {
                                "type": "file",
                                "base64String": [img_str_raw]
                            }
                        ]
                    }
                ]
            }

            result = self.make_api_call(payload_json)

            if result is None:
                return

            new_screenshot_data = {
                "image": screenshot,
                "title": window_title,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "path": file_path,
                "base64": img_str_raw,
                "payload_json": payload_json,
                "api_response": result
            }
            self.screenshots.insert(0, new_screenshot_data)

            self.add_screenshot_to_ui(0, new_screenshot_data)

            self.update_status(f"Captured {capture_type}: {window_title}", "success")

        except Exception as e:
            logging.error(f"Error capturing screenshot: {str(e)}")
            self.log_error({
  "occured_while": "capture_active_window",
  "error_message": str(e),
  "occured_in": "front-end"
})
            self.update_status(f"Error capturing screenshot: {str(e)}", "error")

        finally:
            self.is_capturing = False

    def compress_image(self, image, quality=60, max_size=1024):
        """Compress image to reduce file size while maintaining quality"""
        width, height = image.size
        
        # Resize if larger than max_size
        if width > max_size or height > max_size:
            if width > height:
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                new_height = max_size
                new_width = int(width * (max_size / height))
            
            image = image.resize((new_width, new_height), Image.LANCZOS)
        
        # Create compressed image
        output = BytesIO()
        image.save(output, format='PNG', optimize=True, quality=quality)
        output.seek(0)
        return Image.open(output)
    
    def update_status(self, message, status_type="info"):
        self.status_message = message
        self.status_type = status_type
        
        if status_type == "success":
            bg_color = '#03224c'
            fg_color = self.colors["text_light"]
        elif status_type == "error":
            bg_color = self.colors["error"]
            fg_color = self.colors["text_light"]
        elif status_type == "analyzing":
            bg_color = '#C8DFF6'
            fg_color = '#000000'
        else:  # info
            bg_color = self.colors["secondary"]
            fg_color = self.colors["text_light"]
        
        self.status_label.configure(
            text=message,
            background=bg_color,
            foreground=fg_color
        )

    def add_screenshot_to_ui(self, index, screenshot_data):
        print(len(self.screenshots))
        if len(self.screenshots) % 2 == 0:
            bg=self.colors["bg_light"]
        else:   
            bg=self.colors["bg_dark"]
        
        api_response = screenshot_data.get("api_response", {})
        inspector_notes = api_response.get("inspector_notes")
        engine_details = api_response.get("engine_details")
        fault_accident = api_response.get("fault_accident")
        has_engine_issue = api_response.get("has_engine_issue", False)
        img = screenshot_data.get("image")

        frame = ttk.Frame(self.screenshots_container, relief="solid", borderwidth=1, padding=10)
        frame.pack(fill=tk.X, pady=(0, 15), padx=10, side=tk.TOP)

        # if img:
        #     max_width = 600
        #     width, height = img.size
        #     ratio = min(max_width / width, 1.0)
        #     new_width = int(width * ratio)
        #     new_height = int(height * ratio)
        #     thumbnail = img.resize((new_width, new_height), Image.LANCZOS)
        #     photo = ImageTk.PhotoImage(thumbnail)
        #     screenshot_data["photo"] = photo

            # image_label = ttk.Label(frame, image=photo)
            # image_label.image = photo
            # image_label.pack(pady=(0, 10))

        title_label = ttk.Label(
            frame,
            text=f"{screenshot_data['title']} - {screenshot_data['timestamp']}",
            font=("Arial", 10, "bold"),
            foreground=self.colors["primary"]
        )
        title_label.pack(pady=(5, 0))
        # open_button = ttk.Button(
        #     frame,
        #     text="Open Image",
        #     command=lambda path=screenshot_data["path"]: self.open_screenshot(path),
        # )
        # open_button.pack(pady=(5, 0))

        markdown_display = MarkdownText(
            frame,
            wrap=tk.WORD,
            width=70,
            height=20,
            font=("Arial", 11),
            bg=bg,
            padx=10,
            pady=10
        )
        markdown_display.pack(fill=tk.BOTH, expand=True)

        markdown_content = ""

        if inspector_notes and inspector_notes.strip():
            markdown_content += f"**Inspector Notes:**\n{inspector_notes.strip()}\n\n"

        if engine_details and engine_details.strip():
            if has_engine_issue:
                markdown_content += "<<<**Engine Description:**>>>\n" + engine_details.strip() + "\n\n"
            else:
                markdown_content += f"**Engine Details:**\n{engine_details.strip()}\n\n"

        if fault_accident and fault_accident.strip():
            markdown_content += f"**Faults, Precautions, or Accident Information:**\n{fault_accident.strip()}\n\n"

        markdown_display.config(state=tk.NORMAL)

        if has_engine_issue and engine_details:
            parts = markdown_content.split("<<<**Engine Description:**>>>")
            markdown_display.insert_markdown(parts[0])
            markdown_display.insert(tk.END, "Engine Issue Detected: ", "engine_issue")

            engine_text = parts[1]
            next_section = re.search(r'\n\n\*\*', engine_text)

            if next_section:
                engine_details_part = engine_text[:next_section.start()]
                markdown_display.insert(tk.END, engine_details_part.strip(), "engine_issue")
                remaining_text = engine_text[next_section.start():]
                markdown_display.insert_markdown(remaining_text)
            else:
                markdown_display.insert(tk.END, engine_text.strip(), "engine_issue")
        else:
            markdown_display.insert_markdown(markdown_content)

        markdown_display.config(state=tk.DISABLED)

        self.on_frame_configure(None)

        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def strip_html_tags(self, html_text):
        """Remove HTML tags from text"""
        import re
        clean = re.compile('<.*?>')
        return re.sub(clean, '', html_text)


    
    def create_tables_from_html(self, parent_frame, html_content):
        """Parse full HTML (with <thead> and <tbody>) and render Tkinter tables"""
        import re
        from html import unescape

        sections = re.findall(r'<h3>(.*?)</h3>\s*<table.*?>(.*?)</table>', html_content, re.DOTALL)

        for heading, table_html in sections:
            heading_label = ttk.Label(
                parent_frame,
                text=unescape(heading),
                font=("Arial", 12, "bold"),
                foreground=self.colors["primary"],
                background="white",
                padding=8
            )
            heading_label.pack(fill=tk.X, pady=(10, 0))

            table_frame = ttk.Frame(parent_frame, relief="solid", borderwidth=1)
            table_frame.pack(fill=tk.X, pady=(5, 10))

            headers = re.findall(r'<th>(.*?)</th>', table_html, re.DOTALL)

            row_matches = re.findall(r'<tr>(.*?)</tr>', table_html, re.DOTALL)
            rows = []
            for row_html in row_matches:
                if '<th>' in row_html:
                    continue
                cells = re.findall(r'<td>(.*?)</td>', row_html, re.DOTALL)
                rows.append(cells)

            for i, header in enumerate(headers):
                header_label = ttk.Label(
                    table_frame,
                    text=unescape(header.strip()),
                    font=("Arial", 10, "bold"),
                    foreground=self.colors["primary"],
                    background="white",
                    borderwidth=1,
                    relief="solid",
                    padding=8,
                    anchor="w"
                )
                header_label.grid(row=0, column=i, sticky="nsew")
                table_frame.columnconfigure(i, weight=1)

            for i, row in enumerate(rows):
                for j, cell in enumerate(row):
                    cell_text = unescape(cell.replace('<br>', '\n'))
                    cell_text = self.strip_html_tags(cell_text)

                    cell_label = ttk.Label(
                        table_frame,
                        text=cell_text,
                        borderwidth=1,
                        relief="solid",
                        padding=8,
                        background="white",
                        anchor="w"
                    )
                    cell_label.grid(row=i + 1, column=j, sticky="nsew")

    def open_screenshot(self, path):
        try:
            if platform.system() == 'Windows':
                os.startfile(path)
            elif platform.system() == 'Darwin':  # macOS
                import subprocess
                subprocess.call(['open', path])
            else:  # Linux
                import subprocess
                subprocess.call(['xdg-open', path])
        except Exception as e:
            logging.error(f"Error opening screenshot: {str(e)}")
            self.update_status(f"Error opening screenshot: {str(e)}", "error")

            
    def open_screenshots_folder(self):
        try:
            if platform.system() == 'Windows':
                os.startfile(self.temp_dir)
            elif platform.system() == 'Darwin':  # macOS
                import subprocess
                subprocess.call(['open', self.temp_dir])
            else:  # Linux
                import subprocess
                subprocess.call(['xdg-open', self.temp_dir])
        except Exception as e:
            logging.error(f"Error opening screenshots folder: {str(e)}")
            self.update_status(f"Error opening folder: {str(e)}", "error")
    
    def on_close(self):
        self.root.destroy()

    def stream_api_response(self, response_data, is_mock=False):
        """
        Generator function that yields chunks of a formatted API response.
        Works with both real API responses and mock responses.
        """
        import time
        import random
        
        if is_mock:
            full_formatted_text = response_data
        else:
            try:
                parsed_data = json.loads(response_data)
                full_formatted_text = parsed_data.get("assistant_message", "")
            except json.JSONDecodeError:
                full_formatted_text = response_data
        
        display_text = ""
        chars = list(full_formatted_text)
        
        for char in chars:
            display_text += char
            yield display_text
            time.sleep(random.uniform(0.01, 0.03))

    def make_api_call(self, payload):
        try:
            # url = "http://localhost:8001/v1/chat"
            url = "https://taroapi.impelox.com/v1/chat"

            
            headers = {
                "Content-Type": "application/json",
                'x-api-key': 'demomUwuvZaEYN38J74JVzidgPzGz49h4YwoFhKl2iPzwH4uV5Jm6VH9lZvKgKuO'
            }

            response = requests.post(url, json=payload, headers=headers, stream=True)
            response.raise_for_status()
            print(response.json().get("assistant_message", ""))
            

           

            structured_response = self.parse_markdown_response(response.json().get("assistant_message", ""))
            return structured_response

        except Exception as e:
            logging.error(f"Error in API call: {str(e)}")
            self.log_error({
  "occured_while": "Making API call",
  "error_message": str(e),
  "occured_in": "front-end"
})
            self.update_status(f"API Error: {str(e)}", "error")
            return None
        
        finally:
            self.root.after(1000, self.remove_streaming_display)



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
        
        finally:
            self.root.after(1000, self.remove_streaming_display)


    def parse_markdown_response(self, markdown_text):
        """Parse the markdown response into structured data for storage"""
        structured_data = {
            "inspector_notes": "",
            "engine_details": "",
            "fault_accident": "",
            "has_engine_issue": False
        }
        
        inspector_match = re.search(r'\*\*Inspector Notes:\*\*(.*?)(?=\n\n\*\*|\Z)', markdown_text, re.DOTALL)
        if inspector_match:
            structured_data["inspector_notes"] = inspector_match.group(1).strip()
        
        engine_match = re.search(r'<<<\*\*Engine Description:\*\*>>>(.*?)(?=\n\n\*\*|\Z)', markdown_text, re.DOTALL)
        if engine_match:
            structured_data["engine_details"] = engine_match.group(1).strip()
            structured_data["has_engine_issue"] = True
        
        fault_match = re.search(r'\*\*Faults, Precautions, or Accident Information:\*\*(.*?)(?=\n\n\*\*|\Z)', markdown_text, re.DOTALL)
        if fault_match:
            structured_data["fault_accident"] = fault_match.group(1).strip()
        
        return structured_data


    def create_streaming_display(self):
        self.remove_streaming_display()
        
        self.streaming_frame = ttk.Frame(self.screenshots_container)
        self.streaming_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        self.markdown_text = MarkdownText(
            self.streaming_frame,
            wrap=tk.WORD,
            width=70,
            height=20,
            font=("Arial", 11),
            bg="white",
            padx=10,
            pady=10
        )
        self.markdown_text.pack(fill=tk.BOTH, expand=True)
        
        self.markdown_text.tag_configure("engine_issue", foreground="red", font=("Arial", 12, "bold"))
        
        self.markdown_text.config(state=tk.DISABLED)
        
        self.analyzing_label = ttk.Label(
            self.streaming_frame,
            text="Analyzing screenshot...",
            font=("Arial", 10, "italic"),
            foreground=self.colors["primary"]
        )
        self.analyzing_label.pack(pady=(0, 5))

        self.root.update_idletasks()




    def update_streaming_display(self, text):
        if not hasattr(self, 'streaming_frame'):
            self.create_streaming_display()
        
        self.markdown_text.config(state=tk.NORMAL)
        
        self.markdown_text.delete(1.0, tk.END)
        
        has_engine_issue = "<<<**Engine Description:**>>>" in text
        
        if has_engine_issue:
            parts = text.split("<<<**Engine Description:**>>>")
            
            self.markdown_text.insert_markdown(parts[0])
            
            self.markdown_text.insert(tk.END, "Engine Issue Detected: ", "engine_issue")
            
            engine_text = parts[1]
            next_section = re.search(r'\n\n\*\*', engine_text)
            
            if next_section:
                engine_details = engine_text[:next_section.start()]
                self.markdown_text.insert(tk.END, engine_details.strip(), "engine_issue")
                
                remaining_text = engine_text[next_section.start():]
                self.markdown_text.insert_markdown(remaining_text)
            else:
                self.markdown_text.insert(tk.END, engine_text.strip(), "engine_issue")
        else:
            self.markdown_text.insert_markdown(text)
        
        self.markdown_text.config(state=tk.DISABLED)
        
        dots = "." * (int(time.time() * 2) % 4)
        self.analyzing_label.config(text=f"Analyzing screenshot{dots}")

    def remove_streaming_display(self):
        if hasattr(self, 'streaming_frame'):
            self.streaming_frame.destroy()
            self.root.update_idletasks()
            if hasattr(self, 'streaming_frame'):
                delattr(self, 'streaming_frame')
            if hasattr(self, 'markdown_text'):
                delattr(self, 'markdown_text')
            if hasattr(self, 'analyzing_label'):
                delattr(self, 'analyzing_label')

if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenshotApp(root)
    root.mainloop()