# rag_project

Retrieval-Augmented Generation (RAG) with Django and LangChain
Practical Part:
• Define models Document, Embedding, and ChatSession, with relationships and constraints.
• Implement field validators to ensure valid file types and embedding
dimensions.
• Create DRF serializers and Graphene-Django types for ingestion and
retrieval.
• Build REST endpoints for document upload, embedding generation,
chat session creation, and querying chat history.
• Define GraphQL queries and mutations for semantic search and chat
interactions.
• Secure endpoints with token-based auth, enforce permissions on document access.
• Use Celery tasks for asynchronous embedding generation with FAISS
indexing.
• Integrate LangChain in Celery tasks to perform RAG: retrieve documents and generate responses with OpenAI API.
