# Products/tests.py
from django.test import TestCase, Client, TransactionTestCase
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.db import transaction, IntegrityError
from Products.models import Product
from Pages.models import SubmissionToken
from EORLogging.models import LogEntry
from utils.tokens import create_submission_token
from decimal import Decimal
import json
import time
from concurrent.futures import ThreadPoolExecutor
import threading


class ProductModelTests(TestCase):
    """Test Product model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_superuser=True
        )
        
    def test_product_creation(self):
        """Test basic product creation"""
        print("\n🧪 Testing Product Creation...")
        product = Product.objects.create(
            title='Test Product',
            section='0A',
            level='0A',
            vertical='01',
            horizontal='01',
            is_structured=True,
            product_ID='TEST-001',
            quantity=10,
            min_quantity=5,
            max_quantity=20,
            vendor='Test Vendor',
            user=self.user
        )
        
        self.assertIsNotNone(product.barcode)
        self.assertEqual(product.location_ID, '0A-0A-01-01')
        self.assertTrue(10**11 <= product.barcode <= 10**12 - 1)
        print(f"   ✅ Product created with barcode: {product.barcode}")
        
    def test_barcode_uniqueness(self):
        """Test that barcodes are unique"""
        print("\n🧪 Testing Barcode Uniqueness...")
        products = []
        for i in range(100):
            product = Product.objects.create(
                title=f'Product {i}',
                section='0A',
                level='0A',
                vertical=f'{i:02}',
                horizontal='01',
                is_structured=True,
                product_ID=f'TEST-{i:03}',
                quantity=10,
                user=self.user
            )
            products.append(product)
        
        barcodes = [p.barcode for p in products]
        unique_barcodes = set(barcodes)
        self.assertEqual(len(barcodes), len(unique_barcodes))
        print(f"   ✅ Created {len(products)} products with unique barcodes")
        
    def test_location_validation(self):
        """Test location validation for structured vs unstructured"""
        print("\n🧪 Testing Location Validation...")
        
        # Test structured location (cubby)
        cubby = Product.objects.create(
            title='Cubby Product',
            section='0B',
            level='0B',
            vertical='02',
            horizontal='02',
            is_structured=True,
            product_ID='CUBBY-001',
            quantity=5,
            user=self.user
        )
        self.assertEqual(cubby.location_ID, '0B-0B-02-02')
        print("   ✅ Structured location validation passed")
        
        # Test unstructured location (shelf)
        shelf = Product.objects.create(
            title='Shelf Product',
            section='0C',
            level='0C',
            vertical='',
            horizontal='',
            is_structured=False,
            product_ID='SHELF-001',
            quantity=5,
            user=self.user
        )
        self.assertEqual(shelf.location_ID, '0C-0C-XX-XX')
        print("   ✅ Unstructured location validation passed")
        
    def test_duplicate_location_prevention(self):
        """Test that duplicate cubby locations are prevented"""
        print("\n🧪 Testing Duplicate Location Prevention...")
        
        Product.objects.create(
            title='First Product',
            section='0D',
            level='0D',
            vertical='03',
            horizontal='03',
            is_structured=True,
            product_ID='DUP-001',
            quantity=5,
            user=self.user
        )
        
        # Try to create another product in same cubby
        duplicate = Product(
            title='Duplicate Product',
            section='0D',
            level='0D',
            vertical='03',
            horizontal='03',
            is_structured=True,
            product_ID='DUP-002',
            quantity=5,
            user=self.user
        )
        
        with self.assertRaises(Exception):
            duplicate.clean()
        print("   ✅ Duplicate cubby location correctly prevented")
        
    def test_quantity_validators(self):
        """Test min/max quantity validation"""
        print("\n🧪 Testing Quantity Validators...")
        
        product = Product.objects.create(
            title='Quantity Test',
            section='0E',
            level='0E',
            product_ID='QTY-001',
            quantity=10,
            min_quantity=5,
            max_quantity=20,
            user=self.user
        )
        
        self.assertFalse(product.is_below_min())
        self.assertFalse(product.is_above_max())
        
        product.quantity = 3
        self.assertTrue(product.is_below_min())
        
        product.quantity = 25
        self.assertTrue(product.is_above_max())
        print("   ✅ Quantity validators working correctly")
        
    def test_manufacturer_barcode_constraints(self):
        """Test manufacturer barcode validation"""
        print("\n🧪 Testing Manufacturer Barcode Constraints...")
        
        # Valid barcode
        product1 = Product.objects.create(
            title='Mfg Barcode Test 1',
            section='0F',
            level='0F',
            product_ID='MFG-001',
            quantity=5,
            manufacturer_barcode='ABC-123-DEF',
            user=self.user
        )
        self.assertEqual(product1.manufacturer_barcode, 'ABC-123-DEF')
        print("   ✅ Valid manufacturer barcode accepted")
        
        # Test uniqueness
        with self.assertRaises(IntegrityError):
            Product.objects.create(
                title='Mfg Barcode Test 2',
                section='0G',
                level='0G',
                product_ID='MFG-002',
                quantity=5,
                manufacturer_barcode='ABC-123-DEF',  # Duplicate
                user=self.user
            )
        print("   ✅ Duplicate manufacturer barcode correctly rejected")


class ProductViewTests(TransactionTestCase):
    """Test Product views with transaction support"""
    
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_user(
            username='admin',
            password='admin123',
            is_superuser=True,
            is_staff=True
        )
        
        # Create inventory technician group and user
        self.tech_group = Group.objects.create(name='Inventory Technician')
        self.tech_user = User.objects.create_user(
            username='tech',
            password='tech123'
        )
        self.tech_user.groups.add(self.tech_group)
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username='regular',
            password='regular123'
        )
        
    def test_add_product_permissions(self):
        """Test add product view permissions"""
        print("\n🧪 Testing Add Product Permissions...")
        
        url = reverse('add-product')
        
        # Test anonymous user
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        print("   ✅ Anonymous user correctly redirected")
        
        # Test regular user
        self.client.login(username='regular', password='regular123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        print("   ✅ Regular user correctly denied access")
        
        # Test tech user
        self.client.login(username='tech', password='tech123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        print("   ✅ Tech user granted access")
        
        # Test superuser
        self.client.login(username='admin', password='admin123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        print("   ✅ Superuser granted access")
        
    def test_product_creation_flow(self):
        """Test complete product creation flow"""
        print("\n🧪 Testing Product Creation Flow...")
        
        self.client.login(username='admin', password='admin123')
        token = create_submission_token()
        
        data = {
            'title': 'Flow Test Product',
            'description': 'Test description',
            'product_ID': 'FLOW-001',
            'quantity': 10,
            'min_quantity': 5,
            'max_quantity': 20,
            'vendor': 'Test Vendor',
            'section': '0A',
            'level': '0A',
            'vertical': '01',
            'horizontal': '01',
            'is_structured': True,
            'high_priority': False,
            'admin_field_price1': '10.50',
            'admin_field_price2': '5.25',
            'submission_token': token
        }
        
        response = self.client.post(reverse('add-product'), data)
        self.assertEqual(response.status_code, 302)
        
        # Verify product was created
        product = Product.objects.get(product_ID='FLOW-001')
        self.assertEqual(product.title, 'Flow Test Product')
        self.assertEqual(product.admin_field_price1, Decimal('10.50'))
        
        # Verify log entry was created
        log = LogEntry.objects.filter(
            action_category='CREATE',
            product=product
        ).first()
        self.assertIsNotNone(log)
        print("   ✅ Product creation flow completed successfully")
        
    def test_product_update_flow(self):
        """Test complete product update flow"""
        print("\n🧪 Testing Product Update Flow...")
        
        self.client.login(username='admin', password='admin123')
        
        # Create product first
        product = Product.objects.create(
            title='Update Test',
            section='0B',
            level='0B',
            product_ID='UPDATE-001',
            quantity=10,
            min_quantity=5,
            max_quantity=20,
            user=self.superuser
        )
        
        token = create_submission_token()
        
        data = {
            'title': 'Updated Product',
            'description': 'Updated description',
            'product_ID': 'UPDATE-001-MOD',
            'quantity': 15,
            'min_quantity': 8,
            'max_quantity': 25,
            'vendor': 'Updated Vendor',
            'section': '0B',
            'level': '0B',
            'vertical': '',
            'horizontal': '',
            'is_structured': False,
            'high_priority': True,
            'admin_field_price1': '12.00',
            'admin_field_price2': '6.00',
            'submission_token': token
        }
        
        response = self.client.post(
            reverse('edit-product', kwargs={'pk': product.pk}),
            data
        )
        self.assertEqual(response.status_code, 302)
        
        # Verify updates
        product.refresh_from_db()
        self.assertEqual(product.title, 'Updated Product')
        self.assertEqual(product.quantity, 15)
        self.assertTrue(product.high_priority)
        
        # Verify log entry
        log = LogEntry.objects.filter(
            action_category='UPDATE',
            product=product
        ).first()
        self.assertIsNotNone(log)
        self.assertIn('Quantity', log.changed_fields)
        print("   ✅ Product update flow completed successfully")
        
    def test_product_deletion_flow(self):
        """Test product deletion with logging"""
        print("\n🧪 Testing Product Deletion Flow...")
        
        self.client.login(username='admin', password='admin123')
        
        product = Product.objects.create(
            title='Delete Test',
            section='0C',
            level='0C',
            product_ID='DELETE-001',
            quantity=10,
            user=self.superuser
        )
        
        token = create_submission_token()
        
        response = self.client.post(
            reverse('delete-product', kwargs={'pk': product.pk}),
            {'submission_token': token}
        )
        self.assertEqual(response.status_code, 302)
        
        # Verify product was deleted
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
        
        # Verify log entry exists
        log = LogEntry.objects.filter(
            action_category='DELETE'
        ).first()
        self.assertIsNotNone(log)
        self.assertIn('Product Name', log.changed_fields)
        print("   ✅ Product deletion flow completed successfully")


class ProductLoadTests(TransactionTestCase):
    """Load testing for Product operations"""
    
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_user(
            username='loadtest',
            password='loadtest123',
            is_superuser=True,
            is_staff=True
        )
        
    def test_concurrent_product_creation(self):
        """Test concurrent product creation"""
        print("\n🧪 Testing Concurrent Product Creation...")
        
        def create_product(i):
            client = Client()
            client.login(username='loadtest', password='loadtest123')
            token = create_submission_token()
            
            data = {
                'title': f'Concurrent Product {i}',
                'description': f'Test description {i}',
                'product_ID': f'CONC-{i:03}',
                'quantity': 10,
                'min_quantity': 5,
                'max_quantity': 20,
                'vendor': 'Test Vendor',
                'section': '0A',
                'level': '0A',
                'vertical': f'{i%99:02}',
                'horizontal': '01',
                'is_structured': True,
                'high_priority': False,
                'submission_token': token
            }
            
            try:
                response = client.post(reverse('add-product'), data)
                return response.status_code == 302
            except Exception as e:
                print(f"   ❌ Error in thread {i}: {e}")
                return False
        
        # Run concurrent creations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_product, i) for i in range(50)]
            results = [f.result() for f in futures]
        
        successful = sum(results)
        print(f"   ✅ Successfully created {successful}/50 products concurrently")
        self.assertGreaterEqual(successful, 45)  # Allow some failures
        
    def test_high_volume_search(self):
        """Test search functionality under load"""
        print("\n🧪 Testing High Volume Search...")
        
        # Create many products
        print("   Creating 1000 test products...")
        products = []
        for i in range(1000):
            product = Product.objects.create(
                title=f'Search Test Product {i}',
                section=f'{i//100:02X}'[:2],
                level='0A',
                product_ID=f'SEARCH-{i:04}',
                quantity=10,
                vendor=f'Vendor {i%10}',
                user=self.superuser
            )
            products.append(product)
        
        self.client.login(username='loadtest', password='loadtest123')
        
        # Test various search scenarios
        search_tests = [
            {'product_name': 'Search Test Product 5'},
            {'vendor': 'Vendor 5'},
            {'product_ID': 'SEARCH-0500'},
            {'show_all': True},
        ]
        
        start_time = time.time()
        for i, search_params in enumerate(search_tests * 25):  # 100 searches
            response = self.client.get(reverse('inventory'), search_params)
            self.assertEqual(response.status_code, 200)
        
        duration = time.time() - start_time
        searches_per_second = 100 / duration
        print(f"   ✅ Completed 100 searches in {duration:.2f}s ({searches_per_second:.1f} searches/sec)")
        
    def test_barcode_scanning_load(self):
        """Test barcode scanning under load"""
        print("\n🧪 Testing Barcode Scanning Load...")
        
        # Create products with manufacturer barcodes
        products = []
        for i in range(100):
            product = Product.objects.create(
                title=f'Scan Test {i}',
                section='0A',
                level='0A',
                product_ID=f'SCAN-{i:03}',
                quantity=10,
                manufacturer_barcode=f'MFG-{i:06}',
                user=self.superuser
            )
            products.append(product)
        
        self.client.login(username='loadtest', password='loadtest123')
        
        # Simulate rapid scanning
        scan_results = []
        start_time = time.time()
        
        for product in products[:50]:  # Scan 50 products
            response = self.client.post(
                reverse('barcode-quantity'),
                {'scannedData': product.manufacturer_barcode}
            )
            scan_results.append(response.status_code == 200)
        
        duration = time.time() - start_time
        scans_per_second = 50 / duration
        successful_scans = sum(scan_results)
        
        print(f"   ✅ Completed {successful_scans}/50 scans in {duration:.2f}s ({scans_per_second:.1f} scans/sec)")
        self.assertEqual(successful_scans, 50)


class ProductIntegrityTests(TransactionTestCase):
    """Test data integrity under various conditions"""
    
    def setUp(self):
        self.superuser = User.objects.create_user(
            username='integrity',
            password='integrity123',
            is_superuser=True
        )
        
    def test_transaction_rollback_on_error(self):
        """Test that transactions properly rollback on error"""
        print("\n🧪 Testing Transaction Rollback...")
        
        initial_count = Product.objects.count()
        
        try:
            with transaction.atomic():
                # Create a product
                Product.objects.create(
                    title='Rollback Test',
                    section='0A',
                    level='0A',
                    product_ID='ROLL-001',
                    quantity=10,
                    user=self.superuser
                )
                
                # Force an error
                raise Exception("Simulated error")
        except Exception:
            pass
        
        # Verify rollback
        final_count = Product.objects.count()
        self.assertEqual(initial_count, final_count)
        print("   ✅ Transaction properly rolled back")
        
    def test_concurrent_quantity_updates(self):
        """Test concurrent quantity updates don't cause race conditions"""
        print("\n🧪 Testing Concurrent Quantity Updates...")
        
        product = Product.objects.create(
            title='Concurrent Update Test',
            section='0A',
            level='0A',
            product_ID='CONC-UPDATE-001',
            quantity=100,
            user=self.superuser
        )
        
        def update_quantity(amount):
            try:
                with transaction.atomic():
                    p = Product.objects.select_for_update().get(pk=product.pk)
                    p.quantity += amount
                    p.save()
                    return True
            except Exception as e:
                print(f"   ❌ Update error: {e}")
                return False
        
        # Run concurrent updates
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 5 threads add 10, 5 threads subtract 10
            futures = []
            for i in range(5):
                futures.append(executor.submit(update_quantity, 10))
                futures.append(executor.submit(update_quantity, -10))
            
            results = [f.result() for f in futures]
        
        # Verify final quantity is correct
        product.refresh_from_db()
        self.assertEqual(product.quantity, 100)
        print(f"   ✅ Concurrent updates handled correctly. Final quantity: {product.quantity}")
        
    def test_submission_token_security(self):
        """Test submission token security"""
        print("\n🧪 Testing Submission Token Security...")
        
        client = Client()
        client.login(username='integrity', password='integrity123')
        
        # Test reusing token
        token = create_submission_token()
        
        data = {
            'title': 'Token Test 1',
            'section': '0A',
            'level': '0A',
            'product_ID': 'TOKEN-001',
            'quantity': 10,
            'submission_token': token
        }
        
        # First use should succeed
        response = client.post(reverse('add-product'), data)
        self.assertEqual(response.status_code, 302)
        
        # Second use should fail
        data['product_ID'] = 'TOKEN-002'
        response = client.post(reverse('add-product'), data)
        self.assertEqual(response.status_code, 302)  # Redirects on token failure
        
        # Verify only one product was created
        self.assertEqual(Product.objects.filter(product_ID__startswith='TOKEN-').count(), 1)
        print("   ✅ Submission token security working correctly")


def run_all_product_tests():
    """Run all product tests and provide summary"""
    print("\n" + "="*60)
    print("🚀 RUNNING COMPREHENSIVE PRODUCT TESTS")
    print("="*60)
    
    from django.test.utils import setup_test_environment, teardown_test_environment
    from django.test import TestCase
    
    # Setup test environment
    setup_test_environment()
    
    test_classes = [
        ProductModelTests,
        ProductViewTests,
        ProductLoadTests,
        ProductIntegrityTests
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__name__}...")
        suite = TestCase.TestLoader().loadTestsFromTestCase(test_class)
        runner = TestCase.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        total_tests += result.testsRun
        passed_tests += result.testsRun - len(result.failures) - len(result.errors)
        failed_tests += len(result.failures) + len(result.errors)
    
    # Teardown
    teardown_test_environment()
    
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
    print("="*60)


if __name__ == '__main__':
    run_all_product_tests()