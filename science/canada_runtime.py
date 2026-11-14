"""Process-local Windows memory evidence; no claim about OS/worker/GPU totals."""
import ctypes
import os

def memory():
    if os.name!='nt':return {'scope':'not measured on this platform'}
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
    c=Counters();c.cb=ctypes.sizeof(c);get=ctypes.windll.kernel32.GetCurrentProcess;get.restype=wintypes.HANDLE
    api=ctypes.windll.psapi.GetProcessMemoryInfo;api.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    if not api(get(),ctypes.byref(c),c.cb):return {'scope':'Windows process memory unavailable'}
    return {'peak_working_set_bytes':c.PeakWorkingSetSize,'working_set_bytes':c.WorkingSetSize,'scope':'this Python process; OS-reported peak working set, excluding other processes / disk cache'}
