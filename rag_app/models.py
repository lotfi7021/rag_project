from django.db import models

# Create your models here.
from django.db import models
from django.core.exceptions import ValidationError
import os


def validate_file_type(value):
    valid_extensions = ['.pdf', '.txt', '.docx']
    ext = os.path.splitext(value.name)[1]
    if ext.lower() not in valid_extensions:
        raise ValidationError(f"Unsupported file extension: {ext}. Allowed types: {', '.join(valid_extensions)}")

def validate_embedding_dimensions(value):
    if not isinstance(value, list) or not all(isinstance(x, float) for x in value):
        raise ValidationError("Embedding must be a list of floats.")
    if len(value) != 768:
        raise ValidationError("Embedding must have 768 dimensions.")

# === Models ===

class Document(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/', validators=[validate_file_type])
    uploaded_at = models.DateTimeField(auto_now_add=True)
    content = models.TextField() 

    def __str__(self):
        return self.title


class Embedding(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='embeddings')
    vector = models.JSONField(validators=[validate_embedding_dimensions])
    created_at = models.DateTimeField(auto_now_add=True)
    chunk_text  = models.TextField(default="")      


    def __str__(self):
        return f"Embedding for {self.document.title} (ID {self.id})"
    



from django.contrib.auth.models import User

import uuid
class ChatSession(models.Model):
    session_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=255, blank=True, null=True)

    history = models.JSONField(default=list)  # [{question: "...", answer: "..."}]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions',default=1)

    def __str__(self):
        return f"Session {self.session_id} for {self.document.title}"
