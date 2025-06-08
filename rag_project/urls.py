from django.contrib import admin
from django.urls import path, include
from graphene_django.views import GraphQLView
from graphene_file_upload.django import FileUploadGraphQLView

from rag_app.schema import schema
from rag_app.views import login_view, documents_view, add_document_view,chat_sessions_view
from django.views.generic import TemplateView



from rag_app.views import chat_view

urlpatterns = [
   path('', login_view, name='login'),

path('admin/', admin.site.urls),
path('api/', include('rag_app.urls')),
path('graphql/', GraphQLView.as_view(graphiql=True, schema=schema)),

path('documents/', documents_view, name='documents'),
path('add_document/', add_document_view, name='add_document'),
path('chat-sessions/', chat_sessions_view, name='chat_sessions'),
path('chat/', chat_view, name='chat'),




]



# Serve the React app