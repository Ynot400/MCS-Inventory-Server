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


class CreateJobTicketView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'Jobtickets/create_job_ticket.html'

    def test_func(self):
        # You can customize this check as needed
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('home')

    def get(self, request):
        form = JobTicketForm()
        token = create_submission_token()
        return render(request, self.template_name, {'form': form, 'submission_token': token})

    @transaction.atomic
    def post(self, request):
        # === Submission Token Verification ===
        token_from_form = request.POST.get('submission_token')
        if not token_from_form:
            messages.error(request, "Request Timeout. Please try again.")
            return redirect("jobticket-dashboard")

        token_exists = SubmissionToken.objects.filter(token=token_from_form).exists()
        if not token_exists:
            return redirect("jobticket-dashboard")

        try:
            form = JobTicketForm(request.POST)
            if form.is_valid():
                # Delete the token first to prevent reuse
                SubmissionToken.objects.filter(token=token_from_form).delete()
                
                job_ticket = form.save(commit=False)
                job_ticket.created_by = request.user
                job_ticket.save()

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
                    messages.success(request, f'Job ticket "{job_ticket.customer_name}" created successfully.')
                    return redirect('jobticket-dashboard')
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    form_html = render_to_string('Jobtickets/partials/job_ticket_form.html', {
                        'form': form
                    }, request=request)
                    return JsonResponse({'success': False, 'form_html': form_html}, status=400)

        except ValidationError as e:
            messages.error(request, f"Validation error creating job ticket: {e}")
        except Exception as e:
            messages.error(request, f"Unexpected error creating job ticket: {e}")

        # If we reach here, there was an error - regenerate token for retry
        form = JobTicketForm(request.POST)
        token = create_submission_token()
        return render(request, self.template_name, {
            'form': form,
            'submission_token': token
        })
    
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