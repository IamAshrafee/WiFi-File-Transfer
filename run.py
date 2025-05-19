import os
import sys

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from wifi_transfer import App

if __name__ == '__main__':
    app = App()
    app.mainloop() 