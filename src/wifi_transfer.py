import os
import socket
import threading
import webbrowser
import qrcode
from PIL import Image
from flask import Flask, request, render_template, url_for
from flask_cors import CORS
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import requests
from werkzeug.serving import make_server

# Initialize Flask app
server = Flask(__name__, 
              template_folder='../templates',
              static_folder='../static')
CORS(server)

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class ServerThread(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self, daemon=True)
        self.srv = make_server('0.0.0.0', 5000, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.srv.serve_forever()

    def shutdown(self):
        shutdown_thread = threading.Thread(target=self._shutdown)
        shutdown_thread.daemon = True
        shutdown_thread.start()

    def _shutdown(self):
        try:
            requests.get('http://localhost:5000/')  # Trigger a request to unblock serve_forever
        except:
            pass
        self.srv.shutdown()
        self.srv.server_close()

@server.route('/')
def index():
    return render_template('index.html')

@server.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400
    
    files = request.files.getlist('file')
    
    for file in files:
        if file.filename:
            file.save(os.path.join(UPLOAD_FOLDER, file.filename))
    
    return 'Files uploaded successfully', 200

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def generate_qr_code(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white")
    qr_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'qr_code.png')
    qr_image.save(qr_path)
    return qr_path

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("WiFi File Transfer")
        self.geometry("400x500")

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Status label
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="Server Status: Not Running",
            font=("Arial", 14)
        )
        self.status_label.grid(row=0, column=0, padx=20, pady=10)

        # IP Address label
        self.ip_label = ctk.CTkLabel(
            self.main_frame,
            text="",
            font=("Arial", 14)
        )
        self.ip_label.grid(row=1, column=0, padx=20, pady=10)

        # Start Server button
        self.start_button = ctk.CTkButton(
            self.main_frame,
            text="Start Server",
            command=self.toggle_server
        )
        self.start_button.grid(row=2, column=0, padx=20, pady=10)

        # Open Folder button
        self.folder_button = ctk.CTkButton(
            self.main_frame,
            text="Open Downloads Folder",
            command=self.open_folder
        )
        self.folder_button.grid(row=3, column=0, padx=20, pady=10)

        # QR Code label
        self.qr_label = ctk.CTkLabel(
            self.main_frame,
            text="Scan QR Code to Upload Files",
            font=("Arial", 14)
        )
        self.qr_label.grid(row=4, column=0, padx=20, pady=10)

        self.server_running = False
        self.server_thread = None

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
                
                # Generate and display QR code
                qr_path = generate_qr_code(url)
                self.display_qr_code(qr_path)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start server: {str(e)}")
                self.server_running = False
        else:
            try:
                if self.server_thread:
                    self.start_button.configure(state="disabled", text="Stopping...")
                    self.server_thread.shutdown()
                    self.after(1000, self._complete_shutdown)  # Complete shutdown after 1 second
            except Exception as e:
                messagebox.showerror("Error", f"Failed to stop server: {str(e)}")
                self.start_button.configure(state="normal", text="Stop Server")

    def open_folder(self):
        os.startfile(UPLOAD_FOLDER)

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
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to display QR code: {str(e)}")

    def _complete_shutdown(self):
        self.server_thread = None
        self.server_running = False
        self.status_label.configure(text="Server Status: Not Running")
        self.ip_label.configure(text="")
        self.start_button.configure(state="normal", text="Start Server")
        if hasattr(self, 'qr_display'):
            self.qr_display.destroy()  # Destroy instead of grid_remove

    def on_closing(self):
        if self.server_running:
            try:
                if self.server_thread:
                    self.server_thread.shutdown()
            except:
                pass
        self.quit()

if __name__ == '__main__':
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop() 