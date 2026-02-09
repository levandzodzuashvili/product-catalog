from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from .models import Product, Cart, CartItem
from .forms import ProductForm
from decimal import Decimal


# ====================================
# Authentication Views
# ====================================

def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('Market_App:product_list')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        # Validation
        if password != password2:
            messages.error(request, 'Passwords do not match!')
            return redirect('Market_App:register')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return redirect('Market_App:register')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists!')
            return redirect('Market_App:register')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        user.save()
        
        messages.success(request, 'Account created successfully! Please login.')
        return redirect('Market_App:login')
    
    return render(request, 'market/register.html')


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('Market_App:product_list')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {username}!')
            next_url = request.GET.get('next', 'Market_App:product_list')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password!')
            return redirect('Market_App:login')
    
    return render(request, 'market/login.html')


def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully!')
    return redirect('Market_App:login')


# ====================================
# Product Views
# ====================================

def product_list(request):
    """Display all products with optional search and filtering"""
    products = Product.objects.all().order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Category filter (if you have categories)
    category = request.GET.get('category', '')
    if category:
        products = products.filter(category=category)
    
    # Price range filter
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    
    # Sort options
    sort_by = request.GET.get('sort', '')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('name')
    
    # Cart count for authenticated users
    cart_count = 0
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.items.count()
    
    context = {
        'products': products,
        'search_query': search_query,
        'cart_count': cart_count,
        'sort_by': sort_by,
    }
    
    return render(request, 'market/product_list.html', context)


def product_detail(request, pk):
    """Display detailed information about a specific product"""
    product = get_object_or_404(Product, pk=pk)
    
    # Get related products (same category or random)
    related_products = Product.objects.exclude(pk=pk).order_by('?')[:3]
    
    # Cart count
    cart_count = 0
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.items.count()
    
    context = {
        'product': product,
        'related_products': related_products,
        'cart_count': cart_count,
    }
    
    return render(request, 'market/product_detail.html', context)


@login_required
def product_add(request):
    """Add a new product (requires login)"""
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user  # If you have this field
            product.save()
            messages.success(request, 'Product added successfully!')
            return redirect('market:detail', pk=product.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductForm()
    
    context = {
        'form': form,
        'title': 'Add New Product',
        'button_text': 'Add Product',
    }
    
    return render(request, 'Market_App/product_detail.html', context)


@login_required
def product_edit(request, pk):
    """Edit an existing product"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('market:detail', pk=product.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductForm(instance=product)
    
    context = {
        'form': form,
        'product': product,
        'title': 'Edit Product',
        'button_text': 'Update Product',
    }
    
    return render(request, 'Market_App/product_detail.html', context)


@login_required
def product_delete(request, pk):
    """Delete a product"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Product "{product_name}" deleted successfully!')
        return redirect('market:list')
    
    context = {
        'product': product,
    }
    
    return render(request, 'market/product_confirm_delete.html', context)


# ====================================
# Shopping Cart Views
# ====================================

@login_required
def cart_view(request):
    """Display user's shopping cart"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    
    # Calculate totals
    subtotal = sum(item.total_price for item in cart_items)
    tax = subtotal * Decimal('0.1')  # Wrap 0.1 in Decimal
    shipping = Decimal('10.00') if subtotal > 0 else Decimal('0')
    total = subtotal + tax + shipping
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'tax': tax,
        'shipping': shipping,
        'total': total,
        'cart_count': cart_items.count(),
    }
    
    return render(request, 'market/cart.html', context)


@login_required
def add_to_cart(request, pk):
    """Add a product to the shopping cart"""
    product = get_object_or_404(Product, pk=pk)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Check if item already in cart
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1}
    )
    
    if not created:
        # Item exists, increase quantity
        cart_item.quantity += 1
        cart_item.save()
        messages.success(request, f'Increased {product.name} quantity to {cart_item.quantity}')
    else:
        messages.success(request, f'{product.name} added to cart!')
    
    # Redirect to previous page or cart
    next_url = request.GET.get('next', 'Market_App:cart')
    return redirect(next_url)


@login_required
def remove_from_cart(request, pk):
    """Remove an item from the cart"""
    cart_item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.success(request, f'{product_name} removed from cart!')
    return redirect('Market_App:cart')


@login_required
def update_cart_item(request, pk):
    """Update quantity of a cart item"""
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, 'Cart updated!')
        else:
            cart_item.delete()
            messages.success(request, 'Item removed from cart!')
    
    return redirect('Market_App:cart')


@login_required
def clear_cart(request):
    """Clear all items from the cart"""
    if request.method == 'POST':
        cart = get_object_or_404(Cart, user=request.user)
        cart.items.all().delete()
        messages.success(request, 'Cart cleared!')
    
    return redirect('Market_App:cart')


# ====================================
# Checkout View
# ====================================

@login_required
def checkout(request):
    cart = Cart.objects.get(user=request.user)
    cart_items = cart.items.all()
    
    # 1. Calculate totals FIRST (available for both GET and POST)
    subtotal = sum(item.total_price for item in cart_items)
    tax = subtotal * Decimal('0.1')
    shipping = Decimal('10.00') if subtotal > 0 else Decimal('0')
    total = subtotal + tax + shipping
    if request.method == 'POST':
        form = ProductForm(request.POST) 
        # --- EVERYTHING BELOW IS NOW INDENTED ---
        if form.is_valid():
            order = form.save(commit=False)
            
            # 2. Attach the missing data
            order.user = request.user
            order.subtotal = subtotal  
            order.tax = tax
            order.total = total
            
            # 3. Now save it
            order.save()
            
            # 4. Clear the cart 
            cart_items.delete()
            
            return redirect('Market_App:order_success')
    else:
        form = ProductForm()

    # 2. Pass them to the context
    context = {
        'form': form,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'tax': tax,
        'total': total,
    }
    return render(request, 'market/checkout.html', context)

# ====================================
# User Profile & Wishlist (Optional)
# ====================================
def order_success(request):
        return render(request, 'market/order_success.html')

@login_required
def profile_view(request):
    """User profile view"""
    # You can add order history, saved addresses, etc.
    context = {
        'user': request.user,
    }
    return render(request, 'market/profile.html', context)


@login_required
def wishlist_view(request):
    """User wishlist view (requires Wishlist model)"""
    # This is a placeholder - you'll need to create Wishlist model
    context = {
        'wishlist_items': [],  # Replace with actual wishlist items
    }
    return render(request, 'market/wishlist.html', context)


# ====================================
# API Views (Optional - for AJAX)
# ====================================

def product_search_api(request):
    """API endpoint for product search (for autocomplete)"""
    query = request.GET.get('q', '')
    if len(query) >= 2:
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )[:10]
        
        results = [{
            'id': p.id,
            'name': p.name,
            'price': str(p.price),
            'url': f'/product/{p.id}/'
        } for p in products]
        
        return JsonResponse({'results': results})
    
    return JsonResponse({'results': []})


@login_required
def quick_add_to_cart(request, pk):
    """Quick add to cart (AJAX endpoint)"""
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk)
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': 1}
        )
        
        if not created:
            cart_item.quantity += 1
            cart_item.save()
        
        cart_count = cart.items.count()
        
        return JsonResponse({
            'success': True,
            'message': f'{product.name} added to cart!',
            'cart_count': cart_count,
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})