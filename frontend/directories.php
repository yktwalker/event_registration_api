<?php 
    $active_page = 'directories'; 
    $page_title = 'Управление справочниками';
    include 'components/header.php'; 
?>

<link rel="stylesheet" href="css/directories.css">
<script>document.body.classList.add('participants-page');</script>

<div class="directories-layout">
    
    <!-- ЛЕВАЯ ПАНЕЛЬ -->
    <div class="dir-sidebar">
        <div class="dir-sidebar-header d-flex justify-content-between align-items-center">
            <h5 class="m-0"><i class="fas fa-folder text-warning me-2"></i>Справочники</h5>
            <button class="btn btn-sm btn-success" onclick="openCreateDirModal()" title="Создать справочник">
                <i class="fas fa-plus"></i>
            </button>
        </div>
        <div class="dir-sidebar-list" id="directories-list">
            <div class="text-center text-muted py-4">Загрузка...</div>
        </div>
    </div>

    <!-- ПРАВАЯ ПАНЕЛЬ -->
    <div class="dir-content">
        
        <!-- ШАПКА -->
        <div class="dir-content-header">
            <!-- Левая часть: Инфо и Поиск -->
            <div class="d-flex align-items-center flex-grow-1 overflow-hidden">
                <div id="selected-dir-info" style="min-width: 150px; max-width: 40%;">
                    <h5 class="m-0 text-muted">Выберите справочник</h5>
                </div>
                
                <div id="members-search-container" class="search-box d-none ms-3 flex-grow-1" style="max-width: 300px;">
                    <i class="fas fa-search"></i>
                    <input type="text" id="members-search-input" class="form-control form-control-sm" placeholder="Поиск участников..." oninput="filterMembers()">
                </div>
            </div>

            <!-- Правая часть: Кнопки и Пагинация -->
            <div class="d-flex align-items-center gap-3">
                <div id="dir-actions" class="d-none">
                    <button class="btn btn-sm btn-outline-primary" onclick="openEditDirModal()">
                        <i class="fas fa-pen me-1"></i>Изменить
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="askDeleteDirectory()">
                        <i class="fas fa-trash me-1"></i>Удалить
                    </button>
                </div>
                
                <!-- Пагинация теперь здесь -->
                <nav id="header-pagination" class="d-none border-start ps-3">
                    <ul class="pagination pagination-sm m-0" id="pagination-controls">
                        <!-- Кнопки -->
                    </ul>
                </nav>
            </div>
        </div>

        <!-- ТАБЛИЦА -->
        <div class="dir-content-body">
            <table class="table table-hover align-middle mb-0" id="members-table">
                <thead class="table-light">
                    <tr>
                        <th>ФИО участника</th>
                        <th>Примечание</th>
                        <th class="text-end" style="width: 100px;">Действия</th>
                    </tr>
                </thead>
                <tbody id="members-table-body">
                    <tr>
                        <td colspan="3" class="text-center text-muted py-5">
                            <i class="fas fa-arrow-left me-2"></i>Выберите справочник слева
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <!-- Нижний футер с инфо (опционально, можно убрать если не нужен) -->
        <div class="dir-content-footer py-1 px-3 bg-light border-top text-end">
            <small class="text-muted" id="pagination-info">Всего участников: 0</small>
        </div>
    </div>
</div>

<!-- Модальные окна (без изменений) -->
<div class="modal fade" id="createDirectoryModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Новый справочник</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="mb-3">
                    <label class="form-label">Название <span class="text-danger">*</span></label>
                    <input type="text" id="new-dir-name" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Описание</label>
                    <textarea id="new-dir-desc" class="form-control" rows="3"></textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                <button type="button" class="btn btn-success" onclick="submitCreateDirectory()">Создать</button>
            </div>
        </div>
    </div>
</div>

<div class="modal fade" id="editDirectoryModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Редактирование</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <input type="hidden" id="edit-dir-id">
                <div class="mb-3">
                    <label class="form-label">Название</label>
                    <input type="text" id="edit-dir-name" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Описание</label>
                    <textarea id="edit-dir-desc" class="form-control" rows="3"></textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                <button type="button" class="btn btn-primary" onclick="submitEditDirectory()">Сохранить</button>
            </div>
        </div>
    </div>
</div>

<script src="js/directories.js"></script>
<?php include 'components/footer.php'; ?>
