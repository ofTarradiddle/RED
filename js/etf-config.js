/**
 * Central ETF registry loader and render helpers.
 * Source of truth: data/etfs.json
 */

let etfRegistry = null;
let upcomingLaunches = [];

const ETF_THEME_CLASSES = {
    red: { card: '', ticker: '', tagline: '', dif: '' },
    dark: { card: 'etf-card-dark', ticker: 'ticker-box-dark', tagline: 'tagline-dark', dif: 'dif-dark' },
    purple: { card: 'etf-card-purple', ticker: 'ticker-box-purple', tagline: 'tagline-purple', dif: 'dif-purple' },
    rose: { card: 'etf-card-rose', ticker: 'ticker-box-rose', tagline: 'tagline-rose', dif: 'dif-rose' },
    amber: { card: 'etf-card-amber', ticker: 'ticker-box-amber', tagline: 'tagline-amber', dif: 'dif-amber' }
};

const ETF_STATUS_BADGE = {
    live: { dot: 'bg-green-500', label: 'Live' },
    early: { dot: 'bg-amber-400', label: 'Early Stage' },
    accepting: { dot: 'bg-emerald-400', label: 'Accepting Interest' },
    planned: { dot: 'bg-gray-500', label: 'Planned' }
};

function getEtfDataPath() {
    const path = window.location.pathname;
    if (path.includes('/etfs/')) {
        return '../data/etfs.json';
    }
    return 'data/etfs.json';
}

async function loadEtfRegistry() {
    if (etfRegistry) {
        return etfRegistry;
    }

    const response = await fetch(getEtfDataPath());
    if (!response.ok) {
        throw new Error(`Failed to load ETF registry (${response.status})`);
    }

    etfRegistry = await response.json();
    return etfRegistry;
}

function getFunds(predicate) {
    if (!etfRegistry || !Array.isArray(etfRegistry.funds)) {
        return [];
    }
    return etfRegistry.funds.filter(predicate);
}

function getLineupFunds() {
    return getFunds(fund => fund.showInLineup === true);
}

function getLiveFunds() {
    return getFunds(fund => fund.status === 'live');
}

function get351Funds() {
    return getFunds(fund => {
        return fund.exchange351 === true && ['early', 'accepting', 'planned'].includes(fund.status);
    });
}

function to351Launch(fund) {
    return {
        ticker: fund.ticker,
        name: fund.name,
        status: fund.statusLabel,
        targetLaunch: fund.targetLaunch || 'TBD',
        description: fund.description,
        tags: fund.tags || [],
        expenseRatio: fund.expenseRatio || 'TBD',
        targetAUM: fund.targetAUM || 'TBD'
    };
}

async function initEtfConfig() {
    await loadEtfRegistry();
    upcomingLaunches = get351Funds().map(to351Launch);
    return etfRegistry;
}

function getFundHref(fund) {
    const base = window.location.pathname.includes('/etfs/') ? '../etfs/' : 'etfs/';
    return `${base}${fund.slug}/`;
}

function renderLineupCards(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const funds = getLineupFunds();
    if (funds.length === 0) {
        container.innerHTML = '';
        return;
    }

    container.innerHTML = funds.map(fund => {
        const theme = ETF_THEME_CLASSES[fund.theme] || ETF_THEME_CLASSES.red;
        const statusMeta = ETF_STATUS_BADGE[fund.status];
        const statusBadge = statusMeta && fund.status !== 'live'
            ? `<span class="inline-flex items-center gap-1.5 text-[0.65rem] uppercase tracking-wide text-gray-500 mb-2">
                    <span class="w-1.5 h-1.5 rounded-full ${statusMeta.dot}"></span>${statusMeta.label}
               </span>`
            : '';

        return `
            <a href="${getFundHref(fund)}" class="etf-card ${theme.card}" style="width: 200px;">
                <div class="flex flex-col items-center text-center">
                    ${statusBadge}
                    <div class="ticker-box ${theme.ticker}">${fund.ticker}</div>
                    <h2 class="text-lg font-bold text-gray-900 mb-0">${fund.name}</h2>
                    <p class="tagline ${theme.tagline}">${fund.tagline}</p>
                </div>
            </a>
        `;
    }).join('');
}

function renderLiveFunds(sectionId, listId) {
    const section = document.getElementById(sectionId);
    const list = document.getElementById(listId);
    if (!section || !list) return;

    const funds = getLiveFunds();
    if (funds.length === 0) {
        section.classList.add('hidden');
        list.innerHTML = '';
        return;
    }

    section.classList.remove('hidden');
    list.innerHTML = funds.map(fund => `
        <div class="flex items-center gap-2">
            <span class="w-2 h-2 bg-green-500 rounded-full"></span>
            <span class="text-sm font-medium">${fund.ticker}</span>
        </div>
    `).join('');
}

function populate351Dropdown(selectId) {
    const selectEl = document.getElementById(selectId);
    if (!selectEl) return;

    const defaultOption = selectEl.options.length > 0 ? selectEl.options[0] : null;
    selectEl.innerHTML = '';

    if (defaultOption) {
        selectEl.appendChild(defaultOption);
    }

    upcomingLaunches.forEach(etf => {
        const option = document.createElement('option');
        option.value = etf.ticker;
        option.textContent = `${etf.ticker} — ${etf.name.replace('Diamond ', '')}`;
        if (selectEl.classList.contains('text-white') || selectEl.classList.contains('bg-white/5')) {
            option.style.color = '#111';
        }
        selectEl.appendChild(option);
    });
}

function render351Cards(containerId, templateFn) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (upcomingLaunches.length === 0) {
        container.innerHTML = '<p class="text-gray-400 text-sm text-center">No upcoming 351 exchange opportunities at this time.</p>';
        return;
    }

    container.innerHTML = upcomingLaunches.map(etf => templateFn(etf)).join('');
}

function onEtfConfigReady(callback) {
    document.addEventListener('DOMContentLoaded', async () => {
        try {
            await initEtfConfig();
            callback();
        } catch (error) {
            console.error('ETF config failed to load:', error);
        }
    });
}
