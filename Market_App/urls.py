from django.urls import path
from . import views

app_name = 'market'

urlpatterns = [
    path('', views.index, name='index'),
    path('product/<int:pk>/', views.detail, name='detail'),
    path('product/add/', views.add_edit, name='add'),
    path('product/<int:pk>/edit/', views.add_edit, name='edit'),
]
