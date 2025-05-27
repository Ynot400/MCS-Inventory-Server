# utils/tokens.py
from uuid import uuid4
from Pages.models import SubmissionToken

def create_submission_token():
    token = str(uuid4())
    SubmissionToken.objects.create(token=token)
    return token
