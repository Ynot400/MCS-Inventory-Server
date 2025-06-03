from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.utils.timezone import make_aware
from datetime import datetime, timedelta

from EORLogging.models import LogEntry

class LogReportView(UserPassesTestMixin, View):
    template_name = 'Report/userReport.html'

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('home')

    def get(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        selected_user = request.GET.get('user')

        logs = LogEntry.objects.all().order_by('-timestamp')

        if start_date:
            logs = logs.filter(timestamp__gte=make_aware(datetime.strptime(start_date, '%Y-%m-%d')))
        if end_date:
            end = make_aware(datetime.strptime(end_date, '%Y-%m-%d')) + timedelta(days=1)
            logs = logs.filter(timestamp__lt=end)

        if selected_user and selected_user != "all":
            logs = logs.filter(username_snapshot=selected_user)

        all_usernames = (
            list(User.objects.values_list('username', flat=True)) +
            list(LogEntry.objects.exclude(username_snapshot__isnull=True).values_list('username_snapshot', flat=True))
        )
        all_usernames = sorted(set(all_usernames))

        context = {
            'logs': logs,
            'usernames': all_usernames,
            'selected_user': selected_user,
            'start_date': start_date,
            'end_date': end_date,
        }
        return render(request, self.template_name, context)
