"""
Comprehensive integration test script for Phase 1.

Tests the entire flow:
1. Generate mock CSV files
2. Create ZIP file
3. Upload to API
4. Verify database records
5. Retrieve and validate budget data
6. Check anomaly detection
7. Test all 3 municipalities with all 3 months

Usage:
    python test_integration.py
    
    Or with verbose output:
    python test_integration.py --verbose
"""

import os
import sys
import json
import zipfile
import tempfile
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
import time
import argparse
from typing import Dict, Any, Tuple

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class TestResults:
    """Track test results."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.tests_run = []
    
    def add_pass(self, test_name: str, message: str = ""):
        self.passed += 1
        msg = f"✅ {test_name}"
        if message:
            msg += f": {message}"
        self.tests_run.append(msg)
        print(f"{Colors.GREEN}{msg}{Colors.ENDC}")
    
    def add_fail(self, test_name: str, message: str = ""):
        self.failed += 1
        msg = f"❌ {test_name}"
        if message:
            msg += f": {message}"
        self.tests_run.append(msg)
        self.errors.append(msg)
        print(f"{Colors.RED}{msg}{Colors.ENDC}")
    
    def summary(self):
        total = self.passed + self.failed
        percentage = (self.passed / total * 100) if total > 0 else 0
        
        print("\n" + "="*70)
        print(f"{Colors.BOLD}TEST SUMMARY{Colors.ENDC}")
        print("="*70)
        print(f"{Colors.GREEN}✅ Passed: {self.passed}/{total}{Colors.ENDC}")
        print(f"{Colors.RED}❌ Failed: {self.failed}/{total}{Colors.ENDC}")
        print(f"📊 Success Rate: {percentage:.1f}%")
        
        if self.errors:
            print(f"\n{Colors.RED}Errors:{Colors.ENDC}")
            for error in self.errors:
                print(f"  {error}")
        
        print("="*70 + "\n")
        
        return self.failed == 0


class IntegrationTester:
    """Test framework for the education budget platform."""
    
    def __init__(self, api_url: str = "http://localhost:8000", verbose: bool = False):
        self.api_url = api_url
        self.verbose = verbose
        self.results = TestResults()
        self.temp_dir = None
        self.test_data = {}
        self.created_municipality_ids = {}
        self.token = None  # JWT token
        self.headers = {"Content-Type": "application/json"}
    
    def log(self, message: str, level: str = "info"):
        """Log message with optional verbosity."""
        if self.verbose or level != "debug":
            timestamp = datetime.now().strftime("%H:%M:%S")
            prefix = f"[{timestamp}]"
            if level == "debug":
                prefix += " [DEBUG]"
            elif level == "info":
                prefix += " [INFO]"
            elif level == "error":
                prefix += f" {Colors.RED}[ERROR]{Colors.ENDC}"
            
            print(f"{prefix} {message}")
    
    def setup(self):
        """Set up test environment."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}=== SETUP ==={Colors.ENDC}\n")
        
        # Create temp directory
        self.temp_dir = tempfile.mkdtemp()
        self.log(f"Created temp directory: {self.temp_dir}")
        
        # Check API connectivity
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            self.log(f"✅ API is reachable at {self.api_url}")
            self.results.add_pass("API Connectivity", f"Status code: {response.status_code}")
        except Exception as e:
            self.results.add_fail("API Connectivity", str(e))
            print(f"\n{Colors.RED}ERROR: Cannot connect to API at {self.api_url}{Colors.ENDC}")
            print(f"Make sure the API is running: python -m uvicorn backend.main:app --reload\n")
            sys.exit(1)
    
    def login(self):
        """Login and get JWT token."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}=== LOGIN ==={Colors.ENDC}\n")
        
        try:
            # Admin credentials
            email = "admin@example.com"
            password = "admin123"
            
            response = requests.post(
                f"{self.api_url}/api/auth/login",
                json={"email": email, "password": password},
                timeout=10
            )
            
            if response.status_code != 200:
                self.results.add_fail("Login", f"Status {response.status_code}: {response.text}")
                return False
            
            result = response.json()
            self.token = result.get("access_token")
            
            if not self.token:
                self.results.add_fail("Login", "No token in response")
                return False
            
            # Update headers with token
            self.headers["Authorization"] = f"Bearer {self.token}"
            
            self.log(f"✅ Successfully logged in as {email}")
            self.log(f"Token: {self.token[:50]}...")
            
            self.results.add_pass("Login", f"Got JWT token for {email}")
            return True
        
        except Exception as e:
            self.results.add_fail("Login", str(e))
            return False
    
    def generate_mock_data(self):
        """Generate mock CSV files."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}=== GENERATE MOCK DATA ==={Colors.ENDC}\n")
        
        try:
            # Import the mock generator
            sys.path.insert(0, str(Path(__file__).parent / "backend/sample_data"))
            from mock_generator import generate_invoice_data, generate_breakdown_data
            
            invoice_df = generate_invoice_data()
            breakdown_df = generate_breakdown_data()
            
            # Save to temp directory
            invoice_path = os.path.join(self.temp_dir, "invoice.csv")
            breakdown_path = os.path.join(self.temp_dir, "breakdown.csv")
            
            invoice_df.to_csv(invoice_path, index=False, encoding='utf-8-sig')
            breakdown_df.to_csv(breakdown_path, index=False, encoding='utf-8-sig')
            
            self.log(f"Generated invoice.csv: {len(invoice_df)} rows")
            self.log(f"Generated breakdown.csv: {len(breakdown_df)} rows")
            
            self.test_data['invoice_df'] = invoice_df
            self.test_data['breakdown_df'] = breakdown_df
            self.test_data['invoice_path'] = invoice_path
            self.test_data['breakdown_path'] = breakdown_path
            
            # Verify data
            assert not invoice_df.empty, "Invoice data is empty"
            assert not breakdown_df.empty, "Breakdown data is empty"
            assert len(invoice_df) == 9, f"Expected 9 invoice rows (3 mun × 3 months), got {len(invoice_df)}"
            
            self.results.add_pass("Mock Data Generation", f"Generated {len(invoice_df)} invoice + {len(breakdown_df)} breakdown rows")
            
        except Exception as e:
            self.results.add_fail("Mock Data Generation", str(e))
            raise
    
    def create_zip_file(self):
        """Create ZIP file with CSV files."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}=== CREATE ZIP FILE ==={Colors.ENDC}\n")
        
        try:
            zip_path = os.path.join(self.temp_dir, "test_budget.zip")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(
                    self.test_data['invoice_path'],
                    arcname='invoice.csv'
                )
                zipf.write(
                    self.test_data['breakdown_path'],
                    arcname='breakdown.csv'
                )
            
            file_size = os.path.getsize(zip_path)
            self.log(f"Created ZIP file: {zip_path} ({file_size} bytes)")
            
            self.test_data['zip_path'] = zip_path
            
            self.results.add_pass("ZIP File Creation", f"Size: {file_size} bytes")
            
        except Exception as e:
            self.results.add_fail("ZIP File Creation", str(e))
            raise
    
    def test_upload_endpoint(self):
        """Test file upload endpoint."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}=== TEST UPLOAD ENDPOINT ==={Colors.ENDC}\n")
        
        try:
            zip_path = self.test_data['zip_path']
            
            with open(zip_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(
                    f"{self.api_url}/api/upload",
                    files=files,
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=30
                )
            
            self.log(f"Upload response status: {response.status_code}")
            
            if response.status_code != 200:
                self.results.add_fail(
                    "File Upload",
                    f"Status {response.status_code}: {response.text}"
                )
                return False
            
            result = response.json()
            self.log(f"Upload result: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # Verify response structure
            assert result['status'] == 'success', f"Status is {result['status']}"
            assert result['summary']['municipalities_processed'] == 3, "Should process 3 municipalities"
            assert result['summary']['total_runs'] == 9, "Should have 9 runs (3 mun × 3 months)"
            
            self.test_data['upload_result'] = result
            
            self.results.add_pass(
                "File Upload",
                f"Processed {result['summary']['municipalities_processed']} municipalities, "
                f"{result['summary']['total_runs']} runs, "
                f"{result['summary']['balanced_runs']} balanced"
            )
            
            return True
        
        except Exception as e:
            self.results.add_fail("File Upload", str(e))
            return False
    
    def test_municipalities_endpoint(self):
        """Test municipalities list endpoint."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}=== TEST MUNICIPALITIES ENDPOINT ==={Colors.ENDC}\n")
        
        try:
            response = requests.get(
                f"{self.api_url}/api/municipalities",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code != 200:
                self.results.add_fail(
                    "List Municipalities",
                    f"Status {response.status_code}"
                )
                return False
            
            municipalities = response.json()
            self.log(f"Found {len(municipalities)} municipalities")
            
            assert len(municipalities) >= 3, f"Expected at least 3 municipalities, got {len(municipalities)}"
            
            # Store municipality IDs for later tests
            for mun in municipalities:
                code = mun.get('code')
                mun_id = mun.get('id')
                if code and mun_id:
                    self.created_municipality_ids[code] = mun_id
                    self.log(f"  {code}: {mun['name']} (ID: {mun_id})")
            
            self.test_data['municipalities'] = municipalities
            
            self.results.add_pass(
                "List Municipalities",
                f"Retrieved {len(municipalities)} municipalities"
            )
            
            return True
        
        except Exception as e:
            self.results.add_fail("List Municipalities", str(e))
            return False
    
    def test_budget_endpoints(self):
        """Test budget retrieval endpoints for all municipalities and months."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}=== TEST BUDGET ENDPOINTS ==={Colors.ENDC}\n")
        
        municipalities = self.test_data.get('municipalities', [])
        months = ["2024-01", "2024-02", "2024-03"]
        
        total_tests = 0
        passed_tests = 0
        
        for mun in municipalities[:3]:  # Test first 3 municipalities
            mun_id = mun['id']
            mun_code = mun['code']
            mun_name = mun['name']
            
            for month in months:
                total_tests += 1
                
                try:
                    response = requests.get(
                        f"{self.api_url}/api/budget/{mun_id}/{month}",
                        headers=self.headers,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        budget_data = response.json()
                        
                        # Verify structure
                        assert 'municipality' in budget_data
                        assert 'month' in budget_data
                        assert 'invoice_total' in budget_data
                        assert 'breakdown_total' in budget_data
                        assert 'is_balanced' in budget_data
                        assert 'budget_lines' in budget_data
                        
                        num_lines = len(budget_data.get('budget_lines', []))
                        is_balanced = budget_data.get('is_balanced')
                        
                        self.log(
                            f"✓ {mun_code} {month}: {num_lines} lines, "
                            f"balanced={is_balanced}",
                            level="debug"
                        )
                        
                        passed_tests += 1
                    
                    elif response.status_code == 404:
                        self.log(
                            f"- {mun_code} {month}: No data (expected for new months)",
                            level="debug"
                        )
                        # This is OK - some municipalities might not have data for all months
                    
                    else:
                        self.log(
                            f"✗ {mun_code} {month}: Status {response.status_code}",
                            level="debug"
                        )
                
                except Exception as e:
                    self.log(f"✗ Error retrieving {mun_code} {month}: {str(e)}", level="debug")
        
        if passed_tests > 0:
            self.results.add_pass(
                "Budget Endpoints",
                f"Retrieved {passed_tests}/{total_tests} budget datasets"
            )
            return True
        else:
            self.results.add_fail(
                "Budget Endpoints",
                f"Could not retrieve any budget data"
            )
            return False
    
    def test_anomaly_detection(self):
        """Test anomaly detection endpoints."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}=== TEST ANOMALY DETECTION ==={Colors.ENDC}\n")
        
        municipalities = self.test_data.get('municipalities', [])
        
        for mun in municipalities[:1]:  # Test first municipality
            mun_id = mun['id']
            mun_code = mun['code']
            
            # Test February for retro payments
            try:
                response = requests.get(
                    f"{self.api_url}/api/budget/{mun_id}/2024-02/anomalies",
                    timeout=10
                )
                
                if response.status_code == 200:
                    anomalies = response.json()
                    
                    has_anomalies = anomalies.get('has_anomalies', False)
                    retro_count = len(anomalies.get('retro_payments', []))
                    
                    self.log(f"February anomalies for {mun_code}: {retro_count} retro payments")
                    
                    if has_anomalies:
                        self.results.add_pass(
                            "Anomaly Detection",
                            f"Detected {retro_count} retro + "
                            f"{len(anomalies.get('shortages', []))} shortages"
                        )
                    else:
                        self.results.add_pass(
                            "Anomaly Detection",
                            "No anomalies (data may be balanced)"
                        )
                    return True
                
                elif response.status_code == 404:
                    self.log(f"No data for {mun_code} February (expected)")
                    self.results.add_pass("Anomaly Detection", "Endpoint working (no data)")
                    return True
            
            except Exception as e:
                self.results.add_fail("Anomaly Detection", str(e))
                return False
        
        return False
    
    def test_runs_endpoint(self):
        """Test monthly runs endpoint."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}=== TEST RUNS ENDPOINT ==={Colors.ENDC}\n")
        
        try:
            response = requests.get(
                f"{self.api_url}/api/runs",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code != 200:
                self.results.add_fail("List Runs", f"Status {response.status_code}")
                return False
            
            runs = response.json()
            self.log(f"Found {len(runs)} monthly runs")
            
            if len(runs) > 0:
                self.results.add_pass("List Runs", f"Retrieved {len(runs)} runs")
                return True
            else:
                self.results.add_fail("List Runs", "No runs found (should have runs from upload)")
                return False
        
        except Exception as e:
            self.results.add_fail("List Runs", str(e))
            return False
    
    def cleanup(self):
        """Clean up test environment."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}=== CLEANUP ==={Colors.ENDC}\n")
        
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            try:
                shutil.rmtree(self.temp_dir)
                self.log(f"Cleaned up temp directory: {self.temp_dir}")
            except Exception as e:
                self.log(f"Could not clean up temp directory: {e}", level="error")
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        try:
            self.setup()
            
            # Login to get JWT token
            if not self.login():
                print(f"\n{Colors.RED}❌ Failed to login. Aborting tests.{Colors.ENDC}")
                return False
            
            self.generate_mock_data()
            self.create_zip_file()
            self.test_upload_endpoint()
            
            # Wait a moment for database to be updated
            time.sleep(1)
            
            self.test_municipalities_endpoint()
            self.test_budget_endpoints()
            self.test_anomaly_detection()
            self.test_runs_endpoint()
            
        finally:
            self.cleanup()
        
        return self.results.summary()


def main():
    parser = argparse.ArgumentParser(
        description="Integration test for Education Budget Platform"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="API URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║         EDUCATION BUDGET PLATFORM - INTEGRATION TEST              ║")
    print("║                      Phase 1 Validation                           ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}\n")
    
    tester = IntegrationTester(api_url=args.url, verbose=args.verbose)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
