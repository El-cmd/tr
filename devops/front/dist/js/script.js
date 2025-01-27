document.addEventListener("DOMContentLoaded", function() {
    loadHTML('../partials/header.html', 'header-placeholder');
    loadHTML('../partials/sidebar.html', 'sidebar-placeholder');
    loadHTML('../partials/footer.html', 'footer-placeholder');
	loadHTML('../partials/login-modal.html', 'login-modal-placeholder');
    loadSection('login'); // Charger la section par défaut
});

function loadHTML(url, elementId) {
    fetch(url)
        .then(response => response.text())
        .then(data => {
            document.getElementById(elementId).innerHTML = data;
        })
        .catch(error => console.error('Error loading HTML:', error));
}

function loadSection(section) {
    const sectionMap = {
        'friends': '../partials/friends.html',
        'ranking': '../partials/ranking.html',
        'chat': '../partials/chat.html',
		'login': '../partials/login-modal.html',
        'pong-game': '../partials/pong-game.html'
    };
    if (sectionMap[section]) {
        loadHTML(sectionMap[section], 'main-content');
    }
}