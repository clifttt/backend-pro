const API_BASE = 'http://localhost:8000';

const app = {
    // Current State
    state: {
        currentTab: 'dashboard',

        startups: { page: 1, limit: 12, sort_by: 'name' },
        investors: { page: 1, limit: 12 },
        investments: { page: 1, limit: 15 }
    },

    // Initialization
    init() {
        this.cacheDOM();
        this.bindEvents();
        this.fetchStats(); // Load initial data
    },

    cacheDOM() {
        this.navItems = document.querySelectorAll('.nav-item');
        this.views = document.querySelectorAll('.view');
        this.globalSearchInput = document.getElementById('global-search-input');

        // Containers
        this.statsContainer = document.getElementById('stats-container');
        this.topStartupsContainer = document.getElementById('top-startups-container');
        this.searchResultsContainer = document.getElementById('search-results-container');

        this.startupsContainer = document.getElementById('startups-container');
        this.investorsContainer = document.getElementById('investors-container');
        this.investmentsTbody = document.getElementById('investments-tbody');

        // Pagination
        this.startupsPagination = document.getElementById('startups-pagination');
        this.investorsPagination = document.getElementById('investors-pagination');
        this.investmentsPagination = document.getElementById('investments-pagination');
    },

    bindEvents() {
        // Tab Switching
        this.navItems.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tabId = e.currentTarget.dataset.tab;
                this.switchTab(tabId);
            });
        });

        // Global Search with Debounce
        let searchTimeout;
        this.globalSearchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();

            if (query.length > 0) {
                if (this.state.currentTab !== 'search') {
                    this.switchTab('search');
                }
                document.getElementById('search-meta').innerHTML = `Searching across startups, investors and rounds... <span class="badge">Loading</span>`;
                this.searchResultsContainer.innerHTML = `<div class="skeleton-row"></div><div class="skeleton-row"></div><div class="skeleton-row"></div>`;

                searchTimeout = setTimeout(() => {
                    this.performSearch(query);
                }, 500);
            } else if (this.state.currentTab === 'search') {
                document.getElementById('search-meta').innerHTML = "Type to search across everything...";
                this.searchResultsContainer.innerHTML = "";
            }
        });
    },

    switchTab(tabId) {
        // Update Nav
        this.navItems.forEach(btn => btn.classList.remove('active'));
        document.querySelector(`.nav-item[data-tab="${tabId}"]`).classList.add('active');

        // Update Views
        this.views.forEach(view => {
            view.classList.add('hidden');
            setTimeout(() => view.style.display = 'none', 300); // Wait for fade out
        });

        const targetView = document.getElementById(`view-${tabId}`);
        targetView.style.display = 'flex';
        setTimeout(() => targetView.classList.remove('hidden'), 10);

        this.state.currentTab = tabId;

        // Load data if needed
        if (tabId === 'dashboard') this.fetchStats();
        if (tabId === 'startups') this.fetchStartups();
        if (tabId === 'investors') this.fetchInvestors();
        if (tabId === 'investments') this.fetchInvestments();
    },

    // Utils
    formatMoney(amount) {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);
    },

    formatDate(dateString) {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    },

    // --- API Fetchers --- 

    async fetchStats() {
        try {
            const res = await fetch(`${API_BASE}/statistics`);
            const data = await res.json();
            this.renderStats(data);
        } catch (error) {
            console.error(error);
            this.statsContainer.innerHTML = `<div class="error-msg">Failed to load statistics: Check Backend</div>`;
        }
    },

    async performSearch(query) {
        try {
            const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}&limit=15`);
            const data = await res.json();
            this.renderSearchResults(data.results, data.total, query);
        } catch (error) {
            this.searchResultsContainer.innerHTML = `<div class="error-msg">Search failed.</div>`;
        }
    },

    async fetchStartups(page = this.state.startups.page) {
        this.state.startups.page = page;
        const sortMode = document.getElementById('startup-sort').value;
        const order = sortMode === 'founded_year' ? 'desc' : 'asc';

        this.startupsContainer.innerHTML = `<div class="card skeleton"></div><div class="card skeleton"></div><div class="card skeleton"></div>`;

        try {
            const res = await fetch(`${API_BASE}/startups?page=${page}&per_page=${this.state.startups.limit}&sort_by=${sortMode}&sort_order=${order}`);
            const data = await res.json();
            this.renderStartups(data.data);
            this.renderPagination(data.meta, 'startupsPagination', (p) => this.fetchStartups(p));
        } catch (error) {
            this.startupsContainer.innerHTML = `<div class="error-msg">Network error.</div>`;
        }
    },

    async fetchInvestors(page = this.state.investors.page) {
        this.state.investors.page = page;
        this.investorsContainer.innerHTML = `<div class="card skeleton"></div><div class="card skeleton"></div><div class="card skeleton"></div>`;

        try {
            const res = await fetch(`${API_BASE}/investors?page=${page}&per_page=${this.state.investors.limit}`);
            const data = await res.json();
            this.renderInvestors(data.data);
            this.renderPagination(data.meta, 'investorsPagination', (p) => this.fetchInvestors(p));
        } catch (error) {
            this.investorsContainer.innerHTML = `<div class="error-msg">Network error.</div>`;
        }
    },

    async fetchInvestments(page = this.state.investments.page) {
        this.state.investments.page = page;
        this.investmentsTbody.innerHTML = `<tr><td colspan="4"><div class="skeleton-row"></div></td></tr>`;

        try {
            const res = await fetch(`${API_BASE}/investments?page=${page}&per_page=${this.state.investments.limit}&sort_by=amount_usd&sort_order=desc`);
            const data = await res.json();
            this.renderInvestments(data.data);
            this.renderPagination(data.meta, 'investmentsPagination', (p) => this.fetchInvestments(p));
        } catch (error) {
            this.investmentsTbody.innerHTML = `<tr><td colspan="4" class="error-msg">Network error.</td></tr>`;
        }
    },

    // --- Renderers ---

    renderStats(data) {
        const sum = data.summary;
        const inv = data.investment_stats;

        this.statsContainer.innerHTML = `
            <div class="stat-card">
                <span class="label">Total Startups</span>
                <span class="value">${sum.total_startups}</span>
            </div>
            <div class="stat-card">
                <span class="label">Active Investors</span>
                <span class="value">${sum.total_investors}</span>
            </div>
            <div class="stat-card">
                <span class="label">Funding Rounds</span>
                <span class="value">${sum.total_investments}</span>
            </div>
            <div class="stat-card accent">
                <span class="label">Total Capital Invested</span>
                <span class="value">${this.formatMoney(inv.total_amount_usd)}</span>
            </div>
        `;

        this.topStartupsContainer.innerHTML = data.top_startups.map((s, i) => `
            <div class="search-item startup" style="margin-bottom: 0.5rem">
                <div class="search-item-info">
                    <h3>#${i + 1} ${s.name}</h3>
                    <p>Total Raised</p>
                </div>
                <div style="font-weight: 600; font-size: 1.1rem; color: var(--accent-primary)">
                    ${this.formatMoney(s.total_investment_usd)}
                </div>
            </div>
        `).join('');
    },

    renderSearchResults(results, total, query) {
        const meta = document.getElementById('search-meta');

        if (results.length === 0) {
            meta.innerHTML = `No results found for "<b>${query}</b>"`;
            this.searchResultsContainer.innerHTML = '';
            return;
        }

        meta.innerHTML = `Found ${total} result${total > 1 ? 's' : ''} for "<b>${query}</b>"`;

        this.searchResultsContainer.innerHTML = results.map(item => {
            let badgeClass = item.type;
            let icon = '';
            let subtitle = '';

            if (item.type === 'startup') {
                icon = '🏢';
                subtitle = `${item.details.country || 'Unknown'} • Built in ${item.details.founded_year || 'N/A'}`;
            } else if (item.type === 'investor') {
                icon = '💼';
                subtitle = `Focus: ${item.details.focus_area || 'Various'}`;
            } else {
                icon = '💸';
                badgeClass = 'investment';
                subtitle = `${this.formatMoney(item.details.amount_usd)} • ${this.formatDate(item.details.date)}`;
            }

            return `
                <div class="search-item ${badgeClass}">
                    <div class="search-item-info">
                        <h3>${icon} ${item.name}</h3>
                        <p>${subtitle}</p>
                    </div>
                    <span class="badge ${item.details.status === 'Active' ? 'success' : ''}">${item.type}</span>
                </div>
            `;
        }).join('');
    },

    renderStartups(startups) {
        this.startupsContainer.innerHTML = startups.map(startup => `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">${startup.name}</h3>
                    <span class="badge ${startup.status === 'Active' ? 'success' : ''}">${startup.status || 'Unknown'}</span>
                </div>
                <div class="card-body">
                    <p>${startup.description || 'No description available for this organization.'}</p>
                </div>
                <div class="card-meta">
                    <span>🌍 ${startup.country || 'Global'}</span>
                    <span>📅 ${startup.founded_year || 'N/A'}</span>
                    <span>💸 ${startup.investments.length} Rounds</span>
                </div>
            </div>
        `).join('');
    },

    renderInvestors(investors) {
        this.investorsContainer.innerHTML = investors.map(inv => `
            <div class="card" style="border-top: 3px solid var(--accent-secondary)">
                <div class="card-header">
                    <h3 class="card-title">${inv.name}</h3>
                </div>
                <div class="card-body">
                    <div style="margin-bottom: 1rem; color: var(--text-secondary)">
                        <strong>Fund Name:</strong><br> ${inv.fund_name || 'N/A'}
                    </div>
                    <p><strong>Investment Focus:</strong><br> ${inv.focus_area || 'General Tech'}</p>
                </div>
                <div class="card-meta">
                    <span>Portfolio: ${inv.investments.length} Investments</span>
                </div>
            </div>
        `).join('');
    },

    renderInvestments(investments) {
        this.investmentsTbody.innerHTML = investments.map(inv => `
            <tr>
                <td><span class="badge">${inv.round || 'Unknown'}</span></td>
                <td style="font-weight: 500">${this.formatMoney(inv.amount_usd)}</td>
                <td>${this.formatDate(inv.date)}</td>
                <td><span class="badge ${inv.status === 'Active' ? 'success' : ''}">${inv.status || 'N/A'}</span></td>
            </tr>
        `).join('');
    },

    renderPagination(meta, containerName, callback) {
        const container = this[containerName];
        if (!meta || meta.pages <= 1) {
            container.innerHTML = '';
            return;
        }

        container.innerHTML = `
            <button class="btn-page" ${meta.page === 1 ? 'disabled' : ''} id="prev-${containerName}">Previous</button>
            <span class="page-info">Page ${meta.page} of ${meta.pages}</span>
            <button class="btn-page" ${meta.page === meta.pages ? 'disabled' : ''} id="next-${containerName}">Next</button>
        `;

        if (meta.page > 1) {
            document.getElementById(`prev-${containerName}`).addEventListener('click', () => callback(meta.page - 1));
        }
        if (meta.page < meta.pages) {
            document.getElementById(`next-${containerName}`).addEventListener('click', () => callback(meta.page + 1));
        }
    }
};

// Start App when DOM is ready
document.addEventListener('DOMContentLoaded', () => app.init());
