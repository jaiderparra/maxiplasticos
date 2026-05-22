from django.urls import path
from . import views

urlpatterns = [
    path('', views.HistorialCotizacionesView.as_view(), name='historial_cotizaciones'),
    path('nueva/', views.NuevaCotizacionView.as_view(), name='nueva_cotizacion'),
    path('<int:pk>/', views.DetalleCotizacionView.as_view(), name='detalle_cotizacion'),
    path('<int:pk>/eliminar/', views.EliminarCotizacionView.as_view(), name='eliminar_cotizacion'),
    path('item/<int:pk>/eliminar/', views.eliminar_item_cotizacion, name='eliminar_item'),
]
