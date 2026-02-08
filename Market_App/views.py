from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from .models import Product, Category, Cart, CartItem, Order, OrderItem
from .forms import CheckoutForm


def product_list(request):
    """Product catalog with search and filtering"""
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.all()
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Category filter
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Price range filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    
    # Stock filter
    in_stock_only = request.GET.get('in_stock')
    if in_stock_only:
        products = products.filter(stock__gt=0)
    
    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    valid_sorts = ['price', '-price', 'name', '-name', '-created_at']
    if sort_by in valid_sorts:
        products = products.order_by(sort_by)
    
    # Get cart item count for logged in users
    cart_count = 0
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.total_items
    
    context = {
        'products': products,
        'search_query': search_query,
        'selected_category': category_id,
        'cart_count': cart_count,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
        'in_stock_only': in_stock_only,
    }
    return render(request, 'market/product_list.html', context)


def product_detail(request, pk):
    """Product detail view"""
    product = get_object_or_404(Product, pk=pk, is_active=True)
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(pk=pk)[:4]
    
    cart_count = 0
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.total_items
    
    context = {
        'product': product,
        'related_products': related_products,
        'cart_count': cart_count,
    }
    return render(request, 'market/product_detail.html', context)

def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    # Simple logic to render an edit page
    return render(request, 'market/product_edit.html', {'product': product})


@login_required
def add_to_cart(request, product_id):
    """Add product to cart"""
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    
    # Check stock availability
    if product.stock < 1:
        messages.error(request, f'{product.name} is out of stock.')
        return redirect('market:product_detail', pk=product_id)
    
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Get quantity from POST or default to 1
    quantity = int(request.POST.get('quantity', 1))
    
    # Check if product already in cart
    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart,
        product=product
    )
    
    if not item_created:
        # Update quantity if item exists
        new_quantity = cart_item.quantity + quantity
        if new_quantity > product.stock:
            messages.error(
                request, 
                f'Only {product.stock} items available in stock.'
            )
            return redirect('market:product_detail', pk=product_id)
        cart_item.quantity = new_quantity
        cart_item.save()
        messages.success(request, f'Updated {product.name} quantity in cart.')
    else:
        # Set quantity for new item
        if quantity > product.stock:
            messages.error(
                request, 
                f'Only {product.stock} items available in stock.'
            )
            cart_item.delete()
            return redirect('market:product_detail', pk=product_id)
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, f'Added {product.name} to cart.')
    
    return redirect('market:cart')


@login_required
def cart_view(request):
    """View shopping cart"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related('product').all()
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'cart_count': cart.total_items,
    }
    return render(request, 'market/cart.html', context)


@login_required
def update_cart_item(request, item_id):
    """Update cart item quantity"""
    cart_item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'increase':
            if cart_item.quantity < cart_item.product.stock:
                cart_item.quantity += 1
                cart_item.save()
                messages.success(request, 'Cart updated.')
            else:
                messages.error(request, 'Maximum stock reached.')
        
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
                messages.success(request, 'Cart updated.')
            else:
                messages.error(request, 'Minimum quantity is 1.')
        
        elif action == 'update':
            quantity = int(request.POST.get('quantity', 1))
            if quantity <= 0:
                cart_item.delete()
                messages.success(request, 'Item removed from cart.')
            elif quantity > cart_item.product.stock:
                messages.error(
                    request, 
                    f'Only {cart_item.product.stock} items available.'
                )
            else:
                cart_item.quantity = quantity
                cart_item.save()
                messages.success(request, 'Cart updated.')
    
    return redirect('market:cart')


@login_required
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart_item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.success(request, f'Removed {product_name} from cart.')
    return redirect('market:cart')


@login_required
def clear_cart(request):
    """Clear all items from cart"""
    cart = get_object_or_404(Cart, user=request.user)
    cart.items.all().delete()
    messages.success(request, 'Cart cleared.')
    return redirect('market:cart')


@login_required
def checkout(request):
    """Checkout process"""
    cart = get_object_or_404(Cart, user=request.user)
    
    # Check if cart is empty
    if not cart.items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('market:cart')
    
    # Check stock availability for all items
    for item in cart.items.all():
        if item.quantity > item.product.stock:
            messages.error(
                request,
                f'{item.product.name} only has {item.product.stock} items in stock.'
            )
            return redirect('market:cart')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Create order
            order = Order.objects.create(
                user=request.user,
                full_name=form.cleaned_data['full_name'],
                email=form.cleaned_data['email'],
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address'],
                city=form.cleaned_data['city'],
                postal_code=form.cleaned_data['postal_code'],
                country=form.cleaned_data['country'],
                subtotal=cart.subtotal,
                tax=cart.tax,
                total=cart.total,
            )
            
            # Create order items and update stock
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    product_name=cart_item.product.name,
                    product_price=cart_item.product.price,
                    quantity=cart_item.quantity,
                )
                
                # Update product stock
                product = cart_item.product
                product.stock -= cart_item.quantity
                product.save()
            
            # Clear cart
            cart.items.all().delete()
            
            messages.success(
                request, 
                f'Order {order.order_number} placed successfully!'
            )
            return redirect('market:order_confirmation', order_id=order.id)
    else:
        # Pre-fill form with user data
        initial_data = {
            'full_name': request.user.get_full_name(),
            'email': request.user.email,
        }
        form = CheckoutForm(initial=initial_data)
    
    context = {
        'cart': cart,
        'cart_items': cart.items.all(),
        'form': form,
        'cart_count': cart.total_items,
    }
    return render(request, 'market/checkout.html', context)


@login_required
def order_confirmation(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    
    cart_count = 0
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.total_items
    
    context = {
        'order': order,
        'cart_count': cart_count,
    }
    return render(request, 'market/order_confirmation.html', context)


@login_required
def order_history(request):
    """View user's order history"""
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    
    cart_count = 0
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.total_items
    
    context = {
        'orders': orders,
        'cart_count': cart_count,
    }
    return render(request, 'market/order_history.html', context)


# AJAX endpoint for live cart count
@login_required
def get_cart_count(request):
    """Get current cart item count (AJAX endpoint)"""
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return JsonResponse({'count': cart.total_items})