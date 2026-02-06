from django.shortcuts import render, get_object_or_404, redirect
from .models import Product
from .forms import ProductForm

def index(request):
    products = Product.objects.all()
    return render(request, 'market/index.html', {'products': products})

def detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'market/detail.html', {'product': product})

def add_edit(request, pk=None):
    if pk:
        product = get_object_or_404(Product, pk=pk)
    else:
        product = None

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('market:index')
    else:
        form = ProductForm(instance=product)

    return render(request, 'market/add_edit.html', {'form': form})
