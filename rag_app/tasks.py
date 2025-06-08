import os
import re
import logging
import pickle
from statistics import median
from collections import Counter

from celery import shared_task

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_ollama import ChatOllama

from .models import Document, Embedding
from .utils import extract_text


logger = logging.getLogger(__name__)

# Cache FAISS en mémoire
_faiss_store_cache = {}


@shared_task
def generate_embeddings_task(doc_id):
    """
    Extrait le texte du document, le découpe en chunks, génère les embeddings avec Ollama,
    et les stocke dans la base de données.
    """
    try:
        document = Document.objects.get(id=doc_id)
    except Document.DoesNotExist:
        logger.error(f"Document introuvable : {doc_id}")
        return f"Document with ID {doc_id} does not exist."

    text = extract_text(document.file.path or "")
    if not text.strip():
        logger.warning("Document vide ou illisible.")
        return "Empty or unreadable document."

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(text)
    embedder = OllamaEmbeddings(model="mistral")

    for chunk in chunks:
        logger.info(f"Embedding chunk: {chunk[:50]}...")
        vector = embedder.embed_query(chunk)
        Embedding.objects.create(
            document=document,
            vector=vector,
            chunk_text=chunk
        )

    return f"Embeddings for document {doc_id} generated successfully."


@shared_task(bind=True)
def retrieve_and_respond_task(self, question: str, doc_id: int = None):
    """
    Effectue une tâche RAG pour répondre à une question en utilisant un index FAISS
    lié à un document spécifique (ou global).
    """
    if not question or not question.strip():
        return "Question vide. Veuillez poser une question valide."

    try:
        embeddings = OllamaEmbeddings(model="mistral")
        base_path = os.path.join(os.getcwd(), "faiss_index")
        faiss_folder = os.path.join(base_path, str(doc_id)) if doc_id else base_path

        if not os.path.isdir(faiss_folder):
            logger.error(f"FAISS index introuvable : {faiss_folder}")
            return "Base de données sémantique introuvable."

        if faiss_folder in _faiss_store_cache:
            vectorstore = _faiss_store_cache[faiss_folder]
        else:
            vectorstore = FAISS.load_local(
                faiss_folder,
                embeddings,
                allow_dangerous_deserialization=True
            )
            _faiss_store_cache[faiss_folder] = vectorstore

        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
        llm = ChatOllama(model="mistral", temperature=0.3)
        qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

        answer = qa_chain.run(question).strip()
        if not answer:
            return "Aucune réponse générée. Vérifiez le contenu des documents."
        return answer

    except Exception as e:
        logger.exception(f"Erreur dans retrieve_and_respond_task (doc_id={doc_id}): {e}")
        return f"Une erreur est survenue : {str(e)}"


@shared_task
def analyze_employees_task(text):
    """
    Analyse une liste d'employés au format : "Nom, Métier, Salaire".
    Renvoie des statistiques complètes : moyenne, médiane, top/bas salaires, etc.
    """
    employees = []
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]

    for idx, line in enumerate(lines, 1):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 3:
            logger.warning(f"Ligne {idx} ignorée (format incorrect) : {line}")
            continue
        name, job, salary_str = parts
        try:
            salary = int(salary_str)
        except ValueError:
            logger.warning(f"Ligne {idx} ignorée (salaire non entier) : {line}")
            continue
        employees.append({"name": name, "job": job, "salary": salary})

    if not employees:
        return {"error": "Aucun employé valide détecté."}

    employees_sorted = sorted(employees, key=lambda e: e["salary"])
    salaries = [e["salary"] for e in employees_sorted]
    count = len(employees)

    average_salary = round(sum(salaries) / count, 2)
    median_salary = median(salaries)
    lowest_earner = employees_sorted[0]
    top_earner = employees_sorted[-1]
    top_5_earners = employees_sorted[-5:][::-1]
    bottom_5_earners = employees_sorted[:5]

    job_statistics = Counter(emp["job"] for emp in employees)

    # Détection des développeurs
    dev_pattern = re.compile(r"d[eé]veloppeur", re.IGNORECASE)
    developer_count = sum(1 for emp in employees if dev_pattern.search(emp["job"]))

    # Répartition par tranches de salaires
    salary_distribution = Counter()
    for s in salaries:
        if s < 3000:
            salary_distribution["<3000"] += 1
        elif s <= 4000:
            salary_distribution["3000-4000"] += 1
        elif s <= 5000:
            salary_distribution["4000-5000"] += 1
        else:
            salary_distribution[">5000"] += 1

    return {
        "count": count,
        "average_salary": average_salary,
        "median_salary": median_salary,
        "top_earner": top_earner,
        "lowest_earner": lowest_earner,
        "top_5_earners": top_5_earners,
        "bottom_5_earners": bottom_5_earners,
        "developer_count": developer_count,
        "job_statistics": dict(job_statistics),
        "salary_distribution": dict(salary_distribution),
    }
