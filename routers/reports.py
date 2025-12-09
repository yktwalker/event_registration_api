from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
import models
from database import get_db
from dependencies import get_current_registrar_or_admin

router = APIRouter()

@router.get("/events/{event_id}/report", response_class=HTMLResponse)
async def get_event_report(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_registrar_or_admin),
):
    # 1. Получаем информацию о мероприятии
    event = await db.get(models.Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")

    # 2. Статистика по справочникам (Запланировано vs Пришло)
    stmt_dirs = (
        select(
            models.Directory.name,
            func.count(models.Registration.id).label("planned"),
            func.count(models.Registration.arrival_time).label("actual")
        )
        .select_from(models.Directory)
        .join(models.DirectoryMembership, models.Directory.id == models.DirectoryMembership.directory_id)
        .join(models.Registration, models.DirectoryMembership.participant_id == models.Registration.participant_id)
        .filter(models.Registration.event_id == event_id)
        .group_by(models.Directory.name)
    )
    result_dirs = await db.execute(stmt_dirs)
    stats_by_dir = result_dirs.all()

    # 3. Общая статистика (Уникальные участники)
    stmt_total = select(
        func.count(models.Registration.id).label("total_planned"),
        func.count(models.Registration.arrival_time).label("total_actual")
    ).filter(models.Registration.event_id == event_id)
    
    result_total = await db.execute(stmt_total)
    total_planned, total_actual = result_total.one()

    # Подготовка данных для JS-диаграммы
    dir_labels = [row.name.replace("'", "\\'") for row in stats_by_dir]
    dir_actuals = [row.actual for row in stats_by_dir]
    
    # Генерация HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Отчет: {event.title}</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: sans-serif; padding: 20px; color: #333; }}
            h1 {{ margin-bottom: 5px; }}
            .date {{ color: #666; margin-bottom: 30px; }}
            table {{ border-collapse: collapse; width: 100%; max-width: 800px; margin-top: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background-color: #f8f9fa; font-weight: bold; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            tr:hover {{ background-color: #f1f1f1; }}
            .summary {{ margin-top: 40px; padding: 20px; background-color: #f8f9fa; border-radius: 8px; max-width: 400px; }}
            .chart-container {{ width: 100%; max-width: 600px; margin: 30px 0; }}
            .print-btn {{ margin-top: 20px; padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 4px; }}
            @media print {{
                .print-btn {{ display: none; }}
            }}
        </style>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <h1>Отчет по мероприятию: {event.title}</h1>
        <div class="date">Дата мероприятия: {event.event_date.strftime('%d.%m.%Y %H:%M')}</div>
        
        <div class="chart-container">
            <canvas id="attendanceChart"></canvas>
        </div>

        <h2>Детализация по справочникам</h2>
        <table>
            <thead>
                <tr>
                    <th>Справочник</th>
                    <th>Запланировано (регистраций)</th>
                    <th>Пришло по факту</th>
                    <th>Явка (%)</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for row in stats_by_dir:
        percentage = round((row.actual / row.planned * 100), 1) if row.planned > 0 else 0
        html_content += f"""
                <tr>
                    <td>{row.name}</td>
                    <td>{row.planned}</td>
                    <td>{row.actual}</td>
                    <td>{percentage}%</td>
                </tr>
        """

    html_content += f"""
            </tbody>
        </table>

        <div class="summary">
            <h2 style="margin-top:0">Итого (уникальные участники)</h2>
            <p><strong>Всего запланировано:</strong> {total_planned}</p>
            <p><strong>Всего пришло:</strong> {total_actual}</p>
            <p><strong>Общая явка:</strong> {round((total_actual / total_planned * 100), 1) if total_planned > 0 else 0}%</p>
        </div>
        
        <button class="print-btn" onclick="window.print()">Распечатать / Сохранить как PDF</button>

        <script>
            const ctx = document.getElementById('attendanceChart').getContext('2d');
            new Chart(ctx, {{
                type: 'pie',
                data: {{
                    labels: {dir_labels},
                    datasets: [{{
                        label: 'Количество пришедших',
                        data: {dir_actuals},
                        backgroundColor: [
                            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40',
                            '#8AC926', '#1982C4', '#6A4C93', '#F15BB5'
                        ],
                        hoverOffset: 4
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        title: {{
                            display: true,
                            text: 'Доля пришедших участников по справочникам',
                            font: {{ size: 18 }}
                        }},
                        legend: {{
                            position: 'right'
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)
