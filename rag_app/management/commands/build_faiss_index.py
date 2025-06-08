from django.core.management.base import BaseCommand
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from rag_app.models import Embedding


class Command(BaseCommand):
    help = "Construit un index FAISS à partir des embeddings stockés en base de données."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE(" Construction de l'index FAISS à partir des embeddings..."))

        embeddings_qs = Embedding.objects.all()
        if not embeddings_qs.exists():
            self.stdout.write(self.style.WARNING(" Aucun embedding trouvé dans la base de données."))
            return

        try:
            texts = [e.chunk_text for e in embeddings_qs]
            vectors = [e.vector for e in embeddings_qs]
            data = list(zip(texts, vectors))

            embedding_model = OllamaEmbeddings(model="mistral")

            faiss_index = FAISS.from_embeddings(data, embedding_model)

            # Sauvegarde de l'index FAISS dans le dossier local
            faiss_index.save_local("faiss_index/")
            self.stdout.write(self.style.SUCCESS(" Index FAISS construit et sauvegardé avec succès dans 'faiss_index/'."))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f" Une erreur est survenue lors de la construction de l'index : {str(e)}"))
