document.addEventListener('DOMContentLoaded', () => {
    // Theme logic
    const toggleBtn = document.getElementById('theme-toggle');
    const currentTheme = localStorage.getItem('theme') || 'light';
    
    if (currentTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        toggleBtn.textContent = '☀️ Light Mode';
    }

    toggleBtn.addEventListener('click', () => {
        let theme = document.documentElement.getAttribute('data-theme');
        if (theme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
            toggleBtn.textContent = '🌓 Dark Mode';
            updateChartTheme(false);
        } else {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
            toggleBtn.textContent = '☀️ Light Mode';
            updateChartTheme(true);
        }
    });

    let loadChart = null;

    // Fetch and render data
    async function fetchData() {
        try {
            const res = await fetch('/api/stats');
            const data = await res.json();
            
            // Update simple stats
            document.getElementById('today-total').textContent = data.logs.today.total;
            document.getElementById('week-total').textContent = data.logs.this_week.total;

            // Render Chart
            renderChart(data.logs);

            // Render Table
            renderTable(data.endpoints);
        } catch (err) {
            console.error("Xatolik:", err);
        }
    }

    function renderChart(logs) {
        const ctx = document.getElementById('loadChart').getContext('2d');
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const textColor = isDark ? '#e0e0e0' : '#333';

        if (loadChart) {
            loadChart.destroy();
        }

        loadChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Bugun', 'Shu Hafta'],
                datasets: [
                    {
                        label: "So'rovlar",
                        data: [logs.today.total, logs.this_week.total],
                        backgroundColor: '#4CAF50',
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { color: textColor }
                    },
                    x: {
                        ticks: { color: textColor }
                    }
                },
                plugins: {
                    legend: {
                        labels: { color: textColor }
                    }
                }
            }
        });
    }

    function updateChartTheme(isDark) {
        if (!loadChart) return;
        const textColor = isDark ? '#e0e0e0' : '#333';
        loadChart.options.scales.x.ticks.color = textColor;
        loadChart.options.scales.y.ticks.color = textColor;
        loadChart.options.plugins.legend.labels.color = textColor;
        loadChart.update();
    }

    // Everything below puts server-supplied text on the page with textContent.
    // Request paths are chosen by whoever sends the request, so they are
    // untrusted: never build markup from them.
    function cell(text, tag = 'td') {
        const el = document.createElement(tag);
        el.textContent = text;
        return el;
    }

    function renderTable(endpoints) {
        const tbody = document.querySelector('#api-table tbody');
        tbody.replaceChildren();
        if (endpoints.length === 0) {
            const tr = document.createElement('tr');
            const td = cell("Hozircha ma'lumot yo'q");
            td.colSpan = 2;
            tr.appendChild(td);
            tbody.appendChild(tr);
            return;
        }

        endpoints.forEach(ep => {
            const tr = document.createElement('tr');
            tr.appendChild(cell(ep.path));

            const count = document.createElement('td');
            const strong = document.createElement('strong');
            strong.style.color = 'var(--primary-color)';
            strong.textContent = ep.count;
            count.append(strong, ' marta');
            tr.appendChild(count);

            tbody.appendChild(tr);
        });
    }

    fetchData();
    // Auto-refresh every 10 seconds for standard stats
    setInterval(fetchData, 10000);

    // ==========================================
    // WebSockets (Live Data)
    // ==========================================
    const socket = io();

    // Store metrics by server
    const serverMetrics = {};

    socket.on('metrics', (data) => {
        serverMetrics[data.server] = data;
        renderMetrics();
    });

    function renderMetrics() {
        const container = document.getElementById('metrics-container');
        container.replaceChildren();

        Object.values(serverMetrics).forEach(m => {
            const cpu = Number(m.cpu);
            const ram = Number(m.ram);

            const box = document.createElement('div');
            box.className = 'stat-box';

            const title = document.createElement('h3');
            title.textContent = m.server;

            const line = (label, value) => {
                const p = document.createElement('p');
                const span = document.createElement('span');
                span.style.color = value > 90 ? 'red' : 'var(--primary-color)';
                span.style.fontWeight = 'bold';
                span.textContent = `${value}%`;
                p.append(`${label}: `, span);
                return p;
            };

            const stamp = document.createElement('small');
            stamp.style.color = '#888';
            stamp.textContent = String(m.time).split('T')[1]?.split('.')[0] ?? '';

            box.append(title, line('CPU', cpu), line('RAM', ram), stamp);
            container.appendChild(box);
        });
    }

    const maxLiveRows = 20;
    const liveTbody = document.querySelector('#live-requests-table tbody');

    socket.on('live_request', (data) => {
        const tr = document.createElement('tr');
        tr.appendChild(cell(data.time));
        tr.appendChild(cell(data.server));

        const method = document.createElement('td');
        const strong = document.createElement('strong');
        strong.textContent = data.method;
        method.appendChild(strong);
        tr.appendChild(method);

        tr.appendChild(cell(data.path));
        tr.appendChild(cell(data.status));
        liveTbody.insertBefore(tr, liveTbody.firstChild);

        // limit rows
        while(liveTbody.children.length > maxLiveRows) {
            liveTbody.removeChild(liveTbody.lastChild);
        }
    });

});
