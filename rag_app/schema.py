import graphene
import subprocess
import json
from graphene_django.types import DjangoObjectType

from .models import Document, Embedding, ChatSession


class DocumentType(DjangoObjectType):
    class Meta:
        model = Document
        fields = ("id", "title", "content")

class EmbeddingType(DjangoObjectType):
    class Meta:
        model = Embedding

class ChatSessionType(DjangoObjectType):
    class Meta:
        model = ChatSession

class SemanticSearchResult(graphene.ObjectType):
    chunk = graphene.String()
    score = graphene.Float()



def call_ollama_model(prompt):
    process = subprocess.Popen(
        ['ollama', 'run', 'mistral'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate(input=prompt.encode())
    if process.returncode != 0:
        raise Exception(f"Ollama error: {stderr.decode()}")
    return stdout.decode().strip()



class Query(graphene.ObjectType):
    all_documents = graphene.List(DocumentType)
    all_embeddings = graphene.List(EmbeddingType)
    all_sessions = graphene.List(ChatSessionType)

    semantic_search = graphene.List(
        SemanticSearchResult,
        question=graphene.String(required=True)
    )

    def resolve_all_documents(root, info):
        return Document.objects.all()

    def resolve_all_embeddings(root, info):
        return Embedding.objects.all()

    def resolve_all_sessions(root, info):
        return ChatSession.objects.all()

    def resolve_semantic_search(self, info, question):
        answer = call_ollama_model(question)

        return [SemanticSearchResult(chunk=answer, score=1.0)]

# -------------------------------
# 4. Mutation Definition
# -------------------------------
class ChatInteraction(graphene.Mutation):
    class Arguments:
        session_id = graphene.String(required=True)
        question = graphene.String(required=True)

    answer = graphene.String()

    def mutate(self, info, session_id, question):
        try:
            session = ChatSession.objects.get(session_id=session_id)
        except ChatSession.DoesNotExist:
            raise Exception("Session not found")

        answer = call_ollama_model(question)  # استعمال موديل Ollama

        session.history.append({"question": question, "answer": answer})
        session.save()

        return ChatInteraction(answer=answer)

class Mutation(graphene.ObjectType):
    chat_interaction = ChatInteraction.Field()  ##field 5ater wahda barka djib


schema = graphene.Schema(query=Query, mutation=Mutation)
