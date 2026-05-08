async function loadMenu() {
    const res = await fetch('/static/components/menu.html');
    const html = await res.text();
    document.getElementById('menu-container').innerHTML = html;
}
loadMenu();
