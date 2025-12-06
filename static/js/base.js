// ========================================
// SIDEBAR TOGGLE
// ========================================
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('toggleSidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const mainContent = document.getElementById('mainContent');
    
    // Toggle sidebar
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            if (window.innerWidth <= 991) {
                // Mobile: Mostrar/ocultar sidebar
                sidebar.classList.toggle('active');
                overlay.classList.toggle('active');
                document.body.style.overflow = sidebar.classList.contains('active') ? 'hidden' : '';
            } else {
                // Desktop: Colapsar/expandir sidebar
                sidebar.classList.toggle('collapsed');
                
                // Cerrar todos los submenús cuando se colapsa
                if (sidebar.classList.contains('collapsed')) {
                    const openSubmenus = sidebar.querySelectorAll('.submenu.show');
                    openSubmenus.forEach(submenu => {
                        submenu.classList.remove('show');
                        const toggleLink = document.querySelector(`[data-bs-target="#${submenu.id}"]`);
                        if (toggleLink) {
                            toggleLink.setAttribute('aria-expanded', 'false');
                        }
                    });
                }
                
                // Guardar preferencia en localStorage
                const isCollapsed = sidebar.classList.contains('collapsed');
                localStorage.setItem('sidebarCollapsed', isCollapsed);
            }
        });
    }
    
    // Cerrar sidebar al hacer click en overlay (mobile)
    if (overlay) {
        overlay.addEventListener('click', function() {
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
            document.body.style.overflow = '';
        });
    }
    
    // Restaurar estado del sidebar desde localStorage
    const savedState = localStorage.getItem('sidebarCollapsed');
    if (savedState === 'true' && window.innerWidth > 991) {
        sidebar.classList.add('collapsed');
    }
    
    // Manejar resize de ventana
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            if (window.innerWidth > 991) {
                // Desktop: restaurar estado guardado
                sidebar.classList.remove('active');
                overlay.classList.remove('active');
                document.body.style.overflow = '';
                
                const savedState = localStorage.getItem('sidebarCollapsed');
                if (savedState === 'true') {
                    sidebar.classList.add('collapsed');
                }
            } else {
                // Mobile: quitar collapsed, usar active
                sidebar.classList.remove('collapsed');
            }
        }, 250);
    });
    
    // ========================================
    // ACTIVE LINK
    // ========================================
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link:not([data-bs-toggle])');
    
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && href !== '#' && currentPath.includes(href)) {
            // Remover active de todos
            navLinks.forEach(l => l.classList.remove('active'));
            // Agregar active al link actual
            link.classList.add('active');
            
            // Si está en un submenu, expandirlo
            const collapse = link.closest('.collapse');
            if (collapse) {
                collapse.classList.add('show');
                const toggleLink = document.querySelector(`[data-bs-target="#${collapse.id}"]`);
                if (toggleLink) {
                    toggleLink.setAttribute('aria-expanded', 'true');
                }
            }
        }
    });
    
    // ========================================
    // MANEJAR SUBMENUS - Sin movimiento de scroll
    // ========================================
    const submenuToggles = document.querySelectorAll('[data-bs-toggle="collapse"]');
    submenuToggles.forEach(toggle => {
        const targetId = toggle.getAttribute('data-bs-target');
        const target = document.querySelector(targetId);
        
        if (target) {
            // Prevenir el comportamiento por defecto de Bootstrap collapse
            toggle.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                // Si el sidebar está colapsado, no hacer nada
                if (sidebar.classList.contains('collapsed')) {
                    return;
                }
                
                const sidebarNav = document.querySelector('.sidebar-nav');
                const isExpanded = target.classList.contains('show');
                
                // Bloquear temporalmente el scroll
                const scrollTop = sidebarNav.scrollTop;
                sidebarNav.style.overflow = 'hidden';
                
                // Toggle el submenu
                target.classList.toggle('show');
                this.setAttribute('aria-expanded', !isExpanded);
                
                // Forzar la posición del scroll inmediatamente
                sidebarNav.scrollTop = scrollTop;
                
                // Restaurar overflow después de la animación
                setTimeout(() => {
                    sidebarNav.style.overflow = 'auto';
                    sidebarNav.scrollTop = scrollTop;
                }, 350);
            });
            
            // Prevenir eventos de Bootstrap que causan scroll
            target.addEventListener('show.bs.collapse', function(e) {
                e.preventDefault();
                e.stopPropagation();
            });
            
            target.addEventListener('shown.bs.collapse', function(e) {
                e.preventDefault();
                e.stopPropagation();
            });
        }
    });
    
    // ========================================
    // SMOOTH SCROLL
    // ========================================
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#' && document.querySelector(href)) {
                e.preventDefault();
                document.querySelector(href).scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // ========================================
    // TOOLTIPS & POPOVERS (Bootstrap 5)
    // ========================================
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // ========================================
    // CERRAR DROPDOWNS AL HACER CLICK FUERA
    // ========================================
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.dropdown')) {
            const dropdowns = document.querySelectorAll('.dropdown-menu.show');
            dropdowns.forEach(dropdown => {
                const bsDropdown = bootstrap.Dropdown.getInstance(dropdown.previousElementSibling);
                if (bsDropdown) {
                    bsDropdown.hide();
                }
            });
        }
    });
});

// ========================================
// FUNCIONES ÚTILES
// ========================================

// Mostrar notificación toast
function showToast(message, type = 'info') {
    // Crear contenedor de toasts si no existe
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Crear toast
    const toastId = 'toast-' + Date.now();
    const bgClass = {
        'success': 'bg-success',
        'error': 'bg-danger',
        'warning': 'bg-warning',
        'info': 'bg-info'
    }[type] || 'bg-info';

    const icon = {
        'success': 'bi-check',
        'error': 'bi-x',
        'warning': 'bi-exclamation-triangle',
        'info': 'bi-info'
    }[type] || 'bi-info';

    const colorBorder = {
        'success': 'border-success',
        'error': 'border-danger',
        'warning': 'border-warning',
        'info': 'border-info'
    }[type] || 'border-info';

    const header = {
        'success': 'Éxito',
        'error': 'Error',
        'warning': 'Advertencia',
        'info': 'Información'
    }[type] || 'Información';

    const bgColor = {
        'success': '#D8F6E7',
        'error': '#F7DADC',
        'warning': '#FFF2C7',
        'info': '#D2F4FB'
    }[type] || '#D2F4FB';
    
    const textColor = {
        'success': 'text-success',
        'error': 'text-danger',
        'warning': 'text-warning',
        'info': 'text-info'
    }[type] || 'text-info';
    // const toastHTML = `
    //     <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert">
    //         <div class="d-flex">
    //             <div class="toast-body">
    //                 ${message}
    //             </div>
    //             <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    //         </div>
    //     </div>
    // `;

    const toastHTML = ` <div id="${toastId}" class="toast ${colorBorder}" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="toast-header" style="background-color: ${bgColor};">
        <span class="badge ${bgClass} me-2" ><i class="bi ${icon} fs-5"></i></span>
        <strong class="me-auto ml-2 fs-6 ${textColor}">${header}</strong>
        <small class="text-muted">${new Date().toLocaleTimeString()}</small>
        <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
      <div class="toast-body">
        ${message}
      </div>
    </div>
    `
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 3000 });
    toast.show();
    
    // Remover del DOM después de ocultarse
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

// Confirmar acción
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}