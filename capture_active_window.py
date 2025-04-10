###############this is the first 470 lines of code################

import random
import tkinter as tk
from tkinter import ttk, scrolledtext
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

class HTMLDisplay:
    """A class to handle HTML rendering in the Tkinter app"""
    def __init__(self, parent, html_content, width=800, height=None, padx=10, pady=10):
        self.parent = parent
        
        # Process the HTML content to ensure tables render properly
        self.html_content = self._process_html(html_content)
        
        # Create the HTML display widget
        self.html_widget = HTMLScrolledText(
            parent, 
            html=self.html_content,
            width=width,
            height=height,
            padx=padx,
            pady=pady
        )
        
        # Configure styling and disable editing
        self.html_widget.configure(
            font=("Arial", 10),
            cursor="arrow",
            background="#ffffff",
            state="disabled"  # Make the widget uneditable
        )
        
    def pack(self, **kwargs):
        """Pack the HTML widget with the specified options"""
        self.html_widget.pack(**kwargs)
        
    def update_html(self, new_html):
        """Update the HTML content"""
        self.html_content = self._process_html(new_html)
        self.html_widget.set_html(self.html_content)
        self.html_widget.configure(state="disabled")  # Ensure it remains uneditable

    def _process_html(self, html_content):
        """Process HTML to ensure tables render properly without showing style tags"""
        # Wrap the HTML in a proper HTML document structure if it's not already
        if not html_content.strip().startswith("<html>"):
            html_content = f"""
            <html>
            <head>
            <style>
                /* Table styling */
                table {{ border-collapse: collapse; width: auto; margin: 10px 0; }}
                th, td {{ border: 1px solid #000000; padding: 10px; text-align: left; }}
                th {{ font-weight: bold; color: #1a237e; background-color: #ffffff; }}
                td {{ background-color: #ffffff; }}
                
                /* Content styling */
                .section {{ margin-bottom: 15px; padding: 0; }}
                h3 {{ color: #4a6baf; margin: 10px 0 5px 0; padding: 0; font-size: 14px; border-bottom: 1px solid #e1e5eb; }}
                p {{ margin: 5px 0; line-height: 1.4; text-align: justify; }}
                .issue {{ color: #cc0000; }}
                .highlight {{ background-color: #fff3cd; padding: 2px; }}
            </style>
            </head>
            <body>
            {html_content}
            </body>
            </html>
            """
        return html_content
    
class ScreenshotApp:
    def __init__(self, root):
        logger.info("ScreenshotApp initialized.")
    
        
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
            logger.info(f"Payload saved to {self.payload_file}")

            self.update_status(f"Payload saved to {self.payload_file}", "success")
        except Exception as e:
            logging.error(f"Error saving payload: {str(e)}") 
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
        
        # Change from transparent to a normal window with configurable background
        # self.button_window.attributes('-transparentcolor', '#f0f0f0')
        
        # Create a frame with black border that will act as the draggable area
        button_frame = tk.Frame(
            self.button_window,
            bg="black",  # Black background for the outer frame
            bd=4  # Border width (thickness of the black outline)
        )
        button_frame.pack(fill=tk.BOTH, expand=True)
        
        # Inner frame for the actual button
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
        
        # Bind drag events to the button_frame (black border) for dragging
        button_frame.bind("<ButtonPress-1>", self.start_move)
        button_frame.bind("<ButtonRelease-1>", self.stop_move)
        button_frame.bind("<B1-Motion>", self.do_move)
        
        # Also bind events to inner_frame to ensure we can drag from any part of the window
        inner_frame.bind("<ButtonPress-1>", self.start_move)
        inner_frame.bind("<ButtonRelease-1>", self.stop_move)
        inner_frame.bind("<B1-Motion>", self.do_move)
        
        # The actual button only handles click events, not drag events
        capture_button.bind("<ButtonPress-1>", self.button_press)
        capture_button.bind("<ButtonRelease-1>", self.button_release)

    def position_floating_button(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Increase button size to account for the border
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



###########this is the next 575 lines of code#####################
    # Add new methods for button press and release specifically
    def button_press(self, event):
        # Just for the actual button - no drag logic here
        pass

    def button_release(self, event):
        # Only capture when the button itself is clicked
        if not self.is_capturing:
            self.handle_capture()
    
    def create_loader(self, parent):
        """Create a localized loader overlay with a spinning animation centered on the screen"""
        self.loader_frame = tk.Frame(parent, bg="#2D617F", relief="solid", bd=2)
        self.loader_frame.place(relx=0.5, rely=0.5, anchor="center", width=100, height=100)

        self.spinner_label = ttk.Label(self.loader_frame, background="#2D617F")
        self.spinner_label.pack(expand=True)

        # Create spinning animation
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
        """Show the loader centered on the screen"""
        if not hasattr(self, "loader_frame"):
            self.create_loader(self.root)  # Use the root window as the parent
        self.loader_frame.lift()
        self.loader_frame.place(relx=0.5, rely=0.5, anchor="center", width=60, height=60)

    def hide_loader(self):
        """Hide the loader"""
        if hasattr(self, "loader_frame"):
            self.loader_frame.place_forget()

    def handle_capture(self):
        if self.is_capturing:
            logger.info("Capture already in progress.")
            return
        logger.info("Starting capture process.")
            
        capture_thread = threading.Thread(target=self.capture_active_window)
        capture_thread.daemon = True
        capture_thread.start()
    
##########this is the next 530 lines of code#####################

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
                print(f"Error getting window info on Windows: {e}")
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
                bounds = [int(val) for val in result.split(',')]
                return title, tuple(bounds)
            except Exception as e:
                logging.error(f"Error getting window info on macOS: {e}")
                return f"Window_{datetime.now().strftime('%H%M%S')}", None
        
        elif system == 'Linux':
            try:
                import subprocess
                
                win_id_cmd = ["xdotool", "getactivewindow"]
                win_id = subprocess.check_output(win_id_cmd).decode('utf-8').strip()
                
                name_cmd = ["xdotool", "getwindowname", win_id]
                title = subprocess.check_output(name_cmd).decode('utf-8').strip()
                
                geo_cmd = ["xdotool", "getwindowgeometry", win_id]
                geo_output = subprocess.check_output(geo_cmd).decode('utf-8')
                
                pos_line = [line for line in geo_output.split('\n') if "Position" in line][0]
                pos_parts = pos_line.split(":")[1].strip().split(",")
                x = int(pos_parts[0])
                y = int(pos_parts[1])
                
                size_line = [line for line in geo_output.split('\n') if "Geometry" in line][0]
                size_parts = size_line.split(":")[1].strip().split("x")
                width = int(size_parts[0])
                height = int(size_parts[1])
                
                return title, (x, y, width, height)
            except Exception as e:
                logging.error(f"Error getting window info on Linux: {e}")
                return f"Window_{datetime.now().strftime('%H%M%S')}", None
            
        logging.warning("Unknown operating system. Returning default window info.")
        return f"Window_{datetime.now().strftime('%H%M%S')}", None
    
    def capture_active_window(self):
        self.is_capturing = True
        self.show_loader()  # Show loader centered on the screen
        logger.info("Loader shown for capture process.")

        try:
            self.root.withdraw()
            self.button_window.withdraw()
            logger.info("Windows hidden for capture.")
            
            time.sleep(0.5)
            
            window_title, window_bounds = self.get_window_info()
            logger.info(f"Captured window title: {window_title}")
            
            if "Taro " in window_title or not window_title:
                self.root.deiconify()
                self.button_window.deiconify()
                self.update_status("No active window detected or captured our own app", "info")
                self.is_capturing = False
                self.hide_loader()  # Hide loader on failure
                return
            
            # Take high-resolution screenshot
            if window_bounds:
                x, y, width, height = window_bounds
                logger.info(f"Window bounds: {window_bounds}")
                
                if width <= 0 or height <= 0:
                    self.root.deiconify()
                    self.button_window.deiconify()
                    self.update_status("Invalid window dimensions detected", "error")
                    self.is_capturing = False
                    self.hide_loader()  # Hide loader on failure
                    return
                
                screenshot = pyautogui.screenshot(region=(x, y, width, height))
                capture_type = "active window"

                logger.info("Screenshot taken for active window.")

            else:
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
                        
                        result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 0)
                        
                        bmpinfo = saveBitMap.GetInfo()
                        bmpstr = saveBitMap.GetBitmapBits(True)
                        screenshot = Image.frombuffer(
                            'RGB',
                            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                            bmpstr, 'raw', 'BGRX', 0, 1)
                        
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

                    logger.warning("Falling back to full screen capture.")
                    
                    screenshot = pyautogui.screenshot()
                    capture_type = "full screen (fallback)"

            
            self.root.deiconify()
            self.button_window.deiconify()
            
            sanitized_title = ''.join(c for c in window_title if c.isalnum() or c in ' -_')[:30]
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"screenshot_{timestamp}_{sanitized_title}.png"
            file_path = os.path.join(self.temp_dir, filename)
            
            # Save original high-resolution image
            screenshot.save(file_path, quality=95)
            
            # Compress image for base64 encoding
            compressed_img = self.compress_image(screenshot)
            
            # Convert screenshot to base64
            buffered = BytesIO()
            # screenshot.save(buffered, format="PNG", optimize=True)
            compressed_img.save(buffered, format="PNG", optimize=True)
            img_str_raw = base64.b64encode(buffered.getvalue()).decode()
            
            # Add data URI prefix to base64 string
            # img_str = f"data:image/png;base64,{img_str_raw}"
            img_str =img_str_raw
            
            # Create JSON payload with the base64 image
            session_id = str(uuid.uuid4())
            payload_json = {
                "session_id": session_id,
                "user_message": {
                    "type": "image",
                    "image": [img_str],
                },
                "conversation_history": [
                    {
                        "role": "user",
                        "content": "get only the Inspector's Notes,Engine description and Fault parts and precautions accident from this image",
                        "attachments": [
                            {
                                "type": "file",
                                "base64String": [img_str]
                            }
                        ]
                    }
                ]
            }
            
            # Comment out the API call and use mock response
            result = self.make_api_call(payload_json)
            print(result)
            if type(result) == str or result==None:
                self.update_status("Server Error: Please try again later", "error")
                return
            else:
                self.save_payload_to_file(payload_json)
            
                # Add to screenshots list (at the beginning)
                self.screenshots.insert(0, {
                    "image": screenshot,
                    "title": window_title,
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "path": file_path,
                    "base64": img_str,
                    "payload_json": payload_json,
                    "api_response": result
                })
                
                # Clear existing screenshots from UI
                for widget in self.screenshots_container.winfo_children():
                    widget.destroy()
                
                # Update the UI with all screenshots (newest first)
                for i in range(len(self.screenshots)):
                    self.add_screenshot_to_ui(i)
                
                self.update_status(f"Captured {capture_type}: {window_title}", "success")
            
                logger.info(f"Captured {capture_type}: {window_title}")

        except Exception as e:
            logging.error(f"Error capturing screenshot: {str(e)}")
            self.update_status(f"Error capturing screenshot: {str(e)}", "error")
        
        finally:
            self.is_capturing = False
            self.hide_loader()  # Hide loader when capture is complete
    
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
            # bg_color = self.colors["success"]
            fg_color = self.colors["text_light"]
        elif status_type == "error":
            bg_color = self.colors["error"]
            fg_color = self.colors["text_light"]
        else:  # info
            bg_color = self.colors["secondary"]
            fg_color = self.colors["text_light"]
        
        self.status_label.configure(
            text=message,
            background=bg_color,
            foreground=fg_color
        )

    def add_screenshot_to_ui(self, index):
        screenshot_data = self.screenshots[index]

        # Extract API response
        api_response = screenshot_data.get("api_response", {})
        inspector_notes = api_response.get("inspector_notes", None)
        engine_details = api_response.get("engine_details", None)
        fault_accident = api_response.get("fault_accident", None)

        # Create a single frame for all content
        frame = ttk.Frame(self.screenshots_container, relief="solid", borderwidth=1, padding=10)
        frame.pack(fill=tk.X, pady=(0, 15), padx=10)

        # Inspector Notes Section
        if inspector_notes and inspector_notes.strip():
            inspector_label = ttk.Label(
                frame,
                text="Inspector Notes:",
                font=("Arial", 11, "bold"),
                foreground=self.colors["primary"]
            )
            inspector_label.pack(anchor=tk.W, pady=(5, 0))

            inspector_text = ttk.Label(
                frame,
                text=inspector_notes.replace("\n", "\n").replace(")", ")\n").strip(),  # Add new line after )
                font=("Arial", 10),
                wraplength=600,  # Wrap text to fit within the frame
                justify=tk.LEFT
            )
            inspector_text.pack(anchor=tk.W, pady=(0, 10))

        # Engine Details Section
        if engine_details and engine_details.strip() and engine_details.lower() != "null":
            engine_label = ttk.Label(
                frame,
                text="Engine Details:",
                font=("Arial", 11, "bold"),
                foreground=self.colors["primary"]
            )
            engine_label.pack(anchor=tk.W, pady=(5, 0))

            engine_text = ttk.Label(
                frame,
                text=engine_details.replace("\n", "\n").replace(")", ")\n").strip(),  # Add new line after )
                font=("Arial", 10),
                wraplength=600,
                justify=tk.LEFT
            )
            engine_text.pack(anchor=tk.W, pady=(0, 10))

        # Fault/Accident Details Section
        if fault_accident and fault_accident.strip():
            fault_label = ttk.Label(
                frame,
                text="Fault/Accident Details:",
                font=("Arial", 11, "bold"),
                foreground=self.colors["primary"]
            )
            fault_label.pack(anchor=tk.W, pady=(5, 0))

            fault_text = ttk.Label(
                frame,
                text=fault_accident.replace("\n", "\n").replace(")", ")\n").strip(),  # Add new line after )
                font=("Arial", 10),
                wraplength=600,
                justify=tk.LEFT
            )
            fault_text.pack(anchor=tk.W, pady=(0, 10))

        # Render the screenshot below the information
        img = screenshot_data.get("image")
        if img:
            max_width = 600
            width, height = img.size
            ratio = min(max_width / width, 1.0)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            thumbnail = img.resize((new_width, new_height), Image.LANCZOS)
            photo = ImageTk.PhotoImage(thumbnail)
            screenshot_data["photo"] = photo

            image_label = ttk.Label(frame, image=photo)
            image_label.image = photo
            image_label.pack(pady=10)

        # Add a header with the title and timestamp
        title_label = ttk.Label(
            frame,
            text=f"{screenshot_data['title']} - {screenshot_data['timestamp']}",
            font=("Arial", 10, "bold"),
            foreground=self.colors["primary"]
        )
        title_label.pack(pady=(5, 0))

        # Add an "Open Image" button
        open_button = ttk.Button(
            frame,
            text="Open Image",
            command=lambda path=screenshot_data["path"]: self.open_screenshot(path),
        )
        open_button.pack(pady=(5, 0))

        self.on_frame_configure(None)
        
    def strip_html_tags(self, html_text):
        """Remove HTML tags from text"""
        import re
        clean = re.compile('<.*?>')
        return re.sub(clean, '', html_text)


    
    def create_tables_from_html(self, parent_frame, html_content):
        """Parse full HTML (with <thead> and <tbody>) and render Tkinter tables"""
        import re
        from html import unescape

        # Extract all <h3> headings and their corresponding tables
        sections = re.findall(r'<h3>(.*?)</h3>\s*<table.*?>(.*?)</table>', html_content, re.DOTALL)

        for heading, table_html in sections:
            # Add section heading
            heading_label = ttk.Label(
                parent_frame,
                text=unescape(heading),
                font=("Arial", 12, "bold"),
                foreground=self.colors["primary"],
                background="white",
                padding=8
            )
            heading_label.pack(fill=tk.X, pady=(10, 0))

            # Create a frame for the table
            table_frame = ttk.Frame(parent_frame, relief="solid", borderwidth=1)
            table_frame.pack(fill=tk.X, pady=(5, 10))

            # Extract headers from <thead>
            headers = re.findall(r'<th>(.*?)</th>', table_html, re.DOTALL)

            # Extract rows from <tbody>
            row_matches = re.findall(r'<tr>(.*?)</tr>', table_html, re.DOTALL)
            rows = []
            for row_html in row_matches:
                # Skip <tr> with <th> (already processed)
                if '<th>' in row_html:
                    continue
                cells = re.findall(r'<td>(.*?)</td>', row_html, re.DOTALL)
                rows.append(cells)

            # Draw header
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

            # Draw data rows
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
            # Update status with error message
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
        
    # def make_api_call(self, payload):
    #     self.show_loader()  # Show loader centered on the screen
    #     try:
          
    #         url = "http://localhost:8001/v1/chat"
    #         headers = {
    #             "Content-Type": "application/json",
    #             'x-api-key': 'demomUwuvZaEYN38J74JVzidgPzGz49h4YwoFhKl2iPzwH4uV5Jm6VH9lZvKgKuO'
    #         }

    #         response = requests.post(url, json=payload, headers=headers)
    #         response.raise_for_status()
    #         if response.status_code != 201 and response.status_code == 401:
    #             self.update_status("Unauthorized User:its seems you don't have permission, contact your admin", "error")
    #             return None
    #         elif response.status_code == 500:
    #             self.update_status("Server Error: Please try again later", "error")
    #             return None
    #         elif response.status_code == 201:
    #             return json.loads(response.json().get("assistant_message"))
    #         else:
    #             self.update_status("Unexpected Error: Please try again", "error")
    #             return None
          

    #     except Exception as e:
    #         logging.error(f"Error in mock API call: {str(e)}")
    #         return None

    #     finally:
    #         self.hide_loader()  # Hide loader when API call is complete

    def make_api_call(self, payload):
        self.show_loader()  # Show loader centered on the screen
        try:
            # Mock response
            mock_response = {
                "engine_details": "null",
                "fault_accident": "シートシミ (Manchas en los asientos)\nキズ有  (Tiene rasguños)\nホイール、ミラーキズ (Rayones en las ruedas y los espejos)",
                "has_engine_issue": False,
                "inspector_notes": "シントシミ (Manchas en los asientos)\nキズ有 (Tiene rasguños)\nホイール、ミラーキズ (Rayones en las ruedas y los espejos)"
            }
            return mock_response

        except Exception as e:
            logging.error(f"Error in mock API call: {str(e)}")
            return {
                "inspector_notes": "Error retrieving inspector notes.",
                "engine_details": "Error retrieving engine details.",
                "fault_accident": "Error retrieving fault/accident information.",
                "has_engine_issue": False
            }

        finally:
            self.hide_loader()  # Hide loader when API call is complete


if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenshotApp(root)
    root.mainloop()