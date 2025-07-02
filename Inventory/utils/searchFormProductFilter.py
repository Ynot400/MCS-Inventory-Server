from Products.models import Product

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
        if cd.get('section'):
            filters['section'] = cd['section']
        if cd.get('level'):
            filters['level'] = cd['level']
        if cd.get('vertical'):
            filters['vertical'] = cd['vertical']
        if cd.get('horizontal'):
            filters['horizontal'] = cd['horizontal']

        items = Product.objects.filter(**filters)

    sort_order = cd.get('sort_order')
    if sort_order == 'recent':
        items = items.order_by('-date_created')
    elif sort_order == 'oldest':
        items = items.order_by('date_created')
    elif sort_order == 'alphabetical':
        items = items.order_by('title')

    return items
