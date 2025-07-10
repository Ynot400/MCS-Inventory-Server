from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from Pages.form import JobTicketForm, CustomPartForm
from .models import JobTicket, JobTicketItem
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
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # === Submission Token Verification ===
        token_from_form = request.POST.get('submission_token')
        if not token_from_form:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Request timeout. Please try again.'}, status=400)
            messages.error(request, "Request timeout. Please try again.")
            return redirect("jobticket-dashboard")

        token_exists = SubmissionToken.objects.filter(token=token_from_form).exists()
        if not token_exists:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Invalid or expired token.'}, status=400)
            # Only use messages for non-AJAX
            messages.error(request, "Invalid or expired token.")
            return redirect("jobticket-dashboard")

        try:
            form = JobTicketForm(request.POST)
            if form.is_valid():
                # Delete the token first to prevent reuse
                SubmissionToken.objects.filter(token=token_from_form).delete()
                
                job_ticket = form.save(commit=False)
                job_ticket.created_by = request.user
                job_ticket.save()

                if is_ajax:
                    card_html = render_to_string('Jobtickets/partials/job_ticket_card.html', {
                        'ticket': job_ticket
                    }, request=request)
                    return JsonResponse({
                        'success': True, 
                        'card_html': card_html,
                        'ticket_id': job_ticket.id
                    })
                else:
                    # Only use messages for non-AJAX
                    messages.success(request, f'Job ticket "{job_ticket.customer_name}" created successfully.')
                    return redirect('jobticket-dashboard')
            else:
                # Form has validation errors
                if is_ajax:
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
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
        except Exception as e:
            error_msg = f"Unexpected error creating job ticket: {e}"
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg}, status=500)
            messages.error(request, error_msg)

        # If we reach here, there was an error
        if is_ajax:
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
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            ticket = get_object_or_404(JobTicket, pk=pk)
            form = JobTicketForm(instance=ticket)
            token = create_submission_token()
            
            if is_ajax:
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
            error_msg = f"Error loading edit form for ticket {pk}: {e}"
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg}, status=500)
            messages.error(request, error_msg)
            return redirect('jobticket-dashboard')

    @transaction.atomic
    def post(self, request, pk):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # === Submission Token Verification ===
        token_from_form = request.POST.get('submission_token')
        if not token_from_form:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Request timeout. Please try again.'}, status=400)
            messages.error(request, "Request timeout. Please try again.")
            return redirect("jobticket-dashboard")

        token_exists = SubmissionToken.objects.filter(token=token_from_form).exists()
        if not token_exists:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Invalid or expired token.'}, status=400)
            messages.error(request, "Invalid or expired token.")
            return redirect("jobticket-dashboard")

        try:
            ticket = get_object_or_404(JobTicket, pk=pk)
            form = JobTicketForm(request.POST, instance=ticket)
            
            if form.is_valid():
                # Delete the token first to prevent reuse
                SubmissionToken.objects.filter(token=token_from_form).delete()
                
                updated_ticket = form.save()
                
                if is_ajax:
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
                if is_ajax:
                    # Regenerate token for retry
                    new_token = create_submission_token()
                    html = render_to_string('Jobtickets/partials/job_ticket_edit_form.html', {
                        'form': form,
                        'ticket': ticket,
                        'submission_token': new_token
                    }, request=request)
                    return JsonResponse({'success': False, 'form_html': html}, status=400)
                        
        except ValidationError as e:
            error_msg = f"Validation error updating ticket {pk}: {e}"
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
                
        except Exception as e:
            error_msg = f"Unexpected error updating ticket {pk}: {e}"
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg}, status=500)
            messages.error(request, error_msg)

        # If we reach here, there was an error - regenerate token for retry
        if not is_ajax:
            ticket = get_object_or_404(JobTicket, pk=pk)
            form = JobTicketForm(request.POST, instance=ticket)
            token = create_submission_token()
            return render(request, 'Jobtickets/edit_job_ticket.html', {
                'form': form,
                'ticket': ticket,
                'submission_token': token
            })
        
        # For AJAX, this should have been handled above
        return JsonResponse({'success': False, 'error': 'Unexpected error occurred.'}, status=500)

class DeleteJobTicketView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('home')

    @transaction.atomic
    def post(self, request, pk):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # === Submission Token Verification ===
        token_from_form = request.POST.get('submission_token')
        if not token_from_form:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Request timeout. Please try again.'}, status=400)
            messages.error(request, "Request timeout. Please try again.")
            return redirect("jobticket-dashboard")

        token_exists = SubmissionToken.objects.filter(token=token_from_form).exists()
        if not token_exists:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Invalid or expired token.'}, status=400)
            messages.error(request, "Invalid or expired token.")
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

            if is_ajax:
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
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg}, status=404)
            messages.error(request, error_msg)
        except Exception as e:
            error_msg = f"Unexpected error deleting ticket {pk}: {e}"
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg}, status=500)
            messages.error(request, error_msg)

        # If we reach here, there was an error (non-AJAX fallback)
        return redirect("jobticket-dashboard")

class JobTicketDashboardView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'Jobtickets/dashboard.html'

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('home')

    def get(self, request):
        status_filter = request.GET.get('status', None)
        # Get all tickets ordered by creation date
        all_tickets = JobTicket.objects.all().order_by('-created_at')

        if status_filter:
            all_tickets = all_tickets.filter(status=status_filter)

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

class CustomPartsView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'Jobtickets/add_custom_parts.html'

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('home')

    def get(self, request, pk):
        job_ticket = get_object_or_404(JobTicket, pk=pk)
        form = CustomPartForm()
        token = create_submission_token()
        
        # Get existing custom parts for this job ticket
        existing_parts = job_ticket.items.filter(product__isnull=True).order_by('-timestamp')
        # print("Existing custom parts:", existing_parts)
        
        return render(request, self.template_name, {
            'job_ticket': job_ticket,
            'form': form,
            'existing_parts': existing_parts,
            'submission_token': token,
        })

    @transaction.atomic
    def post(self, request, pk):
        job_ticket = get_object_or_404(JobTicket, pk=pk)
        
        # Handle deletion of existing parts
        if 'delete_part' in request.POST:
            part_id = request.POST.get('part_id')
            try:
                part = JobTicketItem.objects.get(
                    id=part_id, 
                    job_ticket=job_ticket,
                    product__isnull=True  # Ensure it's a custom part
                )
                part_name = part.custom_part_name
                part.delete()
                messages.success(request, f'Custom part "{part_name}" deleted successfully.')
            except JobTicketItem.DoesNotExist:
                messages.error(request, 'Custom part not found.')
            return redirect('add-custom-parts', pk=pk)

        # Handle adding new parts - this is typically a full page form, so messages are appropriate
        token_from_form = request.POST.get('submission_token')
        if not token_from_form:
            messages.error(request, "Request timeout. Please try again.")
            return redirect('add-custom-parts', pk=pk)

        token_exists = SubmissionToken.objects.filter(token=token_from_form).exists()
        if not token_exists:
            messages.error(request, "Invalid or expired token.")
            return redirect('add-custom-parts', pk=pk)

        form = CustomPartForm(request.POST)
        
        if form.is_valid():
            try:
                # Delete the token first to prevent reuse
                SubmissionToken.objects.filter(token=token_from_form).delete()
                
                custom_part = form.save(commit=False)
                custom_part.job_ticket = job_ticket
                custom_part.added_by = request.user
                custom_part.product = None  # Ensure this is a custom part
                custom_part.save()
                
                messages.success(request, f'Custom part "{custom_part.custom_part_name}" added successfully.')
                # print("Custom part added:", custom_part.custom_part_name)
                return redirect('add-custom-parts', pk=pk)

            except Exception as e:
                messages.error(request, f'Error adding custom part: {e}')
        
        # If form is invalid, re-render with errors
        token = create_submission_token()
        existing_parts = job_ticket.items.filter(product__isnull=True).order_by('-timestamp')

        return render(request, self.template_name, {
            'job_ticket': job_ticket,
            'form': form,
            'existing_parts': existing_parts,
            'submission_token': token,
        })
    
    @transaction.atomic
    def delete(self, request, job_ticket_pk, part_pk):
        job_ticket = get_object_or_404(JobTicket, pk=job_ticket_pk)
        try:
            part = JobTicketItem.objects.get(id=part_pk, job_ticket=job_ticket, product__isnull=True)
            part.delete()
            messages.success(request, f'Custom part "{part.custom_part_name}" deleted successfully.')
        except JobTicketItem.DoesNotExist:
            messages.error(request, 'Custom part not found.')
        return redirect('add-custom-parts', pk=job_ticket_pk)
    

class JobTicketDetailsView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('home')

    def get(self, request, pk):
        job_ticket = get_object_or_404(JobTicket, pk=pk)
        
        # Handle AJAX request for modal details
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('jobtickets/partials/job_ticket_details.html', {
                'ticket': job_ticket,
            }, request=request)
            return JsonResponse({'details_html': html})
        
        # Handle regular request (redirect to dashboard)
        return redirect('jobticket-dashboard')