from django.urls import path
from . import views

urlpatterns = [
    path('countries/', views.CountryListView.as_view(), name='countries-list'),
    path('upload/', views.upload_photo, name='upload-photo'),
    path('job/<uuid:job_id>/', views.job_status, name='job-status'),
]