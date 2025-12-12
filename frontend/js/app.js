const API_URL = 'https://reg.iltumen.ru/api';

// Глобальные переменные состояния
let deleteTargetId = null;
let deleteTargetType = null;
let deleteModal = null;
let editUserModal = null;

// --- LOGGING UTILS ---
function log(msg, type = 'info') {
    const el = document.getElementById('console-msg');
    if (!el) return;
    const time = new Date().toLocaleTimeString();
    const color = type === 'error' ? '#ff6b6b' : (type === 'success' ? '#51cf66' : '#ced4da');
    el.innerHTML = `<span style="color:${color}">[${time}]</span> ${msg}`;
    
    const consoleBox = document.getElementById('system-console');
    if (consoleBox && type === 'error') {
        consoleBox.style.borderTop = '1px solid #ff6b6b';
        setTimeout(() => consoleBox.style.borderTop = '1px solid #444', 3000);
    }
}

// --- API WRAPPER ---
async function api(endpoint, method = 'GET', body = null) {
    const token = localStorage.getItem('token');
    const headers = {};

    if (body !== null && body !== undefined) {
        headers['Content-Type'] = 'application/json';
    }

    if (token) headers['Authorization'] = `Bearer ${token}`;

    try {
        const res = await fetch(`${API_URL}${endpoint}`, {
            method,
            headers,
            body: (body !== null && body !== undefined) ? JSON.stringify(body) : null
        });

        if (res.status === 401) {
            log('Сессия истекла. Перенаправление...', 'error');
            setTimeout(logout, 1000);
            throw new Error("Unauthorized");
        }

        if (res.status === 403) {
            log('Доступ запрещен (403).', 'error');
            throw new Error("Forbidden");
        }

        return res;
    } catch (e) {
        if (e.message !== "Unauthorized" && e.message !== "Forbidden") {
            log(`Ошибка сети: ${e.message}`, 'error');
        }
        throw e;
    }
}

// --- AUTH & RBAC LOGIC ---
function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'login.php';
        return;
    }

    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const payload = JSON.parse(window.atob(base64));

        // === ЛОГИКА ДЛЯ РЕГИСТРАТОРА ===
        if (payload.role === 'Registrar') {
            const hiddenPages = ['users.php', 'participants.php', 'directories.php', 'events.php'];
            hiddenPages.forEach(page => {
                const link = document.querySelector(`.main-menu a[href="${page}"]`);
                if (link) link.style.display = 'none';
            });

            const navLeft = document.querySelector('.nav-left');
            if (navLeft) navLeft.style.display = 'none';

            const allowedPages = ['reg_actual.php', 'login.php', 'report.php'];
            const currentPage = window.location.pathname.split('/').pop() || 'index.php';
            
            if (!allowedPages.includes(currentPage)) {
                window.location.href = 'reg_actual.php';
                return;
            }
        }

        // === ЛОГИКА ДЛЯ ОПЕРАТОРА ===
        if (payload.role === 'Operator') {
            const usersLink = document.querySelector('a[href="users.php"]');
            if (usersLink) {
                usersLink.style.display = 'none';
            }
            if (window.location.pathname.includes('users.php')) {
                window.location.href = 'events.php';
            }
        }

        // Отображение пользователя
        const userDisplay = document.getElementById('user-display-name');
        const roleDisplay = document.getElementById('user-display-role');
        
        if (userDisplay) userDisplay.textContent = payload.sub;
        if (roleDisplay) {
            roleDisplay.textContent = payload.role;
            let badgeClass = 'badge bg-secondary';
            if(payload.role === 'Admin') badgeClass = 'badge bg-danger';
            if(payload.role === 'Operator') badgeClass = 'badge bg-warning text-dark';
            if(payload.role === 'Registrar') badgeClass = 'badge bg-success';
            roleDisplay.className = badgeClass;
        }

    } catch (e) {
        console.error("Ошибка токена:", e);
        logout();
    }
}

// Init Modals
document.addEventListener('DOMContentLoaded', () => {
    const delEl = document.getElementById('deleteModal');
    if(delEl) deleteModal = new bootstrap.Modal(delEl);
    
    const editEl = document.getElementById('editUserModal');
    if(editEl) editUserModal = new bootstrap.Modal(editEl);

    // ОБРАБОТЧИК КНОПКИ УДАЛЕНИЯ (ГЛОБАЛЬНЫЙ)
    const confirmDelBtn = document.getElementById('btn-confirm-del');
    if (confirmDelBtn) {
        confirmDelBtn.addEventListener('click', async () => {
            if (!deleteTargetId || !deleteTargetType) return;
            
            // Если вдруг кто-то использует askDelete для простых сущностей
            let endpoint = '';
            if (deleteTargetType === 'event') endpoint = `/events/${deleteTargetId}`;
            if (deleteTargetType === 'participant') endpoint = `/participants/${deleteTargetId}`;
            if (deleteTargetType === 'directory') endpoint = `/directories/${deleteTargetId}`;
            
            if (endpoint) {
                try {
                    const res = await api(endpoint, 'DELETE');
                    if (res.ok) {
                        log('Успешно удалено', 'success');
                        if (deleteModal) deleteModal.hide();
                        // Обновляем страницу (простой вариант)
                        setTimeout(() => window.location.reload(), 500);
                    } else {
                        log('Ошибка при удалении', 'error');
                    }
                } catch (e) {
                    log('Ошибка сети', 'error');
                }
            } else {
                console.warn('Неизвестный тип удаления:', deleteTargetType);
                if (deleteModal) deleteModal.hide();
            }
        });
    }
});

function logout() {
    localStorage.removeItem('token');
    window.location.href = 'login.php';
}

// --- GLOBAL DELETE HANDLER ---
window.askDelete = function(type, id, name) {
    deleteTargetId = id;
    deleteTargetType = type;
    const nameEl = document.getElementById('del-object-name');
    if (nameEl) nameEl.innerText = name;
    if (deleteModal) deleteModal.show();
}

// --- EDIT USER HANDLER ---
window.openEditUser = function(user) {
    document.getElementById('edit-user-id').value = user.id;
    document.getElementById('edit-user-login').value = user.username;
    document.getElementById('edit-user-fullname').value = user.full_name || '';
    document.getElementById('edit-user-role').value = user.role;
    
    const pass1 = document.getElementById('edit-user-pass');
    const pass2 = document.getElementById('edit-user-pass-confirm');
    
    if(pass1) { pass1.value = ''; pass1.classList.remove('is-invalid'); }
    if(pass2) { pass2.value = ''; pass2.classList.remove('is-invalid'); }
    
    if (editUserModal) editUserModal.show();
}

window.submitUserEdit = async function() {
    const id = document.getElementById('edit-user-id').value;
    const body = {
        full_name: document.getElementById('edit-user-fullname').value,
        role: document.getElementById('edit-user-role').value
    };
    
    const pass = document.getElementById('edit-user-pass');
    if(pass && pass.value) {
        const passConf = document.getElementById('edit-user-pass-confirm');
        if(pass.value !== passConf.value) {
            passConf.classList.add('is-invalid');
            return;
        }
        body.password = pass.value;
    }

    try {
        const res = await api(`/system-users/${id}`, 'PUT', body);
        if(res.ok) {
            log('Пользователь обновлен', 'success');
            if (editUserModal) editUserModal.hide();
            if (typeof loadUsers === 'function') loadUsers();
        } else {
            const err = await res.json();
            alert('Ошибка: ' + err.detail);
        }
    } catch(e) {
        console.error(e);
    }
}
