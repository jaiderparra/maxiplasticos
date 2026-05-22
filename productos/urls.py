from django.urls import path
from . import views

urlpatterns = [
    path('', views.ListaProductosView.as_view(), name='lista_productos'),
    path('<int:pk>/', views.DetalleProductoView.as_view(), name='detalle_producto'),
    path('crear/', views.CrearProductoView.as_view(), name='crear_producto'),
    path('<int:pk>/editar/', views.EditarProductoView.as_view(), name='editar_producto'),
    path('<int:pk>/eliminar/', views.EliminarProductoView.as_view(), name='eliminar_producto'),
    path('api/calcular-precio/', views.calcular_precio_ajax, name='calcular_precio'),
    path('importar/', views.ImportarProductosView.as_view(), name='importar_productos'),
]
