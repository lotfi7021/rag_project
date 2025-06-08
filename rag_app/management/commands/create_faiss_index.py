from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Build the FAISS index from documents'

    def handle(self, *args, **kwargs):
        # هنا تحط الكود اللي يبني الفهرس (FAISS)
        # مثلاً تستدعي دالة تبني الفهرس
        self.stdout.write('FAISS index is being created...')
        # مثلا: build_faiss_index()
        self.stdout.write(self.style.SUCCESS('FAISS index created successfully.'))
