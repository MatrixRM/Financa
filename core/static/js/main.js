// ===========================
// Main JavaScript File
// ===========================

document.addEventListener('DOMContentLoaded', function() {
    
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('[data-confirm-delete]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Tem certeza que deseja excluir? Esta ação não pode ser desfeita.')) {
                e.preventDefault();
            }
        });
    });

    // Format currency inputs
    const currencyInputs = document.querySelectorAll('input[type="number"][step="0.01"]');
    currencyInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value) {
                this.value = parseFloat(this.value).toFixed(2);
            }
        });
    });

    // Toggle recurrence frequency field
    const recorrenteCheckbox = document.getElementById('id_recorrente');
    const frequenciaField = document.getElementById('id_frequencia');
    
    if (recorrenteCheckbox && frequenciaField) {
        const frequenciaGroup = frequenciaField.closest('.form-group');
        
        function toggleFrequencia() {
            if (recorrenteCheckbox.checked) {
                frequenciaGroup.style.display = 'block';
                frequenciaField.required = true;
            } else {
                frequenciaGroup.style.display = 'none';
                frequenciaField.required = false;
                frequenciaField.value = '';
            }
        }
        
        recorrenteCheckbox.addEventListener('change', toggleFrequencia);
        toggleFrequencia(); // Initial state
    }

    // Dynamic form field toggling for registration
    const opcaoRadios = document.querySelectorAll('input[name="opcao"]');
    const nomeCasaGroup = document.getElementById('id_nome_casa')?.closest('.form-group');
    const codigoConviteGroup = document.getElementById('id_codigo_convite')?.closest('.form-group');
    
    if (opcaoRadios.length > 0) {
        function toggleCasaFields() {
            const opcao = document.querySelector('input[name="opcao"]:checked')?.value;
            
            if (nomeCasaGroup && codigoConviteGroup) {
                if (opcao === 'criar') {
                    nomeCasaGroup.style.display = 'block';
                    codigoConviteGroup.style.display = 'none';
                    document.getElementById('id_nome_casa').required = true;
                    document.getElementById('id_codigo_convite').required = false;
                } else {
                    nomeCasaGroup.style.display = 'none';
                    codigoConviteGroup.style.display = 'block';
                    document.getElementById('id_nome_casa').required = false;
                    document.getElementById('id_codigo_convite').required = true;
                }
            }
        }
        
        opcaoRadios.forEach(radio => {
            radio.addEventListener('change', toggleCasaFields);
        });
        toggleCasaFields(); // Initial state
    }

    // Smooth scroll to top
    const scrollTopBtn = document.getElementById('scrollTopBtn');
    if (scrollTopBtn) {
        window.addEventListener('scroll', () => {
            if (window.pageYOffset > 300) {
                scrollTopBtn.style.display = 'block';
            } else {
                scrollTopBtn.style.display = 'none';
            }
        });

        scrollTopBtn.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // Table row click to edit
    const clickableRows = document.querySelectorAll('[data-href]');
    clickableRows.forEach(row => {
        row.style.cursor = 'pointer';
        row.addEventListener('click', function(e) {
            if (!e.target.closest('a, button')) {
                window.location.href = this.dataset.href;
            }
        });
    });

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Copy to clipboard functionality
    const copyButtons = document.querySelectorAll('[data-copy]');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const textToCopy = this.dataset.copy;
            navigator.clipboard.writeText(textToCopy).then(() => {
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="bi bi-check"></i> Copiado!';
                setTimeout(() => {
                    this.innerHTML = originalText;
                }, 2000);
            });
        });
    });

    // Add animation class to cards on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.card').forEach(card => {
        observer.observe(card);
    });
});

// ===========================
// Chart.js Helpers
// ===========================

// Chart.js default configuration
if (typeof Chart !== 'undefined') {
    Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
    Chart.defaults.color = '#6c757d';
}

// Format currency for Brazil (BRL)
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

// Format date for Brazil
function formatDate(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('pt-BR').format(date);
}

// Generate random color
function generateRandomColor() {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

// Export table to CSV
function exportTableToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    const rows = table.querySelectorAll('tr');
    const csv = [];

    rows.forEach(row => {
        const cols = row.querySelectorAll('td, th');
        const csvRow = [];
        cols.forEach(col => {
            csvRow.push(col.textContent.trim());
        });
        csv.push(csvRow.join(','));
    });

    const csvString = csv.join('\n');
    const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// ===========================
// Service Worker Registration
// ===========================

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // Uncomment to enable PWA
        // navigator.serviceWorker.register('/sw.js')
        //     .then(registration => console.log('SW registered'))
        //     .catch(error => console.log('SW registration failed', error));
    });
}
