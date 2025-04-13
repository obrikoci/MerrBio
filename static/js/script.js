// Add fade-in animation to elements
document.addEventListener('DOMContentLoaded', function() {
    const elements = document.querySelectorAll('.card, .alert, .table');
    elements.forEach(element => {
        element.classList.add('fade-in');
    });
});

// Confirm delete actions
document.querySelectorAll('[data-confirm]').forEach(element => {
    element.addEventListener('click', function(e) {
        if (!confirm(this.dataset.confirm)) {
            e.preventDefault();
        }
    });
});

// Auto-hide alerts after 5 seconds
document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 500);
    }, 5000);
});

// Add to cart animation
document.querySelectorAll('.add-to-cart').forEach(button => {
    button.addEventListener('click', function() {
        const cart = document.querySelector('.cart-count');
        if (cart) {
            cart.textContent = parseInt(cart.textContent || 0) + 1;
            cart.classList.add('bounce');
            setTimeout(() => cart.classList.remove('bounce'), 1000);
        }
    });
});

// Search functionality
const searchInput = document.querySelector('.search-input');
if (searchInput) {
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const products = document.querySelectorAll('.product-card');
        
        products.forEach(product => {
            const title = product.querySelector('.card-title').textContent.toLowerCase();
            const description = product.querySelector('.card-text').textContent.toLowerCase();
            
            if (title.includes(searchTerm) || description.includes(searchTerm)) {
                product.style.display = '';
            } else {
                product.style.display = 'none';
            }
        });
    });
}

// Message read status
document.querySelectorAll('.message-card').forEach(message => {
    if (message.classList.contains('unread')) {
        message.addEventListener('click', function() {
            this.classList.remove('unread');
            // Here you would typically make an API call to mark the message as read
        });
    }
});

// Price formatting
document.querySelectorAll('.price').forEach(price => {
    const amount = parseFloat(price.textContent);
    price.textContent = new Intl.NumberFormat('sq-AL', {
        style: 'currency',
        currency: 'ALL'
    }).format(amount);
});

// Form validation
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function(e) {
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                field.classList.add('is-invalid');
            } else {
                field.classList.remove('is-invalid');
            }
        });
        
        if (!isValid) {
            e.preventDefault();
        }
    });
});

// Category filter
document.querySelectorAll('.category-pill').forEach(pill => {
    pill.addEventListener('click', function(e) {
        e.preventDefault();
        const category = this.dataset.category;
        const products = document.querySelectorAll('.product-card');
        
        products.forEach(product => {
            if (category === 'all' || product.dataset.category === category) {
                product.style.display = '';
            } else {
                product.style.display = 'none';
            }
        });
        
        // Update active state
        document.querySelectorAll('.category-pill').forEach(p => p.classList.remove('active'));
        this.classList.add('active');
    });
});

// Responsive navigation
const navbarToggler = document.querySelector('.navbar-toggler');
if (navbarToggler) {
    navbarToggler.addEventListener('click', function() {
        document.querySelector('.navbar-collapse').classList.toggle('show');
    });
}

// Smooth scroll
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
}); 