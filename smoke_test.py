#!/usr/bin/env python
"""
Smoke tests for production deployment verification.
Run this after deployment to ensure the system is working correctly.
"""

import requests
import json
import sys
import time
from typing import Tuple, Optional


class Color:
    """ANSI color codes."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_test(message: str):
    """Print test message."""
    print(f"{Color.BLUE}🧪 {message}{Color.END}")


def print_success(message: str):
    """Print success message."""
    print(f"{Color.GREEN}✓ {message}{Color.END}")


def print_error(message: str):
    """Print error message."""
    print(f"{Color.RED}✗ {message}{Color.END}")


def print_warning(message: str):
    """Print warning message."""
    print(f"{Color.YELLOW}⚠ {message}{Color.END}")


def test_health_check(base_url: str) -> bool:
    """Test health check endpoint."""
    print_test("Testing health check...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print_success("Health check passed")
                return True
            else:
                print_error(f"Health check returned unexpected status: {data}")
                return False
        else:
            print_error(f"Health check failed with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Health check failed: {e}")
        return False


def test_root_endpoint(base_url: str) -> bool:
    """Test root endpoint."""
    print_test("Testing root endpoint...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "service" in data and data.get("status") == "running":
                print_success(f"Root endpoint working - Service: {data.get('service')}")
                print(f"   LLM Provider: {data.get('llm_provider')}")
                print(f"   STT Provider: {data.get('stt_provider')}")
                print(f"   TTS Provider: {data.get('tts_provider')}")
                return True
        print_error("Root endpoint returned unexpected data")
        return False
    except requests.exceptions.RequestException as e:
        print_error(f"Root endpoint failed: {e}")
        return False


def test_session_creation(base_url: str) -> Tuple[bool, Optional[str]]:
    """Test session creation."""
    print_test("Testing session creation...")

    # Simple test form
    form_schema = {
        "form_id": "smoke_test",
        "form_name": "Smoke Test Form",
        "fields": [
            {
                "id": "name",
                "label": "Name",
                "type": "text",
                "required": True,
            }
        ],
    }

    try:
        response = requests.post(
            f"{base_url}/sessions",
            json={"form_schema": form_schema},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            session_id = data.get("session_id")
            if session_id:
                print_success(f"Session created: {session_id[:16]}...")
                return True, session_id
            else:
                print_error("Session creation returned no session_id")
                return False, None
        else:
            print_error(f"Session creation failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False, None

    except requests.exceptions.RequestException as e:
        print_error(f"Session creation failed: {e}")
        return False, None


def test_text_processing(base_url: str, session_id: str) -> bool:
    """Test text input processing."""
    print_test("Testing text input processing...")

    try:
        response = requests.post(
            f"{base_url}/sessions/{session_id}/text",
            json={
                "session_id": session_id,
                "text": "My name is Test User",
            },
            timeout=30,  # LLM can take time
        )

        if response.status_code == 200:
            data = response.json()
            if "message" in data:
                print_success("Text processing successful")
                print(f"   Agent response: {data['message'][:100]}...")
                print(f"   Completion: {data.get('completion_percentage', 0)}%")
                return True
            else:
                print_error("Text processing returned unexpected data")
                return False
        else:
            print_error(f"Text processing failed with status {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print_error(f"Text processing failed: {e}")
        return False


def test_form_state(base_url: str, session_id: str) -> bool:
    """Test form state retrieval."""
    print_test("Testing form state retrieval...")

    try:
        response = requests.get(
            f"{base_url}/sessions/{session_id}/form-state",
            timeout=5,
        )

        if response.status_code == 200:
            data = response.json()
            if "form_state" in data:
                print_success("Form state retrieved")
                print(f"   Completion: {data.get('completion_percentage')}%")
                print(f"   Is complete: {data.get('is_complete')}")
                return True
            else:
                print_error("Form state returned unexpected data")
                return False
        else:
            print_error(f"Form state retrieval failed with status {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print_error(f"Form state retrieval failed: {e}")
        return False


def test_session_deletion(base_url: str, session_id: str) -> bool:
    """Test session deletion."""
    print_test("Testing session deletion...")

    try:
        response = requests.delete(
            f"{base_url}/sessions/{session_id}",
            timeout=5,
        )

        if response.status_code == 200:
            print_success("Session deleted successfully")
            return True
        else:
            print_error(f"Session deletion failed with status {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print_error(f"Session deletion failed: {e}")
        return False


def run_smoke_tests(base_url: str = "http://localhost:8000") -> bool:
    """Run all smoke tests."""
    print("\n" + "=" * 60)
    print("🚀 Running Smoke Tests for AI Voice Form Filling Agent")
    print("=" * 60)
    print(f"Target: {base_url}\n")

    results = []

    # Test 1: Health check
    results.append(test_health_check(base_url))
    time.sleep(0.5)

    # Test 2: Root endpoint
    results.append(test_root_endpoint(base_url))
    time.sleep(0.5)

    # Test 3: Session creation
    session_success, session_id = test_session_creation(base_url)
    results.append(session_success)

    if session_id:
        time.sleep(1)

        # Test 4: Text processing (requires LLM)
        text_success = test_text_processing(base_url, session_id)
        results.append(text_success)
        time.sleep(1)

        # Test 5: Form state
        results.append(test_form_state(base_url, session_id))
        time.sleep(0.5)

        # Test 6: Session deletion
        results.append(test_session_deletion(base_url, session_id))
    else:
        print_warning("Skipping dependent tests due to session creation failure")
        results.extend([False, False, False])

    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    percentage = (passed / total * 100) if total > 0 else 0

    print(f"Passed: {passed}/{total} ({percentage:.0f}%)")

    if passed == total:
        print_success("All tests passed! ✨")
        print("\n✅ System is production-ready!")
        return True
    else:
        print_error(f"{total - passed} test(s) failed")
        print("\n⚠️  Please fix the failing tests before deploying to production")
        return False


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Smoke tests for Voice Form Agent")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    try:
        success = run_smoke_tests(args.url)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
