const API_URL_LOGIN = 'https://reg.iltumen.ru/api';

document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const btn = e.target.querySelector('button');
    const errorBox = document.getElementById('login-error');
    
    // Сброс состояния
    btn.disabled = true;
    errorBox.style.display = 'none';
    errorBox.textContent = '';

    // Собираем данные формы
    const formData = new FormData(e.target);
    
    // Если сервер ждет application/x-www-form-urlencoded (стандарт OAuth2):
    const params = new URLSearchParams();
    formData.forEach((value, key) => params.append(key, value));

    try {
        const res = await fetch(`${API_URL_LOGIN}/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded' // Важный заголовок!
            },
            body: params // Отправляем как параметры URL
        });

        if (res.ok) {
            const data = await res.json();
            localStorage.setItem('token', data.access_token);
            
            // Если роль пришла, можно сохранить
            if(data.role) localStorage.setItem('role', data.role);

            // Перенаправление на главную (или reg_actual.php для регистраторов)
            window.location.href = 'reg_actual.php'; 
        } else {
            const errData = await res.json().catch(() => ({}));
            errorBox.textContent = errData.detail || 'Неверный логин или пароль';
            errorBox.style.display = 'block';
        }

    } catch (err) {
        console.error(err);
        errorBox.textContent = 'Ошибка соединения с сервером';
        errorBox.style.display = 'block';
    } finally {
        btn.disabled = false;
    }
});
