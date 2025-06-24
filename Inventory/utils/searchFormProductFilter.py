from django.db.models.functions import Substr
from Products.models import Product  # Adjust import as needed

def filter_products(form):
  """
  Filters and sorts Product queryset based on cleaned_data from the form.
  Returns a queryset of filtered Product objects.
  """
  if not form.is_valid():
    return Product.objects.none()

  cd = form.cleaned_data

  if cd.get('show_all'):
    items = Product.objects.all()
  else:
    filters = {}
    if cd.get('product_name'):
      filters['title__icontains'] = cd['product_name']
    if cd.get('product_ID'):
      filters['product_ID__icontains'] = cd['product_ID']
    if cd.get('vendor'):
      filters['vendor__icontains'] = cd['vendor']

    items = Product.objects.annotate(
      loc_section=Substr('location_ID', 1, 2),
      loc_level=Substr('location_ID', 4, 2),
      loc_vertical=Substr('location_ID', 7, 2),
      loc_horizontal=Substr('location_ID', 10, 2)
    )

    if cd.get('section'):
      items = items.filter(loc_section=cd['section'])
    if cd.get('level'):
      items = items.filter(loc_level=cd['level'])
    if cd.get('vertical'):
      items = items.filter(loc_vertical=cd['vertical'])
    if cd.get('horizontal'):
      items = items.filter(loc_horizontal=cd['horizontal'])

    items = items.filter(**filters)

  sort_order = cd.get('sort_order')
  if sort_order == 'recent':
    items = items.order_by('-date_created')
  elif sort_order == 'oldest':
    items = items.order_by('date_created')
  elif sort_order == 'alphabetical':
    items = items.order_by('title')

  return items