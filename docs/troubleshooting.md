# ResearchLite — Troubleshooting & Diagnostic Guide

This guide details common issues encountered during development, container execution, and external API queries, along with solutions.

---

## 1. Local Python & Environment Issues

### Issue 1.1: `ModuleNotFoundError: No module named 'app'`
- **Cause**: The current working directory is not the project root, or Python does not have the current folder on `sys.path`.
- **Solution**:
  - Ensure you run commands from the project root (`ResearchHub/`).
  - Use `python -m uvicorn app.main:app --reload` or set `PYTHONPATH=.`.

### Issue 1.2: `uvicorn: command not found`
- **Cause**: The virtual environment is not activated or dependencies are not installed.
- **Solution**:
  ```powershell
  # Windows PowerShell
  .venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```

---

## 2. Port & Network Conflicts

### Issue 2.1: `[Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)`
- **Cause**: Another service or previous Uvicorn instance is occupying port 8000.
- **Solution**:
  - Run on an alternative port:
    ```bash
    uvicorn app.main:app --port 8080
    ```
  - Or find and terminate the occupying process:
    - **Windows**: `netstat -ano | findstr :8000` then `taskkill /PID <PID> /F`
    - **Linux/macOS**: `lsof -i :8000` then `kill -9 <PID>`

---

## 3. External Research API Issues

### Issue 3.1: Wikipedia Returns 403 Forbidden
- **Cause**: Wikipedia blocks HTTP requests that do not specify a valid, descriptive `User-Agent` header.
- **Solution**:
  - `WikipediaService` automatically passes a custom `User-Agent`. If overriding via environment variables, ensure `USER_AGENT` includes contact info as required by Wikipedia's API etiquette policy:
    ```text
    USER_AGENT=ResearchLite/1.0.0 (mailto:student@example.edu)
    ```

### Issue 3.2: Crossref or OpenAlex Request Times Out
- **Cause**: Upstream rate limits or network congestion.
- **Solution**:
  - The microservice handles this gracefully and returns the remaining results with an entry in the `warnings` array.
  - Increase `REQUEST_TIMEOUT_SECONDS=15.0` in `.env` if your local network connection is slow.

---

## 4. Docker Issues

### Issue 4.1: `docker: Error response from daemon: Conflict. The container name is already in use`
- **Cause**: An old container with the same name is still running or stopped.
- **Solution**:
  ```bash
  docker rm -f researchlite-app
  docker run -d --name researchlite-app -p 8000:8000 researchlite:1.0.0
  ```

### Issue 4.2: Healthcheck Shows `unhealthy`
- **Cause**: The container cannot reach `http://localhost:8000/health` within the timeout period.
- **Solution**:
  - Inspect container logs:
    ```bash
    docker logs researchlite-app
    ```
  - Verify that Uvicorn started on `0.0.0.0` (not `127.0.0.1`).
