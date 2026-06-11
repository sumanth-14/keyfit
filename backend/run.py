"""
Start the backend on Windows with ProactorEventLoop so asyncio subprocesses work.
Usage: python run.py
"""
import asyncio
import sys

# Windows default (SelectorEventLoop) does not support asyncio subprocesses.
# pdflatex is invoked via asyncio.create_subprocess_exec, so ProactorEventLoop is required.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
