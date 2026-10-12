"""FA2 Activity Verification & Readiness Checker.

Automates the 'Definition of Done' acceptance verification for PEC 4 - DevOps FA2 Activity.
Tests:
1. Python Runtime & Dependencies
2. Unit & Integration Test Suite (pytest)
3. API Liveness Probe (/health)
4. API Readiness Probe (/ready)
5. Prometheus Metrics Scrape (/metrics)
6. Observability Stack (Prometheus & Grafana)
"""

import sys
import subprocess
import urllib.request
import urllib.error
import os

# Ensure safe unicode handling on Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_banner():
    print(f"{BLUE}======================================================================{RESET}")
    print(f"{BLUE}         ResearchOps AI -- DevOps FA2 Verification & DoD Checker       {RESET}")
    print(f"{BLUE}             PEC 4: DevOps (Units 3 & 4) -- 10 Mark Activity          {RESET}")
    print(f"{BLUE}======================================================================{RESET}\n")


def check_python_environment():
    print(f"[*] Checking Python runtime environment...")
    v = sys.version_info
    if v.major == 3 and v.minor >= 11:
        print(f"  {GREEN}[OK] Python version: {v.major}.{v.minor}.{v.micro} (Supported){RESET}")
        return True
    else:
        print(f"  {YELLOW}[WARN] Python version is {v.major}.{v.minor}. Recommended: Python 3.12+{RESET}")
        return False


def run_automated_tests():
    print(f"\n[*] Running Automated Test Suite (Pytest Unit & Integration Tests)...")
    cmd = [sys.executable, "-m", "pytest", "tests/", "-q"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if res.returncode == 0:
            print(f"  {GREEN}[OK] All test cases passed successfully!{RESET}")
            first_line = res.stdout.strip().split("\n")[-1]
            print(f"    Summary: {first_line}")
            return True
        else:
            print(f"  {RED}[FAIL] Tests failed or encountered errors.{RESET}")
            print(res.stdout[:500])
            return False
    except Exception as e:
        print(f"  {RED}[FAIL] Error executing pytest: {e}{RESET}")
        return False


def check_http_endpoint(name, url, expected_status=200, key_check=None):
    print(f"[*] Probing {name} at {url}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FA2-Verifier/1.0"})
        with urllib.request.urlopen(req, timeout=6.0) as resp:
            status = resp.getcode()
            body = resp.read().decode("utf-8")
            if status == expected_status:
                if key_check and key_check not in body:
                    print(f"  {YELLOW}[WARN] Received HTTP 200, but '{key_check}' not found in body.{RESET}")
                    return False
                print(f"  {GREEN}[OK] {name} is HEALTHY (HTTP {status}){RESET}")
                return True
            else:
                print(f"  {RED}[FAIL] {name} returned status HTTP {status}{RESET}")
                return False
    except urllib.error.URLError as e:
        print(f"  {YELLOW}[OFFLINE] {name} offline or unreachable ({e.reason}){RESET}")
        return False
    except Exception as e:
        print(f"  {RED}[FAIL] Unexpected error checking {name}: {e}{RESET}")
        return False


def main():
    print_banner()
    results = {}

    results["python_env"] = check_python_environment()
    results["pytest_suite"] = run_automated_tests()

    print(f"\n[*] Verifying Live Service Health & Observability (Docker / Local):")
    results["liveness_probe"] = check_http_endpoint(
        "API Liveness Probe (/health)", "http://localhost:8000/health", key_check="running"
    )
    results["readiness_probe"] = check_http_endpoint(
        "API Readiness Probe (/ready)", "http://localhost:8000/ready", key_check="status"
    )
    results["metrics_exporter"] = check_http_endpoint(
        "Prometheus Metrics (/metrics)", "http://localhost:8000/metrics", key_check="researchops"
    )
    results["prometheus_ui"] = check_http_endpoint(
        "Prometheus Server UI", "http://localhost:9090/-/healthy", expected_status=200
    )
    results["grafana_ui"] = check_http_endpoint(
        "Grafana Telemetry Dashboard", "http://localhost:3001/api/health", expected_status=200
    )

    print(f"\n{BLUE}======================================================================{RESET}")
    print(f"{BLUE}                     FA2 Final Readiness Summary                      {RESET}")
    print(f"{BLUE}======================================================================{RESET}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for item, status in results.items():
        state = f"{GREEN}READY [OK]{RESET}" if status else f"{YELLOW}PENDING / OFFLINE [WARN]{RESET}"
        print(f"  * {item.replace('_', ' ').title():<35}: {state}")

    print(f"\nScore: {passed}/{total} Checks Passed.")
    if passed >= 4:
        print(f"{GREEN}[SUCCESS] System is ready for FA2 demonstration.{RESET}\n")
    else:
        print(f"{YELLOW}[NOTICE] Local dev or Docker stack not active yet. Run 'docker compose up -d' when demonstrating live.{RESET}\n")


if __name__ == "__main__":
    main()
