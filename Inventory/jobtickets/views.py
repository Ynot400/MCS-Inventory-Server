from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from Pages.form import JobTicketForm
from .models import JobTicket
from django.http import JsonResponse
from django.template.loader import render_to_string


class CreateJobTicketView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'jobtickets/create_job_ticket.html'

    def test_func(self):
        # You can customize this check as needed
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('home')

    def get(self, request):
        form = JobTicketForm()
        return render(request, self.template_name, {'form': form})
    def post(self, request):
            form = JobTicketForm(request.POST)
            if form.is_valid():
                job_ticket = form.save(commit=False)
                job_ticket.created_by = request.user
                job_ticket.save()

                card_html = render_to_string('jobtickets/partials/job_ticket_card.html', {
                    'ticket': job_ticket
                }, request=request)

                return JsonResponse({'success': True, 'card_html': card_html})

            # Return rendered form errors
            form_html = render_to_string('Jobtickets/partials/job_ticket_form.html', {
                'form': form
            }, request=request)

            return JsonResponse({'success': False, 'form_html': form_html}, status=400)

class EditJobTicketView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('home')

    def get(self, request, pk):
        ticket = get_object_or_404(JobTicket, pk=pk)
        form = JobTicketForm(instance=ticket)
        html = render_to_string('Jobtickets/partials/job_ticket_edit_form.html', {
            'form': form,
            'ticket': ticket
        }, request=request)
        return JsonResponse({'form_html': html})

    def post(self, request, pk):
        ticket = get_object_or_404(JobTicket, pk=pk)
        form = JobTicketForm(request.POST, instance=ticket)
        if form.is_valid():
            ticket = form.save()
            card_html = render_to_string('Jobtickets/partials/job_ticket_card.html', {
                'ticket': ticket
            }, request=request)
            return JsonResponse({'success': True, 'card_html': card_html, 'ticket_id': ticket.id})
        else:
            html = render_to_string('Jobtickets/partials/job_ticket_edit_form.html', {
                'form': form,
                'ticket': ticket
            }, request=request)
            return JsonResponse({'success': False, 'form_html': html})


class JobTicketDashboardView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'Jobtickets/dashboard.html'

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('home')

    def get(self, request):
        tickets = JobTicket.objects.all().order_by('-created_at')
        form = JobTicketForm()
        return render(request, self.template_name, {
            'form': form,
            'tickets': tickets
        })
