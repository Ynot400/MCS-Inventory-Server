"""
URL configuration for Inventory project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from Pages.views import home_View, DashboardInventory, Dashboard, ScanBarcode, QRCodeLogin, product_autocomplete, partNumber_autocomplete
from Products.views import AddProduct, EditProduct, DeleteProduct, update_quantity, AddBarcode, AddBarcodeHub
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from barcodes.views import CreateBarcode, CreateQRCode, ProductFinder, PrintBarcode
from EORLogging.views import LogReportView, excel_log_creation


urlpatterns = [
    path('', home_View.as_view(), name='home'),
    # path('signup/', SignUpView.as_view(), name='signup'),
    path('admin/', admin.site.urls, name='admin'),
    path('dashboard/admin/', admin.site.urls, name='admin'),
    path('login/', auth_views.LoginView.as_view(template_name = 'login.html'), name='login'),
    path('QRCode-login', QRCodeLogin.as_view(), name='QR-login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='logout.html'), name='logout'),
    path('dashboard/', Dashboard.as_view(), name='dashboard'),
    path('dashboard/inventory/', DashboardInventory.as_view(), name='inventory'),
    path('dashboard/print-barcode/', PrintBarcode.as_view(), name='print-barcode'),
    path('add-product/', AddProduct.as_view(), name='add-product'),
    path('edit-product/<int:pk>', EditProduct.as_view(), name='edit-product'),
    path('delete-product/<int:pk>', DeleteProduct.as_view(), name='delete-product'),
    #path('dashboard/scan/', scan_barcode, name='scan_barcode'),
    path('dashboard/quantity-modifier', ProductFinder.as_view(), name='barcode-quantity'),
    path('scan/', ScanBarcode.as_view(), name='detect_barcodes'),
    path('dashboard/create-barcode', CreateBarcode.as_view(), name='create-barcode'),
    path('dashboard/create-QRCode', CreateQRCode.as_view(), name='create-QRCode'),
    path('update_model/', update_quantity.as_view(), name='update_model'),
    path('add-barcode/<int:pk>', AddBarcode.as_view(), name='add-barcode'),
    path('barcode_hub/', AddBarcodeHub.as_view(), name='barcode-hub'),
    path('dashboard/eou-report/', LogReportView.as_view(), name='eou-report'),
    path('search-products/', product_autocomplete, name='product-autocomplete'),
    path('search-part-numbers/', partNumber_autocomplete, name='partNumber-autocomplete'),
    path('dashboard/eou-report/download/', excel_log_creation, name='excel-log-creation'),
    


    # path('pdf-logging', report_pdf, name='pdf-logging')
   #path('detail/', )
] 
