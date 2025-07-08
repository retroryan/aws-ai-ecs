#!/usr/bin/env python3
import subprocess
import sys
import time

# Change to weather_agent directory and run the multi-turn demo
proc = subprocess.Popen(
    ["python", "weather_agent/chatbot.py", "--multi-turn-demo"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    universal_newlines=True,
    bufsize=1
)

start_time = time.time()
timeout = 120  # 2 minutes

try:
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        print(line, end='')
        sys.stdout.flush()
        
        # Check timeout
        if time.time() - start_time > timeout:
            print("\n\n[TIMEOUT REACHED - Terminating process]")
            proc.terminate()
            break
            
except KeyboardInterrupt:
    print("\n\n[Process interrupted by user]")
    proc.terminate()

# Wait for process to finish
proc.wait()
print(f"\n[Process exited with code: {proc.returncode}]")