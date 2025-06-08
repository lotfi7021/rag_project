from rest_framework import serializers
from .models import Document, Embedding, ChatSession

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'title', 'file', 'uploaded_at']


class EmbeddingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Embedding
        fields = ['id', 'document', 'vector', 'created_at']


class ChatSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = ['id', 'session_id', 'document', 'created_at', 'history','title']



class ChatSessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = ['document'] 
        def create(self, validated_data):
         return ChatSession.objects.create(**validated_data)
        




##  pdf 