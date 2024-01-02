from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, View
from django.contrib.auth import authenticate, login
from .form import UserRegisterForm, SearchForm
from Products.models import Product
from django.contrib.auth.mixins import LoginRequiredMixin

class Dashboard(LoginRequiredMixin, View):
   def get(self, request):
      if request.user.groups.filter(name='Inventory Technician').exists():
        return render(request, 'Dashboard/dashboard2.html')
      else:
         return render(request, 'Dashboard/dashboard1.html')


class DashboardInventory(LoginRequiredMixin, View):
   items = None
   def get(self, request):
      form = SearchForm()
      self.items = Product.objects.order_by('title')
      return render(request, 'Dashboard/inventory.html', {'items':self.items, 'form': form})
   def post(self, request):
      if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
          selectedOption = form.cleaned_data['inventory_field']
          if selectedOption == 'Show All':
            self.items = Product.objects.order_by('title')
            return render(request, 'Dashboard/inventory.html', {'items': self.items, 'form': form})
          else:
            user_search_input = form.cleaned_data['search_field']
            if user_search_input:
              self.items = Product.objects.filter(**{f"{selectedOption}__contains": user_search_input})
            else:   # If search field is empty, show all products
              self.items = Product.objects.order_by('title')
        else:
          form = SearchForm()
      return render(request, 'Dashboard/inventory.html', {'items': self.items, 'form': form})



class SignUpView(LoginRequiredMixin, View):
  def get(self, request):
      form = UserRegisterForm()
      return render(request, 'signup.html', {'form': form})
  def post(self, request):
      form = UserRegisterForm(request.POST)
      if form.is_valid():
        form.save()
        user = authenticate(
          username=form.cleaned_data['username'],
          password=form.cleaned_data['password1']
        )
        login(request, user)
        return redirect('home')
      return render(request, 'signup.html', {'form': form})


def scan_barcode(request):
    return render(request, 'Dashboard/scan_barcode.html')
  

def home_View(request):
   return render(request, 'home.html')
