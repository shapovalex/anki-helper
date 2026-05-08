async function loadMenu() {
    const res = await fetch('/static/components/menu.html');
    const html = await res.text();
    document.getElementById('menu-container').innerHTML = html;

    const path = window.location.pathname;
    document.querySelectorAll('.nav-links a').forEach(a => {
        const href = a.getAttribute('href');
        const match = href === '/' ? path === '/' : path === href || path.startsWith(href + '/');
        if (match) a.classList.add('active');
    });
}
loadMenu();
