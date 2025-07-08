from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from Pages.form import JobTicketForm
from .models import JobTicket
from django.http import JsonResponse
from django.template.loader import render_to_string
from utils.tokens import create_submission_token
from Pages.models import SubmissionToken
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

class GetSubmissionTokenView(LoginRequiredMixin, View):
    """
    Simple endpoint to get a fresh submission token for AJAX operations
    """
    def get(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            token = create_submission_token()
            return JsonResponse({'submission_token': token})
        else:
            # For non-AJAX requests, redirect to dashboard
            return redirect('jobticket-dashboard')

class CreateJobTicketView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'Jobtickets/create_job_ticket.html'

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('home')

    def get(self, request):
        form = JobTicketForm()
        token = create_submission_token()
        
        # Handle AJAX request (from dashboard modal)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('Jobtickets/partials/job_ticket_form.html', {
                'form': form,
                'submission_token': token
            }, request=request)
            return JsonResponse({'form_html': html})
        
        # Handle regular request (for standalone create page if needed)
        return render(request, self.template_name, {
            'form': form, 
            'submission_token': token
        })

    @transaction.atomic
    def post(self, request):
        # === Submission Token Verification ===
        token_from_form = request.POST.get('submission_token')
        if not token_from_form:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Request timeout. Please try again.'}, status=400)
            messages.error(request, "Request Timeout. Please try again.")
            return redirect("jobticket-dashboard")

        token_exists = SubmissionToken.objects.filter(token=token_from_form).exists()
        if not token_exists:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Invalid or expired token.'}, status=400)
            return redirect("jobticket-dashboard")

        try:
            form = JobTicketForm(request.POST)
            if form.is_valid():
                # Delete the token first to prevent reuse
                SubmissionToken.objects.filter(token=token_from_form).delete()
                
                job_ticket = form.save(commit=False)
                job_ticket.created_by = request.user
                job_ticket.save()

                # Handle AJAX request (from dashboard modal)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    card_html = render_to_string('Jobtickets/partials/job_ticket_card.html', {
                        'ticket': job_ticket
                    }, request=request)
                    return JsonResponse({
                        'success': True, 
                        'card_html': card_html,
                        'ticket_id': job_ticket.id
                    })
                else:
                    # Handle regular form submission
                    messages.success(request, f'Job ticket "{job_ticket.customer_name}" created successfully.')
                    return redirect('jobticket-dashboard')
            else:
                # Form has validation errors
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    # Generate new token for retry
                    new_token = create_submission_token()
                    form_html = render_to_string('Jobtickets/partials/job_ticket_form.html', {
                        'form': form,
                        'submission_token': new_token
                    }, request=request)
                    return JsonResponse({'success': False, 'form_html': form_html}, status=400)
                else:
                    # For non-AJAX, render the create page with errors
                    token = create_submission_token()
                    return render(request, self.template_name, {
                        'form': form,
                        'submission_token': token
                    })

        except ValidationError as e:
            error_msg = f"Validation error creating job ticket: {e}"
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
        except Exception as e:
            error_msg = f"Unexpected error creating job ticket: {e}"
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=500)
            messages.error(request, error_msg)

        # If we reach here, there was an error
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # For AJAX errors, return a new form with token
            new_token = create_submission_token()
            form_html = render_to_string('Jobtickets/partials/job_ticket_form.html', {
                'form': JobTicketForm(request.POST),
                'submission_token': new_token
            }, request=request)
            return JsonResponse({'success': False, 'form_html': form_html}, status=400)
        
        # For non-AJAX requests, redirect to dashboard
        return redirect("jobticket-dashboard")
    
class EditJobTicketView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('home')

    def get(self, request, pk):
        try:
            ticket = get_object_or_404(JobTicket, pk=pk)
            form = JobTicketForm(instance=ticket)
            token = create_submission_token()
            
            # If this is an AJAX request, return the form HTML
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                html = render_to_string('Jobtickets/partials/job_ticket_edit_form.html', {
                    'form': form,
                    'ticket': ticket,
                    'submission_token': token
                }, request=request)
                return JsonResponse({'form_html': html})
            # If it's a normal request, render the full page
            return render(request, 'Jobtickets/edit_job_ticket.html', {
                'form': form,
                'ticket': ticket,
                'submission_token': token
            })
            
        except Exception as e:
            messages.error(request, f"Error loading edit form for ticket {pk}: {e}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Could not load edit form.'}, status=500)
            return redirect('jobticket-dashboard')

    @transaction.atomic
    def post(self, request, pk):
        # === Submission Token Verification ===
        token_from_form = request.POST.get('submission_token')
        if not token_from_form:
            messages.error(request, "Request Timeout. Please try again.")
            return redirect("jobticket-dashboard")

        token_exists = SubmissionToken.objects.filter(token=token_from_form).exists()
        if not token_exists:
            return redirect("jobticket-dashboard")

        try:
            ticket = get_object_or_404(JobTicket, pk=pk)
            form = JobTicketForm(request.POST, instance=ticket)
            
            if form.is_valid():
                # Delete the token first to prevent reuse
                SubmissionToken.objects.filter(token=token_from_form).delete()
                
                updated_ticket = form.save()
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    card_html = render_to_string('Jobtickets/partials/job_ticket_card.html', {
                        'ticket': updated_ticket
                    }, request=request)
                    return JsonResponse({
                        'success': True, 
                        'card_html': card_html, 
                        'ticket_id': updated_ticket.id
                    })
                else:
                    messages.success(request, f'Job ticket "{updated_ticket.customer_name}" updated successfully.')
                    return redirect('jobticket-dashboard')
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    # Regenerate token for retry
                    new_token = create_submission_token()
                    html = render_to_string('Jobtickets/partials/job_ticket_edit_form.html', {
                        'form': form,
                        'ticket': ticket,
                        'submission_token': new_token
                    }, request=request)
                    return JsonResponse({'success': False, 'form_html': html})
                        
        except ValidationError as e:
            messages.error(request, f"Validation error updating ticket {pk}: {e}")
                
        except Exception as e:
            messages.error(request, f"Unexpected error updating ticket {pk}: {e}")

        # If we reach here, there was an error - regenerate token for retry
        ticket = get_object_or_404(JobTicket, pk=pk)
        form = JobTicketForm(request.POST, instance=ticket)
        token = create_submission_token()
        return render(request, 'Jobtickets/edit_job_ticket.html', {
            'form': form,
            'ticket': ticket,
            'submission_token': token
        })
    

class DeleteJobTicketView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('home')

    @transaction.atomic
    def post(self, request, pk):
        # === Submission Token Verification ===
        token_from_form = request.POST.get('submission_token')
        if not token_from_form:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Request timeout. Please try again.'}, status=400)
            messages.error(request, "Request Timeout. Please try again.")
            return redirect("jobticket-dashboard")

        token_exists = SubmissionToken.objects.filter(token=token_from_form).exists()
        if not token_exists:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Invalid or expired token.'}, status=400)
            return redirect("jobticket-dashboard")

        try:
            ticket = get_object_or_404(JobTicket, pk=pk)
            ticket_customer_name = ticket.customer_name
            ticket_boat_name = ticket.boat_name
            
            # Delete the token first to prevent reuse
            SubmissionToken.objects.filter(token=token_from_form).delete()
            
            # Delete the job ticket
            ticket.delete()

            success_message = f'Job ticket for "{ticket_customer_name}" (Boat: {ticket_boat_name}) has been deleted successfully.'

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': success_message,
                    'ticket_id': pk
                })
            else:
                messages.success(request, success_message)
                return redirect('jobticket-dashboard')

        except JobTicket.DoesNotExist:
            error_msg = f"Job ticket with ID {pk} not found."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=404)
            messages.error(request, error_msg)
        except Exception as e:
            error_msg = f"Unexpected error deleting ticket {pk}: {e}"
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=500)
            messages.error(request, error_msg)

        # If we reach here, there was an error
        return redirect("jobticket-dashboard")

class JobTicketDashboardView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'Jobtickets/dashboard.html'

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('home')

    def get(self, request):
        # Get all tickets ordered by creation date
        all_tickets = JobTicket.objects.all().order_by('-created_at')
        
        # Pagination setup
        items_per_page = 6  # Show 6 tickets per page (2 rows of 3 cards)
        paginator = Paginator(all_tickets, items_per_page)
        
        page = request.GET.get('page', 1)
        try:
            tickets = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page
            tickets = paginator.page(1)
        except EmptyPage:
            # If page is out of range, deliver last page
            tickets = paginator.page(paginator.num_pages)
        
        form = JobTicketForm()
        
        return render(request, self.template_name, {
            'form': form,
            'tickets': tickets,  # This is now a Page object, not a QuerySet
            'paginator': paginator,
            'current_page': tickets.number,
            'total_pages': paginator.num_pages,
        })