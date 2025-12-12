<?php 
    $active_page = 'report'; 
    $page_title = ''; 
    include 'components/header.php'; 
?>

<!-- Подключаем стили отчета -->
<link rel="stylesheet" href="css/report_styles.css">

<!-- Подключаем Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<div class="container-fluid mt-3">
    <div id="report-container" class="fade-in shadow-sm rounded">
        <div class="text-center py-5" style="width: 100%;">
            <div class="spinner-border text-primary" role="status"></div>
            <p class="mt-2 text-muted">Загрузка данных...</p>
        </div>
    </div>
</div>

<script>
// Добавляем класс к body для применения специфичных стилей отчета
document.body.classList.add('report-page');

async function loadReport() {
    const container = document.getElementById('report-container');
    try {
        const activeRes = await api('/events/active');
        if (!activeRes.ok) {
            container.innerHTML = `<div class="alert alert-warning text-center" style="width: 100%;"><h4>Нет активного мероприятия</h4></div>`;
            return;
        }
        const activeEvent = await activeRes.json();
        const [reportRes, dirsRes] = await Promise.all([
            api(`/events/${activeEvent.id}/report`),
            api(`/directories/`)
        ]);

        if (reportRes.ok) {
            let htmlContent = await reportRes.text();
            
            // Замены текста
            htmlContent = htmlContent.replace(/Отчет по мероприятию:\s*/gi, '');
            htmlContent = htmlContent.replace(/Детализация по справочникам/gi, 'Детализация:');
            htmlContent = htmlContent.replace(/Доля пришедших участников по справочникам/gi, '');
            htmlContent = htmlContent.replace(/Итого \(уникальные участники\)/gi, 'Итого:');

            let replacements = {};
            if (dirsRes.ok) {
                const dirs = await dirsRes.json();
                dirs.forEach(d => {
                    if (d.description && d.description.trim() !== "") {
                        replacements[d.name] = d.description;
                    }
                });
            }

            // Парсинг
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = htmlContent;

            let totalPlanned = 0, totalActual = 0;
            const summaryBlock = tempDiv.querySelector('.summary');
            if(summaryBlock) {
                const text = summaryBlock.innerText;
                const matchPlan = text.match(/Всего запланировано:\s*(\d+)/);
                const matchFact = text.match(/Всего пришло:\s*(\d+)/);
                if(matchPlan) totalPlanned = parseInt(matchPlan[1]);
                if(matchFact) totalActual = parseInt(matchFact[1]);
            }

            let tablePlanned = 0, tableActual = 0;
            const rows = tempDiv.querySelectorAll('table tbody tr');
            rows.forEach(row => {
                if(row.cells.length > 2) {
                    tablePlanned += parseInt(row.cells[1].innerText) || 0;
                    tableActual += parseInt(row.cells[2].innerText) || 0;
                }
            });

            const otherPlanned = totalPlanned - tablePlanned;
            const otherActual = totalActual - tableActual;

            // Обновление JS
            if (Object.keys(replacements).length > 0) {
                htmlContent = htmlContent.replace(/labels:\s*\[(.*?)\]/s, (match, content) => {
                    let updatedContent = content.replace(/['"](.*?)['"]/g, (m, name) => {
                        const cleanName = name.replace(/\\'/g, "'");
                        if (replacements[cleanName]) return `'${replacements[cleanName].replace(/'/g, "\\'")}'`;
                        return m;
                    });
                    return `labels: [${updatedContent}]`;
                });
            }

            if (otherActual > 0 || otherPlanned > 0) {
                htmlContent = htmlContent.replace(/labels:\s*\[(.*?)\]/, "labels: [$1, 'Иные']");
                htmlContent = htmlContent.replace(/data:\s*\[(.*?)\]/, `data: [$1, ${otherActual}]`);
                htmlContent = htmlContent.replace(/backgroundColor:\s*\[(.*?)\]/, "backgroundColor: [$1, '#d3d3d3']");
            }

            htmlContent = htmlContent.replace(/legend:\s*\{/g, "legend: { onClick: null, ");

            container.innerHTML = htmlContent;

            // DOM манипуляции
            if (otherActual > 0 || otherPlanned > 0) {
                const tbody = container.querySelector('table tbody');
                if (tbody) {
                    const tr = document.createElement('tr');
                    const yieldPercent = otherPlanned > 0 ? ((otherActual / otherPlanned) * 100).toFixed(1) + '%' : '-';
                    tr.innerHTML = `<td>Иные</td><td>${otherPlanned}</td><td>${otherActual}</td><td>${yieldPercent}</td>`;
                    tbody.appendChild(tr);
                }
            }

             if (Object.keys(replacements).length > 0) {
                const realRows = container.querySelectorAll('table tbody tr');
                realRows.forEach(row => {
                    const firstCell = row.cells[0]; 
                    if (firstCell) {
                        const name = firstCell.textContent.trim();
                        if (replacements[name]) firstCell.textContent = replacements[name];
                    }
                });
            }
            
            const ths = container.querySelectorAll('th');
            ths.forEach(th => { if (th.textContent.trim() === 'Справочник') th.textContent = ''; });

            // Запуск
            const scripts = container.querySelectorAll('script');
            scripts.forEach(script => {
                if (script.innerText.includes('new Chart')) {
                    try { eval(script.innerText); } catch (e) { console.error("Chart Error:", e); }
                }
            });

            const nestedBody = container.querySelector('body');
            if (nestedBody) nestedBody.replaceWith(...nestedBody.childNodes);
            
            // Принудительно скрываем консоль, если она вдруг осталась
            const consoleEl = document.getElementById('system-console');
            if(consoleEl) consoleEl.style.display = 'none';

        } else {
            throw new Error('Не удалось получить отчет');
        }
    } catch (e) {
        console.error(e);
        container.innerHTML = `<div class="alert alert-danger text-center" style="width: 100%;">Ошибка: ${e.message}</div>`;
    }
}
document.addEventListener('DOMContentLoaded', loadReport);
</script>

<?php include 'components/footer.php'; ?>
