from django.shortcuts import render
from .models import VectorMemory

def full_site_analysis(request):
    try:
        # Check if the table exists by attempting a simple query
        memories = VectorMemory.objects.all()[:1]
        return render(request, 'analysis_results.html', {'memories': memories})
    except Exception as e:
        # Handle the case where the table doesn't exist or other errors
        return render(request, 'error.html', {'error': str(e)})