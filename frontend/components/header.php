<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Регистрация на мероприятия</title>
    
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Font Awesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    
    <!-- Custom CSS -->
    <link rel="stylesheet" href="css/styles.css">
    <link rel="icon" type="image/svg+xml" href="favicon.svg">
</head>
<body>

<div id="main-wrapper">
    
    <!-- TOP NAVIGATION HEADER -->
    <header class="top-navbar">
        <!-- Левая часть: Ссылки [Факт] и [План] -->
        <div class="nav-left d-flex align-items-center">
            <!-- Блок ссылок, видимость которых управляется JS -->
            <div id="nav-links-block">
                <a href="reg_actual.php" class="nav-link-main">[Факт]</a>
                <span class="nav-text-separator mx-2"></span>
                <a href="reg_planned.php" class="nav-link-main">[План]</a>
            </div>
        </div>

        <!-- Правая часть: Меню и Пользователь -->
        <div class="nav-right d-flex align-items-center gap-4">
            <!-- Главное меню -->
            <nav class="main-menu">
                <a href="users.php" class="menu-item nav-item-users <?php echo ($active_page == 'users') ? 'active' : ''; ?>">
                    [Пользователи]
                </a>
                <a href="participants.php" class="menu-item nav-item-participants <?php echo ($active_page == 'participants') ? 'active' : ''; ?>">
                    [Участники]
                </a>
                <a href="directories.php" class="menu-item nav-item-directories <?php echo ($active_page == 'directories') ? 'active' : ''; ?>">
                    [Справочники]
                </a>
                <a href="events.php" class="menu-item nav-item-events <?php echo ($active_page == 'events') ? 'active' : ''; ?>">
                    [Мероприятия]
                </a>
                
                <!-- ЛОГИКА ПЕРЕКЛЮЧЕНИЯ КНОПКИ ОТЧЕТ/РЕГИСТРАЦИЯ -->
                <?php if ($active_page == 'report'): ?>
                    <a href="reg_actual.php" class="menu-item nav-item-report active">
                        [Регистрация]
                    </a>
                <?php else: ?>
                    <a href="report.php" class="menu-item nav-item-report">
                        [Отчет]
                    </a>
                <?php endif; ?>
            </nav>

            <!-- Блок пользователя (Всегда справа) -->
            <div class="user-section border-start ps-4"> 
                <span class="user-info text-end">
                    <span id="user-display-name" class="fw-bold d-block">Загрузка...</span>
                    <!-- Спан с ролью, нужен для работы JS -->
                    <span id="user-display-role" class="role-badge badge bg-light text-secondary border">...</span>
                </span>
                <a href="#" onclick="logout()" class="btn-logout ms-3">
                    [Выход]
                </a>
            </div>
        </div>
    </header>

    <!-- CONTENT WRAPPER -->
    <div class="content-wrapper">
        
        <?php if (!empty($page_title)): ?>
        <div class="content-header">
            <h2 class="m-0 text-dark"><?php echo $page_title; ?></h2>
        </div>
        <?php endif; ?>

        <div class="content-body">

<!-- JS для скрытия ссылок по роли -->
<script>
document.addEventListener('DOMContentLoaded', () => {
     const roleSpan = document.getElementById('user-display-role');
     const linksBlock = document.getElementById('nav-links-block');

     if(roleSpan && linksBlock) {
         const observer = new MutationObserver(() => {
             const role = roleSpan.textContent.trim();
             // Скрываем ссылки [Факт]/[План] для Регистратора
             if(role === 'Registrar' || role === 'Регистратор') { 
                 linksBlock.classList.add('d-none'); 
             } else {
                 linksBlock.classList.remove('d-none');
             }
         });
         observer.observe(roleSpan, {childList: true, characterData: true, subtree: true});
     }
});
</script>
