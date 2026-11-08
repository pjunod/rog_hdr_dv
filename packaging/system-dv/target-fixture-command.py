#!/usr/bin/env python3
"""Send one atomic command to the explicitly loaded owned headless test module."""
import argparse,json,os,pathlib,stat,time
p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('command',choices=['A','B','ABA','D','E','N']);a=p.parse_args()
f=pathlib.Path(a.runtime)/'physical-target-control';s=f.stat()
assert stat.S_ISFIFO(s.st_mode) and s.st_uid==os.getuid(),'not an owned fixture FIFO'
fd=os.open(f,os.O_WRONLY|os.O_NONBLOCK)
try:assert os.write(fd,(a.command+'\n').encode())==len(a.command)+1
finally:os.close(fd)
print(json.dumps({'command':a.command,'monotonic_ns':time.monotonic_ns(),'fifo':str(f),'acknowledgment':'observe compositor PROFILE/ENABLED log and client feedback; this only confirms command delivery'}))
