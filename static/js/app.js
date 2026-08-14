document.addEventListener('DOMContentLoaded', function () {
    setTimeout(function () {
        document.querySelectorAll('.alert').forEach(function (el) {
            el.classList.add('fade');
            setTimeout(function () {
                if (el.classList.contains('show')) el.classList.remove('show');
            }, 3500);
        });
    }, 0);

    document.querySelectorAll('form[data-confirm]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (!confirm(form.dataset.confirm)) e.preventDefault();
        });
    });
});
