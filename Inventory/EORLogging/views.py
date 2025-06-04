from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.utils.timezone import make_aware
from datetime import datetime, timedelta
from django.http import JsonResponse, HttpResponse
from Products.models import Product
from django.utils.timezone import localtime

from EORLogging.models import LogEntry
from django.db.models import Q
import io
import xlsxwriter


def sanitize_filename(filename):
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*', "'"]
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename

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
        selected_product = request.GET.get('product', '')


        logs = LogEntry.objects.all().order_by('-timestamp')


        if selected_product and selected_product.strip():
            logs = logs.filter(
                Q(product__title__icontains=selected_product) |
                Q(product_name__icontains=selected_product) 
            )


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
            'selected_product': selected_product,
        }
        return render(request, self.template_name, context)

def product_autocomplete(request):
    query = request.GET.get('q', '')
    matches = Product.objects.filter(title__icontains=query).values('id', 'title')[:10]
    return JsonResponse({'results': list(matches)})

def excel_log_creation(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    selected_user = request.GET.get('user')
    selected_product = request.GET.get('product', '')


    logs = LogEntry.objects.all().order_by('-timestamp')


    if selected_product and selected_product.strip():
        logs = logs.filter(
            Q(product__title__icontains=selected_product) |
            Q(product_name__icontains=selected_product) 
        )


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

    # Create in-memory Excel file
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    # === Styles ===
    bold = workbook.add_format({'bold': True})
    wrap_format = workbook.add_format({'text_wrap': True})
    header_format = workbook.add_format({'bold': True, 'bg_color': '#01acca', 'font_color': 'white'})
    cell_top = workbook.add_format({'valign': 'top'})
    cell_top_bold = workbook.add_format({'valign': 'top', 'bold': True})
    action_colors = {
        "CREATE": workbook.add_format({'bold': True, 'font_color': 'blue', 'valign': 'top'}),
        "UPDATE": workbook.add_format({'bold': True, 'font_color': 'green', 'valign': 'top'}),
        "DELETE": workbook.add_format({'bold': True, 'font_color': 'red', 'valign': 'top'}),
    }

    # === SHEET 1: Updates ===
    sheet_updates = workbook.add_worksheet("Updates")
    sheet_updates.set_column("A:H", 25)

    headers_update = ["Timestamp", "Username", "Action", "Product", "Part Number", "Reason", "Field", "Old Value", "New Value"]
    for col_num, header in enumerate(headers_update):
        sheet_updates.write(0, col_num, header, header_format)

    row_u = 1
    for log in logs:
        if log.action_category != "UPDATE" or not isinstance(log.changed_fields, dict):
            continue

        product_name = log.resolved_product_name()
        part_number = log.product.product_ID if log.product else "N/A"
        action_fmt = action_colors.get("UPDATE")



        for field, values in log.changed_fields.items():
            sheet_updates.write(row_u, 0, localtime(log.timestamp).strftime("%Y-%m-%d %H:%M"), cell_top)
            sheet_updates.write(row_u, 1, log.username_snapshot, cell_top)
            sheet_updates.write(row_u, 2, log.action_category, action_fmt)
            sheet_updates.write(row_u, 3, product_name, cell_top_bold)
            sheet_updates.write(row_u, 4, part_number, cell_top_bold)
            sheet_updates.write(row_u, 5, log.summary or "N/A", wrap_format)
            sheet_updates.write(row_u, 6, field, cell_top)
            sheet_updates.write(row_u, 7, str(values.get("old_value")), cell_top)
            sheet_updates.write(row_u, 8, str(values.get("new_value")), cell_top)
            row_u += 1

    # === SHEET 2: Creates & Deletes ===
    sheet_other = workbook.add_worksheet("Creates & Deletes")
    sheet_other.set_column("A:F", 40)

    headers_other = ["Timestamp", "Username", "Action", "Product", "Part Number", "Product Information"]
    for col_num, header in enumerate(headers_other):
        sheet_other.write(0, col_num, header, header_format)

    row_cd = 1
    for log in logs:
        if log.action_category not in ["CREATE", "DELETE"] or not isinstance(log.changed_fields, dict):
            continue

        product_name = log.resolved_product_name()
        part_number = log.product.product_ID if log.product else "N/A"
        action_fmt = action_colors.get(log.action_category)

    
        changes_str = "\n".join([f"{field}: {value}" for field, value in log.changed_fields.items()])

        sheet_other.write(row_cd, 0, localtime(log.timestamp).strftime("%Y-%m-%d %H:%M"), cell_top)
        sheet_other.write(row_cd, 1, log.username_snapshot, cell_top)
        sheet_other.write(row_cd, 2, log.action_category, action_fmt)
        sheet_other.write(row_cd, 3, product_name, cell_top_bold)
        sheet_other.write(row_cd, 4, part_number, cell_top_bold)
        sheet_other.write(row_cd, 5, changes_str, wrap_format)
        row_cd += 1

    # Finalize workbook
    workbook.close()
    output.seek(0)


    filename_parts = ["log_report"]

    if start_date:
        filename_parts.append(f"from_{start_date}")
    if end_date:
        filename_parts.append(f"to_{end_date}")
    if selected_user and selected_user != "all":
        filename_parts.append(f"user_{selected_user}")
    if selected_product:
        filename_parts.append(f"product_{selected_product.replace(' ', '_')}")

    filename = "_".join(filename_parts) + ".xlsx"
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename={filename}'
    return response