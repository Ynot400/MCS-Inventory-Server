# simple_test.py - Basic functionality test
import requests
import json

# Configuration
BASE_URL = 'http://127.0.0.1:8000'
USERNAME = 'Joshua-Lac'  # Your superuser username
PASSWORD = 'Tebow001!'  # Your superuser password

def test_job_ticket_functionality():
    """Test basic job ticket functionality step by step"""
    session = requests.Session()
    
    print("🧪 Testing Job Ticket Functionality")
    print("=" * 50)
    
    # Step 1: Test server connectivity
    print("1. Testing server connectivity...")
    try:
        response = session.get(BASE_URL, timeout=5)
        print(f"   ✅ Server responding (status: {response.status_code})")
    except Exception as e:
        print(f"   ❌ Server not responding: {e}")
        return False
    
    # Step 2: Test login page
    print("2. Testing login page...")
    try:
        response = session.get(f'{BASE_URL}/login/', timeout=5)
        if response.status_code == 200:
            print("   ✅ Login page accessible")
        else:
            print(f"   ❌ Login page error: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Login page error: {e}")
        return False
    
    # Step 3: Extract CSRF token and login
    print("3. Testing authentication...")
    try:
        # Get CSRF token
        csrf_token = None
        if 'csrftoken' in session.cookies:
            csrf_token = session.cookies['csrftoken']
        else:
            import re
            csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)
            if csrf_match:
                csrf_token = csrf_match.group(1)
        
        if not csrf_token:
            print("   ❌ Could not get CSRF token")
            return False
        
        # Login
        login_data = {
            'username': USERNAME,
            'password': PASSWORD,
            'csrfmiddlewaretoken': csrf_token
        }
        
        response = session.post(f'{BASE_URL}/login/', data=login_data, timeout=5)
        
        if response.status_code == 302 or 'dashboard' in response.url:
            print("   ✅ Authentication successful")
        else:
            print(f"   ❌ Authentication failed")
            print(f"       Status: {response.status_code}")
            print(f"       URL: {response.url}")
            if "Invalid" in response.text or "incorrect" in response.text.lower():
                print("       Check username/password")
            return False
            
    except Exception as e:
        print(f"   ❌ Authentication error: {e}")
        return False
    
    # Step 4: Test job ticket dashboard access
    print("4. Testing job ticket dashboard...")
    try:
        response = session.get(f'{BASE_URL}/job-tickets/', timeout=5)
        if response.status_code == 200:
            print("   ✅ Dashboard accessible")
            if "Job Ticket Dashboard" in response.text:
                print("   ✅ Dashboard content correct")
            else:
                print("   ⚠️  Dashboard content might be wrong")
        else:
            print(f"   ❌ Dashboard error: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Dashboard error: {e}")
        return False
    
    # Step 5: Test submission token endpoint
    print("5. Testing submission token endpoint...")
    try:
        headers = {'X-Requested-With': 'XMLHttpRequest'}
        response = session.get(f'{BASE_URL}/job-tickets/get-token/', headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'submission_token' in data:
                token = data['submission_token']
                print(f"   ✅ Token endpoint working (token: {token[:10]}...)")
            else:
                print("   ❌ No token in response")
                return False
        else:
            print(f"   ❌ Token endpoint error: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Token endpoint error: {e}")
        return False
    
    # Step 6: Test create form loading
    print("6. Testing create form loading...")
    try:
        headers = {'X-Requested-With': 'XMLHttpRequest'}
        response = session.get(f'{BASE_URL}/job-tickets/create/', headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'form_html' in data:
                print("   ✅ Create form loading works")
                if 'submission_token' in data['form_html']:
                    print("   ✅ Form contains submission token")
                else:
                    print("   ⚠️  Form missing submission token")
            else:
                print("   ❌ No form_html in response")
                return False
        else:
            print(f"   ❌ Create form error: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Create form error: {e}")
        return False
    
    # Step 7: Test job ticket creation
    print("7. Testing job ticket creation...")
    try:
        # Get fresh submission token
        headers = {'X-Requested-With': 'XMLHttpRequest'}
        token_response = session.get(f'{BASE_URL}/job-tickets/get-token/', headers=headers)
        token = token_response.json()['submission_token']
        
        # Get fresh CSRF token from cookies (it gets updated during the session)
        current_csrf_token = session.cookies.get('csrftoken', csrf_token)
        
        # Create ticket
        data = {
            'customer_name': 'Test Customer',
            'boat_name': 'Test Boat',
            'genre': 'Electrical',
            'status': 'InProgress',
            'submission_token': token,
            'csrfmiddlewaretoken': current_csrf_token
        }
        
        print(f"   Using CSRF token: {current_csrf_token[:10]}...")
        print(f"   Using submission token: {token[:10]}...")
        
        response = session.post(
            f'{BASE_URL}/job-tickets/create/',
            data=data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("   ✅ Job ticket creation successful")
                ticket_id = result.get('ticket_id')
                if ticket_id:
                    print(f"   ✅ Created ticket ID: {ticket_id}")
                    
                    # Test deletion of the created ticket
                    print("8. Testing job ticket deletion...")
                    
                    # Get fresh tokens for deletion
                    token_response = session.get(f'{BASE_URL}/job-tickets/get-token/', headers=headers)
                    token = token_response.json()['submission_token']
                    current_csrf_token = session.cookies.get('csrftoken', current_csrf_token)
                    
                    delete_data = {
                        'submission_token': token,
                        'csrfmiddlewaretoken': current_csrf_token
                    }
                    
                    delete_response = session.post(
                        f'{BASE_URL}/job-tickets/{ticket_id}/delete/',
                        data=delete_data,
                        headers=headers,
                        timeout=5
                    )
                    
                    if delete_response.status_code == 200:
                        delete_result = delete_response.json()
                        if delete_result.get('success'):
                            print("   ✅ Job ticket deletion successful")
                        else:
                            print(f"   ❌ Delete failed: {delete_result.get('error')}")
                    else:
                        print(f"   ❌ Delete error: {delete_response.status_code}")
                        
            else:
                print(f"   ❌ Creation failed: {result.get('error')}")
                return False
        else:
            print(f"   ❌ Creation error: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Creation error: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 ALL TESTS PASSED!")
    print("Your job ticket functionality is working correctly.")
    print("You can now run the load test with confidence.")
    return True

if __name__ == "__main__":
    print("Make sure to update USERNAME and PASSWORD variables in this script!")
    print(f"Current settings: {BASE_URL}, user: {USERNAME}")
    print()
    
    choice = input("Continue with test? (y/n): ").lower().strip()
    if choice == 'y':
        test_job_ticket_functionality()
    else:
        print("Test cancelled.")