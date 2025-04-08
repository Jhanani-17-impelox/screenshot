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

class MarkdownText(tk.Text):
    """A Text widget with improved Markdown rendering capabilities"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tag_configure("bold", font=("Courier", 10, "bold"))
        self.tag_configure("italic", font=("Courier", 10, "italic"))
        self.tag_configure("heading1", font=("Courier", 14, "bold"))
        self.tag_configure("heading2", font=("Courier", 12, "bold"))
        self.tag_configure("heading3", font=("Courier", 11, "bold"))
        self.tag_configure("code", background="#f0f0f0", font=("Courier", 9))
        self.tag_configure("bullet", lmargin1=20, lmargin2=30)
        self.tag_configure("link", foreground="blue", underline=1)

        # Table styling with background colors
        self.tag_configure("table_border", foreground="#555555")
        self.tag_configure("table_header", 
                        font=("Courier", 10, "bold"), 
                        foreground="#000000",
                        background="#e1e5eb")  # Light gray background for header
        self.tag_configure("table_row_even", 
                        foreground="#333333",
                        background="#f5f7fa")  # Very light gray for even rows
        self.tag_configure("table_row_odd", 
                        foreground="#333333",
                        background="#ffffff")  # White for odd rows

    def insert_markdown(self, text):
        """Parse and insert markdown text"""
        # Clear current content
        self.delete(1.0, tk.END)
        
        # Process lines
        code_block = False
        bullet_list = False
        table_mode = False
        table_rows = []
        
        lines = text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Code blocks
            if line.strip().startswith('```'):
                code_block = not code_block
                if not code_block:  # End of code block
                    self.insert(tk.END, '\n')
                i += 1
                continue
            
            if code_block:
                self.insert(tk.END, line + '\n', "code")
                i += 1
                continue
            
            # Table detection
            if line.strip().startswith('|') and '|' in line[1:]:
                if not table_mode:
                    table_mode = True
                    table_rows = []
                
                table_rows.append(line)
                i += 1
                
                # Check if next line is a separator line or if this is the end of the table
                if i < len(lines) and lines[i].strip().startswith('|') and '-' in lines[i]:
                    table_rows.append(lines[i])
                    i += 1
                    continue
                
                # Peek ahead to see if the table continues
                if i < len(lines) and lines[i].strip().startswith('|'):
                    continue
                else:
                    # Process the complete table
                    self.process_table(table_rows)
                    table_mode = False
                    continue
            
            # Headings
            if line.strip().startswith('# '):
                self.insert(tk.END, line[2:] + '\n', "heading1")
                i += 1
                continue
            elif line.strip().startswith('## '):
                self.insert(tk.END, line[3:] + '\n', "heading2")
                i += 1
                continue
            elif line.strip().startswith('### '):
                self.insert(tk.END, line[4:] + '\n', "heading3")
                i += 1
                continue
            
            # Bullet lists
            if line.strip().startswith('- ') or line.strip().startswith('* '):
                bullet_list = True
                self.insert(tk.END, '• ' + line[2:].strip() + '\n', "bullet")
                i += 1
                continue
            
            # Process inline formatting
            self.process_inline_markdown(line)
            self.insert(tk.END, '\n')
            bullet_list = False
            i += 1
    
    def process_table(self, table_rows):
        """Process and render a markdown table with improved formatting"""
        # Parse table structure
        rows = []
        is_header = True
        column_alignments = []
        
        for row_idx, row in enumerate(table_rows):
            # Skip empty rows
            if not row.strip():
                continue
                
            # Check if this is a separator row (|---|---|)
            if row.strip().replace('|', '').replace('-', '').replace(':', '').strip() == '':
                # This is a separator row - parse alignments
                cells = row.strip().split('|')[1:-1]  # Skip first and last empty
                alignments = []
                
                for cell in cells:
                    cell = cell.strip()
                    if cell.startswith(':') and cell.endswith(':'):
                        alignments = 'center'
                    elif cell.startswith(':'):
                        alignments = 'left'
                    elif cell.endswith(':'):
                        alignments = 'right'
                    else:
                        alignments = 'left'  # Default alignment
                    column_alignments.append(alignments)
                    
                is_header = False
                continue
                
            # Process cells in the row
            cells = []
            for cell in row.strip().split('|')[1:-1]:  # Skip the first and last empty cells
                # Process any markdown in the cell
                cells.append(cell.strip())
            
            rows.append((cells, is_header))
            is_header = False
        
        if not rows:
            return
        
        # Calculate column widths based on content
        col_count = max(len(row[0]) for row in rows)
        col_widths = [0] * col_count
        
        for row, _ in rows:
            for i, cell in enumerate(row):
                if i < col_count:
                    # Account for markdown characters in width calculation
                    clean_cell = re.sub(r'\*\*(.*?)\*\*', r'\1', cell)  # Remove bold
                    clean_cell = re.sub(r'\*(.*?)\*', r'\1', clean_cell)  # Remove italic
                    col_widths[i] = max(col_widths[i], len(clean_cell))
        
        # Set minimum column width
        min_col_width = 8
        col_widths = [max(w, min_col_width) for w in col_widths]
        
        # Render table with borders
        self.insert(tk.END, "\n")
        
        # Render top border
        top_border = "┌"
        for i, width in enumerate(col_widths):
            top_border += "─" * (width + 2)
            if i < len(col_widths) - 1:
                top_border += "┬"
        top_border += "┐\n"
        self.insert(tk.END, top_border, "table_border")
        
        # Render rows
        for row_idx, (cells, is_header) in enumerate(rows):
            row_text = "│"
            
            for i, cell in enumerate(cells):
                if i >= col_count:
                    continue
                    
                # Clean cell content from markdown for alignment
                clean_cell = re.sub(r'\*\*(.*?)\*\*', r'\1', cell)
                clean_cell = re.sub(r'\*(.*?)\*', r'\1', clean_cell)
                
                # Apply alignment
                alignment = column_alignments[i] if i < len(column_alignments) else 'left'
                cell_width = col_widths[i]
                
                if alignment == 'left':
                    padded_cell = clean_cell.ljust(cell_width)
                elif alignment == 'right':
                    padded_cell = clean_cell.rjust(cell_width)
                else:  # center
                    padded_cell = clean_cell.center(cell_width)
                
                # Restore markdown formatting
                formatted_cell = cell.replace(clean_cell, padded_cell)
                
                # Add cell to row
                row_text += " " + formatted_cell + " │"
            
            # Insert the row with appropriate tag
            if is_header:
                self.insert(tk.END, row_text + "\n", "table_header")
                
                # Add header separator
                sep_row = "├"
                for i, width in enumerate(col_widths):
                    sep_row += "─" * (width + 2)
                    if i < len(col_widths) - 1:
                        sep_row += "┼"
                sep_row += "┤\n"
                self.insert(tk.END, sep_row, "table_border")
            else:
                tag = "table_row_even" if row_idx % 2 == 0 else "table_row_odd"
                self.insert(tk.END, row_text + "\n", tag) 
        # Render bottom border
        bottom_border = "└"
        for i, width in enumerate(col_widths):
            bottom_border += "─" * (width + 2)
            if i < len(col_widths) - 1:
                bottom_border += "┴"
        bottom_border += "┘\n"
        self.insert(tk.END, bottom_border, "table_border")
        
        self.insert(tk.END, "\n")


    def process_inline_markdown(self, line):
        """Process inline markdown elements like bold, italic, and links"""
        line_remaining = line
        
        while line_remaining:
            # Find the first occurrence of each pattern
            bold_match = re.search(r'\*\*(.*?)\*\*', line_remaining)
            italic_match = re.search(r'\*(.*?)\*', line_remaining)
            link_match = re.search(r'\[(.*?)\]\((.*?)\)', line_remaining)
            
            # Determine which pattern comes first, if any
            matches = []
            if bold_match:
                matches.append(('bold', bold_match.start(), bold_match.end(), bold_match.group(1)))
            if italic_match:
                matches.append(('italic', italic_match.start(), italic_match.end(), italic_match.group(1)))
            if link_match:
                matches.append(('link', link_match.start(), link_match.end(), bold_match.group(1)))
            
            # If no matches, insert remaining text and exit
            if not matches:
                self.insert(tk.END, line_remaining)
                break
            
            # Sort matches by start position
            matches.sort(key=lambda x: x[1])
            match_type, start, end, content = matches[0]
            
            # Insert text before the match
            if start > 0:
                self.insert(tk.END, line_remaining[:start])
            
            # Insert matched content with appropriate tag
            self.insert(tk.END, content, match_type)
            
            # Update remaining line
            line_remaining = line_remaining[end:]
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
    
    def compress_image(self, image, quality=40, max_size=1024):
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
        inspector_notes = api_response.get("inspector_notes", "No Inspector Notes available")
        engine_details = api_response.get("engine_details", "No Engine Details available")
        fault_accident = api_response.get("fault_accident", "No Fault/Accident details available")
        has_engine_issue = api_response.get("has_engine_issue", False)

        frame = ttk.Frame(self.screenshots_container)
        frame.pack(fill=tk.X, pady=(0, 15), padx=10)

        # --- Combined Box for All Information ---
        combined_frame = ttk.Frame(frame, relief="solid", borderwidth=1, padding=10)
        combined_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Inspector Notes section
        inspector_label = ttk.Label(
            combined_frame,
            text="Inspector Notes:",
            font=("Arial", 10, "bold"),
            foreground=self.colors["primary"]
        )
        inspector_label.pack(anchor=tk.W)
        inspector_content = ttk.Label(
            combined_frame,
            text=inspector_notes,
            font=("Arial", 10),
            wraplength=800,
            justify=tk.LEFT
        )
        inspector_content.pack(anchor=tk.W, pady=(0, 10))

        # Engine Details section
        engine_label = ttk.Label(
            combined_frame,
            text="Engine Details:",
            font=("Arial", 10, "bold"),
            foreground=self.colors["primary"]
        )
        engine_label.pack(anchor=tk.W)
        engine_content = ttk.Label(
            combined_frame,
            text=engine_details,
            font=("Arial", 10),
            wraplength=800,
            justify=tk.LEFT,
            foreground="red" if has_engine_issue else self.colors["text_dark"]
        )
        engine_content.pack(anchor=tk.W, pady=(0, 10))

        # Fault/Accident Details section
        fault_label = ttk.Label(
            combined_frame,
            text="Fault/Accident Details:",
            font=("Arial", 10, "bold"),
            foreground=self.colors["primary"]
        )
        fault_label.pack(anchor=tk.W)
        fault_content = ttk.Label(
            combined_frame,
            text=fault_accident,
            font=("Arial", 10),
            wraplength=800,
            justify=tk.LEFT
        )
        fault_content.pack(anchor=tk.W)

        # --- Screenshot Below ---
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
            
            image_frame = ttk.Frame(frame, borderwidth=1, relief="solid")
            image_frame.pack(pady=5)
            
            image_label = ttk.Label(image_frame, image=photo)
            image_label.image = photo
            image_label.pack()

        # --- Header for Open Button ---
        title_frame = ttk.Frame(frame)
        title_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(
            title_frame,
            text=f"{screenshot_data['title']} - {screenshot_data['timestamp']}",
            font=("Arial", 10, "bold"),
            foreground=self.colors["primary"]
        )
        title_label.pack(side=tk.LEFT, pady=5)
        
        open_button = ttk.Button(
            title_frame,
            text="Open Image",
            command=lambda path=screenshot_data["path"]: self.open_screenshot(path),
        )
        open_button.pack(side=tk.RIGHT, padx=5)
        
        self.on_frame_configure(None)


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
        
    def make_api_call(self, payload):
        self.show_loader()  # Show loader centered on the screen
        try:
            url = "http://localhost:8001/v1/chat"
            headers = {
                "Content-Type": "application/json",
                'x-api-key': 'demomUwuvZaEYN38J74JVzidgPzGz49h4YwoFhKl2iPzwH4uV5Jm6VH9lZvKgKuO'
            }

            response = requests.post(url, json=payload, headers=headers)
            
            response.raise_for_status()

            return json.loads(response.json().get("assistant_message").replace("```json", "").replace("```", ""))

        except requests.exceptions.RequestException as e:
            print("The error is:", str(e))
            return None

        finally:
            self.hide_loader()  # Hide loader when API call is complete


    # def make_api_call(self, payload):
    #     self.show_loader()  # Show loader centered on the screen
    #     try:
    #         # Comment out the original API call
    #         """
    #         url = "http://localhost:8001/v1/chat"
    #         headers = {
    #             "Content-Type": "application/json",
    #             'x-api-key': 'demomUwuvZaEYN38J74JVzidgPzGz49h4YwoFhKl2iPzwH4uV5Jm6VH9lZvKgKuO'
    #         }

    #         response = requests.post(url, json=payload, headers=headers)
            
    #         response.raise_for_status()

    #         return json.loads(response.json().get("assistant_message").replace("```json", "").replace("```", ""))
    #         """
            
    #         # Instead, generate a mock response
    #         # time.sleep(1)  # Simulate API latency
    #         mock_response = {
    #             "inspector_notes": "Vehicle inspection completed on April 8, 2025. The vehicle appears to be in generally good condition with some minor issues noted. Regular maintenance has been performed according to service records.",
    #             "engine_details": "2.5L 4-cylinder DOHC engine with VVT. Engine sounds normal with no unusual noises. Oil level is adequate but due for change within 500 miles. Some oil seepage noted around valve cover gasket.",
    #             "fault_accident": "Minor scrape on rear bumper, likely from parking incident. Driver side mirror shows signs of previous repair. No major accident damage detected. Check engine light intermittently appears according to owner.",
    #             "has_engine_issue": True if random.random() > 0.7 else False  # Randomly return True ~30% of the time
    #         }
    #         return mock_response

    #     except Exception as e:
    #         logging.error(f"Error in mock API call: {str(e)}")
    #         return {
    #             "inspector_notes": "Error retrieving inspector notes.",
    #             "engine_details": "Error retrieving engine details.",
    #             "fault_accident": "Error retrieving fault/accident information.",
    #             "has_engine_issue": False
    #         }

    #     finally:
    #         self.hide_loader()  # Hide loader when API call is complete

            
if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenshotApp(root)
    root.mainloop()