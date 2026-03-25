import os
import json
import asyncio
import subprocess
import sys
import threading
import time

# Global variable to track bot process
bot_process = None

def start_bot():
    """Start the Discord bot in a separate process"""
    global bot_process
    try:
        if bot_process is None or bot_process.poll() is not None:
            # Start bot process
            bot_process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd="/app"
            )
            return True
    except Exception as e:
        print(f"Error starting bot: {e}")
    return False

def handler(request, context):
    """Vercel API handler"""
    global bot_process
    
    # Try to start bot on first request
    started = start_bot()
    
    response = {
        "status": "ok",
        "bot_started": started,
        "bot_running": bot_process is not None and bot_process.poll() is None,
        "message": "Bot startup requested"
    }
    
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(response)
    }
