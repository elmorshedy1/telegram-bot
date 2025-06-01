import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import os
import sys
import subprocess

class TelegramBotService(win32serviceutil.ServiceFramework):
    _svc_name_ = "TelegramBotService"
    _svc_display_name_ = "Telegram Bot Service"
    _svc_description_ = "Service to keep Telegram bot running"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcDoRun(self):
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        self.main()

    def main(self):
        # Start the bot in a separate process
        process = subprocess.Popen(
            [sys.executable, "bot.py"],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        
        # Wait for stop event
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
        
        # Terminate the bot process when service stops
        process.terminate()
        process.wait()

if __name__ == '__main__':
    if len(sys.argv) == 1:
        try:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(TelegramBotService)
            servicemanager.StartServiceCtrlDispatcher()
        except win32service.error as details:
            print(details)
