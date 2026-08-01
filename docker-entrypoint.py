#!/usr/bin/env python3
import os
import pwd
import subprocess
import sys

APP_USER = "appuser"
DATA_DIR = "/data"

if os.geteuid() == 0:
    os.makedirs(DATA_DIR, exist_ok=True)
    subprocess.run(["chown", "-R", "appuser:appuser", DATA_DIR], check=True)
    pw = pwd.getpwnam(APP_USER)
    os.setgroups([])
    os.setgid(pw.pw_gid)
    os.setuid(pw.pw_uid)
    os.environ["HOME"] = pw.pw_dir

os.execvp(sys.argv[1], sys.argv[1:])
