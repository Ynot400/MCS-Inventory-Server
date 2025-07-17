# simple_admin_test.py - Simplified test that can be run directly
"""
Simple Admin Security Test

Run this file directly to test admin security features:
python simple_admin_test.py
"""

import os
import sys
import django

# Setup Django environment
def setup_django():
    # Get the current file's directory
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    
    # Look for the Django project directory
    # Check if we're already in the project root (has manage.py)
    if os.path.exists(os.path.join(current_dir, 'manage.py')):
        project_root = current_dir
    else:
        # Look for Inventory directory
        possible_paths = [
            os.path.join(current_dir, 'Inventory'),
            os.path.join(os.path.dirname(current_dir), 'Inventory'),
            os.path.join(current_dir, 'MCS-Inventory-Server', 'Inventory'),
        ]
        
        project_root = None
        for path in possible_paths:
            if os.path.exists(os.path.join(path, 'manage.py')):
                project_root = path
                break
        
        if not project_root:
            print("❌ Could not find Django project directory (looking for manage.py)")
            print(f"   Current directory: {current_dir}")
            print("   Please run this script from the project root or move it there")
            sys.exit(1)
    
    print(f"📁 Found Django project at: {project_root}")
    
    # Add project root to Python path
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Set Django settings
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Inventory.settings")
    
    # Change to project directory
    os.chdir(project_root)
    
    try:
        django.setup()
        print("✅ Django environment configured successfully")
    except Exception as e:
        print(f"❌ Failed to setup Django: {e}")
        print(f"   Project root: {project_root}")
        print(f"   Python path: {sys.path[:3]}...")
        sys.exit(1)

setup_django()

# Now import Django modules
from django.test import Client
from django.contrib.auth.models import User, Group
from django.db import transaction


def test_admin_security():
    """Run basic admin security tests"""
    print("🧪 Simple Admin Security Test")
    print("=" * 40)
    
    client = Client()
    test_results = []
    
    # Test 1: Create/Get admin user
    print("\n1. Setting up admin user...")
    try:
        admin_user, created = User.objects.get_or_create(
            username='test_admin',
            defaults={
                'is_superuser': True,
                'is_staff': True,
            }
        )
        if created:
            admin_user.set_password('admin123!')
            admin_user.save()
        
        print("   ✅ Admin user ready")
        test_results.append(("Admin user setup", True, ""))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        test_results.append(("Admin user setup", False, str(e)))
        return False
    
    # Test 2: Login
    print("\n2. Testing admin login...")
    try:
        login_success = client.login(username='test_admin', password='admin123!')
        if login_success:
            print("   ✅ Login successful")
            test_results.append(("Admin login", True, ""))
        else:
            print("   ❌ Login failed")
            test_results.append(("Admin login", False, "Login credentials rejected"))
            return False
    except Exception as e:
        print(f"   ❌ Login error: {e}")
        test_results.append(("Admin login", False, str(e)))
        return False
    
    # Test 3: Groups admin blocked
    print("\n3. Testing groups admin access (should be blocked)...")
    try:
        response = client.get('/admin/auth/group/')
        if response.status_code == 404:
            print("   ✅ Groups admin properly blocked")
            test_results.append(("Groups admin blocked", True, ""))
        else:
            print(f"   ❌ Groups admin not blocked (status: {response.status_code})")
            test_results.append(("Groups admin blocked", False, f"Status: {response.status_code}"))
    except Exception as e:
        print(f"   ❌ Error testing groups access: {e}")
        test_results.append(("Groups admin blocked", False, str(e)))
    
    # Test 4: User admin accessible
    print("\n4. Testing user admin access (should work)...")
    try:
        response = client.get('/admin/auth/user/')
        if response.status_code == 200:
            print("   ✅ User admin accessible")
            test_results.append(("User admin accessible", True, ""))
        else:
            print(f"   ❌ User admin not accessible (status: {response.status_code})")
            test_results.append(("User admin accessible", False, f"Status: {response.status_code}"))
    except Exception as e:
        print(f"   ❌ Error accessing user admin: {e}")
        test_results.append(("User admin accessible", False, str(e)))
    
    # Test 5: Create test group
    print("\n5. Setting up test group...")
    try:
        test_group, created = Group.objects.get_or_create(name='Test Group')
        print("   ✅ Test group ready")
        test_results.append(("Test group setup", True, ""))
    except Exception as e:
        print(f"   ❌ Failed to create test group: {e}")
        test_results.append(("Test group setup", False, str(e)))
    
    # Test 6: Get CSRF token and create regular user
    print("\n6. Testing user creation...")
    try:
        # First get the add user form to get CSRF token
        response = client.get('/admin/auth/user/add/')
        if response.status_code != 200:
            print(f"   ❌ Could not access add user form (status: {response.status_code})")
            test_results.append(("User creation", False, f"Add form status: {response.status_code}"))
        else:
            # Extract CSRF token
            from django.middleware.csrf import get_token
            csrf_token = get_token(client.session._get_session_key() if hasattr(client.session, '_get_session_key') else None)
            
            # Alternative: get from response
            import re
            csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.content.decode())
            if csrf_match:
                csrf_token = csrf_match.group(1)
            
            # Create user with CSRF token
            response = client.post('/admin/auth/user/add/', {
                'username': 'test_regular_user',
                'password1': 'testpass123!',
                'password2': 'testpass123!',
                'is_superuser': False,
                'groups': test_group.id if 'test_group' in locals() else '',
                'csrfmiddlewaretoken': csrf_token
            })
            
            if response.status_code == 302:  # Redirect means success
                # Check if user was created correctly
                try:
                    new_user = User.objects.get(username='test_regular_user')
                    issues = []
                    
                    if not new_user.is_staff:
                        issues.append("is_staff not True")
                    if not new_user.is_active:
                        issues.append("is_active not True")
                    if new_user.groups.count() > 1:
                        issues.append(f"has {new_user.groups.count()} groups (should be max 1)")
                    
                    if not issues:
                        print("   ✅ User created correctly")
                        test_results.append(("User creation", True, ""))
                    else:
                        print(f"   ❌ User created but with issues: {', '.join(issues)}")
                        test_results.append(("User creation", False, ', '.join(issues)))
                    
                except User.DoesNotExist:
                    print("   ❌ User not found after creation")
                    test_results.append(("User creation", False, "User not found after creation"))
            else:
                print(f"   ❌ User creation failed (status: {response.status_code})")
                if response.status_code == 200:
                    # Form returned with errors - check for specific errors
                    content = response.content.decode()
                    if 'errorlist' in content:
                        print("   📋 Form validation errors found")
                test_results.append(("User creation", False, f"Status: {response.status_code}"))
    except Exception as e:
        print(f"   ❌ Error creating user: {e}")
        test_results.append(("User creation", False, str(e)))
    
    # Test 7: Test superuser with group (should fail)
    print("\n7. Testing superuser + group validation (should fail)...")
    try:
        # Get CSRF token
        response = client.get('/admin/auth/user/add/')
        csrf_token = None
        if response.status_code == 200:
            import re
            csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.content.decode())
            if csrf_match:
                csrf_token = csrf_match.group(1)
        
        if csrf_token:
            response = client.post('/admin/auth/user/add/', {
                'username': 'invalid_superuser',
                'password1': 'testpass123!',
                'password2': 'testpass123!',
                'is_superuser': True,
                'groups': test_group.id if 'test_group' in locals() else '',
                'csrfmiddlewaretoken': csrf_token
            })
            
            if response.status_code == 200:  # Form returned with errors
                content = response.content.decode()
                if 'Superusers cannot be assigned to groups' in content:
                    print("   ✅ Superuser + group validation working")
                    test_results.append(("Superuser group validation", True, ""))
                else:
                    print("   ❌ Validation message not found")
                    test_results.append(("Superuser group validation", False, "Validation message not found"))
            elif response.status_code == 302:
                print("   ❌ Superuser with group was allowed (should have failed)")
                test_results.append(("Superuser group validation", False, "Invalid combination was allowed"))
            else:
                print(f"   ❌ Unexpected status: {response.status_code}")
                test_results.append(("Superuser group validation", False, f"Unexpected status: {response.status_code}"))
        else:
            print("   ❌ Could not get CSRF token")
            test_results.append(("Superuser group validation", False, "Could not get CSRF token"))
    except Exception as e:
        print(f"   ❌ Error testing superuser validation: {e}")
        test_results.append(("Superuser group validation", False, str(e)))
    
    # Test 8: Check form fields
    print("\n8. Testing form field restrictions...")
    try:
        # Check if we have a test user to examine
        try:
            new_user = User.objects.get(username='test_regular_user')
            response = client.get(f'/admin/auth/user/{new_user.id}/change/')
            if response.status_code == 200:
                content = response.content.decode()
                issues = []
                
                if 'id_is_staff' in content:
                    issues.append("is_staff field visible")
                if 'id_is_active' in content:
                    issues.append("is_active field visible")
                if 'user_permissions' in content:
                    issues.append("user_permissions field visible")
                
                if not issues:
                    print("   ✅ Form fields properly restricted")
                    test_results.append(("Form field restrictions", True, ""))
                else:
                    print(f"   ❌ Form field issues: {', '.join(issues)}")
                    test_results.append(("Form field restrictions", False, ', '.join(issues)))
            else:
                print(f"   ❌ Could not access user edit form (status: {response.status_code})")
                test_results.append(("Form field restrictions", False, f"Status: {response.status_code}"))
        except User.DoesNotExist:
            print("   ⚠️  Skipped (no test user created)")
            test_results.append(("Form field restrictions", None, "Skipped - no test user"))
    except Exception as e:
        print(f"   ❌ Error testing form fields: {e}")
        test_results.append(("Form field restrictions", False, str(e)))
    
    # Cleanup
    print("\n9. Cleaning up test data...")
    try:
        User.objects.filter(username__in=['test_regular_user', 'invalid_superuser']).delete()
        Group.objects.filter(name='Test Group').delete()
        print("   ✅ Cleanup completed")
    except Exception as e:
        print(f"   ⚠️  Cleanup warning: {e}")
    
    # Summary
    print("\n" + "=" * 40)
    print("📊 TEST SUMMARY")
    print("=" * 40)
    
    passed = sum(1 for _, result, _ in test_results if result is True)
    failed = sum(1 for _, result, _ in test_results if result is False)
    skipped = sum(1 for _, result, _ in test_results if result is None)
    total = len(test_results)
    
    print(f"Total Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    if skipped > 0:
        print(f"⚠️  Skipped: {skipped}")
    
    success_rate = (passed / (total - skipped) * 100) if (total - skipped) > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Admin security features are working correctly")
        return True
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("Failed tests:")
        for test_name, result, error in test_results:
            if result is False:
                print(f"   • {test_name}: {error}")
        return False


if __name__ == "__main__":
    print("🚀 Starting Simple Admin Security Test")
    print("Make sure your Django server is set up correctly...")
    
    try:
        success = test_admin_security()
        if success:
            print("\n✅ All admin security features are working!")
        else:
            print("\n❌ Some issues found. Please check the output above.")
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)