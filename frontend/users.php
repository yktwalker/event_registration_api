<?php 
    $active_page = 'users'; 
    $page_title = 'Системные пользователи';
    include 'components/header.php'; 
?>

<div class="row">
    <!-- Форма создания -->
    <div class="col-md-4 mb-4">
        <div class="card border-0 shadow-sm">
            <div class="card-header bg-white fw-bold">
                <i class="fas fa-user-plus text-success me-2"></i> Новый пользователь
            </div>
            <div class="card-body">
                <form id="create-user-form">
                    <div class="mb-3">
                        <label class="form-label small text-muted">Логин</label>
                        <input type="text" id="u-username" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label small text-muted">ФИО</label>
                        <input type="text" id="u-fullname" class="form-control">
                    </div>
                    <div class="mb-3">
                        <label class="form-label small text-muted">Роль</label>
                        <select id="u-role" class="form-select">
                            <option value="Registrar">Registrar</option>
                            <option value="Operator">Operator</option>
                            <option value="Admin">Admin</option>
                        </select>
                    </div>
                    <div class="row mb-3">
                        <div class="col-6">
                            <label class="form-label small text-muted">Пароль</label>
                            <input type="password" id="u-pass1" class="form-control" required>
                        </div>
                        <div class="col-6">
                            <label class="form-label small text-muted">Повтор</label>
                            <input type="password" id="u-pass2" class="form-control" required>
                        </div>
                    </div>
                    <button type="submit" class="btn btn-success w-100">Создать</button>
                </form>
            </div>
        </div>
    </div>

    <!-- Таблица -->
    <div class="col-md-8">
        <div class="card border-0 shadow-sm">
            <div class="card-header bg-white d-flex justify-content-between align-items-center">
                <span class="fw-bold">Список пользователей</span>
                <button class="btn btn-sm btn-outline-secondary" onclick="loadUsers()">
                    <i class="fas fa-sync-alt"></i>
                </button>
            </div>
            <div class="card-body p-0">
                <table class="table table-hover align-middle mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Login</th>
                            <th>Имя</th>
                            <th>Роль</th>
                            <th class="text-end">Действия</th>
                        </tr>
                    </thead>
                    <tbody id="users-table-body">
                        <!-- JS content -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<!-- Модальное окно редактирования -->
<div class="modal fade" id="editUserModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Редактирование</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <input type="hidden" id="edit-user-id">
                
                <div class="mb-3">
                    <label class="form-label">Логин</label>
                    <input type="text" id="edit-user-login" class="form-control bg-light" disabled>
                </div>
                
                <div class="mb-3">
                    <label class="form-label">ФИО</label>
                    <input type="text" id="edit-user-fullname" class="form-control">
                </div>
                
                <div class="mb-3">
                    <label class="form-label">Роль</label>
                    <select id="edit-user-role" class="form-select">
                        <option value="Registrar">Registrar</option>
                        <option value="Operator">Operator</option>
                        <option value="Admin">Admin</option>
                    </select>
                </div>

                <hr class="my-4">
                <h6 class="text-muted mb-3">Смена пароля (необязательно)</h6>
                
                <div class="mb-3">
                    <label class="form-label small text-muted">Новый пароль</label>
                    <input type="password" id="edit-user-pass" class="form-control" placeholder="Оставьте пустым, если не меняете">
                </div>
                
                <div class="mb-3">
                    <label class="form-label small text-muted">Повторите новый пароль</label>
                    <input type="password" id="edit-user-pass-confirm" class="form-control" placeholder="Повтор пароля">
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                <button type="button" class="btn btn-primary" onclick="submitUserEdit()">Сохранить</button>
            </div>
        </div>
    </div>
</div>

<script>
    document.addEventListener('DOMContentLoaded', loadUsers);

    async function loadUsers() {
        const tbody = document.getElementById('users-table-body');
        tbody.innerHTML = '<tr><td colspan="4" class="text-center py-4 text-muted">Загрузка...</td></tr>';
        
        try {
            const res = await api('/system-users/');
            if (res.ok) {
                const users = await res.json();
                tbody.innerHTML = users.map(u => {
                    let roleBadge = 'bg-secondary';
                    if(u.role === 'Admin') roleBadge = 'bg-danger';
                    if(u.role === 'Operator') roleBadge = 'bg-warning text-dark';
                    if(u.role === 'Registrar') roleBadge = 'bg-info text-dark';

                    return `
                    <tr>
                        <td class="fw-bold">${u.username}</td>
                        <td>${u.full_name || '<span class="text-muted">-</span>'}</td>
                        <td><span class="badge ${roleBadge}">${u.role}</span></td>
                        <td class="text-end">
                            <button class="btn btn-sm btn-link text-decoration-none" onclick='openEditUser(${JSON.stringify(u)})'>
                                <i class="fas fa-edit"></i>
                            </button>
                            <!-- ИСПРАВЛЕНО: используем deleteUser вместо askDelete -->
                            <button class="btn btn-sm btn-link text-danger text-decoration-none" onclick="deleteUser(${u.id}, '${u.username}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    </tr>`;
                }).join('');
            }
        } catch (e) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Ошибка загрузки данных</td></tr>';
        }
    }

    document.getElementById('create-user-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const p1 = document.getElementById('u-pass1').value;
        const p2 = document.getElementById('u-pass2').value;
        
        if (p1 !== p2) {
            log('Пароли не совпадают!', 'error');
            return;
        }

        const body = {
            username: document.getElementById('u-username').value,
            full_name: document.getElementById('u-fullname').value,
            role: document.getElementById('u-role').value,
            password: p1
        };

        const res = await api('/system-users/', 'POST', body);
        if (res.ok) {
            log('Пользователь успешно создан', 'success');
            e.target.reset();
            loadUsers();
        } else {
            const err = await res.json();
            log(err.detail || 'Ошибка создания', 'error');
        }
    });

    // ДОБАВЛЕНО: Специальная функция для удаления системных пользователей
    async function deleteUser(id, username) {
        if (!confirm(`Вы действительно хотите удалить пользователя "${username}"?`)) {
            return;
        }

        try {
            // Используем прямой путь к API системных пользователей
            const res = await api('/system-users/' + id, 'DELETE');
            
            if (res.ok) {
                // Успешное удаление (200 или 204)
                loadUsers();
                log('Пользователь удален', 'success');
            } else {
                const err = await res.json();
                log(err.detail || 'Ошибка удаления', 'error');
            }
        } catch (e) {
            console.error(e);
            log('Ошибка соединения с сервером', 'error');
        }
    }
</script>

<?php include 'components/footer.php'; ?>
