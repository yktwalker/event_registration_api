<?php 
    $active_page = 'reg_actual'; 
    $page_title = ''; 
    include 'components/header.php'; 
?>

<div class="container-fluid h-100 d-flex flex-column">
    
    <!-- СТИЛИ ДЛЯ БАНЕРА -->
    <link rel="stylesheet" href="css/reg_common.css">
    <link rel="stylesheet" href="css/reg_actual.css">

    <!-- ИЗМЕНЕНО: Новый банер -->
    <div id="active-event-info" class="event-banner event-banner-actual" style="display:none !important;">
        
        <!-- Левая часть: Дата, Бейдж, Заголовок -->
        <div class="banner-content">
            <div class="meta-row">
                <div class="date-wrap">
                    <i class="far fa-calendar-check"></i> 
                    <span id="ae-date" class="fw-bold">...</span>
                </div>
                
                <span id="reg-mode-badge" 
                      class="status-badge" 
                      onclick="toggleRegistrationMode()">
                    Режим регистрации
                </span>
            </div>
            
            <h4 id="ae-title" class="event-title" title="">Загрузка...</h4>
        </div>
        
        <!-- Правая часть: Счетчик -->
        <div class="banner-counter-block">
            <div class="counter-box">
                <div id="arrival-counter" class="counter-value">0 / 0</div>
            </div>
        </div>
    </div>

    <!-- No Event -->
    <div id="no-active-event" class="text-center py-5 d-none flex-grow-1 d-flex flex-column justify-content-center">
        <div>
            <i class="fas fa-user-clock text-muted mb-3" style="font-size: 4rem;"></i>
            <h3 class="text-muted">Нет активного мероприятия</h3>
        </div>
    </div>

    <!-- Workspace -->
    <div id="workspace" class="d-none flex-column flex-grow-1" style="min-height: 0;">
        <!-- Search Toolbar -->
        <div class="card border-0 shadow-sm mb-3 flex-shrink-0">
            <div class="card-body p-3">
                <div class="row g-2">
                    <div class="col">
                        <div class="input-group input-group-lg">
                            <span class="input-group-text bg-primary text-white border-primary"><i class="fas fa-search"></i></span>
                            <input type="text" id="list-search-input" class="form-control border-primary" placeholder="Поиск по фамилии...">
                            <button class="btn btn-outline-secondary" type="button" onclick="document.getElementById('list-search-input').value=''; loadEventParticipants();"><i class="fas fa-times"></i></button>
                        </div>
                    </div>
                    <div class="col-auto">
                        <button class="btn btn-lg btn-light border" onclick="loadEventParticipants()"><i class="fas fa-sync-alt"></i></button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Table Container -->
        <div class="card border-0 shadow-sm flex-grow-1" style="min-height: 0;">
            <div class="card-body p-0 h-100">
                <div class="table-scroll-container">
                    <table class="table table-hover align-middle mb-0 w-100">
                        <thead class="table-light">
                            <tr>
                                <th style="width: 45%">ФИО</th>
                                <th style="width: 35%">Примечание</th>
                                <th style="width: 20%" class="text-end">Действие</th>
                            </tr>
                        </thead>
                        <tbody id="event-participants-body">
                            <tr><td colspan="3" class="text-center text-muted py-5">Загрузка списка...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="js/reg_actual.js?v=<?php echo time(); ?>"></script>

<?php include 'components/footer.php'; ?>
