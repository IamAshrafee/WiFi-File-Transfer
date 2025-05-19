# WiFi File Transfer

A modern and user-friendly application that enables quick file transfers between devices over WiFi. Perfect for moving files from your phone to your PC without cables or complicated setup.

## 🌟 Features

- **Easy Setup**: Just start the server and scan the QR code
- **Modern Interface**: Clean GUI built with CustomTkinter
- **Drag & Drop**: Simple drag and drop file upload interface
- **Multi-Device**: Works with any device that has a web browser
- **QR Code Access**: Quick connection using QR code scanning
- **Progress Tracking**: Visual feedback for file uploads
- **Responsive Design**: Works on all screen sizes
- **Multiple Files**: Upload multiple files at once
- **Desktop Notifications**: Get notified when files are received
- **Automatic Directory Creation**: No manual setup needed

## 🚀 Quick Start

### Prerequisites

- Python 3.7 or higher
- All devices must be connected to the same WiFi network

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/WiFi-File-Transfer.git
   cd WiFi-File-Transfer
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Usage

1. Start the application:

   ```bash
   python run.py
   ```

2. In the GUI:

   - Click "Start Server"
   - Note the displayed IP address or scan the QR code
   - The uploads folder will be created automatically

3. On other devices:

   - Scan the QR code with your phone's camera
   - Or enter the displayed URL in any web browser
   - Select files to upload
   - Click "Upload Files"

4. Access transferred files:
   - Click "Open Downloads Folder" in the GUI
   - Or check the `uploads` folder in the project directory

## 📁 Project Structure

```
WiFi-File-Transfer/
├── src/                # Source code
│   ├── __init__.py
│   └── wifi_transfer.py
├── static/            # Static files
│   ├── css/
│   │   └── style.css
│   └── images/        # Application images and logo
│       └── png/       # Application icons
├── templates/         # HTML templates
│   └── index.html
├── scripts/          # Utility scripts
│   └── resize_logo.py
├── uploads/          # Default upload directory
├── logs/            # Application logs
├── requirements.txt  # Python dependencies
├── run.py           # Application runner
└── README.md        # Documentation
```

## 🔒 Security Note

This application creates a local server accessible to all devices on your network. For security:

- Only use it on trusted networks
- Stop the server when not in use
- Don't expose the server to the internet
- Be cautious with sensitive files

## 🛠️ Development

Want to contribute? Great! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 🐛 Known Issues

- Server must be manually stopped before closing the application
- Large files might take longer to upload without progress indication
- Only works within the same network

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📧 Contact

If you have any questions or suggestions, please open an issue in the GitHub repository.
