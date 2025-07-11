# Contemplative AI - Setup Guide

This project has both Python (FastAPI backend) and React (frontend) components.

## Prerequisites

### Python Setup
1. **Python 3.8+** should be installed on your system
2. **ffmpeg** must be installed on your system. This is required for audio/video processing. For Ubuntu/Debian:
   ```bash
   sudo apt-get install ffmpeg
   ```
   For other systems, see: https://ffmpeg.org/download.html
2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Node.js Setup
1. **Install Node.js and npm:**
   ```bash
   # Ubuntu/Debian
   sudo apt install npm
   
   # Or using nvm (recommended for version management)
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
   nvm install node
   nvm use node
   ```

2. **Verify installation:**
   ```bash
   node --version
   npm --version
   ```

## Project Structure

```
contemplative-ai/
├── data/                    # Data files (audio, texts, etc.)
├── notebooks/              # Jupyter notebooks
├── scripts/                # Python scripts
├── web-ui/                 # Simple HTML/CSS/JS version
├── react-app/              # React application (future)
├── venv/                   # Python virtual environment
├── requirements.txt        # Python dependencies
├── package.json           # Node.js dependencies (future)
└── README.md              # Main project documentation
```

## Development

### Python Backend
```bash
# Activate virtual environment
source venv/bin/activate

# Run FastAPI server (when implemented)
uvicorn main:app --reload
```

### React Frontend
```bash
# Navigate to React app directory
cd react-app

# Install dependencies (first time only)
npm install

# Start development server
npm start
```

## Sharing the Repository

When sharing this repository:

1. **Include:** All source code, configuration files, and documentation
2. **Exclude:** `venv/`, `node_modules/`, `data/`, and build artifacts
3. **Document:** Required system dependencies (Python, Node.js, npm)

## Troubleshooting

### Node.js Issues
- If npm commands fail, ensure Node.js is properly installed
- Try using nvm for better version management
- Check that npm is in your PATH

### Python Issues
- Ensure you're in the virtual environment (`source venv/bin/activate`)
- Reinstall requirements if needed: `pip install -r requirements.txt`

### Audio File Issues
- Ensure the audio file exists at `data/audio/voz_kokoro.wav`
- Check file permissions
- Verify the file path in the web UI 