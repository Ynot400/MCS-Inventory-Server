
import logging
from django.contrib.auth.models import User

class LoggingRetrieval(logging.Formatter):
    def format(self, record):
        record.custom_data = "Your custom data here"
        try:
            user = User.objects.get(id=record.user_id)
            record.username = user.username
        except User.DoesNotExist:
            record.username = "Unknown User"

        return super().format(record)