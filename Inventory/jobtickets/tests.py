# jobtickets/tests.py
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.http import JsonResponse
from .models import JobTicket
from Pages.models import SubmissionToken
from utils.tokens import create_submission_token
import json


class JobTicketViewTests(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create superuser
        self.superuser = User.objects.create_user(
            username='admin',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username='regular',
            password='testpass123'
        )
        
        # Create test job ticket
        self.job_ticket = JobTicket.objects.create(
            customer_name='Test Customer',
            boat_name='Test Boat',
            genre='Electrical',
            status='InProgress',
            created_by=self.superuser
        )
        
        self.client = Client()

    def test_dashboard_access_superuser(self):
        """Test dashboard access for superuser"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('jobticket-dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Customer')

    def test_dashboard_access_regular_user(self):
        """Test dashboard access denied for regular user"""
        self.client.login(username='regular', password='testpass123')
        response = self.client.get(reverse('jobticket-dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect

    def test_dashboard_access_anonymous(self):
        """Test dashboard access denied for anonymous user"""
        response = self.client.get(reverse('jobticket-dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_create_job_ticket_get_ajax(self):
        """Test getting create form via AJAX"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(
            reverse('create-jobticket'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('form_html', data)
        self.assertIn('submission_token', data['form_html'])

    def test_create_job_ticket_post_valid(self):
        """Test creating job ticket with valid data"""
        self.client.login(username='admin', password='testpass123')
        token = create_submission_token()
        
        response = self.client.post(
            reverse('create-jobticket'),
            {
                'customer_name': 'New Customer',
                'boat_name': 'New Boat',
                'genre': 'Mechanical',
                'status': 'InProgress',
                'submission_token': token
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('card_html', data)
        
        # Verify ticket was created
        self.assertTrue(JobTicket.objects.filter(customer_name='New Customer').exists())

    def test_create_job_ticket_post_invalid(self):
        """Test creating job ticket with invalid data"""
        self.client.login(username='admin', password='testpass123')
        token = create_submission_token()
        
        response = self.client.post(
            reverse('create-jobticket'),
            {
                'customer_name': '',  # Required field left empty
                'boat_name': 'New Boat',
                'genre': 'Mechanical',
                'submission_token': token
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('form_html', data)

    def test_create_job_ticket_no_token(self):
        """Test creating job ticket without submission token"""
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.post(
            reverse('create-jobticket'),
            {
                'customer_name': 'New Customer',
                'boat_name': 'New Boat',
                'genre': 'Mechanical',
                'status': 'InProgress'
                # No submission_token
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])

    def test_create_job_ticket_custom_genre(self):
        """Test creating job ticket with custom genre"""
        self.client.login(username='admin', password='testpass123')
        token = create_submission_token()
        
        response = self.client.post(
            reverse('create-jobticket'),
            {
                'customer_name': 'Custom Customer',
                'boat_name': 'Custom Boat',
                'genre': 'Custom',
                'custom_genre': 'Custom Work Type',
                'status': 'InProgress',
                'submission_token': token
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify custom genre was saved
        ticket = JobTicket.objects.get(customer_name='Custom Customer')
        self.assertEqual(ticket.effective_genre, 'Custom Work Type')

    def test_edit_job_ticket_get_ajax(self):
        """Test getting edit form via AJAX"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(
            reverse('edit-jobticket', kwargs={'pk': self.job_ticket.pk}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('form_html', data)

    def test_edit_job_ticket_post_valid(self):
        """Test editing job ticket with valid data"""
        self.client.login(username='admin', password='testpass123')
        token = create_submission_token()
        
        response = self.client.post(
            reverse('edit-jobticket', kwargs={'pk': self.job_ticket.pk}),
            {
                'customer_name': 'Updated Customer',
                'boat_name': 'Updated Boat',
                'genre': 'Mechanical',
                'status': 'Complete',
                'submission_token': token
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify changes were saved
        self.job_ticket.refresh_from_db()
        self.assertEqual(self.job_ticket.customer_name, 'Updated Customer')
        self.assertEqual(self.job_ticket.status, 'Complete')

    def test_delete_job_ticket(self):
        """Test deleting job ticket"""
        self.client.login(username='admin', password='testpass123')
        token = create_submission_token()
        ticket_id = self.job_ticket.pk
        
        response = self.client.post(
            reverse('delete-jobticket', kwargs={'pk': ticket_id}),
            {
                'submission_token': token
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify ticket was deleted
        self.assertFalse(JobTicket.objects.filter(pk=ticket_id).exists())

    def test_delete_nonexistent_job_ticket(self):
        """Test deleting non-existent job ticket"""
        self.client.login(username='admin', password='testpass123')
        token = create_submission_token()
        
        response = self.client.post(
            reverse('delete-jobticket', kwargs={'pk': 99999}),
            {
                'submission_token': token
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 404)

    def test_get_submission_token(self):
        """Test getting submission token endpoint"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(
            reverse('get-submission-token'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('submission_token', data)
        
        # Verify token exists in database
        token = data['submission_token']
        self.assertTrue(SubmissionToken.objects.filter(token=token).exists())

    def test_pagination(self):
        """Test pagination functionality"""
        # Create 10 more tickets for pagination testing
        for i in range(10):
            JobTicket.objects.create(
                customer_name=f'Customer {i}',
                boat_name=f'Boat {i}',
                genre='Electrical',
                status='InProgress',
                created_by=self.superuser
            )
        
        self.client.login(username='admin', password='testpass123')
        
        # Test first page
        response = self.client.get(reverse('jobticket-dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Showing 1 to 6')
        
        # Test second page
        response = self.client.get(reverse('jobticket-dashboard') + '?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Showing 7 to')

    def test_job_ticket_model_properties(self):
        """Test JobTicket model properties"""
        # Test regular genre
        self.assertEqual(self.job_ticket.effective_genre, 'Electrical')
        
        # Test custom genre
        custom_ticket = JobTicket.objects.create(
            customer_name='Custom Customer',
            boat_name='Custom Boat',
            genre='Custom',
            custom_genre='Solar Installation',
            created_by=self.superuser
        )
        self.assertEqual(custom_ticket.effective_genre, 'Solar Installation')

    def test_job_ticket_model_validation(self):
        """Test JobTicket model validation"""
        from django.core.exceptions import ValidationError
        
        # Test custom genre without custom_genre field
        ticket = JobTicket(
            customer_name='Test',
            boat_name='Test',
            genre='Custom',
            custom_genre='',  # Empty custom genre
            created_by=self.superuser
        )
        
        with self.assertRaises(ValidationError):
            ticket.full_clean()

    def tearDown(self):
        """Clean up after tests"""
        # Clean up any remaining submission tokens
        SubmissionToken.objects.all().delete()