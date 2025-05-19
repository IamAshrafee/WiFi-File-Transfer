import os
import socket
import threading
import webbrowser
import qrcode
import logging
from datetime import datetime
from PIL import Image
from flask import Flask, request, render_template, url_for
from flask_cors import CORS
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import requests
from werkzeug.serving import make_server
from win10toast import ToastNotifier
import humanize

# Configure logging
def setup_logging():
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'wifi_transfer_{datetime.now().strftime("%Y%m%d")}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

setup_logging()
logger = logging.getLogger(__name__)

def is_port_available(port):
    """Check if a port is available."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', port))
            return True
    except OSError:
        return False

def find_available_port(start_port=5000, max_port=5050):
    """Find an available port in the given range."""
    for port in range(start_port, max_port):
        if is_port_available(port):
            return port
    raise RuntimeError(f"No available ports found between {start_port} and {max_port}")

# Initialize Flask app and notification
try:
    server = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    CORS(server)
    toaster = ToastNotifier()
    logger.info("Application initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize application: {str(e)}")
    raise

# Configure upload folder
def setup_upload_directory():
    """Setup and verify the upload directory with proper permissions"""
    try:
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Test write permissions
        test_file = os.path.join(upload_dir, '.test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except (IOError, OSError) as e:
            raise RuntimeError(f"Upload directory is not writable: {str(e)}")
            
        logger.info(f"Upload folder configured and verified at: {upload_dir}")
        return upload_dir
    except Exception as e:
        logger.error(f"Failed to setup upload directory: {str(e)}")
        raise

try:
    UPLOAD_FOLDER = setup_upload_directory()
except Exception as e:
    logger.error(f"Critical error setting up upload folder: {str(e)}")
    raise

class LogoManager:
    """Manages logo assets and their usage throughout the application"""
    
    SIZES = {
        'small': (32, 32),
        'medium': (64, 64),
        'large': (128, 128),
        'xlarge': (256, 256)
    }
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.images_dir = os.path.join(self.base_dir, 'static', 'images')
        self.png_dir = os.path.join(self.images_dir, 'png')
        self.cached_images = {}
        
    def get_icon_path(self):
        """Get the best available icon for window and taskbar"""
        icon_paths = [
            os.path.join(self.png_dir, 'logo.ico'),
            os.path.join(self.png_dir, 'logo-normal.png'),
            os.path.join(self.images_dir, 'logo.ico'),
            os.path.join(self.images_dir, 'logo-normal.png')
        ]
        
        for path in icon_paths:
            if os.path.exists(path):
                return path
        return None
        
    def get_notification_icon(self):
        """Get icon path for system notifications"""
        icon_path = os.path.join(self.png_dir, 'logo.ico')
        if os.path.exists(icon_path):
            return icon_path
            
        # Fallback to PNG
        png_path = os.path.join(self.png_dir, 'logo-normal.png')
        if os.path.exists(png_path):
            return png_path
            
        return None
        
    def get_logo_image(self, size='large', for_dark_mode=False):
        """Get CTkImage for the specified size, with dark mode support"""
        cache_key = f"{size}_{'dark' if for_dark_mode else 'light'}"
        
        if cache_key in self.cached_images:
            return self.cached_images[cache_key]
            
        dimensions = self.SIZES.get(size, self.SIZES['large'])
        
        # Try to find the best image for the requested size
        image_paths = [
            os.path.join(self.png_dir, f'logo_{size}.png'),
            os.path.join(self.images_dir, f'logo_{size}.png'),
            os.path.join(self.png_dir, 'logo-normal.png'),
            os.path.join(self.images_dir, 'logo-normal.png')
        ]
        
        for path in image_paths:
            if os.path.exists(path):
                try:
                    image = Image.open(path)
                    # Create CTkImage with both light and dark variants
                    ctk_image = ctk.CTkImage(
                        light_image=image,
                        dark_image=image,
                        size=dimensions
                    )
                    self.cached_images[cache_key] = ctk_image
                    return ctk_image
                except Exception as e:
                    logger.error(f"Failed to load logo image {path}: {str(e)}")
                    continue
        
        # Create empty image as fallback
        empty_image = Image.new('RGB', dimensions, color='white')
        ctk_image = ctk.CTkImage(
            light_image=empty_image,
            dark_image=empty_image,
            size=dimensions
        )
        self.cached_images[cache_key] = ctk_image
        return ctk_image

# Update the show_notification function to use LogoManager
def show_notification(title, message):
    """Show a Windows notification with application icon"""
    try:
        logo_manager = LogoManager()
        icon_path = logo_manager.get_notification_icon()
        
        toaster.show_toast(
            title,
            message,
            icon_path=icon_path,
            duration=2,
            threaded=True
        )
        logger.info(f"Notification shown - Title: {title}, Message: {message}")
        
    except Exception as e:
        logger.error(f"Failed to show notification: {str(e)}")
        # Fallback to notification without icon
        try:
            toaster.show_toast(
                title,
                message,
                duration=2,
                threaded=True
            )
            logger.info("Fallback notification shown without icon")
        except Exception as e:
            logger.error(f"Failed to show fallback notification: {str(e)}")

class ServerThread(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self, daemon=True)
        try:
            self.port = find_available_port()
            self.srv = make_server('0.0.0.0', self.port, app)
            self.ctx = app.app_context()
            self.ctx.push()
            logger.info(f"Server thread initialized successfully on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to initialize server thread: {str(e)}")
            raise

    def run(self):
        try:
            logger.info(f"Starting server on port {self.port}...")
            self.srv.serve_forever()
        except Exception as e:
            logger.error(f"Server error: {str(e)}")
            raise

    def shutdown(self):
        try:
            logger.info("Initiating server shutdown...")
            shutdown_thread = threading.Thread(target=self._shutdown)
            shutdown_thread.daemon = True
            shutdown_thread.start()
        except Exception as e:
            logger.error(f"Error during server shutdown: {str(e)}")
            raise

    def _shutdown(self):
        try:
            requests.get(f'http://localhost:{self.port}/')
        except requests.exceptions.RequestException:
            logger.debug("Expected connection error during shutdown")
        
        try:
            self.srv.shutdown()
            self.srv.server_close()
            logger.info("Server shutdown completed")
        except Exception as e:
            logger.error(f"Error closing server: {str(e)}")

@server.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index page: {str(e)}")
        return "Error loading page", 500

@server.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            logger.warning("No file part in the request")
            return 'No file part', 400
        
        files = request.files.getlist('file')
        uploaded_files = []
        
        for file in files:
            if file.filename:
                try:
                    # Sanitize filename
                    filename = os.path.basename(file.filename)
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    
                    # Check available space
                    try:
                        total, used, free = os.statvfs(UPLOAD_FOLDER)[0:6:2]
                        if free * total < file.content_length:
                            return 'Not enough disk space', 507
                    except AttributeError:
                        # statvfs not available on Windows
                        pass
                    
                    file.save(file_path)
                    
                    file_size = os.path.getsize(file_path)
                    readable_size = humanize.naturalsize(file_size)
                    
                    logger.info(f"File uploaded successfully: {filename} ({readable_size})")
                    uploaded_files.append(filename)
                    
                    show_notification(
                        "File Received",
                        f"Name: {filename}\nSize: {readable_size}"
                    )
                except Exception as e:
                    logger.error(f"Error saving file {file.filename}: {str(e)}")
                    return f'Error saving file: {str(e)}', 500
        
        return f'Successfully uploaded {len(uploaded_files)} files', 200
    
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return f'Upload error: {str(e)}', 500

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        logger.info(f"Local IP address: {ip}")
        return ip
    except Exception as e:
        logger.warning(f"Failed to get local IP: {str(e)}, using localhost")
        return "127.0.0.1"

def generate_qr_code(url):
    """Generate QR code for the given URL"""
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Ensure static directory exists
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
        os.makedirs(static_dir, exist_ok=True)
        
        qr_path = os.path.join(static_dir, 'qr_code.png')
        
        # Save with error handling
        try:
            qr_image.save(qr_path)
        except Exception as e:
            logger.error(f"Failed to save QR code image: {str(e)}")
            # Try alternative location if static directory is not writable
            qr_path = os.path.join(UPLOAD_FOLDER, 'qr_code.png')
            qr_image.save(qr_path)
            
        logger.info(f"QR code generated and saved at: {qr_path}")
        return qr_path
    except Exception as e:
        logger.error(f"Failed to generate QR code: {str(e)}")
        raise

class App(ctk.CTk):
    def __init__(self):
        try:
            super().__init__()
            self.title("WiFi File Transfer")
            self.geometry("400x600")
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            # Initialize logo manager
            self.logo_manager = LogoManager()
            
            # Set window icon
            icon_path = self.logo_manager.get_icon_path()
            if icon_path:
                self.after(200, lambda: self.iconbitmap(icon_path))
                logger.debug(f"Window icon set successfully: {icon_path}")
            
            # Load logo image for header
            self.header_logo = self.logo_manager.get_logo_image('large')
            
            self._setup_ui()
            logger.info("Application UI initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize application window: {str(e)}")
            raise

    def _create_logo_label(self):
        """Create the logo label with proper error handling"""
        try:
            self.logo_label = ctk.CTkLabel(
                self,
                text="",
                image=self.header_logo
            )
            self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 0))
            
        except Exception as e:
            logger.error(f"Failed to create logo label: {str(e)}")
            # Create a minimal label as last resort
            self.logo_label = ctk.CTkLabel(
                self,
                text="WiFi File Transfer",
                font=("Arial", 20, "bold")
            )
            self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 0))

    def _setup_ui(self):
        try:
            # Configure grid with proper weights
            self.grid_columnconfigure(0, weight=1)
            for i in range(5):  # Adjust based on number of rows
                self.grid_rowconfigure(i, weight=1)

            # Create UI elements
            self._create_logo_label()
            self._create_main_frame()
            self._create_status_labels()
            self._create_buttons()
            
            # Initialize server state
            self.server_thread = None
            self.is_server_running = False
            
        except Exception as e:
            logger.error(f"Failed to setup UI: {str(e)}")
            raise

    def _create_main_frame(self):
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

    def _create_status_labels(self):
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="Server Status: Not Running",
            font=("Arial", 14)
        )
        self.status_label.grid(row=0, column=0, padx=20, pady=10)

        self.ip_label = ctk.CTkLabel(
            self.main_frame,
            text="",
            font=("Arial", 14)
        )
        self.ip_label.grid(row=1, column=0, padx=20, pady=10)

    def _create_buttons(self):
        self.start_button = ctk.CTkButton(
            self.main_frame,
            text="Start Server",
            command=self.toggle_server
        )
        self.start_button.grid(row=2, column=0, padx=20, pady=10)

        self.folder_button = ctk.CTkButton(
            self.main_frame,
            text="Open Downloads Folder",
            command=self.open_folder
        )
        self.folder_button.grid(row=3, column=0, padx=20, pady=10)

        self.qr_label = ctk.CTkLabel(
            self.main_frame,
            text="Scan QR Code to Upload Files",
            font=("Arial", 14)
        )
        self.qr_label.grid(row=4, column=0, padx=20, pady=10)

    def toggle_server(self):
        if not self.is_server_running:
            try:
                self.server_thread = ServerThread(server)
                self.server_thread.start()
                self.is_server_running = True
                
                ip_address = get_local_ip()
                url = f"http://{ip_address}:{self.server_thread.port}"
                self.status_label.configure(text="Server Status: Running")
                self.ip_label.configure(text=f"Access URL: {url}")
                self.start_button.configure(text="Stop Server")
                
                qr_path = generate_qr_code(url)
                self.display_qr_code(qr_path)
                
                logger.info(f"Server started successfully at {url}")
                
            except Exception as e:
                logger.error(f"Failed to start server: {str(e)}")
                messagebox.showerror("Error", f"Failed to start server: {str(e)}")
                self.is_server_running = False
        else:
            try:
                if self.server_thread:
                    self.start_button.configure(state="disabled", text="Stopping...")
                    self.server_thread.shutdown()
                    self.after(1000, self._reset_server_state)
                    logger.info("Server shutdown initiated")
            except Exception as e:
                logger.error(f"Failed to stop server: {str(e)}")
                messagebox.showerror("Error", f"Failed to stop server: {str(e)}")
                self.start_button.configure(state="normal", text="Stop Server")

    def _reset_server_state(self):
        """Reset the UI state after server shutdown"""
        try:
            self.server_thread = None
            self.is_server_running = False
            self.status_label.configure(text="Server Status: Not Running")
            self.ip_label.configure(text="")
            self.start_button.configure(state="normal", text="Start Server")
            
            # Clear QR code display
            if hasattr(self, 'qr_display'):
                self.qr_display.destroy()
                delattr(self, 'qr_display')
            
            logger.info("Server state reset successfully")
        except Exception as e:
            logger.error(f"Error resetting server state: {str(e)}")
            self.start_button.configure(state="normal", text="Start Server")

    def open_folder(self):
        try:
            os.startfile(UPLOAD_FOLDER)
            logger.info(f"Opened uploads folder: {UPLOAD_FOLDER}")
        except Exception as e:
            logger.error(f"Failed to open uploads folder: {str(e)}")
            messagebox.showerror("Error", f"Failed to open folder: {str(e)}")

    def display_qr_code(self, qr_path):
        try:
            # Load and resize QR code image
            image = Image.open(qr_path)
            image = image.resize((200, 200))
            image.save(qr_path)
            
            # Create CTkImage for better HighDPI support
            self.qr_image = ctk.CTkImage(
                light_image=Image.open(qr_path),
                dark_image=Image.open(qr_path),
                size=(200, 200)
            )
            
            # Always create a new QR display label
            if hasattr(self, 'qr_display'):
                self.qr_display.destroy()
            
            self.qr_display = ctk.CTkLabel(
                self.main_frame,
                text="",
                image=self.qr_image
            )
            self.qr_display.grid(row=5, column=0, padx=20, pady=10)
            logger.info("QR code displayed successfully")
                
        except Exception as e:
            logger.error(f"Failed to display QR code: {str(e)}")
            messagebox.showerror("Error", f"Failed to display QR code: {str(e)}")

    def on_closing(self):
        """Handle window closing event"""
        try:
            if self.is_server_running:
                if messagebox.askokcancel("Quit", "The server is still running. Do you want to stop it and quit?"):
                    self._complete_shutdown()
            else:
                self._complete_shutdown()
        except Exception as e:
            logger.error(f"Error during application shutdown: {str(e)}")
            self._complete_shutdown()

    def _complete_shutdown(self):
        """Complete shutdown of the application"""
        try:
            if self.server_thread and self.is_server_running:
                logger.info("Stopping server thread...")
                self.server_thread.shutdown()
                self.is_server_running = False
            
            logger.info("Destroying main window...")
            self.quit()
            self.destroy()
            
        except Exception as e:
            logger.error(f"Error during complete shutdown: {str(e)}")
            # Force quit in case of error
            import sys
            sys.exit(1)

if __name__ == '__main__':
    try:
        app = App()
        logger.info("Starting application main loop")
        app.mainloop()
    except Exception as e:
        logger.critical(f"Critical error in main application: {str(e)}")
        raise 