from django.shortcuts import render, redirect
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import CreateView, UpdateView, View
from django.contrib.auth.models import User
from .models import LogEntry
from datetime import timedelta
from django.utils import timezone
from django.http import FileResponse
import io
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors  # Import colors module
import os
from os.path import expanduser

def report_pdf(request):

     # Get the user's desktop directory
    desktop_path = expanduser("~/Desktop")
    
    # Create a folder named "UserLogs" if it doesn't exist
    folder_path = os.path.join(desktop_path, "UserLogs")
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    if request.method == 'POST':
        selected_user = request.POST.get('selected_user')
        selected_time_range = request.POST.get('selected_time_range')

       # Filter logs based on the selected user and time range
        if selected_time_range == 'all':
            logs = LogEntry.objects.filter(user__username=selected_user).order_by('-timestamp')
            time_range_text = "Date Range: All Recorded Logs Since Account Creation"
            filename = f"{selected_user}_all_logs_as_of_{timezone.now().strftime('%m-%d-%y')}.pdf"
        else:
            days = int(selected_time_range)
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            logs = LogEntry.objects.filter(user__username=selected_user, timestamp__gte=start_date).order_by('-timestamp')
            time_range_text = f"Date Range: {start_date.strftime('%m/%d/%y')} - {end_date.strftime('%m/%d/%y')}"
            filename = f"{selected_user}_logs_from_{start_date.strftime('%m-%d-%y')}_to_{end_date.strftime('%m-%d-%y')}.pdf"

        # Create a PDF file
        file_path = os.path.join(folder_path, filename)  # Full path to save the PDF
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        pdf.setTitle("User Logs Report")

        # Title
        title_text = f"Logging Report for User: {selected_user}"
        pdf.setFont("Helvetica-Bold", 16)
        title_width = pdf.stringWidth(title_text, "Helvetica-Bold", 16)
        page_width = letter[0]
        pdf.drawString((page_width - title_width) / 2, 10.5 * inch, title_text)
        


        pdf.setFont("Helvetica", 12)
        time_range_text = f"{time_range_text}"
        time_range_width = pdf.stringWidth(time_range_text, "Helvetica", 12)
        pdf.drawString((page_width - time_range_width) / 2, 10 * inch, time_range_text)

        # Log entries
        pdf.setFont("Helvetica", 10)
        y_position = 9.5 * inch
        for log in logs:
            if y_position < 1 * inch:
                pdf.showPage()
                y_position = 10.5 * inch
            
            # Format the timestamp
            formatted_timestamp = log.timestamp.strftime("%m/%d/%Y %I:%M %p")

            # Set text color based on action category
            if log.action_category == 'CREATE':
                pdf.setFillColor(colors.green)
            elif log.action_category == 'DELETE':
                pdf.setFillColor(colors.red)
            elif log.action_category == 'UPDATE':
                pdf.setFillColor(colors.blue)
            else:
                pdf.setFillColor(colors.black)

            log_text = f"{formatted_timestamp} - {log.action_category} - {log.product_name}"
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(1 * inch, y_position, log_text)
            y_position -= 0.25 * inch

            details_text = f"Details: {log.details}"
            pdf.setFillColor(colors.black)  # Reset to black for details text

            # Split details text into lines
            lines = details_text.split('\n')

            # Set font to bold for the first line
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(1 * inch, y_position, lines[0])
            y_position -= 0.25 * inch

            # Set font to regular for the remaining lines
            pdf.setFont("Helvetica", 10)
            for line in lines[1:]:
              if line.strip():  # Check if the line is not empty after stripping whitespace
                pdf.drawString(1 * inch, y_position, f"- {line.strip()}")
                y_position -= 0.25 * inch

            y_position -= 0.25 * inch

        pdf.save()

        # Save the PDF file to the folder on the desktop
        with open(file_path, 'wb') as f:
            f.write(buffer.getvalue())

        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=filename)

    return redirect('end-of-report')

class EndOfReport(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.groups.filter(name='Inventory Technician').exists() or self.request.user.is_superuser
    def handle_no_permission(self):
        return redirect('home')
    def get(self, request):
        users = User.objects.all()
        usernames = [user.username for user in users]
        return render(request, 'Dashboard/eou_report.html', {'usernames': usernames})
    def post(self, request):
       if request.method == 'POST':
        users = User.objects.all()
        usernames = [user.username for user in users]
        # get post data of selected user and time range
        selected_user = request.POST.get('userSelect')
        selected_time_range = request.POST.get('timeRangeSelect')

        # Validate inputs
        if not selected_user or not selected_time_range:
            # Handle invalid inputs
            return render(request, 'Dashboard/eou_report.html', {'error': 'Invalid user or time range selected', 'usernames': usernames})

        # Check if user exists
        if not User.objects.filter(username=selected_user).exists():
            # Handle non-existent user
            return render(request, 'Dashboard/eou_report.html', {'error': 'User does not exist', 'usernames': usernames})

        try:

            # filter logs based on time range
            if selected_time_range == 'all':
                logs = LogEntry.objects.filter(user__username=selected_user).order_by('-timestamp')
            else:
                start_date = timezone.now() - timedelta(days=int(selected_time_range))
                # Filter LogEntry objects
                logs = LogEntry.objects.filter(user__username=selected_user, timestamp__gte=start_date).order_by('-timestamp')
            # grab count data for logs
            create_count = logs.filter(action_category='CREATE').count()
            update_count = logs.filter(action_category='UPDATE').count()
            delete_count = logs.filter(action_category='DELETE').count()
            post = True
        except Exception as e:
            # Handle exceptions
            return render(request, 'Dashboard/eou_report.html', {'error': str(e)})
        print("test")
        return render(request, 'Dashboard/eou_report.html', {'post': post, 'log_objects': logs, 'log_count': logs.count(), 'create_count': create_count, 'update_count': update_count, 'delete_count': delete_count, 'selected_user': selected_user, 'selected_time_range': selected_time_range, 'usernames': usernames})
       
