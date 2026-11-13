"""Own a Windows Job: only assigned child processes die when this handle closes."""
import ctypes,os,subprocess
from ctypes import wintypes as w

class Job:
    def __init__(self):
        if os.name!='nt':raise RuntimeError('WINDOWS_REQUIRED')
        class Basic(ctypes.Structure):
            _fields_=[('processTime',ctypes.c_int64),('jobTime',ctypes.c_int64),('flags',w.DWORD),('minWorking',ctypes.c_size_t),('maxWorking',ctypes.c_size_t),('activeLimit',w.DWORD),('affinity',ctypes.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
        class IO(ctypes.Structure):_fields_=[(n,ctypes.c_uint64) for n in ['readOps','writeOps','otherOps','readBytes','writeBytes','otherBytes']]
        class Extended(ctypes.Structure):_fields_=[('basic',Basic),('io',IO),('processMemory',ctypes.c_size_t),('jobMemory',ctypes.c_size_t),('peakProcess',ctypes.c_size_t),('peakJob',ctypes.c_size_t)]
        self.api=ctypes.WinDLL('kernel32',use_last_error=True)
        self.api.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR];self.api.CreateJobObjectW.restype=w.HANDLE
        self.api.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD]
        self.api.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]
        self.api.CloseHandle.argtypes=[w.HANDLE]
        self.handle=self.api.CreateJobObjectW(None,None)
        info=Extended();info.basic.flags=0x2000 # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.handle or not self.api.SetInformationJobObject(self.handle,9,ctypes.byref(info),ctypes.sizeof(info)):
            self.close();raise RuntimeError('WINDOWS_JOB_UNAVAILABLE')
        self.children=[]
    def spawn(self,args,**kwargs):
        child=subprocess.Popen(args,creationflags=subprocess.CREATE_NO_WINDOW,**kwargs)
        if not self.api.AssignProcessToJobObject(self.handle,w.HANDLE(int(child._handle))):
            child.terminate();child.wait(timeout=5);raise RuntimeError('WINDOWS_JOB_ASSIGN_FAILED')
        self.children.append(child);return child
    def close(self):
        if getattr(self,'handle',None):self.api.CloseHandle(self.handle);self.handle=None
        for child in getattr(self,'children',[]):
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
