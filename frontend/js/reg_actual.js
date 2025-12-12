/**
 * js/reg_actual.js
 * Исправлено:
 * - После регистрации и очистки поиска список автоматически обновляется (сбрасывается фильтр).
 */

let currentEventId = null;
let isUnregisterMode = false;
let currentStats = { total: 0, arrived: 0 };
let syncInterval = null;
let socket = null;
const WS_URL = 'wss://reg.iltumen.ru/api/ws/events';

document.addEventListener('DOMContentLoaded', () => {
    initPage();
    const searchInput = document.getElementById('list-search-input');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(() => loadEventParticipants(), 300));
        searchInput.focus();
    }
});

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

async function initPage() {
    try {
        const res = await api('/events/active');
        if (res.ok) {
            const active = await res.json();
            if (active && active.id) {
                currentEventId = active.id;
                renderActiveEventHeader(active);
                document.getElementById('active-event-info').style.display = 'flex';
                document.getElementById('workspace').classList.remove('d-none');
                
                await loadEventStats(); 
                loadEventParticipants(); 
                
                connectWebSocket(currentEventId);
                startBackupSyncLoop(); 
            } else { showNoActiveEvent(); }
        } else { showNoActiveEvent(); }
    } catch (e) { console.error(e); showNoActiveEvent(); }
}

function connectWebSocket(eventId) {
    if (socket) socket.close();
    socket = new WebSocket(`${WS_URL}/${eventId}`);
    socket.onopen = () => { loadEventStats(); loadEventParticipants(); };
    socket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        } catch (e) { console.error(e); }
    };
    socket.onclose = () => { setTimeout(() => { if (currentEventId) connectWebSocket(currentEventId); }, 3000); };
    socket.onerror = (error) => { socket.close(); };
}

function handleWebSocketMessage(data) {
    loadEventStats();
    if (['new_registrations', 'arrival_update', 'deleted_registration'].includes(data.type)) {
        const searchInput = document.getElementById('list-search-input');
        // Если пользователь что-то пишет (поле не пустое и в фокусе), не мешаем ему обновлением
        if (document.activeElement === searchInput && searchInput.value.trim() !== '') return;
        loadEventParticipants(true);
    }
}

function startBackupSyncLoop() {
    if (syncInterval) clearInterval(syncInterval);
    syncInterval = setInterval(() => {
        loadEventStats();
        const searchInput = document.getElementById('list-search-input');
        if (document.activeElement === searchInput && searchInput.value.trim() !== '') return;
        loadEventParticipants(true);
    }, 30000); 
}

async function loadEventStats() {
    try {
        const res = await api('/events/active/stats');
        if (res.ok) {
            const stats = await res.json();
            currentStats.total = stats.total_registrants;
            currentStats.arrived = stats.arrived_participants;
            renderStats();
        }
    } catch (e) { console.error(e); }
}

function renderStats() {
    const counterEl = document.getElementById('arrival-counter');
    if (counterEl) {
        const total = currentStats.total;
        const arrived = currentStats.arrived;
        const expected = total - arrived;
        const displayCount = isUnregisterMode ? arrived : expected;
        counterEl.textContent = `${displayCount} / ${total}`;
    }
}

function showNoActiveEvent() {
    const noEvent = document.getElementById('no-active-event');
    if (noEvent) noEvent.classList.remove('d-none');
}

function renderActiveEventHeader(ev) {
    document.getElementById('ae-title').textContent = ev.title;
    document.getElementById('ae-title').title = ev.title; 
    document.getElementById('ae-date').textContent = new Date(ev.event_date).toLocaleDateString('ru-RU');
}

window.toggleRegistrationMode = function() {
    isUnregisterMode = !isUnregisterMode;
    const badge = document.getElementById('reg-mode-badge');
    if (isUnregisterMode) {
        badge.innerText = "Снять с регистрации";
        badge.classList.remove('text-success', 'bg-light');
        badge.classList.add('text-white', 'bg-danger');
    } else {
        badge.innerText = "Режим регистрации";
        badge.classList.remove('text-white', 'bg-danger');
        badge.classList.add('text-success', 'bg-light');
    }
    
    const searchInput = document.getElementById('list-search-input');
    if (searchInput) { searchInput.value = ''; searchInput.focus(); }
    
    renderStats();
    loadEventParticipants();
}

async function loadEventParticipants(isBackground = false) {
    if (!currentEventId) return;
    const tbody = document.getElementById('event-participants-body');
    if (!tbody) return;
    const searchInput = document.getElementById('list-search-input');
    const searchQuery = searchInput ? searchInput.value.trim() : '';

    try {
        const filterArrived = isUnregisterMode ? 'true' : 'false';
        const url = `/events/${currentEventId}/registrations/search?query=${encodeURIComponent(searchQuery)}&filter_arrived=${filterArrived}&limit=200&sort_by=alphabet`;
        const res = await api(url);
        if (res.ok) {
            const data = await res.json();
            const filteredData = data.filter(p => isUnregisterMode ? !!p.arrival_time : !p.arrival_time);
            renderTable(filteredData, searchQuery);
        }
    } catch (e) { console.error(e); }
}

function highlightMatch(text, query) {
    if (!query || !text) return text;
    const safeQuery = query.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&');
    const regex = new RegExp(`(${safeQuery})`, 'gi');
    return text.replace(regex, '<span class="fw-bold text-primary bg-warning-subtle px-1 rounded">$1</span>');
}

function renderTable(participants, searchQuery) {
    const tbody = document.getElementById('event-participants-body');
    if (!tbody) return;

    if (!participants || participants.length === 0) {
        const emptyMsg = isUnregisterMode ? "Нет прибывших участников для снятия" : "Все ожидаемые участники зарегистрированы (или не найдены)";
        tbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted py-5">${emptyMsg}</td></tr>`;
        return;
    }

    tbody.innerHTML = participants.map(p => {
        const displayName = highlightMatch(p.full_name, searchQuery);
        let actionBtn = '';
        if (isUnregisterMode) {
            actionBtn = `<button class="btn btn-danger btn-sm btn-action shadow-sm" onclick="handleUnsetArrival(${p.id}, '${p.full_name.replace(/'/g, "\\'")}')">Снять</button>`;
        } else {
            actionBtn = `<button class="btn btn-success btn-sm btn-action shadow-sm" onclick="handleSetArrival(${p.id}, '${p.full_name.replace(/'/g, "\\'")}')">Регистрация</button>`;
        }
        const note = p.note ? p.note : '';
        return `<tr><td class="align-middle">${displayName}</td><td class="align-middle"><small class="text-muted">${note}</small></td><td class="align-middle text-end">${actionBtn}</td></tr>`;
    }).join('');
}

function updateSystemStatus(message, isError = false) {
    const consoleEl = document.getElementById('console-msg');
    const consoleBox = document.getElementById('system-console');
    if (consoleEl) {
        const time = new Date().toLocaleTimeString('ru-RU');
        consoleEl.innerHTML = `<span class="text-muted">[${time}]</span> ${message}`;
        if (consoleBox) {
            consoleBox.style.borderTop = isError ? '2px solid #ff6b6b' : '2px solid #51cf66';
            setTimeout(() => { consoleBox.style.borderTop = '1px solid #444'; }, 2000);
        }
    }
}

// === ACTIONS ===

window.handleSetArrival = async function(participantId, participantName) {
    if (!currentEventId) return;
    try {
        const res = await api(`/events/${currentEventId}/participants/${participantId}/arrival`, 'PUT');
        if (res.ok) {
            const searchInput = document.getElementById('list-search-input');
            if(searchInput) {
                searchInput.value = ''; // Очищаем поиск
                searchInput.focus();
            }
            updateSystemStatus(`Зарегистрирован: <strong>${participantName}</strong>`);
            loadEventStats(); 
            
            // ВАЖНО: Принудительно обновляем список, чтобы показать всех (без фильтра)
            loadEventParticipants(true); 
        } else { updateSystemStatus(`Ошибка регистрации: ${participantName}`, true); }
    } catch (e) { updateSystemStatus("Ошибка сети", true); }
}

window.handleUnsetArrival = async function(participantId, participantName) {
    if (!currentEventId) return;
    if (!confirm(`Снять регистрацию у "${participantName}"?`)) return; 
    try {
        const res = await api(`/events/${currentEventId}/participants/${participantId}/arrival`, 'DELETE');
        if (res.ok) {
            const searchInput = document.getElementById('list-search-input');
            if(searchInput) {
                searchInput.value = ''; // Очищаем поиск
                searchInput.focus();
            }
            updateSystemStatus(`Снята регистрация: <strong>${participantName}</strong>`);
            loadEventStats(); 
            
            // ВАЖНО: Принудительно обновляем список
            loadEventParticipants(true); 
        } else { updateSystemStatus(`Ошибка отмены: ${participantName}`, true); }
    } catch (e) { updateSystemStatus("Ошибка сети", true); }
}
