import time
import subprocess

sleepMinutes = 5

while True:
    subprocess.Popen("python ftpSync.py").communicate()
    print("waiting for %d minutes..."%sleepMinutes)
    time.sleep(60*sleepMinutes)
