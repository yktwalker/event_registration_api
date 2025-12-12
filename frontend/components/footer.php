        </div> <!-- End content-body -->

        <!-- SYSTEM CONSOLE -->
        <div id="system-console">
            <span class="me-2">[SYSTEM]:</span>
            <span id="console-msg">Ожидание действий...</span>
        </div>

    </div> <!-- End content-wrapper -->
</div> <!-- End main-wrapper -->

<!-- GLOBAL DELETE MODAL -->
<div class="modal fade" id="deleteModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Удаление</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p>Вы уверены, что хотите удалить <b id="del-object-name"></b>?</p>
                <p class="text-danger small"><i class="fas fa-exclamation-triangle"></i> Это действие необратимо.</p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                <button type="button" class="btn btn-danger" id="btn-confirm-del">Да, удалить</button>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="js/app.js"></script>
<script>
    // Запуск проверки авторизации на всех страницах, кроме логина
    document.addEventListener('DOMContentLoaded', () => {
        checkAuth();
    });
</script>

</body>
</html>

