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
                        label: logs.meta.server_one_label || 'Server 1',
                        data: [logs.today.server_one, logs.this_week.server_one],
                        backgroundColor: '#4CAF50',
                        borderRadius: 4
                    },
                    {
                        label: logs.meta.server_two_label || 'Server 2',
                        data: [logs.today.server_two, logs.this_week.server_two],
                        backgroundColor: '#2196F3',
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

    function renderTable(endpoints) {
        const tbody = document.querySelector('#api-table tbody');
        tbody.innerHTML = '';
        if (endpoints.length === 0) {
            tbody.innerHTML = '<tr><td colspan="2">Hozircha ma\'lumot yo\'q</td></tr>';
            return;
        }
        
        endpoints.forEach(ep => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${ep.path}</td>
                <td><strong style="color:var(--primary-color)">${ep.count}</strong> marta</td>
            `;
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
        container.innerHTML = '';
        
        Object.values(serverMetrics).forEach(m => {
            const cpuColor = m.cpu > 90 ? 'red' : 'var(--primary-color)';
            const ramColor = m.ram > 90 ? 'red' : 'var(--primary-color)';
            
            const box = document.createElement('div');
            box.className = 'stat-box';
            box.innerHTML = `
                <h3>${m.server}</h3>
                <p>CPU: <span style="color:${cpuColor}; font-weight:bold;">${m.cpu}%</span></p>
                <p>RAM: <span style="color:${ramColor}; font-weight:bold;">${m.ram}%</span></p>
                <small style="color:#888;">${m.time.split('T')[1].split('.')[0]}</small>
            `;
            container.appendChild(box);
        });
    }

    const maxLiveRows = 20;
    const liveTbody = document.querySelector('#live-requests-table tbody');

    socket.on('live_request', (data) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${data.time}</td>
            <td>${data.server}</td>
            <td><strong>${data.method}</strong></td>
            <td>${data.path}</td>
            <td>${data.status}</td>
        `;
        liveTbody.insertBefore(tr, liveTbody.firstChild);
        
        // limit rows
        while(liveTbody.children.length > maxLiveRows) {
            liveTbody.removeChild(liveTbody.lastChild);
        }
    });

});
