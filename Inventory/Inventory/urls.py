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
from Pages.views import home_View, SignUpView, DashboardInventory, Dashboard, scan_barcode
from Products.views import AddProduct, EditProduct, DeleteProduct
from detect_barcodes.views import detect, camera_feed
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', home_View, name='home'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('dashboard/admin/', admin.site.urls, name='admin'),
    path('login/', auth_views.LoginView.as_view(template_name = 'login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='logout.html'), name='logout'),
    path('dashboard/', Dashboard.as_view(), name='dashboard'),
    path('dashboard/inventory/', DashboardInventory.as_view(), name='inventory'),
    path('add-product/', AddProduct.as_view(), name='add-product'),
    path('edit-product/<int:pk>', EditProduct.as_view(), name='edit-product'),
    path('delete-product/<int:pk>', DeleteProduct.as_view(), name='delete-product'),
    #path('dashboard/scan/', scan_barcode, name='scan_barcode'),
    path('barcode/scan', detect, name='detect_barcodes'),
    path('barcode/camera_feed', camera_feed, name='camera_feed'),
   #path('detail/', )
] 
