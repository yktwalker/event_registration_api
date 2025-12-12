let selectedDirectoryId = null;
let createModalInst = null;
let editModalInst = null;
let currentDirectories = [];
let currentPage = 1;
const ITEMS_PER_PAGE = 20;
let searchTimeout = null;

document.addEventListener('DOMContentLoaded', () => {
    const createModalEl = document.getElementById('createDirectoryModal');
    if (createModalEl) createModalInst = new bootstrap.Modal(createModalEl);
    
    const editModalEl = document.getElementById('editDirectoryModal');
    if (editModalEl) editModalInst = new bootstrap.Modal(editModalEl);
    
    loadDirectories();
});

async function loadDirectories() {
    const listContainer = document.getElementById('directories-list');
    try {
        const res = await api('/directories/'); 
        if (res.ok) {
            currentDirectories = await res.json();
            // Инициализируем поле для счетчика, если его нет (для кэша)
            currentDirectories.forEach(d => { if (d._memberCount === undefined) d._memberCount = null; });
            
            renderDirectoriesList();
            // Запускаем подсчет
            fetchDirectoriesCounts();
        } else {
            listContainer.innerHTML = '<div class="text-center text-danger py-3">Ошибка загрузки</div>';
        }
    } catch (e) {
        listContainer.innerHTML = '<div class="text-center text-danger py-3">Ошибка сети</div>';
    }
}

function renderDirectoriesList() {
    const listContainer = document.getElementById('directories-list');
    if (currentDirectories.length === 0) {
        listContainer.innerHTML = '<div class="text-center text-muted py-4 small">Нет справочников</div>';
        return;
    }

    listContainer.innerHTML = currentDirectories.map(d => {
        // Проверяем, есть ли уже загруженное значение
        const hasCount = d._memberCount !== null;
        const count = d._memberCount || 0;
        
        let badgeClass = 'badge rounded-pill dir-count-badge';
        let badgeContent = '';
        
        if (!hasCount) {
             badgeClass += ' bg-primary badge-loading'; // Пока грузится
        } else {
             badgeClass += ' badge-loaded';
             badgeContent = count;
             if (count === 0) badgeClass += ' bg-secondary';
             else badgeClass += ' bg-primary';
        }

        return `
        <div class="directory-item d-flex justify-content-between align-items-center ${selectedDirectoryId === d.id ? 'active' : ''}" onclick="selectDirectory(${d.id})">
            <div style="min-width: 0;">
                <div class="fw-bold text-truncate">${d.name}</div>
                <div class="small text-muted text-truncate">${d.description || 'Нет описания'}</div>
            </div>
            <span class="${badgeClass}" id="dir-count-${d.id}">${badgeContent}</span>
        </div>
    `}).join('');
}

async function fetchDirectoriesCounts() {
    // Грузим только для тех, у кого еще нет данных, или обновляем всех? 
    // Лучше обновить всех, но если данные уже есть в UI, не мигать.
    
    const promises = currentDirectories.map(async (dir) => {
        // Если уже загружено и мы не хотим обновлять каждый раз, можно добавить условие:
        // if (dir._memberCount !== null) return; 

        try {
            const res = await api(`/directories/${dir.id}/members/?limit=10000`); 
            if (res.ok) {
                const data = await res.json();
                const count = data.length;
                
                // Сохраняем в объект (кэш)
                dir._memberCount = count;
                
                // Обновляем UI точечно, чтобы не перерисовывать всё
                const badge = document.getElementById(`dir-count-${dir.id}`);
                if (badge) {
                    badge.textContent = count;
                    badge.classList.remove('badge-loading');
                    badge.classList.add('badge-loaded');
                    
                    if (count === 0) {
                        badge.classList.remove('bg-primary');
                        badge.classList.add('bg-secondary');
                    } else {
                        badge.classList.add('bg-primary');
                        badge.classList.remove('bg-secondary');
                    }
                }
            }
        } catch (e) {
            console.error(`Ошибка получения кол-ва для справочника ${dir.id}`);
        }
    });

    await Promise.all(promises);
}

function selectDirectory(id) {
    selectedDirectoryId = id;
    // При перерисовке теперь мы берем данные из currentDirectories, где уже лежат _memberCount
    renderDirectoriesList();
    
    const dir = currentDirectories.find(d => d.id === id);
    if (!dir) return;

    updateHeaderInfo(dir.name, dir.description);
    
    document.getElementById('dir-actions').classList.remove('d-none');
    document.getElementById('members-search-container').classList.remove('d-none');
    document.getElementById('members-search-input').value = '';
    
    currentPage = 1;
    loadDirectoryMembers(id);
}

function updateHeaderInfo(name, desc) {
    document.getElementById('selected-dir-info').innerHTML = `
        <h5 class="m-0 text-primary text-truncate">${name}</h5>
        <small class="text-muted text-truncate d-block">${desc || ''}</small>
    `;
}

async function loadDirectoryMembers(dirId) {
    const tbody = document.getElementById('members-table-body');
    const paginationNav = document.getElementById('header-pagination');
    
    tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-5">Загрузка...</td></tr>';
    
    const searchQuery = document.getElementById('members-search-input').value.trim();
    const offset = (currentPage - 1) * ITEMS_PER_PAGE;

    try {
        let url = `/directories/${dirId}/members/?limit=${ITEMS_PER_PAGE}&offset=${offset}`;
        if (searchQuery) {
            url += `&query=${encodeURIComponent(searchQuery)}`;
        }

        const res = await api(url);
        
        if (res.ok) {
            const members = await res.json();
            renderMembersTable(members, offset);
        } else {
            tbody.innerHTML = '<tr><td colspan="3" class="text-center text-danger py-4">Ошибка загрузки</td></tr>';
            paginationNav.classList.add('d-none');
        }
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center text-danger py-4">Ошибка сети</td></tr>';
        paginationNav.classList.add('d-none');
    }
}

function filterMembers() {
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        currentPage = 1;
        if (selectedDirectoryId) loadDirectoryMembers(selectedDirectoryId);
    }, 500);
}

function renderMembersTable(members, currentOffset) {
    const tbody = document.getElementById('members-table-body');
    const paginationNav = document.getElementById('header-pagination');
    const paginationControls = document.getElementById('pagination-controls');
    const footerInfo = document.getElementById('pagination-info');

    const count = members.length;
    const startNum = currentOffset + 1;
    const endNum = currentOffset + count;

    if (count === 0 && currentPage === 1) {
        footerInfo.textContent = 'Нет участников';
    } else {
        footerInfo.textContent = `Показано ${startNum}-${endNum}`;
    }

    if (members.length === 0) {
        if (currentPage === 1) {
             tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-5">Нет участников</td></tr>';
             paginationNav.classList.add('d-none');
        } else {
             tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-5">Больше записей нет</td></tr>';
             paginationNav.classList.remove('d-none');
        }
        return;
    }

    paginationNav.classList.remove('d-none');
    
    tbody.innerHTML = members.map(m => {
        const p = m.participant ? m.participant : m;
        const safeName = (p.full_name || '').replace(/'/g, "\\'");
        
        return `
        <tr>
            <td class="fw-bold">${p.full_name}</td>
            <td><small class="text-muted">${p.note || '-'}</small></td>
            <td class="text-end">
                <button class="btn btn-sm btn-link text-danger" onclick="removeMember(${p.id}, '${safeName}')">
                    <i class="fas fa-times"></i>
                </button>
            </td>
        </tr>`;
    }).join('');

    const isLastPage = count < ITEMS_PER_PAGE;
    
    let paginationHtml = '';
    
    paginationHtml += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage - 1}); return false;">&laquo;</a>
        </li>
    `;

    paginationHtml += `
        <li class="page-item active">
            <span class="page-link">${currentPage}</span>
        </li>
    `;

    paginationHtml += `
        <li class="page-item ${isLastPage ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage + 1}); return false;">&raquo;</a>
        </li>
    `;

    paginationControls.innerHTML = paginationHtml;
}

function changePage(page) {
    if (page < 1) return;
    currentPage = page;
    if (selectedDirectoryId) loadDirectoryMembers(selectedDirectoryId);
}

async function removeMember(participantId, name) {
    if (!confirm(`Убрать участника "${name}" из этого справочника?`)) return;
    if (!selectedDirectoryId) return;

    try {
        const res = await api(`/directories/${selectedDirectoryId}/members/${participantId}`, 'DELETE');
        if (res.ok) {
            loadDirectoryMembers(selectedDirectoryId);
            
            // Обновляем кэш и UI
            const dir = currentDirectories.find(d => d.id === selectedDirectoryId);
            if (dir && dir._memberCount > 0) {
                dir._memberCount--;
                // Обновляем бейдж вручную
                const badge = document.getElementById(`dir-count-${dir.id}`);
                if(badge) {
                    badge.textContent = dir._memberCount;
                    if (dir._memberCount === 0) {
                        badge.classList.remove('bg-primary');
                        badge.classList.add('bg-secondary');
                    }
                }
            }
            
            log('Участник исключен', 'success');
        } else {
            log('Ошибка исключения', 'error');
        }
    } catch (e) { log('Ошибка сети', 'error'); }
}

function openCreateDirModal() {
    document.getElementById('new-dir-name').value = '';
    document.getElementById('new-dir-desc').value = '';
    createModalInst.show();
}

async function submitCreateDirectory() {
    const name = document.getElementById('new-dir-name').value;
    const desc = document.getElementById('new-dir-desc').value;
    if (!name) { alert('Введите название'); return; }

    const res = await api('/directories/', 'POST', { name: name, description: desc });
    if (res.ok) {
        createModalInst.hide();
        loadDirectories();
        log('Справочник создан', 'success');
    } else {
        log('Ошибка создания', 'error');
    }
}

function openEditDirModal() {
    if (!selectedDirectoryId) return;
    const dir = currentDirectories.find(d => d.id === selectedDirectoryId);
    document.getElementById('edit-dir-id').value = dir.id;
    document.getElementById('edit-dir-name').value = dir.name;
    document.getElementById('edit-dir-desc').value = dir.description || '';
    editModalInst.show();
}

async function submitEditDirectory() {
    const id = document.getElementById('edit-dir-id').value;
    const name = document.getElementById('edit-dir-name').value;
    const desc = document.getElementById('edit-dir-desc').value;
    const res = await api(`/directories/${id}`, 'PUT', { name: name, description: desc });
    if (res.ok) {
        editModalInst.hide();
        await loadDirectories();
        if (selectedDirectoryId == id) selectDirectory(parseInt(id));
        log('Справочник обновлен', 'success');
    } else {
        log('Ошибка обновления', 'error');
    }
}

async function askDeleteDirectory() {
    if (!selectedDirectoryId) return;
    if (confirm(`Удалить справочник?`)) {
         const res = await api(`/directories/${selectedDirectoryId}`, 'DELETE');
         if (res.ok) {
             selectedDirectoryId = null;
             document.getElementById('selected-dir-info').innerHTML = '<h5 class="m-0 text-muted">Выберите справочник</h5>';
             document.getElementById('dir-actions').classList.add('d-none');
             document.getElementById('header-pagination').classList.add('d-none');
             document.getElementById('members-search-container').classList.add('d-none');
             document.getElementById('members-table-body').innerHTML = '<tr><td colspan="3" class="text-center text-muted py-5"><i class="fas fa-arrow-left me-2"></i>Выберите справочник</td></tr>';
             loadDirectories();
             log('Справочник удален', 'success');
         } else {
             log('Ошибка удаления', 'error');
         }
    }
}
