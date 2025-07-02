from django import template

register = template.Library()

@register.simple_tag
def range_list(start, end):
    """
    Returns a list of integers from start to end (inclusive).
    """
    return range(start, end + 1)