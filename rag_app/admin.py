from django.contrib import admin

from .models import Document, Embedding, ChatSession

admin.site.register(Document)
admin.site.register(Embedding)
admin.site.register(ChatSession)
