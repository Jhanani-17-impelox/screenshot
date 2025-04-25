import tkinter as tk
from tkinter import ttk, PhotoImage
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
import requests
from utils import MarkdownText , setup_icon,configure_styles, log_error,toggle_connection,create_connection_toggle,draw_toggle

# Configure logging
logging.basicConfig(
    filename='screenshot_app.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Create a logger object
logger = logging.getLogger(__name__)


class ScreenshotApp:
    def __init__(self, root):
        self.root = root
        self.is_connected = False
        self.use_websocket = False  # Default to REST API
        self.root.title("Taro ")
        self.root.geometry("1024x768")
        self.root.resizable(True, True)

        self.script_dir = os.path.dirname(os.path.abspath(__file__))
       
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
        configure_styles(self)
        setup_icon(self)
        
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
        create_connection_toggle(self)  # Add toggle button creation
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Initialize Socket.IO client but don't connect
        self.sio = socketio.Client(reconnection=True, reconnection_attempts=5, reconnection_delay=1, reconnection_delay_max=5)
        self.setup_socketio_events()
        
        self.request_start_time = None
        self.thread_loops = {}

    def clear_websocket_events(self):
        """Clear application-specific WebSocket events, preserving core connection events"""
        if hasattr(self, 'sio'):
            # Store the core event handlers before clearing
            connect_handler = self.sio.handlers.get('connect', None)
            disconnect_handler = self.sio.handlers.get('disconnect', None)
            connect_error_handler = self.sio.handlers.get('connect_error', None)
            
            # Clear all registered event handlers
            self.sio.handlers.clear()
            
            # Restore core event handlers
            if connect_handler:
                self.sio.handlers['connect'] = connect_handler
            if disconnect_handler:
                self.sio.handlers['disconnect'] = disconnect_handler
            if connect_error_handler:
                self.sio.handlers['connect_error'] = connect_error_handler
                
            logging.info("Cleared application WebSocket events while preserving core events")
    
    def setup_socketio_events(self):
        """Setup Socket.IO event handlers without connecting"""
        @self.sio.event
        def connect():
            logging.info("Connected to server")
            self.is_connected = True
            self.update_status("WebSocket connected", "success")
            threading.Thread(target=self.start_periodic_ping, daemon=True).start()

        @self.sio.event
        def connect_error(data):
            logging.error(f"Connection failed: {data}")
            self.is_connected = False
            self.clear_websocket_events()  # Clear events on connection error
            self.update_status("Socket.IO connection failed", "error")

        @self.sio.event
        def disconnect():
            self.is_connected = False
            self.clear_websocket_events()  # Clear events on disconnect
            logging.info("Disconnected from server")
            self.update_status("Socket.IO disconnected", "info")

        @self.sio.on('ping')  
        def on_ping(data):
            logging.info(f"Received ping from server: {data}")
            if not self.is_connected:
                self.is_connected = True
            self.sio.emit('pong', "Pong back to server")

        @self.sio.on('pong')
        def on_pong(data):
            logging.info(f"Received pong from server: {data}")
            if not self.is_connected:
                self.is_connected = True

    def start_periodic_ping(self):
        """Send periodic pings to keep the connection alive"""
        """Send periodic pings to the server to keep the connection alive"""
        while self.is_connected:
            try:
                if self.is_connected:
                    start_time = time.time()
                    self.sio.emit('ping', "Ping from client")
                    print("Ping sent to server")
                
                time.sleep(15)
            except Exception as e:
                print(f"Error in ping thread: {e}")

    def connect_socketio(self):
        """Establish Socket.IO connection"""
        try:
            print("Connecting to Socket.IO server...", self.is_connected)
            if not self.is_connected:
                # self.sio.connect('wss://taroapi.impelox.com/gemini', transports=['websocket'])  
                self.sio.connect('ws://localhost:8001/gemini', transports=['websocket'],socketio_path='/socket.io')  
                print("Connected to server")    # Wait for the connection to be established                    
                self.is_connected = True
            return True
        except Exception as e:
            logging.error(f"Socket.IO connection failed: {str(e)}")
            self.is_connected = False
            self.update_status("Socket.IO connection failed", "error")
            return False

    def send_to_socketio(self, image_data):
        """Send data through Socket.IO connection"""
        try:
            payload = {
                "message": "Get the required information from the image - Inspectore Notes, Faults, Precautions, or Accident Information and Engine Description",
                "image": image_data 
            }
            if not self.sio.connected:
                self.connect_socketio()
            self.sio.emit('geminiRequest', payload)
            try:
               return True
            except asyncio.TimeoutError:
                logging.error("Socket.IO response timeout")
                self.update_status("Response timeout", "error")
                return None
                
        except Exception as e:
            logging.error(f"Socket.IO communication error: {str(e)}")
            self.update_status("Socket.IO communication error", "error")
            return None

    def send_to_rest_api(self, image_data):
        """Send data through REST API"""
        try:
            session_id = str(uuid.uuid4())
            payload = {
                "session_id": session_id,
                "user_message": {
                    "type": "image",
                    "image": [image_data],
                },
                "conversation_history": [
                    {
                        "role": "user",
                        "content": "get only the Inspector's Notes,Engine description and Fault parts and precautions accident from this image",
                        "attachments": [
                            {
                                "type": "file",
                                "base64String": [image_data]
                            }
                        ]
                    }
                ]
            }
            url = "http://localhost:8001/v1/chat"
            # url = "https://taroapi.impelox.com/v1/chat"
            print("Sending data to REST API")
            
            headers = {
                "Content-Type": "application/json",
                'x-api-key': 'demomUwuvZaEYN38J74JVzidgPzGz49h4YwoFhKl2iPzwH4uV5Jm6VH9lZvKgKuO'
            }

            response = requests.post(url, json=payload, headers=headers, stream=True)
            response.raise_for_status()
            print(response.json().get("assistant_message", ""))
            if response.status_code == 201:
                return response.json().get("assistant_message", "")
            else:
                logging.error(f"REST API error: {response.status_code}")
                self.update_status(f"REST API error: {response.status_code}", "error")
                return None
        except Exception as e:
            logging.error(f"REST API communication error: {str(e)}")
            self.update_status("REST API communication error", "error")
            return None

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
            log_error({
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


    def on_toggle_click(self, event):
        """Handle toggle click event"""
        self.connection_var.set(not self.connection_var.get())
        draw_toggle(self)
        toggle_connection(self)
        

    def handle_capture(self):
        if self.is_capturing:
            return
        self.request_start_time = time.time()  # Start timing
        self.update_status("Processing request...", "analyzing")
        capture_thread = threading.Thread(target=self.capture_active_window)
        capture_thread.daemon = True
        capture_thread.start()
    

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
                log_error({
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

           
            print(self.use_websocket, self.is_connected)
            if self.use_websocket and self.is_connected:
                # Use WebSocket connection
                result = self.send_to_socketio(img_str_raw)
            else:
                # Use REST API
                result = self.send_to_rest_api(img_str_raw)
                if result:
                    # Handle REST API response directly
                    new_screenshot_data = {
                        "image": screenshot,
                        "title": window_title,
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "path": file_path,
                        "api_response": result
                    }
                    self.screenshots.insert(0, new_screenshot_data)
                    self.add_screenshot_to_ui(0, new_screenshot_data)
                    self.update_status(f"Captured {capture_type}: {window_title}", "success")

            @self.sio.on('gemini_response')
            def on_response(data):
                logging.info(f"Received response from server: {data}")

                if data is None:
                    return

                new_screenshot_data = {
                    "image": screenshot,
                    "title": window_title,
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "path": file_path,
                    "api_response": data
                }
                self.screenshots.insert(0, new_screenshot_data)

                self.add_screenshot_to_ui(0, new_screenshot_data)

                self.update_status(f"Captured {capture_type}: {window_title}", "success")

        except Exception as e:
            logging.error(f"Error capturing screenshot: {str(e)}")
            log_error({
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
            bg_color = '#7DDA58'
            fg_color = self.colors["text_light"]
        elif status_type == "error":
            bg_color = self.colors["error"]
            fg_color = self.colors["text_light"]
        elif status_type == "analyzing":
            bg_color = '#FFDE59'
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
        if len(self.screenshots) % 2 == 0:
            bg=self.colors["bg_light"]
        else:   
            bg=self.colors["bg_dark"]
         # Debug print to see what we're working with
        print(f"Current screenshots count: {len(self.screenshots) if hasattr(self, 'screenshots') else 0}")
        
        # Ensure screenshots list exists
        if not hasattr(self, 'screenshots') or self.screenshots is None:
            self.screenshots = []
        
        # Add the new screenshot
        self.screenshots.append(screenshot_data)
        print(f"After adding, screenshots count: {len(self.screenshots)}")
        
        # If we exceed the limit (3 in your case)
        if len(self.screenshots) > 20:
            # Get reference to the UI element before removing it from the list
            if hasattr(self, 'screenshots_container') and self.screenshots_container.winfo_children():
                # Get the oldest UI element (first one added)
                try:
                    oldest_ui_element = self.screenshots_container.winfo_children()[0]
                    print(f"Removing oldest UI element, child count before: {len(self.screenshots_container.winfo_children())}")
                    oldest_ui_element.destroy()
                    print(f"Child count after: {len(self.screenshots_container.winfo_children())}")
                except (IndexError, TypeError) as e:
                    print(f"Error removing UI element: {e}")
            
            # Now remove the oldest screenshot from our list (first one)
            try:
                removed = self.screenshots.pop(0)  # Remove the FIRST (oldest) element
                print(f"Removed oldest screenshot: {removed.get('title', 'unknown')} from list")
            except (IndexError, AttributeError) as e:
                print(f"Error removing from screenshots list: {e}")
                
        
        
            
        full_text = screenshot_data.get("api_response", "")
        has_engine_issue = "<<<**Engine Description:**>>>" in full_text

        # Use regex to extract each section
        inspector_match = re.search(r"\*\*Inspector Notes:\*\*\s*\n(.*?)(?=(<<<\*\*Engine Description:\*\*>>>|\*\*Faults, Precautions,|$))", full_text, re.DOTALL)
        engine_match = re.search(r"<<<\*\*Engine Description:\*\*>>>\s*\n(.*?)(?=(\*\*Faults, Precautions,|$))", full_text, re.DOTALL)
        faults_match = re.search(r"\*\*Faults, Precautions, or Accident Information:\*\*\s*\n(.*)", full_text, re.DOTALL)

        inspector_notes = inspector_match.group(1).strip() if inspector_match else ""
        engine_details = engine_match.group(1).strip() if engine_match else ""
        fault_accident = faults_match.group(1).strip() if faults_match else ""
        img = screenshot_data.get("image")

        frame = ttk.Frame(self.screenshots_container, relief="solid", borderwidth=1, padding=10)
        frame.pack(fill=tk.X, pady=(0, 15), padx=10, side=tk.TOP)

        title_label = ttk.Label(
            frame,
            text=f"{screenshot_data['title']} - {screenshot_data['timestamp']}",
            font=("Arial", 10, "bold"),
            foreground=self.colors["primary"]
        )
        title_label.pack(pady=(5, 0))
 # --- Scrollbars ---
        v_scrollbar = ttk.Scrollbar(frame, orient="vertical")
        markdown_display = MarkdownText(
            frame,
            wrap=tk.WORD,
            width=70,
            height=20,
            font=("Arial", 11),
            bg=bg,
            padx=10,
            pady=10,
            yscrollcommand=v_scrollbar.set
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
        if not inspector_notes and not engine_details and not fault_accident:
            markdown_content += f"{full_text}\n\n"

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
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

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

    def on_close(self):
        """Clean up Socket.IO connection before closing"""
        if self.sio.connected:
            self.sio.disconnect()
            
        # Close all thread loops
        for loop in self.thread_loops.values():
            try:
                loop.stop()
                loop.close()
            except Exception:
                pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenshotApp(root)
    root.mainloop()