# load_test.py - Run this separately to test under load
import requests
import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor
import json

# Configuration
BASE_URL = 'http://127.0.0.1:8000'  # Adjust to your server
USERNAME = 'Joshua-Lac'  # Your superuser username
PASSWORD = 'Tebow001!'  # Your superuser password
NUM_THREADS = 5  # Reduced for initial testing
NUM_REQUESTS_PER_THREAD = 10  # Reduced for initial testing

class JobTicketLoadTester:
    def __init__(self):
        self.session = requests.Session()
        self.csrf_token = None
        
    def login(self):
        """Login and get CSRF token"""
        try:
            print(f"Attempting to connect to {BASE_URL}")
            
            # Get login page for CSRF token
            response = self.session.get(f'{BASE_URL}/login/', timeout=10)
            print(f"Login page status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Failed to load login page: {response.status_code}")
                return False
            
            # Extract CSRF token from cookies or form
            if 'csrftoken' in self.session.cookies:
                self.csrf_token = self.session.cookies['csrftoken']
                print(f"Got CSRF token from cookies: {self.csrf_token[:10]}...")
            else:
                # Try to extract from form
                import re
                csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)
                if csrf_match:
                    self.csrf_token = csrf_match.group(1)
                    print(f"Got CSRF token from form: {self.csrf_token[:10]}...")
                else:
                    print("Could not find CSRF token")
                    return False
            
            # Login
            login_data = {
                'username': USERNAME,
                'password': PASSWORD,
                'csrfmiddlewaretoken': self.csrf_token
            }
            
            print("Attempting login...")
            response = self.session.post(f'{BASE_URL}/login/', data=login_data, timeout=10)
            print(f"Login response status: {response.status_code}")
            print(f"Login response URL: {response.url}")
            
            # Check if we're redirected to dashboard (successful login)
            if response.status_code == 302 or 'dashboard' in response.url:
                print("Login successful!")
                return True
            else:
                print(f"Login failed. Response content: {response.text[:200]}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to {BASE_URL}. Is the server running?")
            return False
        except requests.exceptions.Timeout:
            print("❌ Request timed out. Server might be slow or unresponsive.")
            return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def get_submission_token(self):
        """Get a fresh submission token"""
        try:
            headers = {'X-Requested-With': 'XMLHttpRequest'}
            response = self.session.get(f'{BASE_URL}/job-tickets/get-token/', headers=headers, timeout=10)
            
            if response.status_code == 200:
                token = response.json().get('submission_token')
                if token:
                    print(f"Got submission token: {token[:10]}...")
                    return token
                else:
                    print("No submission token in response")
            else:
                print(f"Failed to get submission token: {response.status_code}")
                print(f"Response: {response.text[:200]}")
            return None
        except Exception as e:
            print(f"Error getting submission token: {e}")
            return None
    
    def create_job_ticket(self):
        """Create a job ticket"""
        try:
            token = self.get_submission_token()
            if not token:
                print("Failed to get submission token for ticket creation")
                return False
            
            # Get current CSRF token from cookies (it might have been updated)
            current_csrf_token = self.session.cookies.get('csrftoken', self.csrf_token)
                
            headers = {'X-Requested-With': 'XMLHttpRequest'}
            data = {
                'customer_name': f'Load Test Customer {random.randint(1000, 9999)}',
                'boat_name': f'Test Boat {random.randint(1000, 9999)}',
                'genre': random.choice(['Electrical', 'Mechanical', 'Fabrication']),
                'status': random.choice(['InProgress', 'Complete']),
                'submission_token': token,
                'csrfmiddlewaretoken': current_csrf_token
            }
            
            response = self.session.post(
                f'{BASE_URL}/job-tickets/create/',
                data=data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print("✅ Created job ticket successfully")
                    return True
                else:
                    print(f"❌ Job ticket creation failed: {result.get('error', 'Unknown error')}")
                    return False
            elif response.status_code == 403:
                print("❌ CSRF token issue - this is common under load")
                return False
            else:
                print(f"❌ Job ticket creation failed with status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating job ticket: {e}")
            return False
    
    def load_dashboard(self):
        """Load the dashboard page"""
        try:
            response = self.session.get(f'{BASE_URL}/job-tickets/', timeout=10)
            if response.status_code == 200:
                print("✅ Dashboard loaded successfully")
                return True
            else:
                print(f"❌ Dashboard load failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error loading dashboard: {e}")
            return False
    
    def run_load_test(self, thread_id):
        """Run load test for one thread"""
        results = {
            'thread_id': thread_id,
            'dashboard_loads': 0,
            'ticket_creates': 0,
            'errors': 0,
            'start_time': time.time()
        }
        
        # Login first
        if not self.login():
            print(f"Thread {thread_id}: Login failed")
            return results
        
        print(f"Thread {thread_id}: Starting load test")
        
        for i in range(NUM_REQUESTS_PER_THREAD):
            try:
                # Alternate between loading dashboard and creating tickets
                if i % 2 == 0:
                    if self.load_dashboard():
                        results['dashboard_loads'] += 1
                    else:
                        results['errors'] += 1
                else:
                    if self.create_job_ticket():
                        results['ticket_creates'] += 1
                    else:
                        results['errors'] += 1
                
                # Small delay to simulate real usage
                time.sleep(random.uniform(0.1, 0.5))
                
            except Exception as e:
                print(f"Thread {thread_id}: Error - {e}")
                results['errors'] += 1
        
        results['end_time'] = time.time()
        results['duration'] = results['end_time'] - results['start_time']
        
        print(f"Thread {thread_id}: Completed in {results['duration']:.2f}s")
        return results

def run_load_test():
    """Run the complete load test"""
    print(f"Starting load test with {NUM_THREADS} threads, {NUM_REQUESTS_PER_THREAD} requests each")
    print(f"Target server: {BASE_URL}")
    print(f"Username: {USERNAME}")
    print("="*60)
    
    # First, test basic connectivity with a single request
    print("Testing basic connectivity...")
    test_tester = JobTicketLoadTester()
    if not test_tester.login():
        print("❌ Basic connectivity test failed. Please check:")
        print(f"   1. Server is running at {BASE_URL}")
        print(f"   2. Username '{USERNAME}' exists and has superuser privileges")
        print("   3. Password is correct")
        print("   4. CSRF protection is working")
        return
    
    print("✅ Basic connectivity test passed. Starting load test...")
    print("="*60)
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        testers = [JobTicketLoadTester() for _ in range(NUM_THREADS)]
        futures = [
            executor.submit(tester.run_load_test, i) 
            for i, tester in enumerate(testers)
        ]
        
        results = [future.result() for future in futures]
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Calculate statistics
    total_dashboard_loads = sum(r['dashboard_loads'] for r in results)
    total_ticket_creates = sum(r['ticket_creates'] for r in results)
    total_errors = sum(r['errors'] for r in results)
    total_requests = total_dashboard_loads + total_ticket_creates + total_errors
    
    print("\n" + "="*50)
    print("LOAD TEST RESULTS")
    print("="*50)
    print(f"Total Duration: {total_duration:.2f} seconds")
    print(f"Total Requests: {total_requests}")
    print(f"Dashboard Loads: {total_dashboard_loads}")
    print(f"Ticket Creates: {total_ticket_creates}")
    print(f"Errors: {total_errors}")
    
    # Fix division by zero error
    if total_requests > 0:
        success_rate = ((total_requests - total_errors) / total_requests * 100)
        requests_per_second = total_requests / total_duration
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Requests/Second: {requests_per_second:.2f}")
    else:
        print("Success Rate: 0% (No requests completed)")
        print("Requests/Second: 0")
    
    print()
    
    if total_errors > 0:
        print("⚠️  Some errors occurred. Check server logs for details.")
        print("   Common issues:")
        print("   - Server overload (reduce NUM_THREADS or NUM_REQUESTS_PER_THREAD)")
        print("   - Database connection limits")
        print("   - Memory issues")
    elif total_requests == 0:
        print("❌ No requests completed successfully.")
        print("   This usually means:")
        print("   - Authentication failed")
        print("   - Server is not responding")
        print("   - Incorrect URL configuration")
    else:
        print("✅ All requests successful!")
        
    # Show per-thread results for debugging
    print("\nPER-THREAD RESULTS:")
    print("-" * 50)
    for r in results:
        print(f"Thread {r['thread_id']}: {r['dashboard_loads']} dashboards, "
              f"{r['ticket_creates']} tickets, {r['errors']} errors "
              f"({r['duration']:.1f}s)")

# Add a simple connectivity test function
def test_connectivity():
    """Test basic connectivity before running load test"""
    print("Testing basic connectivity...")
    
    try:
        response = requests.get(BASE_URL, timeout=5)
        print(f"✅ Server is responding (status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {BASE_URL}")
        print("   Make sure your Django server is running:")
        print("   python manage.py runserver")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Job Ticket Load Tester")
    print("="*50)
    print("Before running the load test, make sure:")
    print(f"1. Your Django server is running at {BASE_URL}")
    print(f"2. You have a superuser account: {USERNAME}")
    print("3. The password in this script is correct")
    print("4. Job ticket functionality is working manually")
    print()
    
    choice = input("Continue? (y/n): ").lower().strip()
    if choice != 'y':
        print("Load test cancelled.")
        exit()
    
    if test_connectivity():
        run_load_test()
    else:
        print("Connectivity test failed. Please fix the issues above before running the load test.")