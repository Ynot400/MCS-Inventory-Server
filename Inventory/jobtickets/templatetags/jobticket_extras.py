from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


@register.filter
def mul(value, arg):
    """
    Multiply the value by the argument and return as a Decimal for money calculations.
    Handles None values, invalid inputs, and maintains precision for financial data.
    """
    try:
        # Handle None values
        if value is None or arg is None:
            return Decimal('0.00')
        
        # Convert to Decimal for precise money calculations
        decimal_value = Decimal(str(value))
        decimal_arg = Decimal(str(arg))
        
        # Perform multiplication and round to 2 decimal places for money
        result = (decimal_value * decimal_arg).quantize(Decimal('0.01'))
        
        return result
        
    except (ValueError, TypeError, InvalidOperation):
        # Return 0.00 as Decimal for consistency with money values
        return Decimal('0.00')

@register.filter
def get_custom_parts(items):
    """Filter to get only custom parts from job ticket items"""
    return [item for item in items if item.is_custom_part()]

@register.filter
def get_inventory_items(items):
    """Filter to get only inventory items from job ticket items"""
    return [item for item in items if item.product is not None]