from django import forms
from .models import Producto, EscalaPrecios


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion', 'costo', 'precio_base', 'unidad_paquete', 'categoria', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Vasos desechables 7oz'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'costo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'precio_base': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unidad_paquete': forms.NumberInput(attrs={'class': 'form-control'}),
            'categoria': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Vasos, Platos, Bolsas'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class EscalaPreciosForm(forms.ModelForm):
    class Meta:
        model = EscalaPrecios
        fields = ['nombre_escala', 'cantidad_minima', 'cantidad_maxima', 'precio_unitario', 'descuento_porcentaje']
        widgets = {
            'nombre_escala': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Docena'}),
            'cantidad_minima': forms.NumberInput(attrs={'class': 'form-control'}),
            'cantidad_maxima': forms.NumberInput(attrs={'class': 'form-control'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'descuento_porcentaje': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


EscalaFormSet = forms.inlineformset_factory(
    Producto,
    EscalaPrecios,
    form=EscalaPreciosForm,
    extra=1,
    can_delete=True,
)
