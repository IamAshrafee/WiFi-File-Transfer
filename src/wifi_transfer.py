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
try:
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    logger.info(f"Upload folder configured at: {UPLOAD_FOLDER}")
except Exception as e:
    logger.error(f"Failed to create upload folder: {str(e)}")
    raise

def show_notification(title, message):
    """Show a Windows notification with application icon"""
    try:
        # Get the base directory (src's parent directory)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, 'static', 'images', 'png', 'logo.ico')
        
        logger.debug(f"Notification icon path: {icon_path}")
        
        # Verify the icon exists
        if not os.path.exists(icon_path):
            logger.warning(f"Notification icon not found at: {icon_path}")
            # Try the PNG version as fallback
            png_path = os.path.join(base_dir, 'static', 'images', 'png', 'logo-normal.png')
            if os.path.exists(png_path):
                logger.info("Using PNG as fallback icon")
                icon_path = png_path
            else:
                logger.warning("No suitable icon file found")
                icon_path = None
        
        # Show the notification
        toaster.show_toast(
            title,
            message,
            icon_path=icon_path,
            duration=5,
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
                duration=5,
                threaded=True
            )
            logger.info("Fallback notification shown without icon")
        except Exception as e:
            logger.error(f"Failed to show fallback notification: {str(e)}")

class ServerThread(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self, daemon=True)
        try:
            self.srv = make_server('0.0.0.0', 5000, app)
            self.ctx = app.app_context()
            self.ctx.push()
            logger.info("Server thread initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize server thread: {str(e)}")
            raise

    def run(self):
        try:
            logger.info("Starting server...")
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
            requests.get('http://localhost:5000/')
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
                    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
                    file.save(file_path)
                    
                    file_size = os.path.getsize(file_path)
                    readable_size = humanize.naturalsize(file_size)
                    
                    logger.info(f"File uploaded successfully: {file.filename} ({readable_size})")
                    uploaded_files.append(file.filename)
                    
                    show_notification(
                        "File Received",
                        f"Name: {file.filename}\nSize: {readable_size}"
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
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        qr_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'qr_code.png')
        qr_image.save(qr_path)
        
        logger.info(f"QR code generated for URL: {url}")
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
            
            # Set window icon
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                   'static', 'images', 'png', 'logo.ico')
            if os.path.exists(icon_path):
                self.after(200, lambda: self.iconbitmap(icon_path))
                logger.debug("Window icon set successfully")
            else:
                logger.warning(f"Window icon not found at: {icon_path}")

            self._setup_ui()
            logger.info("Application UI initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize application window: {str(e)}")
            raise

    def _setup_ui(self):
        try:
            # Configure grid
            self.grid_columnconfigure(0, weight=1)
            self.grid_rowconfigure(1, weight=1)

            # Load and display logo
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                   'static', 'images', 'png', 'logo_large.png')
            
            if not os.path.exists(logo_path):
                logger.warning(f"Logo file not found at: {logo_path}")
                raise FileNotFoundError(f"Logo file not found: {logo_path}")
            
            self.logo_image = ctk.CTkImage(
                light_image=Image.open(logo_path),
                dark_image=Image.open(logo_path),
                size=(100, 100)
            )
            
            # Create UI elements
            self._create_logo_label()
            self._create_main_frame()
            self._create_status_labels()
            self._create_buttons()
            
            self.server_running = False
            self.server_thread = None
            
        except Exception as e:
            logger.error(f"Error setting up UI: {str(e)}")
            raise

    def _create_logo_label(self):
        self.logo_label = ctk.CTkLabel(
            self,
            text="",
            image=self.logo_image
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 0))

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
        if not self.server_running:
            try:
                self.server_thread = ServerThread(server)
                self.server_thread.start()
                self.server_running = True
                
                ip_address = get_local_ip()
                url = f"http://{ip_address}:5000"
                self.status_label.configure(text="Server Status: Running")
                self.ip_label.configure(text=f"Access URL: {url}")
                self.start_button.configure(text="Stop Server")
                
                qr_path = generate_qr_code(url)
                self.display_qr_code(qr_path)
                
                logger.info(f"Server started successfully at {url}")
                
            except Exception as e:
                logger.error(f"Failed to start server: {str(e)}")
                messagebox.showerror("Error", f"Failed to start server: {str(e)}")
                self.server_running = False
        else:
            try:
                if self.server_thread:
                    self.start_button.configure(state="disabled", text="Stopping...")
                    self.server_thread.shutdown()
                    self.after(1000, self._complete_shutdown)
                    logger.info("Server shutdown initiated")
            except Exception as e:
                logger.error(f"Failed to stop server: {str(e)}")
                messagebox.showerror("Error", f"Failed to stop server: {str(e)}")
                self.start_button.configure(state="normal", text="Stop Server")

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

    def _complete_shutdown(self):
        try:
            self.server_thread = None
            self.server_running = False
            self.status_label.configure(text="Server Status: Not Running")
            self.ip_label.configure(text="")
            self.start_button.configure(state="normal", text="Start Server")
            if hasattr(self, 'qr_display'):
                self.qr_display.destroy()
            logger.info("Server shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown completion: {str(e)}")

    def on_closing(self):
        try:
            if self.server_running and self.server_thread:
                logger.info("Shutting down server before closing application")
                self.server_thread.shutdown()
            self.quit()
            logger.info("Application closed successfully")
        except Exception as e:
            logger.error(f"Error during application shutdown: {str(e)}")
            self.quit()

if __name__ == '__main__':
    try:
        app = App()
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        logger.info("Starting application main loop")
        app.mainloop()
    except Exception as e:
        logger.critical(f"Critical error in main application: {str(e)}")
        raise 