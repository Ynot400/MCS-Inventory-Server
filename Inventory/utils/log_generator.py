from EORLogging.models import LogEntry
from Products.models import Product

def log_product_action(*, user, action_category, product=None, summary="", changes=None):
    """
    Creates a structured log entry.
    - user: request.user
    - action_category: "CREATE", "UPDATE", "DELETE"
    - product: Product instance (optional)
    - summary: one-line description
    - changes: dict for update details (optional, field_name: {old, new})
    """
    LogEntry.objects.create(
        user=user,
        username_snapshot=user.username if user else None,
        action_category=action_category,
        product=product,
        summary=summary,
        changed_fields=changes or None
    )
