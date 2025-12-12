<?php 
    $active_page = 'events'; 
    $page_title = 'Управление мероприятиями';
    include 'components/header.php'; 
?>

<!-- Скрываем заголовок страницы через CSS -->
<script>document.body.classList.add('events-page');</script>
<style>.events-page h2 { display: none; }</style>

<!-- Панель действий -->
<div class="toolbar-fixed">
    <div class="card border-0 shadow-sm mb-3">
        <div class="card-body p-3">
            <div class="d-flex justify-content-between align-items-center">
                <button class="btn btn-success" onclick="openCreateEventModal()">
                    <i class="fas fa-plus me-2"></i> Добавить мероприятие
                </button>
                <button class="btn btn-outline-secondary" onclick="loadEvents()">
                    <i class="fas fa-sync-alt"></i> Обновить
                </button>
            </div>
        </div>
    </div>
</div>

<!-- Таблица мероприятий -->
<div class="table-scroll-area">
    <div class="card border-0 shadow-sm">
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                    <thead class="table-light">
                        <tr>
                            <th style="width: 50px;">Активное</th>
                            <th>Название</th>
                            <th>Дата</th>
                            <th class="text-end" style="width: 120px;">Действия</th>
                        </tr>
                    </thead>
                    <tbody id="events-table-body"></tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<!-- Модальное окно СОЗДАНИЯ события -->
<div class="modal fade" id="createEventModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Новое мероприятие</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <form id="create-event-form">
                    <div class="mb-3">
                        <label class="form-label">Название <span class="text-danger">*</span></label>
                        <input type="text" id="e-title" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Дата начала <span class="text-danger">*</span></label>
                        <input type="datetime-local" id="e-date" class="form-control" required>
                    </div>
                    <div class="form-check mb-3">
                        <input class="form-check-input" type="checkbox" id="e-active">
                        <label class="form-check-label">Сделать активным сразу</label>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                <button type="button" class="btn btn-success" onclick="submitCreateEvent()">Создать</button>
            </div>
        </div>
    </div>
</div>

<!-- Модальное окно РЕДАКТИРОВАНИЯ события -->
<div class="modal fade" id="editEventModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Редактирование</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <input type="hidden" id="edit-event-id">
                <div class="mb-3">
                    <label class="form-label">Название</label>
                    <input type="text" id="edit-event-title" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Дата начала</label>
                    <input type="datetime-local" id="edit-event-date" class="form-control" required>
                </div>
                <!-- В редактировании чекбокс тоже может быть полезен, если хотим снять активность без назначения другого -->
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="edit-event-active">
                    <label class="form-check-label">Активно</label>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                <button type="button" class="btn btn-primary" onclick="submitEditEvent()">Сохранить</button>
            </div>
        </div>
    </div>
</div>

<script>
    let createEventModalInst = null;
    let editEventModalInst = null;

    document.addEventListener('DOMContentLoaded', () => {
        createEventModalInst = new bootstrap.Modal(document.getElementById('createEventModal'));
        editEventModalInst = new bootstrap.Modal(document.getElementById('editEventModal'));
        loadEvents();
    });

    function openCreateEventModal() {
        document.getElementById('create-event-form').reset();
        const now = new Date();
        now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
        document.getElementById('e-date').value = now.toISOString().slice(0,16);
        createEventModalInst.show();
    }

    async function loadEvents() {
        const tbody = document.getElementById('events-table-body');
        tbody.innerHTML = '<tr><td colspan="4" class="text-center py-4">Загрузка...</td></tr>';
        
        try {
            const res = await api('/events/');
            if (res.ok) {
                let events = await res.json();
                
                events.sort((a, b) => {
                    if (a.registration_active === b.registration_active) {
                        return b.id - a.id; 
                    }
                    return a.registration_active ? -1 : 1;
                });

                if (events.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" class="text-center py-4 text-muted">Нет мероприятий</td></tr>';
                    return;
                }

                tbody.innerHTML = events.map(ev => `
                    <tr class="${ev.registration_active ? 'table-success' : ''}">
                        <td class="text-center">
                            <div class="form-check d-flex justify-content-center">
                                <input class="form-check-input" type="radio" name="activeEventGroup" 
                                    ${ev.registration_active ? 'checked' : ''} 
                                    onclick="handleActiveChange(${ev.id})" 
                                    style="cursor:pointer; transform: scale(1.2);">
                            </div>
                        </td>
                        <td class="fw-bold">${ev.title}</td>
                        <td>${new Date(ev.event_date).toLocaleDateString()} ${new Date(ev.event_date).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
                        <td class="text-end">
                            <button class="btn btn-sm btn-link" onclick='openEditEvent(${JSON.stringify(ev)})'>
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-sm btn-link text-danger" onclick="askDelete('event', ${ev.id}, '${ev.title}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">Ошибка загрузки</td></tr>`;
            }
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">Ошибка сети</td></tr>`;
        }
    }

    // === НОВАЯ ЛОГИКА ПЕРЕКЛЮЧЕНИЯ ===
    async function handleActiveChange(newActiveId) {
        // 1. Узнаем, кто сейчас активен
        const activeEv = await getActiveEvent();
        
        // Если кликнули на того же самого, ничего не делаем
        if (activeEv && activeEv.id === newActiveId) {
            return; 
        }

        // 2. Если есть активный - отключаем его
        if (activeEv) {
            const success = await updateEventStatus(activeEv, false);
            if (!success) {
                log('Не удалось отключить текущее активное мероприятие', 'error');
                loadEvents(); // Откат
                return;
            }
        }

        // 3. Включаем новое (получаем данные, потом обновляем)
        try {
            const res = await api(`/events/${newActiveId}`);
            if(res.ok) {
                const targetEv = await res.json();
                const success = await updateEventStatus(targetEv, true);
                if(success) {
                    log('Активное мероприятие изменено', 'success');
                    setTimeout(loadEvents, 300);
                } else {
                    log('Ошибка активации', 'error');
                    loadEvents();
                }
            }
        } catch (e) {
            loadEvents();
        }
    }

    // Вспомогательная: получить текущее активное
    async function getActiveEvent() {
        try {
            // Запрашиваем список всех, ищем активное (т.к. эндпоинт /active может вернуть 404 или null)
            // Или используем специальный эндпоинт, если он гарантированно есть
            const res = await api('/events/');
            if (res.ok) {
                const list = await res.json();
                return list.find(e => e.registration_active === true);
            }
        } catch(e) {}
        return null;
    }

    // Вспомогательная: обновить статус конкретного события
    async function updateEventStatus(evObj, isActive) {
        try {
            const body = {
                title: evObj.title,
                event_date: evObj.event_date,
                registration_active: isActive
            };
            const res = await api(`/events/${evObj.id}`, 'PUT', body);
            return res.ok;
        } catch (e) { return false; }
    }

    async function submitCreateEvent() {
        const titleVal = document.getElementById('e-title').value;
        const dateVal = document.getElementById('e-date').value;
        const wantActive = document.getElementById('e-active').checked;

        if(!titleVal || !dateVal) { alert("Заполните обязательные поля"); return; }

        // === ЕСЛИ ХОТИМ СОЗДАТЬ АКТИВНЫМ ===
        if (wantActive) {
            const activeEv = await getActiveEvent();
            if (activeEv) {
                // Отключаем старое перед созданием нового
                await updateEventStatus(activeEv, false);
            }
        }

        const body = {
            title: titleVal,
            event_date: dateVal,
            registration_active: wantActive
        };

        if (document.activeElement instanceof HTMLElement) {
            document.activeElement.blur();
        }

        const res = await api('/events/', 'POST', body);
        if (res.ok) {
            log('Мероприятие создано', 'success');
            createEventModalInst.hide();
            loadEvents();
        } else {
            log('Ошибка создания', 'error');
        }
    }

    window.openEditEvent = function(ev) {
        document.getElementById('edit-event-id').value = ev.id;
        document.getElementById('edit-event-title').value = ev.title;
        
        const d = new Date(ev.event_date);
        d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
        document.getElementById('edit-event-date').value = d.toISOString().slice(0,16);
        
        document.getElementById('edit-event-active').checked = ev.registration_active;
        
        editEventModalInst.show();
    }

    window.submitEditEvent = async function() {
        const id = document.getElementById('edit-event-id').value;
        const titleVal = document.getElementById('edit-event-title').value;
        const dateVal = document.getElementById('edit-event-date').value;
        const wantActive = document.getElementById('edit-event-active').checked;

        // Логика смены активности при редактировании
        // 1. Проверим, изменился ли статус
        // Получим текущее состояние из базы (надежнее)
        let currentIsActive = false;
        try {
            const gRes = await api(`/events/${id}`);
            if(gRes.ok) {
                const data = await gRes.json();
                currentIsActive = data.registration_active;
            }
        } catch(e){}

        // Если мы включаем активность (было выкл -> стало вкл)
        if (wantActive && !currentIsActive) {
             const activeEv = await getActiveEvent();
             if (activeEv && activeEv.id != id) {
                 await updateEventStatus(activeEv, false);
             }
        }

        const body = {
            title: titleVal,
            event_date: dateVal,
            registration_active: wantActive
        };

        const res = await api(`/events/${id}`, 'PUT', body);
        if(res.ok) {
            log('Мероприятие обновлено', 'success');
            
            if (document.activeElement instanceof HTMLElement) {
                document.activeElement.blur();
            }
            
            editEventModalInst.hide();
            loadEvents();
        } else {
            const err = await res.json();
            log(`Ошибка: ${err.detail}`, 'error');
        }
    }
</script>

<?php include 'components/footer.php'; ?>
