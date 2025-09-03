// Configuración de la API
const API_BASE_URL = 'http://localhost:8000/api/v1';

// Función principal de Alpine.js
function orderApp() {
    return {
        // Estado de la aplicación
        orders: [],
        showCreateModal: false,
        showEditModal: false,
        loading: false,
        error: null,
        
        // Datos para nueva orden
        newOrder: {
            customer_name: '',
            product_name: '',
            quantity: 1,
            price: 0,
            notes: ''
        },
        
        // Datos para editar orden
        editingOrder: null,
        
        // Inicialización
        async init() {
            await this.loadOrders();
        },
        
        // Cargar órdenes desde la API
        async loadOrders() {
            this.loading = true;
            this.error = null;
            
            try {
                const response = await fetch(`${API_BASE_URL}/orders`);
                if (!response.ok) {
                    throw new Error('Error al cargar las órdenes');
                }
                this.orders = await response.json();
            } catch (error) {
                console.error('Error:', error);
                this.error = error.message;
                this.showToast('Error al cargar las órdenes', 'error');
            } finally {
                this.loading = false;
            }
        },
        
        // Crear nueva orden
        async createOrder() {
            if (!this.validateOrderForm(this.newOrder)) {
                return;
            }
            
            this.loading = true;
            
            try {
                const response = await fetch(`${API_BASE_URL}/orders`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(this.newOrder)
                });
                
                if (!response.ok) {
                    throw new Error('Error al crear la orden');
                }
                
                const newOrder = await response.json();
                this.orders.push(newOrder);
                this.resetNewOrderForm();
                this.showCreateModal = false;
                this.showToast('Orden creada exitosamente', 'success');
                
            } catch (error) {
                console.error('Error:', error);
                this.showToast('Error al crear la orden', 'error');
            } finally {
                this.loading = false;
            }
        },
        
        // Editar orden
        editOrder(order) {
            this.editingOrder = { ...order };
            this.showEditModal = true;
        },
        
        // Actualizar orden
        async updateOrder() {
            if (!this.validateOrderForm(this.editingOrder)) {
                return;
            }
            
            this.loading = true;
            
            try {
                const response = await fetch(`${API_BASE_URL}/orders/${this.editingOrder.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(this.editingOrder)
                });
                
                if (!response.ok) {
                    throw new Error('Error al actualizar la orden');
                }
                
                const updatedOrder = await response.json();
                const index = this.orders.findIndex(o => o.id === updatedOrder.id);
                if (index !== -1) {
                    this.orders[index] = updatedOrder;
                }
                
                this.showEditModal = false;
                this.editingOrder = null;
                this.showToast('Orden actualizada exitosamente', 'success');
                
            } catch (error) {
                console.error('Error:', error);
                this.showToast('Error al actualizar la orden', 'error');
            } finally {
                this.loading = false;
            }
        },
        
        // Actualizar estado de orden
        async updateOrderStatus(orderId, newStatus) {
            this.loading = true;
            
            try {
                const response = await fetch(`${API_BASE_URL}/orders/${orderId}/status`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ status: newStatus })
                });
                
                if (!response.ok) {
                    throw new Error('Error al actualizar el estado');
                }
                
                const order = this.orders.find(o => o.id === orderId);
                if (order) {
                    order.status = newStatus;
                }
                
                this.showToast('Estado actualizado exitosamente', 'success');
                
            } catch (error) {
                console.error('Error:', error);
                this.showToast('Error al actualizar el estado', 'error');
            } finally {
                this.loading = false;
            }
        },
        
        // Eliminar orden
        async deleteOrder(orderId) {
            if (!confirm('¿Estás seguro de que quieres eliminar esta orden?')) {
                return;
            }
            
            this.loading = true;
            
            try {
                const response = await fetch(`${API_BASE_URL}/orders/${orderId}`, {
                    method: 'DELETE'
                });
                
                if (!response.ok) {
                    throw new Error('Error al eliminar la orden');
                }
                
                this.orders = this.orders.filter(o => o.id !== orderId);
                this.showToast('Orden eliminada exitosamente', 'success');
                
            } catch (error) {
                console.error('Error:', error);
                this.showToast('Error al eliminar la orden', 'error');
            } finally {
                this.loading = false;
            }
        },
        
        // Validar formulario de orden
        validateOrderForm(order) {
            if (!order.customer_name.trim()) {
                this.showToast('El nombre del cliente es requerido', 'error');
                return false;
            }
            
            if (!order.product_name.trim()) {
                this.showToast('El nombre del producto es requerido', 'error');
                return false;
            }
            
            if (order.quantity <= 0) {
                this.showToast('La cantidad debe ser mayor a 0', 'error');
                return false;
            }
            
            if (order.price <= 0) {
                this.showToast('El precio debe ser mayor a 0', 'error');
                return false;
            }
            
            return true;
        },
        
        // Resetear formulario de nueva orden
        resetNewOrderForm() {
            this.newOrder = {
                customer_name: '',
                product_name: '',
                quantity: 1,
                price: 0,
                notes: ''
            };
        },
        
        // Mostrar notificación toast
        showToast(message, type = 'info') {
            // Crear elemento toast
            const toast = document.createElement('div');
            toast.className = `toast ${type} fade-in`;
            toast.innerHTML = `
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        ${this.getToastIcon(type)}
                    </div>
                    <div class="ml-3">
                        <p class="text-sm font-medium text-gray-900">${message}</p>
                    </div>
                    <div class="ml-auto pl-3">
                        <button class="inline-flex text-gray-400 hover:text-gray-600" onclick="this.parentElement.parentElement.parentElement.remove()">
                            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                            </svg>
                        </button>
                    </div>
                </div>
            `;
            
            // Agregar al DOM
            document.body.appendChild(toast);
            
            // Remover automáticamente después de 5 segundos
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.remove();
                }
            }, 5000);
        },
        
        // Obtener icono para toast
        getToastIcon(type) {
            const icons = {
                success: '<svg class="w-5 h-5 text-green-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>',
                error: '<svg class="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>',
                warning: '<svg class="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path></svg>',
                info: '<svg class="w-5 h-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path></svg>'
            };
            return icons[type] || icons.info;
        },
        
        // Formatear fecha
        formatDate(dateString) {
            const date = new Date(dateString);
            return date.toLocaleDateString('es-ES', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        },
        
        // Obtener clase CSS para estado
        getStatusClass(status) {
            const classes = {
                pending: 'bg-yellow-100 text-yellow-800',
                processing: 'bg-blue-100 text-blue-800',
                completed: 'bg-green-100 text-green-800',
                cancelled: 'bg-red-100 text-red-800'
            };
            return classes[status] || 'bg-gray-100 text-gray-800';
        },
        
        // Obtener texto en español para estado
        getStatusText(status) {
            const texts = {
                pending: 'Pendiente',
                processing: 'Procesando',
                completed: 'Completada',
                cancelled: 'Cancelada'
            };
            return texts[status] || status;
        }
    };
}

// Funciones utilitarias globales
window.orderApp = orderApp;

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    console.log('Sistema de Órdenes inicializado');
});