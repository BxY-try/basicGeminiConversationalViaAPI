# Python Backend Setup Troubleshooting

This guide addresses common issues when setting up the Python backend and provides solutions for different operating systems.

## Common Issues and Solutions

### 1. "python" command not found

**Problem**: 
```
Command 'python' not found
```

**Solution**:
On many Linux distributions and some other systems, you need to use `python3` instead of `python`:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify Python version
python --version
```

If `python` still doesn't work after activation, you can explicitly use `python3`:
```bash
python3 --version
python3 -m pip install -r requirements.txt
```

### 2. "venv/bin/activate: No such file or directory"

**Problem**: 
```
bash: venv/bin/activate: No such file or directory
```

**Solution**:
This error occurs when the virtual environment wasn't created successfully. Try these steps:

1. **Remove any existing venv directory**:
   ```bash
   rm -rf venv
   ```

2. **Create the virtual environment using python3**:
   ```bash
   python3 -m venv venv
   ```

3. **Activate the virtual environment**:
   ```bash
   source venv/bin/activate
   ```

### 3. Permission denied when installing packages

**Problem**: 
```
PermissionError: [Errno 13] Permission denied
```

**Solution**:
Never use `sudo` with `pip`. Instead, always use a virtual environment:

1. Make sure you're in the virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. Then install packages:
   ```bash
   pip install -r requirements.txt
   ```

## System-Specific Instructions

### Ubuntu/Debian Linux

1. Install Python 3 and pip if not already installed:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv
   ```

2. Create and activate virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### CentOS/RHEL/Fedora Linux

1. Install Python 3 and pip:
   ```bash
   sudo yum install python3 python3-pip
   # Or on newer versions:
   sudo dnf install python3 python3-pip
   ```

2. Create and activate virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

### macOS

1. Install Python 3 using Homebrew (if not already installed):
   ```bash
   brew install python3
   ```

2. Create and activate virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

### Windows

1. Install Python 3 from the official website if not already installed

2. Create and activate virtual environment:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

## Verifying Your Setup

After following the setup instructions, verify your environment:

1. **Check Python version**:
   ```bash
   python --version
   # or
   python3 --version
   ```

2. **Check pip version**:
   ```bash
   pip --version
   ```

3. **Verify virtual environment**:
   ```bash
   which python
   # On Windows:
   where python
   ```

4. **List installed packages**:
   ```bash
   pip list
   ```

## Installing System Dependencies

Some packages require system-level dependencies. For audio processing, you may need to install ffmpeg:

### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install ffmpeg
```

### CentOS/RHEL/Fedora:
```bash
sudo yum install ffmpeg
# Or on newer versions:
sudo dnf install ffmpeg
```

### macOS:
```bash
brew install ffmpeg
```

### Windows:
Download and install ffmpeg from https://ffmpeg.org/download.html

## Environment Variables

Create a `.env` file in the `python-backend` directory with your Google API key:

```
GOOGLE_API_KEY=your_actual_google_api_key_here
```

Make sure to replace `your_actual_google_api_key_here` with your real Google API key.

## Testing Google Generative AI SDK

To verify that the Google Generative AI SDK is properly installed and configured, run the test script:

```bash
python test_google_genai.py
```

This script will:
1. Test that the required modules can be imported
2. Verify that the Google Generative AI client can be initialized
3. Check that your API key works by listing available models

If any of these tests fail, check:
- That you have installed all required dependencies with `pip install -r requirements.txt`
- That your `.env` file contains a valid Google API key
- That you have an active internet connection

## Running the Application

After successful setup:

1. Make sure your virtual environment is activated:
   ```bash
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate     # Windows
   ```

2. Run the application:
   ```bash
   python main.py
   ```

The server should start on `http://localhost:8000`.

## Common pip Issues

### Upgrading pip
If you encounter issues with pip, try upgrading it:
```bash
python -m pip install --upgrade pip
```

### Installing with --user flag
If you still have permission issues:
```bash
pip install --user -r requirements.txt
```

However, using a virtual environment is still the recommended approach.

## Testing the API

After starting the server, you can test the endpoints:

1. **Test health check**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Test text generation**:
   ```bash
   curl -X POST "http://localhost:8000/api/generateText" \
        -H "Content-Type: application/json" \
        -d '{"text": "Hello, how are you?"}'
   ```

If you continue to experience issues, please share the exact error messages and your operating system information for more specific help.