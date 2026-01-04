"""
Main entry point - Chọn GUI hoặc Flask
"""

import sys
import os

# Entry point: khi chạy trực tiếp file này (python app.py), đoạn code dưới sẽ thực thi
if __name__ == '__main__':
    # Kiểm tra argument để chọn mode
    if len(sys.argv) > 1 and sys.argv[1] == '--web':
        # Chạy Flask web app
        from web.app import app
        print("[WEB] Starting Flask web server on http://0.0.0.0:5000")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        # Mặc định chạy GUI
        from modules.gui import GUIController
        print("[GUI] Starting GUI application...")
        GUIController().run()


