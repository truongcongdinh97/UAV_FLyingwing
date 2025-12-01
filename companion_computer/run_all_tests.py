"""
Run All Tests
Chạy tất cả test scripts và tạo báo cáo
"""

import subprocess
import sys
import os

def run_test(script_name, description):
    """Run a test script"""
    print("\n" + "=" * 70)
    print(f"🧪 {description}")
    print("=" * 70)
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED")
            return False
    
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def main():
    print("=" * 70)
    print("FLYING WING UAV - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    
    tests = [
        ("test_windows.py", "Full System Test"),
        ("test_logging.py", "Data Logger Test"),
        ("view_config.py", "Configuration Viewer"),
    ]
    
    results = []
    
    for script, description in tests:
        passed = run_test(script, description)
        results.append((description, passed))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    failed = total - passed
    
    for description, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {description}")
    
    print()
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    
    if failed == 0:
        print()
        print("🎉 ALL TESTS PASSED!")
        print("✅ Code is ready to deploy to Raspberry Pi")
        print()
        print("Next steps:")
        print("  1. Review code and configurations")
        print("  2. Follow DEPLOYMENT.md to deploy to Pi")
        print("  3. Test with actual hardware")
    else:
        print()
        print("⚠️  Some tests failed. Please review and fix.")
    
    print("=" * 70)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
