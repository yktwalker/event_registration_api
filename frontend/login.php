<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Вход в систему | Ил Тумэн</title>
    <!-- Подключаем Bootstrap -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Подключаем стили -->
    <link rel="stylesheet" href="css/login_styles.css">
    <link rel="icon" type="image/svg+xml" href="favicon.svg">
</head>
<body class="login-page">

    <div class="login-container">
        <!-- Заголовок -->
        <div class="login-header">
            <h1>Система регистрации<br>участников мероприятий</h1>
            <p>Государственное Собрание (Ил Тумэн)<br>Республики Саха (Якутия)</p>
        </div>

        <!-- Форма -->
        <form id="login-form">
            <div class="form-group">
                <label for="username" class="form-label">Пользователь</label>
                <!-- Добавлен name="username" -->
                <input type="text" id="username" name="username" class="form-control" placeholder="Введите логин" required autofocus>
            </div>
            
            <div class="form-group">
                <label for="password" class="form-label">Пароль</label>
                <!-- Добавлен name="password" -->
                <input type="password" id="password" name="password" class="form-control" placeholder="Введите пароль" required>
            </div>

            <button type="submit" class="btn-login">Войти</button>
        </form>

        <!-- Блок ошибки (исправлен ID) -->
        <div id="login-error" class="alert alert-danger mt-3" style="display:none;"></div>

        <!-- Подвал -->
        <div class="login-footer">
            &copy; <?php echo date("Y"); ?> W@lker
        </div>
    </div>

    <!-- Скрипт логина -->
    <script src="js/login.js"></script>

</body>
</html>
