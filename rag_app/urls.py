# rag_app/urls.py

from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ProtectedEndpointView,ChatSessionListView 
from .views import ProtectedEndpointView, ChatSessionListView
from .views import generate_embeddings
from rag_app.views import ProtectedEndpointView

from .views import (
    DocumentViewSet,
    EmbeddingViewSet,
    ChatSessionViewSet,
    generate_embeddings,
    create_chat_session,
    query_chat,
    semantic_search,

)


router = DefaultRouter()
router.register(r'documents', DocumentViewSet)
router.register(r'embeddings', EmbeddingViewSet)
router.register(r'sessions', ChatSessionViewSet, basename='chatsession')


from .views import ChatSessionViewSet

urlpatterns = [
    path('generate-embeddings/<int:doc_id>/', generate_embeddings),
    path('create-session/', create_chat_session),
    path('chat/<str:session_id>/<str:doc_id>/', query_chat),
    path('semantic-search/', semantic_search),
    path('protected-endpoint/', ProtectedEndpointView.as_view(), name='protected-endpoint'),

    path('api/c/<int:doc_id>/', generate_embeddings, name='generate_embeddings'),


     path('chat-sessions/', ChatSessionListView.as_view(), name='chat-session-list'),


]

# نلصّق قائمة الـ router بعد المسارات اليدوية
urlpatterns += router.urls



