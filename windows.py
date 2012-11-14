#! /usr/bin/env python

# Definitions

# Seconds after which system is considered idle
IDLE_STOP_WORK = 60

import time, os
import math

from datetime import datetime

# SQL related stuff

from sqlalchemy.orm import sessionmaker
from models import *

class WindowTracker:
    is_win = os.name == 'nt'

    def __init__(self):
        if self.is_win:
            import win32api, win32gui
            self.win32api = win32api
            self.win32gui = win32gui
            self.get_win_name = self._win_get_win_name
            self.get_idle_time = self._win_get_idle_time
            self._win_last_known_win = 0
            self._win_last_known_win_name = ""
            self._win_last_known_win_class = ""
        else:
            from ewmh import EWMH
            self.ewmh = EWMH()
            self.get_win_name = self._posix_get_win_name
            self.get_idle_time = self._posix_get_idle_time

    def _win_get_win_name(self):
        cur_window = self.win32gui.GetForegroundWindow()
        if cur_window == 0:
            cur_window = self._win_last_known_win
            cur_name = self._win_last_known_win_name
            cur_class = self._win_last_known_win_class
            cur_class = self.win32gui.GetClassName(cur_window)
        else:
            cur_name = self.win32gui.GetWindowText(cur_window)
            cur_class = self.win32gui.GetClassName(cur_window)
        self._win_last_known_win = cur_window
        self._win_last_known_win_class = cur_class
        self._win_last_known_win_name = cur_name
        
        return ((cur_class, cur_class), cur_name)
    
    def _win_get_idle_time(self):
        now = self.win32api.GetTickCount()
        last_activity = self.win32api.GetLastInputInfo()
        return round((now - last_activity)/1000.0)
        
    def _posix_get_win_name(self):        
        cur_window = self.ewmh.getActiveWindow()
        cur_class = None
        while cur_class is None:
            cur_name = cur_window.get_wm_name()
            cur_class = cur_window.get_wm_class()
            if cur_class is None:
                cur_window = cur_window.query_tree().parent
        return (cur_class, cur_name)
        
    def _posix_get_idle_time(self):
        import ctypes
        class XScreenSaverInfo( ctypes.Structure):
          """ typedef struct { ... } XScreenSaverInfo; """
          _fields_ = [('window',      ctypes.c_ulong), # screen saver window
                      ('state',       ctypes.c_int),   # off,on,disabled
                      ('kind',        ctypes.c_int),   # blanked,internal,external
                      ('since',       ctypes.c_ulong), # milliseconds
                      ('idle',        ctypes.c_ulong), # milliseconds
                      ('event_mask',  ctypes.c_ulong)] # events

        xlib = ctypes.cdll.LoadLibrary('libX11.so.6')
        display = xlib.XOpenDisplay(os.environ['DISPLAY'])
        xss = ctypes.cdll.LoadLibrary('libXss.so.1')
        xss.XScreenSaverAllocInfo.restype = ctypes.POINTER(XScreenSaverInfo)
        xssinfo = xss.XScreenSaverAllocInfo()
        xss.XScreenSaverQueryInfo(display, xlib.XDefaultRootWindow(display), xssinfo)
        idle = int(round(xssinfo.contents.idle / 1000.0))
        xlib.XCloseDisplay(display)

        return idle

def main():
    Session = sessionmaker(bind = eng)
    sess = Session()
    def add_record(win_class, win_name, seconds_on_window):
        ww = WorkOnWindow(win_class, win_name, seconds_on_window)
        sess.add(ww)
        sess.commit()
        sess.close()
    
    wt = WindowTracker()
    (pre_win_class, pre_win_name) = ('', '')
    seconds_on_window = 0
    
    while 1:
        (cur_class,cur_name) = wt.get_win_name()

        # First round, set variables
        if pre_win_class == '' and pre_win_name == '':
            (pre_win_class, pre_win_name) = (cur_class,cur_name)
        
        if wt.get_idle_time() <= IDLE_STOP_WORK:
            idled = False
            if pre_win_class == cur_class and pre_win_name == cur_name:
                seconds_on_window = seconds_on_window + 3
            else:
                add_record(pre_win_class, pre_win_name, seconds_on_window)
                seconds_on_window = 3
            (pre_win_class, pre_win_name) = (cur_class,cur_name)
        else:
            if not idled:
                add_record(pre_win_class, pre_win_name, seconds_on_window - IDLE_STOP_WORK)
                idled = True
                pre_win_class = ('system-idle', 'System-Idle')
                pre_win_name = "System idle"
            else:
                seconds_on_window = wt.get_idle_time()
                
        time.sleep(3)

if __name__ == "__main__":
    main()
