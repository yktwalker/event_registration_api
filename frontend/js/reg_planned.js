/* js/reg_planned.js */

let currentEventId = null;
let dirModal = null;
let createModal = null;
let globalSearchModal = null;

// Переменная для статистики
let currentStats = { total: 0, arrived: 0 };

document.addEventListener('DOMContentLoaded', () => {
    // === ИНИЦИАЛИЗАЦИЯ МОДАЛЬНЫХ ОКОН ===
    
    // 1. Directory Modal
    const dirEl = document.getElementById('directoryModal');
    if (dirEl) {
        dirModal = new bootstrap.Modal(dirEl);
        handleModalFocus(dirEl, 'dir-select');
    }
    
    // 2. Create Modal
    const createEl = document.getElementById('quickCreateModal');
    if (createEl) {
        createModal = new bootstrap.Modal(createEl);
        handleModalFocus(createEl, 'new-p-name');
    }

    // 3. Global Search Modal
    const globalEl = document.getElementById('globalSearchModal');
    if (globalEl) {
        globalSearchModal = new bootstrap.Modal(globalEl);
        handleModalFocus(globalEl, 'global-search-input');
        
        const globalInput = document.getElementById('global-search-input');
        if(globalInput) {
            globalInput.addEventListener('keypress', (e) => {
                if(e.key === 'Enter') searchGlobalUsers();
            });
        }
    }
    
    initPage();
    
    // === ЖИВОЙ ПОИСК ПО СПИСКУ ===
    const listSearchInput = document.getElementById('list-search-input');
    if (listSearchInput) {
        listSearchInput.addEventListener('input', debounce(() => {
            loadEventParticipants(); 
        }, 400));
    }
});

// Универсальная функция для фокуса
function handleModalFocus(modalEl, focusTargetId) {
    modalEl.addEventListener('shown.bs.modal', () => {
        const input = document.getElementById(focusTargetId);
        if (input) input.focus();
    });

    modalEl.addEventListener('hide.bs.modal', () => {
        if (document.activeElement && modalEl.contains(document.activeElement)) {
            document.activeElement.blur();
        }
    });
}

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

// --- ИНИЦИАЛИЗАЦИЯ ---

async function initPage() {
    try {
        const res = await api('/events/active');
        if(res.ok) {
            const active = await res.json();
            if (active) {
                currentEventId = active.id;
                renderActiveEventHeader(active);
                document.getElementById('active-event-info').style.display = 'flex';
                document.getElementById('workspace').classList.remove('d-none');
                
                // Загружаем статистику для шапки
                await loadEventStats();
                
                loadEventParticipants();
                loadDirectories();
            } else {
                document.getElementById('no-active-event').classList.remove('d-none');
            }
        } else {
            document.getElementById('no-active-event').classList.remove('d-none');
        }
    } catch (e) {
        console.error(e);
        document.getElementById('no-active-event').classList.remove('d-none');
    }
}

function renderActiveEventHeader(ev) {
    document.getElementById('ae-title').textContent = ev.title;
    
    // Если элемент ae-id существует, заполняем его
    const idEl = document.getElementById('ae-id');
    if(idEl) idEl.textContent = ev.id;
    
    document.getElementById('ae-date').textContent = new Date(ev.event_date).toLocaleDateString();
}

// --- НОВЫЕ ФУНКЦИИ (ДЛЯ СЧЕТЧИКА) ---
async function loadEventStats() {
    if (!currentEventId) return;
    try {
        const res = await api('/events/active/stats');
        if (res.ok) {
            const stats = await res.json();
            currentStats.total = stats.total_registrants;
            currentStats.arrived = stats.arrived_participants;
            renderStats();
        }
    } catch (e) {
        console.error(e);
    }
}

function renderStats() {
    const counterEl = document.getElementById('arrival-counter');
    if (counterEl) {
        // Отображение: Прибыло / Всего (как в reg_actual)
        counterEl.textContent = `${currentStats.arrived} / ${currentStats.total}`;
    }
}
// ------------------------------------

// --- ЗАГРУЗКА И ФИЛЬТРАЦИЯ ---

async function loadEventParticipants() {
    if(!currentEventId) return;
    
    // Обновляем статистику каждый раз при обновлении списка
    loadEventStats();

    const tbody = document.getElementById('event-participants-body');
    const searchQuery = document.getElementById('list-search-input').value.trim();
    
    if(tbody.children.length === 0 || tbody.innerText.includes('Загрузка')) {
         tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4"><span class="spinner-border spinner-border-sm"></span> Обновление...</td></tr>';
    }
    
    try {
        let url = `/events/${currentEventId}/participants/`;
        if (searchQuery) {
            url += `?query=${encodeURIComponent(searchQuery)}`;
        }

        const res = await api(url);
        if(res.ok) {
            const list = await res.json();
            document.getElementById('p-count').textContent = list.length;

            if(list.length === 0) {
                if (searchQuery) {
                    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">Ничего не найдено по запросу</td></tr>';
                } else {
                    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">Пока никого нет</td></tr>';
                }
                return;
            }
            
            list.sort((a, b) => b.id - a.id); 

            tbody.innerHTML = list.map(p => `
                <tr>
                    <td class="fw-bold">
                        ${highlightMatch(p.full_name, searchQuery)}
                    </td>
                    <td class="small text-muted">${p.note || '-'}</td>
                    <td class="small">
                        <span class="badge bg-light text-dark border">
                            <i class="fas fa-user-tag me-1"></i> ${p.registered_by_full_name}
                        </span>
                    </td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-link text-danger" onclick="removeParticipantFromEvent(${p.id})" title="Удалить из мероприятия">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        }
    } catch(e) {
        console.error(e);
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Ошибка загрузки данных</td></tr>';
    }
}

function highlightMatch(text, query) {
    if (!query) return text;
    const regex = new RegExp(`(${query})`, 'gi');
    return text.replace(regex, '<span class="bg-warning text-dark px-1 rounded">$1</span>');
}

// --- СПРАВОЧНИКИ ---

async function loadDirectories() {
    try {
        const res = await api('/directories/');
        if(res.ok) {
            const dirs = await res.json();
            const select = document.getElementById('dir-select');
            select.innerHTML = '<option value="">Выберите справочник...</option>' + 
                dirs.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
        }
    } catch(e){}
}

function openAddFromDirectoryModal() {
    if (dirModal) dirModal.show();
}

async function submitDirectoryImport() {
    const dirId = document.getElementById('dir-select').value;
    if(!dirId) return;
    
    if(!confirm("Добавить всех людей из справочника?")) return;

    try {
        const res = await api(`/events/${currentEventId}/register/`, 'POST', {
            participant_ids: null,
            directory_id: parseInt(dirId)
        });

        if(res.ok) {
            const added = await res.json();
            showSystemMessage(`Добавлено участников: ${added.length}`, 'success'); // Используем showSystemMessage если log не определен
            if (dirModal) dirModal.hide();
            document.getElementById('list-search-input').value = '';
            loadEventParticipants();
        } else {
            const err = await res.json();
            showSystemMessage(`Ошибка: ${err.detail}`, 'error');
        }
    } catch(e) { showSystemMessage('Ошибка сети', 'error'); }
}

// --- СОЗДАНИЕ НОВОГО УЧАСТНИКА ---

function openQuickCreateModal() {
    document.getElementById('new-p-name').value = '';
    document.getElementById('new-p-note').value = '';
    if (createModal) createModal.show();
}

async function submitQuickCreate() {
    const name = document.getElementById('new-p-name').value;
    const note = document.getElementById('new-p-note').value;
    if(!name) return;

    try {
        // 1. Создаем участника
        const createRes = await api('/participants/', 'POST', {
            full_name: name,
            note: note,
            email: "user@example.com", 
            phone: ""
        });
        
        if(createRes.ok) {
            const newP = await createRes.json();
            
            // 2. Регистрируем на текущее мероприятие
            // Ждем завершения этой операции ПЕРЕД закрытием окна
            await registerParticipantById(newP.id);
            
            // 3. Теперь точно закрываем окно и очищаем поля
            document.getElementById('new-p-name').value = '';
            document.getElementById('new-p-note').value = '';
            
            if (createModal) {
                createModal.hide();
                // Удаляем backdrop вручную, если вдруг он залип
                const backdrop = document.querySelector('.modal-backdrop');
                if(backdrop) backdrop.remove();
            }

            // 4. Обновляем список (registerParticipantById уже вызывает его, но на всякий случай)
            // loadEventParticipants(); 
            
        } else {
            try {
                const err = await createRes.json();
                showSystemMessage(`Ошибка создания: ${err.detail || 'Неизвестная ошибка'}`, 'error');
            } catch(jsonErr) {
                showSystemMessage('Ошибка сервера (500)', 'error');
            }
        }
    } catch(e) { 
        console.error(e);
        showSystemMessage('Ошибка сети', 'error'); 
    }
}

// --- ГЛОБАЛЬНЫЙ ПОИСК ---

function openGlobalSearchModal() {
    document.getElementById('global-search-input').value = '';
    document.getElementById('global-search-results').innerHTML = '';
    if(globalSearchModal) globalSearchModal.show();
}

async function searchGlobalUsers() {
    const q = document.getElementById('global-search-input').value;
    const tbody = document.getElementById('global-search-results');
    tbody.innerHTML = '<tr><td>Поиск...</td></tr>';
    
    try {
        const res = await api(`/participants/search/?query=${encodeURIComponent(q)}&limit=10`);
        if(res.ok) {
            const items = await res.json();
            if(items.length === 0) {
                tbody.innerHTML = '<tr><td class="text-muted">Не найдено</td></tr>';
                return;
            }
            tbody.innerHTML = items.map(p => `
                <tr>
                    <td>${p.full_name}</td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-outline-primary" onclick="registerParticipantById(${p.id})">
                            <i class="fas fa-plus"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        }
    } catch(e){}
}

// --- ОБЩИЕ УТИЛИТЫ ---

async function registerParticipantById(pId) {
    if(!currentEventId) return;
    try {
        const res = await api(`/events/${currentEventId}/register/`, 'POST', {
            participant_ids: [parseInt(pId)],
            directory_id: null
        });
        
        if(res.ok) {
            // Если мы регистрируем из глобального поиска, закрываем его модалку тоже
            if(globalSearchModal && document.getElementById('globalSearchModal').classList.contains('show')) {
                 globalSearchModal.hide();
            }

            showSystemMessage('Участник добавлен', 'success');
            loadEventParticipants();
        } else {
            const err = await res.json();
            showSystemMessage(`Ошибка: ${err.detail}`, 'error');
        }
    } catch(e) { showSystemMessage('Ошибка сети', 'error'); }
}

async function removeParticipantFromEvent(pId) {
    if(!confirm('Удалить участника из списка мероприятия?')) return;
    
    try {
        const res = await api(`/events/${currentEventId}/participants/${pId}`, 'DELETE');
        if(res.ok) {
            showSystemMessage('Удалено', 'success');
            loadEventParticipants();
        } else {
            showSystemMessage('Ошибка удаления', 'error');
        }
    } catch(e) { showSystemMessage('Ошибка сети', 'error'); }
}

// Вспомогательная функция для замены log, если его нет
function showSystemMessage(msg, type) {
    // Пытаемся вызвать глобальный метод из app.js, если он там есть
    if (window.App && window.App.showToast) {
        window.App.showToast(msg, type);
    } else {
        console.log(`[${type}] ${msg}`);
        // Можно добавить вывод в консоль подвала, если элемент существует
        const consoleEl = document.getElementById('system-console');
        if(consoleEl) {
             consoleEl.textContent = msg;
             consoleEl.className = type === 'error' ? 'text-danger' : 'text-success';
             setTimeout(() => { consoleEl.textContent = 'Система готова.'; consoleEl.className = ''; }, 3000);
        }
    }
}
