"""Real Windows owned-process cleanup, including abrupt supervisor death."""
import os,sys,subprocess,time,ctypes
from pathlib import Path
import pytest
from commerce_hub.infrastructure.windows_job import Job

pytestmark=pytest.mark.skipif(os.name!='nt',reason='Windows native process ownership test')

def test_duplicate_launcher_lock_does_not_read_a_mandatory_locked_byte(tmp_path,monkeypatch):
    import tools.local_platform as launcher
    monkeypatch.setattr(launcher,'PRIVATE',tmp_path)
    owner=launcher.scope_lock()
    try:assert owner is not None and launcher.scope_lock() is None
    finally:owner.close()
    following=launcher.scope_lock()
    assert following is not None
    following.close()

def test_job_close_only_kills_its_own_children():
    unrelated=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],creationflags=subprocess.CREATE_NO_WINDOW)
    job=Job()
    try:
        managed=job.spawn([sys.executable,'-c','import time;time.sleep(60)'])
        assert managed.poll() is None
        job.close();assert managed.poll() is not None and unrelated.poll() is None
    finally:job.close();unrelated.terminate();unrelated.wait(timeout=5)

def test_abrupt_supervisor_death_closes_job_and_kills_owned_service(tmp_path):
    output=tmp_path/'owned-pid.txt'
    code="from commerce_hub.infrastructure.windows_job import Job;from pathlib import Path;import sys,time;j=Job();p=j.spawn([sys.executable,'-c','import time;time.sleep(60)']);Path(sys.argv[1]).write_text(str(p.pid));time.sleep(60)"
    parent=subprocess.Popen([sys.executable,'-c',code,str(output)],creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        until=time.monotonic()+10
        while not output.exists() and time.monotonic()<until:time.sleep(.05)
        assert output.exists();pid=int(output.read_text())
        from ctypes import wintypes as w
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
        kernel.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];kernel.CloseHandle.argtypes=[w.HANDLE]
        handle=kernel.OpenProcess(0x100000,False,pid);assert handle
        try:parent.terminate();parent.wait(timeout=5);assert kernel.WaitForSingleObject(handle,5000)==0
        finally:kernel.CloseHandle(handle)
    finally:
        if parent.poll() is None:parent.terminate();parent.wait(timeout=5)
