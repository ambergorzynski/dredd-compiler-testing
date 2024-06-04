import os
import signal
import subprocess

from pathlib import Path
from typing import AnyStr, Dict, List, Optional


class ProcessResult:
    def __init__(self, returncode: int, stdout: bytes, stderr: bytes):
        self.returncode: int = returncode
        self.stdout: bytes = stdout
        self.stderr: bytes = stderr


def run_process_with_timeout(cmd: List[str],
                             timeout_seconds: int,
                             env: Optional[Dict[AnyStr, AnyStr]] = None,
                             cwd: Path = None) -> Optional[ProcessResult]:
    process = None
    try:
        process = subprocess.run(cmd,
                                   start_new_session=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   env=env,
                                   cwd=cwd,
                                   timeout=timeout_seconds)
        return ProcessResult(returncode=process.returncode, stdout=process.stdout, stderr=process.stderr)
    except subprocess.TimeoutExpired:
        return None
