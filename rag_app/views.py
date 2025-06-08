import os
import numpy as np
import pickle
import docx
import PyPDF2

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login

from rest_framework import viewsets, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from celery.result import AsyncResult

from .models import Document, Embedding, ChatSession
from .serializers import (
    DocumentSerializer,
    EmbeddingSerializer,
    ChatSessionSerializer,
    ChatSessionCreateSerializer,
)

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_ollama import OllamaEmbeddings, ChatOllama, OllamaLLM

from .tasks import generate_embeddings_task, retrieve_and_respond_task


def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
    if ext == '.docx':
        doc = docx.Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    if ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""




class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [AllowAny]

class EmbeddingViewSet(viewsets.ModelViewSet):
    queryset = Embedding.objects.all()
    serializer_class = EmbeddingSerializer
    permission_classes = [AllowAny]

class ChatSessionViewSet(viewsets.ModelViewSet):
    queryset = ChatSession.objects.all()
    serializer_class = ChatSessionSerializer
    permission_classes = [AllowAny]

class ChatSessionListView(generics.ListAPIView):
    queryset = ChatSession.objects.all()
    serializer_class = ChatSessionSerializer
    permission_classes = [AllowAny]


from rest_framework import status
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
def generate_embeddings(request, doc_id):
    try:
        document = Document.objects.get(id=doc_id)
    except Document.DoesNotExist:
        logger.warning(f"Document with ID {doc_id} not found.")
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        task = generate_embeddings_task.delay(doc_id)
        logger.info(f"Enqueued embedding generation task for document ID {doc_id} with task ID {task.id}")
        return Response({"message": "Embedding task enqueued.", "task_id": task.id}, status=status.HTTP_202_ACCEPTED)
    except Exception as e:
        logger.error(f"Failed to enqueue embedding task for document ID {doc_id}: {str(e)}")
        return Response({"error": "Failed to enqueue task."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



from rest_framework import status
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def semantic_search(request):
    question = request.data.get("question", "").strip()
    if not question:
        return Response({"error": "La question est requise."}, status=400)

    try:
        q_vec = np.array(OllamaEmbeddings(model="mistral").embed_query(question))
    except Exception as e:
        logger.error(f"Erreur embedding : {e}")
        return Response({"error": "Échec de la génération des embeddings."}, status=500)

    embeddings = Embedding.objects.all()
    if not embeddings:
        return Response({"message": "Aucun embedding trouvé."}, status=404)

    results = []
    for emb in embeddings:
        try:
            v = np.array(emb.vector)
            score = float(np.dot(v, q_vec) / (np.linalg.norm(v) * np.linalg.norm(q_vec)))
            if score > 0.6:
                results.append((score, emb.chunk_text))
        except:
            continue

    if not results:
        return Response({"message": "Aucun résultat pertinent trouvé."}, status=204)

    top = sorted(results, key=lambda x: x[0], reverse=True)[:3]
    return Response([
        {
            "chunk": txt,
            "score": round(s, 4),
            "score_percent": f"{s*100:.1f}%"
        } for s, txt in top
    ])



@api_view(['POST'])
@permission_classes([AllowAny])
def create_chat_session(request):
    data = request.data.copy()
    data['user'] = request.user.id if request.user.is_authenticated else None
    serializer = ChatSessionCreateSerializer(data=data)
    if serializer.is_valid():
        session = serializer.save()
        return Response({"session_id": session.session_id}, status=201)
    return Response(serializer.errors, status=400)




@api_view(['POST'])
@permission_classes([AllowAny])
def query_chat(request, session_id, doc_id):
    # Vérification de l'existence de la session
    try:
        session = ChatSession.objects.get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response({"error": "Session introuvable."}, status=404)

    # Récupération de la question
    question = request.data.get("question", "").strip()
    if not question:
        return Response({"error": "La question est requise."}, status=400)

    # Génération de l'embedding de la question
    try:
        q_vec = np.array(OllamaEmbeddings(model="mistral").embed_query(question))
    except Exception:
        return Response({"error": "Échec lors de la génération de l'embedding de la question."}, status=500)

    # Récupération des embeddings liés au document
    try:
        embeddings = Embedding.objects.filter(document_id=doc_id)
        if not embeddings.exists():
            return Response({"error": "Aucun contenu indexé pour ce document."}, status=404)
    except Document.DoesNotExist:
        return Response({"error": "Document introuvable."}, status=404)

    # Calcul des similarités cosinus
    similitudes = []
    for emb in embeddings:
        try:
            v = np.array(emb.vector)
            score = float(np.dot(v, q_vec) / (np.linalg.norm(v) * np.linalg.norm(q_vec)))
            similitudes.append((score, emb.chunk_text))
        except:
            continue

    top_chunks = [txt for _, txt in sorted(similitudes, reverse=True)[:3]]

    if not top_chunks:
        return Response({"message": "Aucune information pertinente trouvée dans le document."}, status=200)

    prompt = (
        "أنت مساعد ذكي، مهمتك هي الإجابة فقط استنادًا إلى المقاطع التالية:\n\n"
        + "\n---\n".join(top_chunks)
        + f"\n\nالسؤال: {question}\n"
        + "اعتمد فقط على النص، لا تخمّن. كن واضحًا ومباشرًا."
    )

    try:
        llm = OllamaLLM(model="mistral")
        result = llm.generate([prompt])
        answer = result.generations[0][0].text
    except Exception:
        answer = "Une erreur est survenue lors de la génération de la réponse."

    # Mise à jour de l’historique de la session
    session.history = (session.history or []) + [{"question": question, "answer": answer}]
    session.save()

    return Response({"answer": answer})






def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('/chat/')
        else:
            return render(request, 'rag_app/login.html', {'error': 'Nom d’utilisateur ou mot de passe incorrect.'})
    return render(request, 'rag_app/login.html')

def documents_view(request):
    return render(request, 'rag_app/documents.html')

def add_document_view(request):
    return render(request, 'rag_app/add_document.html')

def chat_sessions_view(request):
    return render(request, 'rag_app/chat_sessions.html')

def chat_view(request):
    return render(request, 'rag_app/chat.html')






@api_view(['GET'])
@permission_classes([AllowAny])
def ask_question_view(request):
    question = request.GET.get("q")
    if not question:
        return JsonResponse({"error": "Missing 'q' parameter"}, status=400)

    task = retrieve_and_respond_task.delay(question) ##yab3eth quest l retrieve_and_respond_task

    return JsonResponse({"task_id": task.id})

@api_view(['GET'])
@permission_classes([AllowAny])
def get_task_status(request):
    task_id = request.GET.get("task_id")
    if not task_id:
        return JsonResponse({"error": "Missing 'task_id'"}, status=400)

    result = AsyncResult(task_id)
    if result.state == "PENDING":
        return JsonResponse({"status": "Pending"})
    elif result.state == "STARTED":
        return JsonResponse({"status": "In Progress"})
    elif result.state == "FAILURE":
        return JsonResponse({"status": "Failed", "error": str(result.result)})
    elif result.state == "SUCCESS":
        return JsonResponse({"status": "Completed", "result": result.result})
    else:
        return JsonResponse({"status": result.state})






class ProtectedEndpointView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"message": "Bienvenue sur le endpoint ouvert !"})
