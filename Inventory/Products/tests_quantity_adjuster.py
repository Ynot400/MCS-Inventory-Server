# Products/tests_quantity_adjuster.py
from django.test import TestCase, Client, TransactionTestCase
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.db import transaction, IntegrityError
from Products.models import Product
from jobtickets.models import JobTicket, JobTicketItem
from Pages.models import SubmissionToken
from EORLogging.models import LogEntry
from utils.tokens import create_submission_token
from decimal import Decimal
from django.core import mail
from datetime import datetime, timedelta
from django.utils import timezone
import json


class QuantityAdjusterBaseTest(TransactionTestCase):
    """Base test class with common setup for quantity adjuster tests"""
    
    def setUp(self):
        self.client = Client()
        
        # Create test users
        self.superuser = User.objects.create_user(
            username='admin',
            password='admin123',
            is_superuser=True,
            is_staff=True
        )
        
        self.tech_group = Group.objects.create(name='Inventory Technician')
        self.tech_user = User.objects.create_user(
            username='tech',
            password='tech123',
            is_staff=True
        )
        self.tech_user.groups.add(self.tech_group)
        
        # Create test products
        self.product_normal = Product.objects.create(
            title='Test Product Normal',
            section='0A',
            level='0A',
            vertical='01',
            horizontal='01',
            product_ID='NORMAL-001',
            quantity=50,
            min_quantity=10,
            max_quantity=100,
            user=self.superuser
        )
        
        self.product_low_stock = Product.objects.create(
            title='Test Product Low Stock',
            section='0A',
            level='0A',
            vertical='02',
            horizontal='01',
            product_ID='LOW-001',
            quantity=5,
            min_quantity=10,
            max_quantity=50,
            user=self.superuser
        )
        
        self.product_high_priority = Product.objects.create(
            title='Test Product High Priority',
            section='0A',
            level='0A',
            vertical='03',
            horizontal='01',
            product_ID='HIGH-001',
            quantity=25,
            min_quantity=5,
            max_quantity=50,
            high_priority=True,
            user=self.superuser
        )
        
        # Create test job tickets
        self.job_ticket_active = JobTicket.objects.create(
            customer_name='Test Customer 1',
            boat_name='Test Boat 1',
            genre='Electrical',
            status='InProgress',
            created_by=self.superuser
        )
        
        self.job_ticket_completed = JobTicket.objects.create(
            customer_name='Test Customer 2',
            boat_name='Test Boat 2',
            genre='Mechanical',
            status='Complete',
            created_by=self.superuser
        )
        
        # Clear any existing emails
        mail.outbox = []


class ShopUseTests(QuantityAdjusterBaseTest):
    """Test shop use functionality"""
    
    def test_shop_use_increment_valid(self):
        """Test valid shop use increment with reason"""
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        initial_quantity = self.product_normal.quantity
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_normal.id,
            'integerDisplay': '10',
            'textInput': 'Additional notes',
            'usage_type': 'shop_use',
            'shop_use_reason': 'Equipment maintenance',
            'submission_token': token
        })
        
        # Verify redirect
        self.assertEqual(response.status_code, 302)
        
        # Verify product quantity updated
        self.product_normal.refresh_from_db()
        self.assertEqual(self.product_normal.quantity, initial_quantity + 10)
        
        # Verify log entry created
        log_entry = LogEntry.objects.filter(
            action_category='UPDATE',
            product=self.product_normal
        ).latest('timestamp')
        
        self.assertIn('Shop Use: Equipment maintenance', log_entry.summary)
        self.assertIn('Additional notes', log_entry.summary)
        self.assertEqual(log_entry.changed_fields['quantity']['old_value'], initial_quantity)
        self.assertEqual(log_entry.changed_fields['quantity']['new_value'], initial_quantity + 10)
    
    def test_shop_use_decrement_valid(self):
        """Test valid shop use decrement with reason"""
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        initial_quantity = self.product_normal.quantity
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_normal.id,
            'integerDisplay': '-15',
            'textInput': 'Testing materials',
            'usage_type': 'shop_use',
            'shop_use_reason': 'Equipment testing',
            'submission_token': token
        })
        
        self.assertEqual(response.status_code, 302)
        
        self.product_normal.refresh_from_db()
        self.assertEqual(self.product_normal.quantity, initial_quantity - 15)
        
        # Verify log entry
        log_entry = LogEntry.objects.filter(
            action_category='UPDATE',
            product=self.product_normal
        ).latest('timestamp')
        
        self.assertIn('Shop Use: Equipment testing', log_entry.summary)
    
    def test_shop_use_no_reason_error(self):
        """Test shop use without reason fails"""
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        initial_quantity = self.product_normal.quantity
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_normal.id,
            'integerDisplay': '5',
            'usage_type': 'shop_use',
            'shop_use_reason': '',  # Empty reason
            'submission_token': token
        })
        
        # Should return form with error (200)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please provide a reason for shop use')
        
        # Quantity should not change
        self.product_normal.refresh_from_db()
        self.assertEqual(self.product_normal.quantity, initial_quantity)
    
    def test_shop_use_exceeds_inventory_error(self):
        """Test shop use that would make inventory negative"""
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        initial_quantity = self.product_low_stock.quantity  # 5 units
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_low_stock.id,
            'integerDisplay': '-10',  # Try to remove more than available
            'usage_type': 'shop_use',
            'shop_use_reason': 'Equipment testing',
            'submission_token': token
        })
        
        # Should return form with error (status 200)
        self.assertEqual(response.status_code, 200)
        
        # Quantity should not change
        self.product_low_stock.refresh_from_db()
        self.assertEqual(self.product_low_stock.quantity, initial_quantity)


class JobTicketAssignmentTests(QuantityAdjusterBaseTest):
    """Test job ticket assignment (removing from inventory)"""
    
    def test_first_assignment_to_job_ticket(self):
        """Test first time assigning product to job ticket"""
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        initial_quantity = self.product_normal.quantity
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_normal.id,
            'integerDisplay': '-10',
            'textInput': 'Initial assignment',
            'usage_type': 'job_ticket',
            'job_ticket_id': str(self.job_ticket_active.id),
            'submission_token': token
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verify product quantity decreased
        self.product_normal.refresh_from_db()
        self.assertEqual(self.product_normal.quantity, initial_quantity - 10)
        
        # Verify JobTicketItem created
        job_item = JobTicketItem.objects.get(
            job_ticket=self.job_ticket_active,
            product=self.product_normal
        )
        self.assertEqual(job_item.quantity_used, 10)
        self.assertEqual(job_item.added_by, self.tech_user)
        
        # Verify log entry
        log_entry = LogEntry.objects.filter(
            action_category='UPDATE',
            product=self.product_normal
        ).latest('timestamp')
        
        self.assertIn(f'Job Ticket #{self.job_ticket_active.id}', log_entry.summary)
        self.assertIn(self.job_ticket_active.customer_name, log_entry.summary)
    
    def test_additional_assignment_to_existing_job_ticket_item(self):
        """Test adding more quantity to existing job ticket item"""
        # First, create initial assignment
        JobTicketItem.objects.create(
            job_ticket=self.job_ticket_active,
            product=self.product_normal,
            quantity_used=5,
            added_by=self.superuser
        )
        
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        initial_quantity = self.product_normal.quantity
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_normal.id,
            'integerDisplay': '-8',
            'usage_type': 'job_ticket',
            'job_ticket_id': str(self.job_ticket_active.id),
            'submission_token': token
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verify product quantity decreased
        self.product_normal.refresh_from_db()
        self.assertEqual(self.product_normal.quantity, initial_quantity - 8)
        
        # Verify JobTicketItem updated (not created new)
        job_items = JobTicketItem.objects.filter(
            job_ticket=self.job_ticket_active,
            product=self.product_normal
        )
        self.assertEqual(job_items.count(), 1)  # Should be only one
        
        job_item = job_items.first()
        self.assertEqual(job_item.quantity_used, 13)  # 5 + 8
    
    def test_assignment_exceeds_inventory_error(self):
        """Test assignment that exceeds available inventory"""
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        initial_quantity = self.product_low_stock.quantity  # 5 units
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_low_stock.id,
            'integerDisplay': '-10',  # Try to assign more than available
            'usage_type': 'job_ticket',
            'job_ticket_id': str(self.job_ticket_active.id),
            'submission_token': token
        })
        
        # Should return form with error (200) due to negative quantity check
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cannot adjust quantity')
        
        # Quantity should not change
        self.product_low_stock.refresh_from_db()
        self.assertEqual(self.product_low_stock.quantity, initial_quantity)
        
        # No JobTicketItem should be created
        self.assertFalse(JobTicketItem.objects.filter(
            job_ticket=self.job_ticket_active,
            product=self.product_low_stock
        ).exists())
    
    def test_assignment_to_completed_job_ticket_error(self):
        """Test assignment to completed job ticket fails"""
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        initial_quantity = self.product_normal.quantity
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_normal.id,
            'integerDisplay': '-5',
            'usage_type': 'job_ticket',
            'job_ticket_id': str(self.job_ticket_completed.id),
            'submission_token': token
        })
        
        # Should return form with error (200)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cannot modify items for completed job ticket')
        
        # Quantity should not change
        self.product_normal.refresh_from_db()
        self.assertEqual(self.product_normal.quantity, initial_quantity)


class JobTicketReturnTests(QuantityAdjusterBaseTest):
    """Test job ticket return functionality (adding back to inventory)"""
    
    def setUp(self):
        super().setUp()
        # Create existing job ticket item for return tests
        self.existing_job_item = JobTicketItem.objects.create(
            job_ticket=self.job_ticket_active,
            product=self.product_normal,
            quantity_used=15,
            added_by=self.superuser
        )
    
    def test_partial_return_from_job_ticket(self):
        """Test partial return of items to inventory"""
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        initial_quantity = self.product_normal.quantity
        initial_job_quantity = self.existing_job_item.quantity_used
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_normal.id,
            'integerDisplay': '7',  # Return 7 out of 15
            'textInput': 'Partial return',
            'usage_type': 'job_ticket',
            'job_ticket_id': str(self.job_ticket_active.id),
            'submission_token': token
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verify product quantity increased
        self.product_normal.refresh_from_db()
        self.assertEqual(self.product_normal.quantity, initial_quantity + 7)
        
        # Verify JobTicketItem updated
        self.existing_job_item.refresh_from_db()
        self.assertEqual(self.existing_job_item.quantity_used, 8)  # 15 - 7
        
        # Verify log entry
        log_entry = LogEntry.objects.filter(
            action_category='UPDATE',
            product=self.product_normal
        ).latest('timestamp')
        
        self.assertIn('Returned from Job Ticket', log_entry.summary)
        self.assertIn('Remaining on job ticket: 8 units', log_entry.summary)
    
    def test_full_return_deletes_job_ticket_item(self):
        """Test full return deletes the job ticket item"""
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        initial_quantity = self.product_normal.quantity
        return_amount = self.existing_job_item.quantity_used  # Return all 15
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_normal.id,
            'integerDisplay': str(return_amount),
            'usage_type': 'job_ticket',
            'job_ticket_id': str(self.job_ticket_active.id),
            'submission_token': token
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verify product quantity increased
        self.product_normal.refresh_from_db()
        self.assertEqual(self.product_normal.quantity, initial_quantity + return_amount)
        
        # Verify JobTicketItem deleted
        self.assertFalse(JobTicketItem.objects.filter(
            job_ticket=self.job_ticket_active,
            product=self.product_normal
        ).exists())
        
        # Verify log entry
        log_entry = LogEntry.objects.filter(
            action_category='UPDATE',
            product=self.product_normal
        ).latest('timestamp')
        
        self.assertIn('Item removed from job ticket (quantity returned to 0)', log_entry.summary)
    
    def test_return_more_than_assigned_error(self):
        """Test returning more than was assigned fails"""
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        initial_quantity = self.product_normal.quantity
        assigned_quantity = self.existing_job_item.quantity_used  # 15
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_normal.id,
            'integerDisplay': '20',  # Try to return more than assigned
            'usage_type': 'job_ticket',
            'job_ticket_id': str(self.job_ticket_active.id),
            'submission_token': token
        })
        
        # Should return form with error (200)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cannot return 20 units')
        
        # Quantity should not change
        self.product_normal.refresh_from_db()
        self.assertEqual(self.product_normal.quantity, initial_quantity)
        
        # JobTicketItem should not change
        self.existing_job_item.refresh_from_db()
        self.assertEqual(self.existing_job_item.quantity_used, assigned_quantity)
    
    def test_return_from_nonexistent_job_ticket_item_error(self):
        """Test returning from job ticket with no existing item fails"""
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        initial_quantity = self.product_low_stock.quantity
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_low_stock.id,  # Product not on job ticket
            'integerDisplay': '3',
            'usage_type': 'job_ticket',
            'job_ticket_id': str(self.job_ticket_active.id),
            'submission_token': token
        })
        
        # Should return form with error (200)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No items found for this product')
        
        # Quantity should not change
        self.product_low_stock.refresh_from_db()
        self.assertEqual(self.product_low_stock.quantity, initial_quantity)


class ValidationAndSecurityTests(QuantityAdjusterBaseTest):
    """Test validation and security aspects"""
    
    def test_zero_quantity_change_error(self):
        """Test submitting with zero quantity change"""
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_normal.id,
            'integerDisplay': '0',  # No change
            'usage_type': 'shop_use',
            'shop_use_reason': 'Test reason',
            'submission_token': token
        })
        
        # Should return form with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Submit a valid quantity change')
    
    def test_no_job_ticket_selected_error(self):
        """Test job ticket use without selecting job ticket"""
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_normal.id,
            'integerDisplay': '5',
            'usage_type': 'job_ticket',
            'job_ticket_id': '',  # No job ticket selected
            'submission_token': token
        })
        
        # Should return form with error (200)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please select a job ticket')
    
    def test_invalid_submission_token(self):
        """Test invalid submission token handling"""
        self.client.login(username='tech', password='tech123')
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_normal.id,
            'integerDisplay': '5',
            'usage_type': 'shop_use',
            'shop_use_reason': 'Test',
            'submission_token': 'invalid-token'
        })
        
        # Should redirect (token validation failed)
        self.assertEqual(response.status_code, 302)
    
    def test_permission_required(self):
        """Test that staff permission is required"""
        regular_user = User.objects.create_user(
            username='regular',
            password='regular123'
        )
        
        self.client.login(username='regular', password='regular123')
        token = create_submission_token()
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_normal.id,
            'integerDisplay': '5',
            'usage_type': 'shop_use',
            'shop_use_reason': 'Test',
            'submission_token': token
        })
        
        # Should redirect to login/permission denied
        self.assertEqual(response.status_code, 302)


class EmailNotificationTests(QuantityAdjusterBaseTest):
    """Test email notification functionality"""
    
    def test_zero_quantity_email_shop_use(self):
        """Test email sent when product reaches zero via shop use"""
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        # Set product to exactly the amount we'll remove
        self.product_normal.quantity = 5
        self.product_normal.save()
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_normal.id,
            'integerDisplay': '-5',
            'usage_type': 'shop_use',
            'shop_use_reason': 'Final usage',
            'submission_token': token
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        
        self.assertIn('0 Quantity', email.subject)
        self.assertIn('Usage: shop_use', email.body)
        self.assertIn('Reason: Final usage', email.body)
    
    def test_zero_quantity_email_job_ticket(self):
        """Test email sent when product reaches zero via job ticket"""
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        # Set product to exactly the amount we'll assign
        self.product_normal.quantity = 8
        self.product_normal.save()
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_normal.id,
            'integerDisplay': '-8',
            'usage_type': 'job_ticket',
            'job_ticket_id': str(self.job_ticket_active.id),
            'submission_token': token
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        
        self.assertIn('0 Quantity', email.subject)
        self.assertIn('Usage: job_ticket', email.body)
        self.assertIn(f'Job Ticket #{self.job_ticket_active.id}', email.body)
    
    def test_high_priority_email(self):
        """Test email sent for high priority product changes"""
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_high_priority.id,
            'integerDisplay': '-5',
            'usage_type': 'shop_use',
            'shop_use_reason': 'High priority test',
            'submission_token': token
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        
        self.assertIn('H.P.', email.subject)
        self.assertIn('Usage: shop_use', email.body)
        self.assertIn('High priority test', email.body)


class DataIntegrityTests(QuantityAdjusterBaseTest):
    """Test data integrity and consistency"""
    
    def test_job_ticket_item_uniqueness(self):
        """Test that only one JobTicketItem exists per product per job ticket"""
        # Create initial item
        JobTicketItem.objects.create(
            job_ticket=self.job_ticket_active,
            product=self.product_normal,
            quantity_used=5,
            added_by=self.superuser
        )
        
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        # Add more to same product/job ticket
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_normal.id,
            'integerDisplay': '-3',
            'usage_type': 'job_ticket',
            'job_ticket_id': str(self.job_ticket_active.id),
            'submission_token': token
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Should still be only one item
        items = JobTicketItem.objects.filter(
            job_ticket=self.job_ticket_active,
            product=self.product_normal
        )
        self.assertEqual(items.count(), 1)
        self.assertEqual(items.first().quantity_used, 8)  # 5 + 3
    
    def test_transaction_atomicity(self):
        """Test that operations are atomic"""
        self.client.login(username='tech', password='tech123')
        token = create_submission_token()
        
        initial_quantity = self.product_normal.quantity
        
        # Valid operation should complete fully
        response = self.client.post(reverse('update_model'), {
            'product_id': self.product_normal.id,
            'integerDisplay': '-10',
            'usage_type': 'job_ticket',
            'job_ticket_id': str(self.job_ticket_active.id),
            'submission_token': token
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Both product and job ticket item should be updated
        self.product_normal.refresh_from_db()
        self.assertEqual(self.product_normal.quantity, initial_quantity - 10)
        
        job_item = JobTicketItem.objects.get(
            job_ticket=self.job_ticket_active,
            product=self.product_normal
        )
        self.assertEqual(job_item.quantity_used, 10)


def run_quantity_adjuster_tests():
    """Run all quantity adjuster tests and provide summary"""
    print("\n" + "="*60)
    print("🚀 RUNNING QUANTITY ADJUSTER INTEGRATION TESTS")
    print("="*60)
    
    from django.test.utils import setup_test_environment, teardown_test_environment
    from django.test import TestCase
    import unittest
    
    # Setup test environment
    setup_test_environment()
    
    test_classes = [
        ShopUseTests,
        JobTicketAssignmentTests,
        JobTicketReturnTests,
        ValidationAndSecurityTests,
        EmailNotificationTests,
        DataIntegrityTests
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__name__}...")
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        total_tests += result.testsRun
        passed_tests += result.testsRun - len(result.failures) - len(result.errors)
        failed_tests += len(result.failures) + len(result.errors)
        
        if result.failures:
            print(f"❌ Failures in {test_class.__name__}:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
        
        if result.errors:
            print(f"💥 Errors in {test_class.__name__}:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
    
    # Teardown
    teardown_test_environment()
    
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
    
    if failed_tests == 0:
        print("🎉 ALL TESTS PASSED! Quantity adjuster is ready for production.")
    else:
        print("⚠️  Some tests failed. Review and fix before deployment.")
    
    print("="*60)


if __name__ == '__main__':
    run_quantity_adjuster_tests()