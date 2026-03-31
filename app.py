import sys
import os

# Add the root directory to path so imports work correctly
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import uvicorn
from backend.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
