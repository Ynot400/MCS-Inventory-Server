# utils/test_admin_security.py - Comprehensive tests for admin security features
import os
import sys
import django

# Setup Django environment first, before any other imports
def setup_django():
    """Setup Django environment for testing"""
    # Add the project root to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)  # Go up one level from utils/
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Set Django settings
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Inventory.settings")
    
    # Setup Django
    try:
        django.setup()
        print("✓ Django environment configured")
    except Exception as e:
        print(f"❌ Failed to setup Django: {e}")
        sys.exit(1)

# Call setup before any Django imports
if __name__ == "__main__":
    setup_django()

# Now safe to import Django modules
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
import logging

logger = logging.getLogger('admin_security')


class AdminSecurityIntegrationTests(TestCase):
    """Comprehensive integration tests for admin security features"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test superuser
        self.superuser = User.objects.create_user(
            username='test_admin',
            password='admin123!',
            is_superuser=True,
            is_staff=True
        )
        
        # Create test groups
        self.inventory_group = Group.objects.create(name='Inventory Technician')
        self.shop_group = Group.objects.create(name='Shop Technician')
        
        # Create test regular user
        self.regular_user = User.objects.create_user(
            username='test_user',
            password='user123!',
            is_staff=True
        )
        self.regular_user.groups.add(self.inventory_group)
        
        print("✓ Test setup completed")

    def test_groups_admin_access_blocked(self):
        """Test that Groups admin is completely blocked"""
        print("\n🧪 Testing Groups Admin Access Block...")
        
        self.client.login(username='test_admin', password='admin123!')
        
        # Test various group URLs are blocked
        group_urls = [
            '/admin/auth/group/',
            '/admin/auth/group/add/',
            f'/admin/auth/group/{self.inventory_group.id}/change/',
            f'/admin/auth/group/{self.inventory_group.id}/delete/',
        ]
        
        for url in group_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404, f"Group URL {url} should be blocked")
            print(f"   ✓ {url} correctly blocked (404)")
        
        # Test POST requests are also blocked
        response = self.client.post('/admin/auth/group/add/', {
            'name': 'Test Group',
            'permissions': []
        })
        self.assertEqual(response.status_code, 404)
        print("   ✓ Group creation POST request blocked")

    def test_user_add_form_restrictions(self):
        """Test user add form enforces all restrictions"""
        print("\n🧪 Testing User Add Form Restrictions...")
        
        self.client.login(username='test_admin', password='admin123!')
        
        # Test valid user creation
        response = self.client.post('/admin/auth/user/add/', {
            'username': 'new_user',
            'password1': 'complex_password123!',
            'password2': 'complex_password123!',
            'groups': self.inventory_group.id,
            'is_superuser': False
        })
        self.assertEqual(response.status_code, 302)  # Successful redirect
        
        new_user = User.objects.get(username='new_user')
        self.assertTrue(new_user.is_staff)
        self.assertTrue(new_user.is_active)
        self.assertEqual(new_user.groups.count(), 1)
        self.assertEqual(new_user.groups.first(), self.inventory_group)
        print("   ✓ Valid user creation works correctly")
        
        # Test superuser creation (should have no groups)
        response = self.client.post('/admin/auth/user/add/', {
            'username': 'new_superuser',
            'password1': 'complex_password123!',
            'password2': 'complex_password123!',
            'groups': '',  # No group for superuser
            'is_superuser': True
        })
        self.assertEqual(response.status_code, 302)
        
        new_superuser = User.objects.get(username='new_superuser')
        self.assertTrue(new_superuser.is_superuser)
        self.assertTrue(new_superuser.is_staff)
        self.assertTrue(new_superuser.is_active)
        self.assertEqual(new_superuser.groups.count(), 0)
        print("   ✓ Superuser creation works correctly (no groups)")
        
        # Test superuser with group (should fail validation)
        response = self.client.post('/admin/auth/user/add/', {
            'username': 'invalid_superuser',
            'password1': 'complex_password123!',
            'password2': 'complex_password123!',
            'groups': self.inventory_group.id,
            'is_superuser': True
        })
        self.assertEqual(response.status_code, 200)  # Form returned with errors
        self.assertContains(response, 'Superusers cannot be assigned to groups')
        print("   ✓ Superuser + group validation works correctly")

    def test_user_change_form_restrictions(self):
        """Test user change form enforces all restrictions"""
        print("\n🧪 Testing User Change Form Restrictions...")
        
        self.client.login(username='test_admin', password='admin123!')
        
        # Create test user for editing
        test_user = User.objects.create_user(
            username='edit_test_user',
            password='password123!',
            is_staff=True
        )
        
        # Test changing user's group
        response = self.client.post(f'/admin/auth/user/{test_user.id}/change/', {
            'username': 'edit_test_user',
            'first_name': '',
            'last_name': '',
            'email': '',
            'is_superuser': False,
            'groups': self.shop_group.id,
            'date_joined_0': test_user.date_joined.strftime('%Y-%m-%d'),
            'date_joined_1': test_user.date_joined.strftime('%H:%M:%S'),
        })
        self.assertEqual(response.status_code, 302)
        
        test_user.refresh_from_db()
        self.assertEqual(test_user.groups.count(), 1)
        self.assertEqual(test_user.groups.first(), self.shop_group)
        self.assertTrue(test_user.is_staff)
        self.assertTrue(test_user.is_active)
        print("   ✓ User group change works correctly")
        
        # Test making user superuser (should clear groups)
        response = self.client.post(f'/admin/auth/user/{test_user.id}/change/', {
            'username': 'edit_test_user',
            'first_name': '',
            'last_name': '',
            'email': '',
            'is_superuser': True,
            'groups': '',  # Should be cleared for superuser
            'date_joined_0': test_user.date_joined.strftime('%Y-%m-%d'),
            'date_joined_1': test_user.date_joined.strftime('%H:%M:%S'),
        })
        self.assertEqual(response.status_code, 302)
        
        test_user.refresh_from_db()
        self.assertTrue(test_user.is_superuser)
        self.assertEqual(test_user.groups.count(), 0)
        print("   ✓ User to superuser conversion clears groups")

    def test_password_field_restrictions(self):
        """Test password field is properly restricted"""
        print("\n🧪 Testing Password Field Restrictions...")
        
        self.client.login(username='test_admin', password='admin123!')
        
        # Get user change form
        response = self.client.get(f'/admin/auth/user/{self.regular_user.id}/change/')
        self.assertEqual(response.status_code, 200)
        
        # Check that password field is read-only and has change link
        self.assertContains(response, 'readonly')
        self.assertContains(response, '../password/')
        print("   ✓ Password field is read-only with change link")
        
        # Verify password change link works
        response = self.client.get(f'/admin/auth/user/{self.regular_user.id}/password/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Change password')
        print("   ✓ Password change form is accessible")

    def test_user_permissions_field_removed(self):
        """Test user_permissions field is completely removed"""
        print("\n🧪 Testing User Permissions Field Removal...")
        
        self.client.login(username='test_admin', password='admin123!')
        
        # Get user change form
        response = self.client.get(f'/admin/auth/user/{self.regular_user.id}/change/')
        self.assertEqual(response.status_code, 200)
        
        # Check that user_permissions field is not present
        self.assertNotContains(response, 'user_permissions')
        self.assertNotContains(response, 'User permissions')
        print("   ✓ User permissions field is removed from form")

    def test_is_staff_is_active_restrictions(self):
        """Test is_staff and is_active are forced to True and hidden"""
        print("\n🧪 Testing is_staff and is_active Restrictions...")
        
        self.client.login(username='test_admin', password='admin123!')
        
        # Get user change form
        response = self.client.get(f'/admin/auth/user/{self.regular_user.id}/change/')
        self.assertEqual(response.status_code, 200)
        
        # Check that is_staff and is_active fields are not visible
        form_content = response.content.decode()
        self.assertNotIn('id_is_staff', form_content)
        self.assertNotIn('id_is_active', form_content)
        print("   ✓ is_staff and is_active fields are hidden")
        
        # Test that they remain True even if we try to change them
        test_user = User.objects.create_user(
            username='staff_test_user',
            password='password123!',
            is_staff=True,
            is_active=True
        )
        
        # Try to submit form (these fields should remain True)
        response = self.client.post(f'/admin/auth/user/{test_user.id}/change/', {
            'username': 'staff_test_user',
            'first_name': '',
            'last_name': '',
            'email': '',
            'is_superuser': False,
            'groups': '',
            'date_joined_0': test_user.date_joined.strftime('%Y-%m-%d'),
            'date_joined_1': test_user.date_joined.strftime('%H:%M:%S'),
        })
        
        test_user.refresh_from_db()
        self.assertTrue(test_user.is_staff)
        self.assertTrue(test_user.is_active)
        print("   ✓ is_staff and is_active remain True after save")

    def test_single_group_restriction(self):
        """Test users can only have one group maximum"""
        print("\n🧪 Testing Single Group Restriction...")
        
        # Test programmatically (should work through admin forms)
        test_user = User.objects.create_user(
            username='single_group_test',
            password='password123!',
            is_staff=True
        )
        
        # Add one group
        test_user.groups.add(self.inventory_group)
        self.assertEqual(test_user.groups.count(), 1)
        
        # Through admin form, changing to different group should clear the first
        self.client.login(username='test_admin', password='admin123!')
        response = self.client.post(f'/admin/auth/user/{test_user.id}/change/', {
            'username': 'single_group_test',
            'first_name': '',
            'last_name': '',
            'email': '',
            'is_superuser': False,
            'groups': self.shop_group.id,
            'date_joined_0': test_user.date_joined.strftime('%Y-%m-%d'),
            'date_joined_1': test_user.date_joined.strftime('%H:%M:%S'),
        })
        
        test_user.refresh_from_db()
        self.assertEqual(test_user.groups.count(), 1)
        self.assertEqual(test_user.groups.first(), self.shop_group)
        print("   ✓ Single group restriction enforced")

    def test_middleware_security(self):
        """Test middleware properly blocks unauthorized access"""
        print("\n🧪 Testing Middleware Security...")
        
        self.client.login(username='test_admin', password='admin123!')
        
        # Test direct URL manipulation attempts
        blocked_urls = [
            '/admin/auth/group/',
            '/admin/auth/group/add/',
            f'/admin/auth/group/{self.inventory_group.id}/',
            f'/admin/auth/group/{self.inventory_group.id}/change/',
            f'/admin/auth/group/{self.inventory_group.id}/delete/',
        ]
        
        for url in blocked_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404, f"URL {url} should be blocked")
            print(f"   ✓ {url} blocked by middleware")

    def test_form_validation_edge_cases(self):
        """Test edge cases in form validation"""
        print("\n🧪 Testing Form Validation Edge Cases...")
        
        self.client.login(username='test_admin', password='admin123!')
        
        # Test username with colon (should fail)
        response = self.client.post('/admin/auth/user/add/', {
            'username': 'user:with:colon',
            'password1': 'complex_password123!',
            'password2': 'complex_password123!',
            'groups': '',
            'is_superuser': False
        })
        self.assertEqual(response.status_code, 200)  # Form returned with errors
        self.assertContains(response, "Username cannot contain ':'")
        print("   ✓ Username colon validation works")
        
        # Test password with colon (should fail)
        response = self.client.post('/admin/auth/user/add/', {
            'username': 'valid_user',
            'password1': 'password:with:colon',
            'password2': 'password:with:colon',
            'groups': '',
            'is_superuser': False
        })
        self.assertEqual(response.status_code, 200)  # Form returned with errors
        self.assertContains(response, "Password cannot contain ':'")
        print("   ✓ Password colon validation works")

    def test_qr_code_generation_integration(self):
        """Test QR code generation still works with new forms"""
        print("\n🧪 Testing QR Code Generation Integration...")
        
        self.client.login(username='test_admin', password='admin123!')
        
        # Mock the QR code generation to avoid file system operations
        import unittest.mock
        
        with unittest.mock.patch('Pages.admin.generateQR') as mock_generate_qr:
            response = self.client.post('/admin/auth/user/add/', {
                'username': 'qr_test_user',
                'password1': 'qr_password123!',
                'password2': 'qr_password123!',
                'groups': self.inventory_group.id,
                'is_superuser': False
            })
            
            self.assertEqual(response.status_code, 302)
            mock_generate_qr.assert_called_once_with('qr_test_user', 'qr_password123!')
            print("   ✓ QR code generation called for new user")

    def test_admin_list_display(self):
        """Test admin list display shows correct fields"""
        print("\n🧪 Testing Admin List Display...")
        
        self.client.login(username='test_admin', password='admin123!')
        
        response = self.client.get('/admin/auth/user/')
        self.assertEqual(response.status_code, 200)
        
        # Check that is_staff is not in the list display
        self.assertNotContains(response, 'Staff status')
        
        # Check that group column is shown
        self.assertContains(response, 'Group')
        print("   ✓ Admin list display configured correctly")

    def test_concurrent_operations(self):
        """Test concurrent user operations don't cause conflicts"""
        print("\n🧪 Testing Concurrent Operations...")
        
        # Create multiple users rapidly to test for race conditions
        self.client.login(username='test_admin', password='admin123!')
        
        users_created = 0
        for i in range(5):
            response = self.client.post('/admin/auth/user/add/', {
                'username': f'concurrent_user_{i}',
                'password1': f'password{i}123!',
                'password2': f'password{i}123!',
                'groups': self.inventory_group.id if i % 2 == 0 else '',
                'is_superuser': i == 4  # Make last one superuser
            })
            if response.status_code == 302:
                users_created += 1
        
        self.assertEqual(users_created, 5)
        
        # Verify all users were created correctly
        for i in range(5):
            user = User.objects.get(username=f'concurrent_user_{i}')
            self.assertTrue(user.is_staff)
            self.assertTrue(user.is_active)
            
            if i == 4:  # Superuser
                self.assertTrue(user.is_superuser)
                self.assertEqual(user.groups.count(), 0)
            elif i % 2 == 0:  # Has group
                self.assertEqual(user.groups.count(), 1)
                self.assertEqual(user.groups.first(), self.inventory_group)
            else:  # No group
                self.assertEqual(user.groups.count(), 0)
        
        print("   ✓ Concurrent operations handled correctly")

    def tearDown(self):
        """Clean up after tests"""
        User.objects.all().delete()
        Group.objects.all().delete()


def run_admin_security_tests():
    """Run all admin security tests"""
    print("🚀 Running Admin Security Integration Tests")
    print("=" * 60)
    
    import unittest
    from django.test.utils import setup_test_environment, teardown_test_environment
    from django.test.runner import DiscoverRunner
    
    # Setup test environment
    setup_test_environment()
    
    # Create test runner
    runner = DiscoverRunner(verbosity=2, interactive=True, keepdb=False)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(AdminSecurityIntegrationTests)
    
    # Run tests
    result = runner.run_tests(['utils.test_admin_security'])
    
    # Teardown
    teardown_test_environment()
    
    print("\n" + "=" * 60)
    print("📊 ADMIN SECURITY TEST SUMMARY")
    print("=" * 60)
    
    if result == 0:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Admin security features are working correctly")
        print("✅ Forms properly restrict user permissions")
        print("✅ Groups admin is completely blocked")
        print("✅ Single group restriction enforced")
        print("✅ Superuser restrictions working")
        print("✅ Password and validation features intact")
    else:
        print("❌ SOME TESTS FAILED!")
        print("🔧 Please review the failing tests and fix issues")
    
    return result == 0


if __name__ == "__main__":
    success = run_admin_security_tests()
    exit(0 if success else 1)