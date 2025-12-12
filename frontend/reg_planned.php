<?php 
    $active_page = 'eventactive'; 
    $page_title = '';
    include 'components/header.php'; 
?>

<div class="container-fluid">
    
    <!-- СТИЛИ ДЛЯ БАНЕРА -->
    <link rel="stylesheet" href="css/reg_common.css">
    <link rel="stylesheet" href="css/reg_planned.css">

    <!-- ИЗМЕНЕНО: Новый банер -->
    <div id="active-event-info" class="event-banner event-banner-planned" style="display:none !important;">
        
        <!-- Левая часть: Дата, Бейдж, Заголовок -->
        <div class="banner-content">
            <div class="meta-row">
                <div class="date-wrap">
                    <i class="far fa-calendar-alt"></i> 
                    <span id="ae-date" class="fw-bold">...</span>
                </div>
                
                <span class="status-badge">
                    Планирование
                </span>
            </div>
            
            <h4 id="ae-title" class="event-title" title="">Загрузка...</h4>
            <!-- Скрываем ID, он нужен для JS -->
            <span id="ae-id" class="d-none"></span>
        </div>
        
        <!-- Правая часть: Счетчик -->
        <div class="banner-counter-block">
            <div class="counter-box">
                <div id="arrival-counter" class="counter-value">...</div>
            </div>
        </div>
    </div>

    <!-- Если нет активного мероприятия -->
    <div id="no-active-event" class="text-center py-5 d-none">
        <i class="fas fa-calendar-times text-muted mb-3" style="font-size: 3rem;"></i>
        <h4 class="text-muted">Нет активного мероприятия</h4>
        <p class="text-muted">Назначьте активное мероприятие в разделе "Мероприятия".</p>
        <a href="events.php" class="btn btn-outline-primary mt-3">Перейти к выбору</a>
    </div>

    <!-- Основная рабочая область -->
    <div id="workspace" class="d-none">
        <div class="row">
            <!-- Панель управления -->
            <div class="col-md-12 mb-3">
                <div class="card border-0 shadow-sm">
                    <div class="card-body p-3">
                        <div class="row g-2 align-items-center">
                            <!-- Кнопки действий -->
                            <div class="col-auto d-flex gap-2">
                                <button class="btn btn-primary" onclick="openAddFromDirectoryModal()">
                                    <i class="fas fa-users me-2"></i> Из Справочника
                                </button>
                                <button class="btn btn-success" onclick="openQuickCreateModal()">
                                    <i class="fas fa-user-plus me-2"></i> Новый участник
                                </button>
                                <!-- Глобальный поиск (опционально) -->
                                <button class="btn btn-outline-secondary" onclick="openGlobalSearchModal()" title="Поиск по всей базе для добавления">
                                    <i class="fas fa-globe"></i>
                                </button>
                            </div>

                            <!-- Поле поиска (Фильтр списка) -->
                            <div class="col">
                                <div class="input-group">
                                    <span class="input-group-text bg-light border-end-0">
                                        <i class="fas fa-search text-muted"></i>
                                    </span>
                                    <input type="text" id="list-search-input" class="form-control border-start-0" placeholder="Поиск участников в списке...">
                                </div>
                            </div>

                            <!-- Кнопка обновления -->
                            <div class="col-auto">
                                <button class="btn btn-light" onclick="loadEventParticipants()" title="Обновить список">
                                    <i class="fas fa-sync-alt"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Таблица участников -->
            <div class="col-md-12">
                <div class="card border-0 shadow-sm">
                    <div class="card-header bg-white fw-bold d-flex justify-content-between align-items-center">
                        <span>Список участников</span>
                        <span class="badge bg-secondary" id="p-count">0</span>
                    </div>
                    <div class="card-body p-0">
                        <!-- ЗДЕСЬ ДОБАВЛЕН КЛАСС table-scroll-container -->
                        <div class="table-responsive table-scroll-container">
                            <table class="table table-hover align-middle mb-0">
                                <thead class="table-light">
                                    <tr>
                                        <th>ФИО</th>
                                        <th>Примечание</th>
                                        <th>Кем зарегистрирован</th>
                                        <th class="text-end">Действия</th>
                                    </tr>
                                </thead>
                                <tbody id="event-participants-body">
                                    <tr><td colspan="4" class="text-center text-muted py-4">Загрузка...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- МОДАЛЬНОЕ ОКНО: Из справочника -->
<div class="modal fade" id="directoryModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Добавить справочник целиком</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <label class="form-label">Выберите справочник</label>
                <select id="dir-select" class="form-select mb-3">
                    <option value="">Загрузка...</option>
                </select>
                <div class="alert alert-warning small">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Все участники выбранного справочника будут зарегистрированы на мероприятие.
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-primary w-100" onclick="submitDirectoryImport()">
                    <i class="fas fa-download me-2"></i> Добавить всех
                </button>
            </div>
        </div>
    </div>
</div>

<!-- МОДАЛЬНОЕ ОКНО: Создание нового -->
<div class="modal fade" id="quickCreateModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header bg-success text-white">
                <h5 class="modal-title">Новый участник</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="mb-3">
                    <label class="form-label">ФИО <span class="text-danger">*</span></label>
                    <input type="text" id="new-p-name" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Примечание</label>
                    <textarea id="new-p-note" class="form-control" rows="2"></textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-success w-100" onclick="submitQuickCreate()">
                    Создать и добавить
                </button>
            </div>
        </div>
    </div>
</div>

<!-- МОДАЛЬНОЕ ОКНО: Глобальный поиск (если нужно найти кого-то, кого нет в списке) -->
<div class="modal fade" id="globalSearchModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Поиск по всей базе (для добавления)</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="input-group mb-3">
                    <input type="text" id="global-search-input" class="form-control" placeholder="ФИО...">
                    <button class="btn btn-primary" onclick="searchGlobalUsers()">Найти</button>
                </div>
                <table class="table table-sm table-hover"><tbody id="global-search-results"></tbody></table>
            </div>
        </div>
    </div>
</div>

<script src="js/reg_planned.js"></script>

<?php include 'components/footer.php'; ?>
