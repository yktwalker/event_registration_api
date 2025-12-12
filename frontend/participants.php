<?php 
    $active_page = 'participants'; 
    $page_title = 'Управление участниками';
    include 'components/header.php'; 
?>

<!-- Добавляем класс для страницы, чтобы через CSS скрыть лишний заголовок -->
<script>document.body.classList.add('participants-page');</script>

<!-- 1. Фиксированная панель кнопок -->
<div class="toolbar-fixed">
    <div class="card border-0 shadow-sm mb-3">
        <div class="card-body p-3">
            <div class="d-flex justify-content-between align-items-center gap-3 flex-wrap">
                
                <div class="d-flex gap-2">
                    <button class="btn btn-success" onclick="openCreateModal()">
                        <i class="fas fa-user-plus me-2"></i> Добавить
                    </button>
                    <button class="btn btn-outline-success" onclick="openImportModal()">
                        <i class="fas fa-file-upload me-2"></i> Импорт
                    </button>
                </div>

                <div class="d-flex gap-2 flex-grow-1 justify-content-end" style="max-width: 600px;">
                    <div class="input-group">
                        <span class="input-group-text bg-white border-end-0"><i class="fas fa-search text-muted"></i></span>
                        <input type="text" id="search-input" class="form-control border-start-0 ps-0" placeholder="Поиск по имени...">
                    </div>
                    <button class="btn btn-primary" onclick="searchParticipants()">Поиск</button>
                    <button class="btn btn-secondary" onclick="resetSearch()">Все</button>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- 2. Скроллящаяся область с таблицей -->
<div class="table-scroll-area">
    <div class="card border-0 shadow-sm">
        <div class="card-body p-0">
            <div class="table-responsive"> 
                <table class="table table-hover align-middle mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Имя / ФИО</th>
                            <th style="width: 200px;">Справочники</th>
                            <th>Примечание</th>
                            <th class="text-end" style="width: 100px;">Действия</th>
                        </tr>
                    </thead>
                    <tbody id="participants-table-body">
                        <tr><td colspan="4" class="text-center text-muted py-5">Загрузка списка...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<!-- МОДАЛЬНЫЕ ОКНА -->

<!-- Create Modal -->
<div class="modal fade" id="createParticipantModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Новый участник</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <form id="create-participant-form">
                    <div class="mb-3">
                        <label class="form-label">ФИО / Название <span class="text-danger">*</span></label>
                        <input type="text" id="p-name" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Добавить в справочник</label>
                        <select id="p-directory" class="form-select">
                            <option value="">нет</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Примечание</label>
                        <textarea id="p-note" class="form-control" rows="3"></textarea>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                <button type="button" class="btn btn-success" onclick="submitCreateParticipant()">Добавить</button>
            </div>
        </div>
    </div>
</div>

<!-- Import Modal -->
<div class="modal fade" id="importModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title"><i class="fas fa-file-csv text-success me-2"></i>Массовый импорт</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="alert alert-info small">
                    <i class="fas fa-info-circle me-2"></i>
                    Формат: <b>.txt</b> или <b>.csv</b> (UTF-8).<br>
                    Строка: <code>ФИО, Примечание</code>
                </div>
                <div class="mb-3">
                    <label class="form-label fw-bold">1. Выберите файл</label>
                    <input type="file" id="import-file" class="form-control" accept=".csv, .txt">
                </div>
                <div class="mb-3">
                    <label class="form-label fw-bold">2. Куда добавить?</label>
                    <select id="import-directory" class="form-select">
                        <option value="">Просто в базу</option>
                    </select>
                </div>
                <div id="import-preview" class="d-none">
                    <label class="form-label fw-bold text-success">Предпросмотр:</label>
                    <table class="table table-sm table-bordered small">
                        <thead><tr class="table-light"><th>ФИО</th><th>Примечание</th></tr></thead>
                        <tbody id="import-preview-body"></tbody>
                    </table>
                    <div class="text-end text-muted small" id="import-count-msg"></div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                <button type="button" class="btn btn-primary" id="btn-start-import" disabled onclick="submitImport()">
                    <i class="fas fa-upload me-2"></i> Загрузить
                </button>
            </div>
        </div>
    </div>
</div>

<!-- Edit Modal -->
<div class="modal fade" id="editParticipantModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Редактирование</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <input type="hidden" id="edit-participant-id">
                <input type="hidden" id="current-directory-id">
                <div class="mb-3">
                    <label class="form-label">ФИО / Название</label>
                    <input type="text" id="edit-participant-name" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Справочник</label>
                    <select id="edit-participant-directory" class="form-select">
                        <option value="">Загрузка...</option>
                    </select>
                    <div class="form-text text-muted">Выберите "нет", чтобы удалить из справочника.</div>
                </div>
                <div class="mb-3">
                    <label class="form-label">Примечание</label>
                    <textarea id="edit-participant-note" class="form-control" rows="3"></textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                <button type="button" class="btn btn-primary" onclick="submitEditParticipant()">Сохранить</button>
            </div>
        </div>
    </div>
</div>

<script>
    let createModalInst = null;
    let editModalInst = null;
    let importModalInst = null;
    let parsedImportData = [];

    document.addEventListener('DOMContentLoaded', () => {
        createModalInst = new bootstrap.Modal(document.getElementById('createParticipantModal'));
        editModalInst = new bootstrap.Modal(document.getElementById('editParticipantModal'));
        importModalInst = new bootstrap.Modal(document.getElementById('importModal'));

        document.getElementById('search-input').addEventListener('keypress', function (e) {
            if (e.key === 'Enter') searchParticipants();
        });
        document.getElementById('import-file').addEventListener('change', handleFileSelect);

        window.loadParticipants = searchParticipants;

        loadDirectoriesForSelects();
        searchParticipants();
    });

    function resetSearch() {
        document.getElementById('search-input').value = '';
        searchParticipants();
    }

    async function loadDirectoriesForSelects() {
        try {
            const res = await api('/directories/');
            if (res.ok) {
                const items = await res.json();
                const optionsHtml = '<option value="">нет</option>' + 
                    items.map(d => `<option value="${d.id}">${d.name}</option>`).join('');

                document.getElementById('p-directory').innerHTML = optionsHtml;
                document.getElementById('edit-participant-directory').innerHTML = optionsHtml;
                
                const importOptions = '<option value="">Просто в базу (без справочника)</option>' + 
                    items.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
                document.getElementById('import-directory').innerHTML = importOptions;
            }
        } catch (e) {}
    }

    async function searchParticipants() {
        let query = document.getElementById('search-input').value.trim();
        const tbody = document.getElementById('participants-table-body');
        const apiQuery = query ? query : '%';

        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">Поиск...</td></tr>';

        try {
            const res = await api(`/participants/search/?query=${encodeURIComponent(apiQuery)}&limit=100`);
            if (res.ok) {
                const items = await res.json();
                
                // === СОРТИРОВКА НА КЛИЕНТЕ: Новые сверху ===
                // Сортируем полученный массив по ID в порядке убывания
                items.sort((a, b) => b.id - a.id);

                if (items.length > 0) {
                    tbody.innerHTML = items.map(p => {
                        const safeName = (p.full_name || '').replace(/'/g, "\'").replace(/"/g, '&quot;');
                        let dirsHtml = '<span class="text-muted small">-</span>';
                        if (p.directories && p.directories.length > 0) {
                            dirsHtml = p.directories.map(d => `<span class="badge bg-info text-dark me-1">${d.name}</span>`).join('');
                        }
                        return `<tr>
                            <td class="fw-bold">${p.full_name}</td>
                            <td>${dirsHtml}</td>
                            <td><small class="text-muted">${p.note || '-'}</small></td>
                            <td class="text-end">
                                <button class="btn btn-sm btn-link" onclick='openEditParticipant(${JSON.stringify(p)})'><i class="fas fa-edit"></i></button>
                                <button class="btn btn-sm btn-link text-danger" onclick="askDelete('participant', ${p.id}, '${safeName}')"><i class="fas fa-trash"></i></button>
                            </td>
                        </tr>`;
                    }).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">Ничего не найдено</td></tr>';
                }
            } else {
                tbody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">Ошибка: ${res.status}</td></tr>`;
            }
        } catch (e) {
             tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Ошибка сети</td></tr>';
        }
    }

    function openImportModal() {
        document.getElementById('import-file').value = '';
        document.getElementById('import-preview').classList.add('d-none');
        document.getElementById('btn-start-import').disabled = true;
        parsedImportData = [];
        importModalInst.show();
    }

    function handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = function(e) { parseCSV(e.target.result); };
        reader.readAsText(file, 'UTF-8');
    }

    function parseCSV(text) {
        const lines = text.split(/\r\n|\n/);
        parsedImportData = [];
        lines.forEach(line => {
            line = line.trim();
            if (!line) return; 
            const parts = line.split(',');
            let fullName = parts[0].trim();
            let note = parts.slice(1).join(',').trim(); 
            if (fullName) {
                parsedImportData.push({ full_name: fullName, email: "user@example.com", phone: "", note: note });
            }
        });
        showImportPreview();
    }

    function showImportPreview() {
        const previewDiv = document.getElementById('import-preview');
        const tbody = document.getElementById('import-preview-body');
        const countMsg = document.getElementById('import-count-msg');
        const btn = document.getElementById('btn-start-import');
        if (parsedImportData.length === 0) {
            previewDiv.classList.add('d-none');
            btn.disabled = true;
            alert("Не удалось найти данные.");
            return;
        }
        const previewItems = parsedImportData.slice(0, 5);
        tbody.innerHTML = previewItems.map(item => `<tr><td>${item.full_name}</td><td>${item.note}</td></tr>`).join('');
        countMsg.textContent = `Всего будет загружено: ${parsedImportData.length} записей`;
        previewDiv.classList.remove('d-none');
        btn.disabled = false;
    }

    async function submitImport() {
        const btn = document.getElementById('btn-start-import');
        const dirId = document.getElementById('import-directory').value;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Загрузка...';
        try {
            const res = await api('/participants/bulk/', 'POST', parsedImportData);
            if (res.ok) {
                const created = await res.json();
                log(`Импортировано: ${created.length}`, 'success');
                if (dirId && created.length > 0) {
                    const promises = created.map(p => 
                        api('/directories/add-member/', 'POST', { participant_id: p.id, directory_id: parseInt(dirId) }).catch(() => {}) 
                    );
                    await Promise.all(promises);
                }
                importModalInst.hide();
                searchParticipants();
            } else { log('Ошибка импорта', 'error'); }
        } catch (e) { log('Ошибка сети', 'error'); } 
        finally { btn.innerHTML = '<i class="fas fa-upload me-2"></i> Загрузить'; btn.disabled = false; }
    }

    function openCreateModal() {
        document.getElementById('create-participant-form').reset();
        createModalInst.show();
    }

    async function submitCreateParticipant() {
        const nameVal = document.getElementById('p-name').value;
        if(!nameVal) { alert("Введите имя"); return; }
        
        const dirId = document.getElementById('p-directory').value;
        const noteVal = document.getElementById('p-note').value || "";
        
        const res = await api('/participants/', 'POST', { full_name: nameVal, email: "user@example.com", phone: "", note: noteVal });
        
        if (res.ok) {
            const newP = await res.json();
            log(`Добавлен: ${nameVal}`, 'success');
            
            if (dirId && newP.id) {
                await api('/directories/add-member/', 'POST', { participant_id: newP.id, directory_id: parseInt(dirId) }).catch(()=>{});
            }
            
            if (document.activeElement instanceof HTMLElement) {
                 document.activeElement.blur();
            }

            createModalInst.hide();
            
            // Фильтрация по добавленному имени
            document.getElementById('search-input').value = nameVal;
            searchParticipants();

        } else { 
            log('Ошибка добавления', 'error'); 
        }
    }

    window.openEditParticipant = async function(p) {
        document.getElementById('edit-participant-id').value = p.id;
        document.getElementById('edit-participant-name').value = p.full_name || '';
        document.getElementById('edit-participant-note').value = p.note || '';
        const dirSelect = document.getElementById('edit-participant-directory');
        const currentDirInput = document.getElementById('current-directory-id');
        dirSelect.value = "";
        currentDirInput.value = "";
        editModalInst.show();
        try {
            const res = await api(`/participants/${p.id}`);
            if (res.ok) {
                const fullP = await res.json();
                if (fullP.directories && fullP.directories.length > 0) {
                    const currentId = fullP.directories[0].id;
                    dirSelect.value = currentId;
                    currentDirInput.value = currentId;
                }
            }
        } catch (e) {}
    }

    window.submitEditParticipant = async function() {
        const id = document.getElementById('edit-participant-id').value;
        const nameVal = document.getElementById('edit-participant-name').value;
        const noteVal = document.getElementById('edit-participant-note').value || "";
        const oldDirId = document.getElementById('current-directory-id').value;
        const newDirId = document.getElementById('edit-participant-directory').value;
        const res = await api(`/participants/${id}`, 'PUT', { full_name: nameVal, email: "user@example.com", phone: "", note: noteVal });
        if(res.ok) {
            log(`Обновлено`, 'success');
            if (oldDirId && oldDirId !== newDirId) await api(`/directories/${oldDirId}/members/${id}`, 'DELETE').catch(()=>{});
            if (newDirId && newDirId !== oldDirId) await api('/directories/add-member/', 'POST', { participant_id: parseInt(id), directory_id: parseInt(newDirId) }).catch(()=>{});
            
            if (document.activeElement instanceof HTMLElement) {
                 document.activeElement.blur();
            }
            
            editModalInst.hide();
            searchParticipants();
        } else { log('Ошибка', 'error'); }
    }
</script>

<?php include 'components/footer.php'; ?>
