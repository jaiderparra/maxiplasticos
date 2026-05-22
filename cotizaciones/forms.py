from django import forms
from .models import Cotizacion, ItemCotizacion


class CotizacionForm(forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = ['cliente_nombre', 'estado', 'notas']
        widgets = {
            'cliente_nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del cliente'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class AgregarItemForm(forms.Form):
    producto_id = forms.IntegerField(widget=forms.HiddenInput())
    cantidad = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Cantidad', 'min': '1'})
    )
