// Grind & Crumb Operational Intelligence Dashboard Client

let currentTab = 'tab-pnl';
let charts = {};

document.addEventListener('DOMContentLoaded', () => {
    initStoreFilter();
    loadDashboardData();
});

// Tab Switching
function switchTab(tabId) {
    currentTab = tabId;
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active', 'text-amber-600', 'font-bold');
        btn.classList.add('text-slate-600');
    });

    const activeContent = document.getElementById(tabId);
    if (activeContent) activeContent.classList.remove('hidden');

    const activeBtn = document.getElementById(`tab-btn-${tabId.replace('tab-', '')}`);
    if (activeBtn) {
        activeBtn.classList.add('active', 'text-amber-600', 'font-bold');
        activeBtn.classList.remove('text-slate-600');
    }

    // Lazy load / redraw specific tab data
    if (tabId === 'tab-pnl') loadPnLData();
    else if (tabId === 'tab-delivery') loadDeliveryData();
    else if (tabId === 'tab-labor') loadLaborData();
    else if (tabId === 'tab-waste') loadWasteData();
    else if (tabId === 'tab-digital') loadDigitalData();
    else if (tabId === 'tab-expansion') loadExpansionData();
}

// Global Filter Handler
function onGlobalFilterChange() {
    loadDashboardData();
}

function getFilterParams() {
    const store = document.getElementById('global-store-filter')?.value || '';
    const month = document.getElementById('global-month-filter')?.value || '';
    let params = [];
    if (store) params.push(`store_id=${encodeURIComponent(store)}`);
    if (month) params.push(`month=${encodeURIComponent(month)}`);
    return params.length ? `?${params.join('&')}` : '';
}

// Init Store Filter Dropdown
async function initStoreFilter() {
    try {
        const res = await fetch('/api/stores/');
        const data = await res.json();
        const select = document.getElementById('global-store-filter');
        if (!select || !data.stores) return;

        select.innerHTML = data.stores.length > 1 ? '<option value="">All 12 Locations (Chain-wide)</option>' : '';
        data.stores.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.store_id;
            opt.textContent = `${s.store_name} (${s.store_id})`;
            select.appendChild(opt);
        });
    } catch (err) {
        console.error("Failed to load stores", err);
    }
}

// Master Data Load
function loadDashboardData() {
    loadPnLData();
    // Pre-load current tab
    if (currentTab === 'tab-delivery') loadDeliveryData();
    else if (currentTab === 'tab-labor') loadLaborData();
    else if (currentTab === 'tab-waste') loadWasteData();
    else if (currentTab === 'tab-digital') loadDigitalData();
    else if (currentTab === 'tab-expansion') loadExpansionData();
}

// ==========================================
// MODULE 1: PnL & Occupancy Engine
// ==========================================
async function loadPnLData() {
    const query = getFilterParams();
    try {
        const [rankingRes, occupancyRes, cannibalRes] = await Promise.all([
            fetch(`/api/pnl/ranking${query}`),
            fetch(`/api/pnl/occupancy-alerts`),
            fetch(`/api/pnl/cannibalization`)
        ]);

        const ranking = await rankingRes.json();
        const occupancy = await occupancyRes.json();
        const cannibal = await cannibalRes.json();

        // 1. Populate Heatmap Table
        renderPnLTable(ranking.stores || []);

        // 2. Render Occupancy Chart
        renderOccupancyChart(occupancy.stores || []);

        // 3. Update Cannibalization Metrics
        if (cannibal.metrics) {
            document.getElementById('cannibal-pre-s03').textContent = `£${cannibal.metrics.pre_opening_s03_avg_monthly_sales.toLocaleString()} / mo`;
            document.getElementById('cannibal-post-s03').textContent = `£${cannibal.metrics.post_opening_s03_avg_monthly_sales.toLocaleString()} / mo`;
            document.getElementById('cannibal-dilution').textContent = `-£${cannibal.metrics.s03_monthly_sales_dilution_gbp.toLocaleString()} / mo (-${cannibal.metrics.s03_sales_dilution_pct}%)`;
            document.getElementById('cannibal-net-growth').textContent = `+£${cannibal.metrics.net_leeds_market_sales_delta_gbp.toLocaleString()} / mo Net Gain`;
        }
    } catch (err) {
        console.error("Error loading PnL data:", err);
    }
}

function renderPnLTable(stores) {
    const tbody = document.getElementById('pnl-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    stores.forEach(s => {
        const tr = document.createElement('tr');
        tr.className = `table-heat-row ${s.is_high_volume_loss_maker ? 'bg-rose-50/60 font-semibold' : ''}`;

        const profitClass = s.net_profit_gbp < 0 ? 'text-rose-600 font-bold' : 'text-slate-900';
        const occupancyBadge = s.occupancy_alert 
            ? `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-200">${s.fixed_occupancy_pct}% ALERT</span>`
            : `<span class="text-slate-600">${s.fixed_occupancy_pct}%</span>`;

        const badgeColorMap = {
            'red': 'bg-rose-100 text-rose-800 border border-rose-200',
            'amber': 'bg-amber-100 text-amber-800 border border-amber-200',
            'blue': 'bg-blue-100 text-blue-800 border border-blue-200',
            'emerald': 'bg-emerald-100 text-emerald-800 border border-emerald-200'
        };

        tr.innerHTML = `
            <td class="px-4 py-3 font-bold text-slate-900 flex items-center space-x-2">
                <span>${s.store_name}</span>
                ${s.is_high_volume_loss_maker ? '<span class="text-[10px] bg-rose-600 text-white font-extrabold px-1.5 py-0.5 rounded uppercase">Loss Trap</span>' : ''}
            </td>
            <td class="px-4 py-3 text-slate-500">${s.city} &bull; ${s.format}</td>
            <td class="px-4 py-3 text-right font-medium">£${Math.round(s.total_sales_gbp).toLocaleString()}</td>
            <td class="px-4 py-3 text-right font-medium text-slate-500">#${s.sales_rank}</td>
            <td class="px-4 py-3 text-right ${profitClass}">£${Math.round(s.net_profit_gbp).toLocaleString()}</td>
            <td class="px-4 py-3 text-right font-medium text-slate-500">#${s.profit_rank}</td>
            <td class="px-4 py-3 text-right font-bold ${s.operating_margin_pct < 0 ? 'text-rose-600' : 'text-emerald-700'}">${s.operating_margin_pct}%</td>
            <td class="px-4 py-3 text-right">${occupancyBadge}</td>
            <td class="px-4 py-3 text-center">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold ${badgeColorMap[s.margin_badge_color] || ''}">${s.margin_status}</span>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function renderOccupancyChart(stores) {
    const ctx = document.getElementById('occupancyChart');
    if (!ctx) return;
    if (charts.occupancy) charts.occupancy.destroy();

    const labels = stores.map(s => s.store_name.split(' ')[0] + ' ' + (s.store_name.split(' ')[1] || ''));
    const data = stores.map(s => s.occupancy_pct);
    const backgroundColors = stores.map(s => s.occupancy_pct > 25.0 ? 'rgba(225, 29, 72, 0.85)' : 'rgba(5, 150, 105, 0.7)');

    charts.occupancy = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Fixed Occupancy Cost % of Sales',
                data: data,
                backgroundColor: backgroundColors,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                annotation: {
                    annotations: {
                        line1: {
                            type: 'line',
                            yMin: 25,
                            yMax: 25,
                            borderColor: 'rgb(225, 29, 72)',
                            borderWidth: 2,
                            borderDash: [6, 6],
                            label: { content: '25% Ceiling Threshold', enabled: true }
                        }
                    }
                }
            },
            scales: {
                y: {
                    title: { display: true, text: '% of Store Sales' },
                    suggestedMax: 45
                }
            }
        }
    });
}

// ==========================================
// MODULE 2: Delivery & Channel Economics
// ==========================================
async function loadDeliveryData() {
    const query = getFilterParams();
    try {
        const [waterfallRes, sub8Res] = await Promise.all([
            fetch(`/api/delivery/waterfall${query}`),
            fetch(`/api/delivery/sub8-alarm${query}`)
        ]);

        const waterfall = await waterfallRes.json();
        const sub8 = await sub8Res.json();

        // 1. Render Waterfall Cards
        renderWaterfallCards(waterfall.channels || []);

        // 2. Render Sub-8 Hourly Chart
        renderSub8HourlyChart(sub8.hourly_distribution || []);

        // Run baseline simulation
        runDeliverySimulation();
    } catch (err) {
        console.error("Error loading delivery data:", err);
    }
}

function renderWaterfallCards(channels) {
    const container = document.getElementById('channel-waterfall-cards');
    if (!container) return;
    container.innerHTML = '';

    channels.forEach(ch => {
        const isDelivery = ch.channel_name.includes('Dashly') || ch.channel_name.includes('RushEats');
        const card = document.createElement('div');
        card.className = `p-4 rounded-xl border ${isDelivery ? 'border-amber-200 bg-amber-50/20' : 'border-slate-200 bg-white'} shadow-sm text-xs flex flex-col justify-between`;

        card.innerHTML = `
            <div>
                <div class="flex justify-between items-center mb-1">
                    <span class="font-bold text-sm text-slate-900">${ch.channel_name}</span>
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold ${ch.contribution_margin_pct > 50 ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">
                        ${ch.contribution_margin_pct}% Margin
                    </span>
                </div>
                <div class="text-[11px] text-slate-500 mb-3">${ch.order_count.toLocaleString()} Orders &bull; Avg Ticket: <strong>£${ch.avg_ticket_gbp.toFixed(2)}</strong></div>
                
                <div class="space-y-1.5 border-t border-slate-100 pt-2 text-slate-600">
                    <div class="flex justify-between">
                        <span>Platform Commission:</span>
                        <span class="font-semibold text-rose-600">-£${ch.commission_gbp.toFixed(2)} (${ch.commission_rate_pct}%)</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Packaging Cost:</span>
                        <span class="font-semibold text-slate-700">-£${ch.packaging_cost_gbp.toFixed(2)}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Labor Packing (4 min):</span>
                        <span class="font-semibold text-slate-700">-£${ch.labor_packing_cost_gbp.toFixed(2)}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Food Cost:</span>
                        <span class="font-semibold text-slate-700">-£${ch.food_cost_gbp.toFixed(2)}</span>
                    </div>
                </div>
            </div>

            <div class="mt-4 pt-2 border-t border-slate-200 flex justify-between items-center font-bold">
                <span class="text-slate-900">Net Contribution / Order:</span>
                <span class="text-base ${ch.net_contribution_gbp > 2.0 ? 'text-emerald-600' : 'text-amber-700'}">£${ch.net_contribution_gbp.toFixed(2)}</span>
            </div>
        `;
        container.appendChild(card);
    });
}

function renderSub8HourlyChart(hourly) {
    const ctx = document.getElementById('sub8HourlyChart');
    if (!ctx) return;
    if (charts.sub8) charts.sub8.destroy();

    const hours = hourly.map(h => `${h.order_hour}:00`);
    const totalOrders = hourly.map(h => h.total_orders);
    const sub8Orders = hourly.map(h => h.sub8_orders);

    charts.sub8 = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hours,
            datasets: [
                {
                    label: 'Sub-£8 Single Drink Orders',
                    data: sub8Orders,
                    backgroundColor: 'rgba(225, 29, 72, 0.85)',
                    borderRadius: 3
                },
                {
                    label: 'Standard Orders (>= £8)',
                    data: totalOrders.map((tot, i) => tot - sub8Orders[i]),
                    backgroundColor: 'rgba(148, 163, 184, 0.5)',
                    borderRadius: 3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { stacked: true },
                y: { stacked: true, title: { display: true, text: 'Delivery Orders' } }
            }
        }
    });
}

async function runDeliverySimulation() {
    const slider = document.getElementById('sim-markup-slider');
    const check = document.getElementById('sim-minbasket-check');
    const display = document.getElementById('sim-markup-display');
    if (!slider || !display) return;

    const markup = parseFloat(slider.value);
    display.textContent = `+${markup}%`;

    const payload = {
        markup_pct: markup,
        apply_min_basket_8: check ? check.checked : false,
        volume_elasticity: -0.3
    };

    try {
        const res = await fetch('/api/delivery/simulate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.impact) {
            document.getElementById('sim-margin-pts').textContent = `+${data.impact.margin_improvement_pts} pts`;
            document.getElementById('sim-profit-recovery').textContent = `+£${data.impact.annualized_chain_profit_recovery_gbp.toLocaleString()}`;
        }
    } catch (err) {
        console.error("Simulation error", err);
    }
}

// ==========================================
// MODULE 3: Labor & Throughput
// ==========================================
async function loadLaborData() {
    const query = getFilterParams();
    try {
        const [bottleneckRes, walkoutsRes] = await Promise.all([
            fetch(`/api/labor/bottlenecks${query}`),
            fetch(`/api/labor/walkouts${query}`)
        ]);

        const bottlenecks = await bottleneckRes.json();
        const walkouts = await walkoutsRes.json();

        // Render Bottleneck Chart
        renderBottleneckChart(bottlenecks.stores || []);

        if (walkouts.total_annual_lost_revenue_gbp) {
            document.getElementById('labor-annual-walkout-loss').textContent = `£${walkouts.total_annual_lost_revenue_gbp.toLocaleString()}`;
        }
    } catch (err) {
        console.error("Error loading labor data", err);
    }
}

function renderBottleneckChart(stores) {
    const ctx = document.getElementById('bottleneckChart');
    if (!ctx) return;
    if (charts.bottleneck) charts.bottleneck.destroy();

    const labels = stores.map(s => s.store_name.split(' ')[0] + ' ' + (s.store_name.split(' ')[1] || ''));
    const demand = stores.map(s => s.expected_demand_tx);
    const capacity = stores.map(s => s.capacity_tx);

    charts.bottleneck = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Customer Demand (11am-2pm)',
                    data: demand,
                    backgroundColor: 'rgba(217, 119, 6, 0.85)',
                    borderRadius: 4
                },
                {
                    label: 'Staff Extraction Capacity',
                    data: capacity,
                    backgroundColor: 'rgba(51, 65, 85, 0.75)',
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { title: { display: true, text: 'Drinks / Transactions' } }
            }
        }
    });
}

async function runWageStressTest() {
    const wageInput = document.getElementById('stress-wage-input');
    const priceInput = document.getElementById('stress-price-input');
    const wage = parseFloat(wageInput.value) || 6.7;
    const price = parseFloat(priceInput.value) || 0.0;

    try {
        const res = await fetch('/api/labor/wage-stress', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({wage_increase_pct: wage, price_offset_pct: price})
        });
        const data = await res.json();
        if (data.summary) {
            document.getElementById('wage-stress-summary-text').innerHTML = `
                Total Wage Increase: <strong>£${data.summary.total_wage_cost_increase_gbp.toLocaleString()}</strong> &bull; 
                Net Stressed Profit: <strong>£${data.summary.total_stressed_profit_gbp.toLocaleString()}</strong> &bull; 
                Chain Breakeven Price Rise: <strong>${data.summary.chain_breakeven_price_rise_pct}%</strong>
            `;
        }
    } catch (err) {
        console.error("Wage stress test error", err);
    }
}

// ==========================================
// MODULE 4: Waste & Par Levels
// ==========================================
async function loadWasteData() {
    const query = getFilterParams();
    try {
        const res = await fetch(`/api/waste/variance${query}`);
        const data = await res.json();
        renderWasteChart(data.stores || []);
        runDynamicParCalc();
    } catch (err) {
        console.error("Error loading waste data", err);
    }
}

function renderWasteChart(stores) {
    const ctx = document.getElementById('wasteChart');
    if (!ctx) return;
    if (charts.waste) charts.waste.destroy();

    const labels = stores.map(s => s.store_name.split(' ')[0] + ' ' + (s.store_name.split(' ')[1] || ''));
    const rates = stores.map(s => s.avg_waste_rate_pct);
    const bgColors = stores.map(s => s.avg_waste_rate_pct > 15.0 ? 'rgba(225, 29, 72, 0.9)' : s.avg_waste_rate_pct > 9.0 ? 'rgba(217, 119, 6, 0.8)' : 'rgba(5, 150, 105, 0.7)');

    charts.waste = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Waste Rate % of Food Cost',
                data: rates,
                backgroundColor: bgColors,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { title: { display: true, text: 'Waste Rate (%)' }, suggestedMax: 25 }
            }
        }
    });
}

async function runDynamicParCalc() {
    const dow = document.getElementById('par-dow')?.value || 'Wednesday';
    const weather = document.getElementById('par-weather')?.value || 'Rainy';
    const store = document.getElementById('global-store-filter')?.value || 'S10';

    try {
        const res = await fetch(`/api/waste/dynamic-par?store_id=${store}&day_of_week=${dow}&weather=${weather}`);
        const data = await res.json();
        const tbody = document.getElementById('dynamic-par-body');
        if (!tbody || !data.recommendations) return;
        tbody.innerHTML = '';

        data.recommendations.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="px-4 py-3 font-bold text-slate-900">${r.category}</td>
                <td class="px-4 py-3 text-right font-extrabold text-amber-600">${r.recommended_prep_units} units</td>
                <td class="px-4 py-3 text-right text-slate-500">${r.safety_buffer_pct}%</td>
                <td class="px-4 py-3 text-right text-slate-700">£${r.est_prep_cost_gbp.toFixed(2)}</td>
                <td class="px-4 py-3 text-right font-semibold text-emerald-600">£${r.est_revenue_potential_gbp.toFixed(2)}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Dynamic par error", err);
    }
}

// ==========================================
// MODULE 5: Digital App & Sentiment
// ==========================================
async function loadDigitalData() {
    try {
        const [healthRes, sentimentRes] = await Promise.all([
            fetch('/api/digital/health'),
            fetch('/api/digital/sentiment')
        ]);

        const health = await healthRes.json();
        const sentiment = await sentimentRes.json();

        renderDigitalHealthChart(health.timeline || []);
        renderSentimentList(sentiment.keyword_clusters || []);
    } catch (err) {
        console.error("Error loading digital data", err);
    }
}

function renderDigitalHealthChart(timeline) {
    const ctx = document.getElementById('digitalHealthChart');
    if (!ctx) return;
    if (charts.digitalHealth) charts.digitalHealth.destroy();

    const weeks = timeline.map(t => t.week_start.slice(5));
    const appOrders = timeline.map(t => t.app_orders);
    const delivOrders = timeline.map(t => t.delivery_orders);

    charts.digitalHealth = new Chart(ctx, {
        type: 'line',
        data: {
            labels: weeks,
            datasets: [
                {
                    label: 'Direct App Orders (0% Commission)',
                    data: appOrders,
                    borderColor: 'rgb(5, 150, 105)',
                    backgroundColor: 'rgba(5, 150, 105, 0.1)',
                    fill: true,
                    tension: 0.3
                },
                {
                    label: 'Third-Party Delivery Orders (Displacement Bleed)',
                    data: delivOrders,
                    borderColor: 'rgb(225, 29, 72)',
                    backgroundColor: 'rgba(225, 29, 72, 0.05)',
                    fill: true,
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { title: { display: true, text: 'Weekly Orders' } }
            }
        }
    });
}

function renderSentimentList(clusters) {
    const container = document.getElementById('sentiment-clusters-list');
    if (!container) return;
    container.innerHTML = '';

    clusters.forEach(c => {
        const item = document.createElement('div');
        item.className = 'p-3 bg-slate-50 rounded-lg border border-slate-200 flex justify-between items-center';
        item.innerHTML = `
            <div>
                <div class="font-bold text-slate-900">${c.label}</div>
                <div class="text-[11px] text-slate-500">${c.mentions.toLocaleString()} review mentions &bull; ${c.negative_share_pct}% negative</div>
            </div>
            <div class="text-right">
                <span class="text-sm font-extrabold ${c.avg_rating < 3.0 ? 'text-rose-600' : 'text-slate-800'}">${c.avg_rating} / 5.0 &#9733;</span>
            </div>
        `;
        container.appendChild(item);
    });
}

// ==========================================
// MODULE 6: Capital Expansion & Candidate Sites
// ==========================================
async function loadExpansionData() {
    runSiteScoring();
}

async function runSiteScoring() {
    const wFootfall = parseFloat(document.getElementById('w-footfall')?.value || 25) / 100;
    const wDemo = parseFloat(document.getElementById('w-demo')?.value || 25) / 100;
    const wRent = parseFloat(document.getElementById('w-rent')?.value || 20) / 100;
    const wCapex = parseFloat(document.getElementById('w-capex')?.value || 15) / 100;
    const wCannibal = parseFloat(document.getElementById('w-cannibal')?.value || 15) / 100;

    // Update displays
    document.getElementById('weight-footfall-val').textContent = `${Math.round(wFootfall * 100)}%`;
    document.getElementById('weight-demo-val').textContent = `${Math.round(wDemo * 100)}%`;
    document.getElementById('weight-rent-val').textContent = `${Math.round(wRent * 100)}%`;
    document.getElementById('weight-capex-val').textContent = `${Math.round(wCapex * 100)}%`;
    document.getElementById('weight-cannibal-val').textContent = `${Math.round(wCannibal * 100)}%`;

    const payload = {
        weight_footfall: wFootfall,
        weight_demographics: wDemo,
        weight_rent_efficiency: wRent,
        weight_fitout_capex: wCapex,
        weight_cannibalization_risk: wCannibal
    };

    try {
        const res = await fetch('/api/expansion/score', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        renderCandidateSitesTable(data.candidate_sites || []);
        renderSitesComparisonChart(data.candidate_sites || []);
    } catch (err) {
        console.error("Site scoring error", err);
    }
}

function renderCandidateSitesTable(sites) {
    const tbody = document.getElementById('candidate-sites-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    const badgeMap = {
        'emerald': 'bg-emerald-100 text-emerald-800 border-emerald-200',
        'blue': 'bg-blue-100 text-blue-800 border-blue-200',
        'amber': 'bg-amber-100 text-amber-800 border-amber-200',
        'red': 'bg-rose-100 text-rose-800 border-rose-200'
    };

    sites.forEach(s => {
        const tr = document.createElement('tr');
        tr.className = s.recommendation.includes('HIGH - PRIORITY') ? 'bg-emerald-50/50' : s.recommendation.includes('HIGH RISK') ? 'bg-rose-50/50' : '';
        tr.innerHTML = `
            <td class="px-4 py-3 font-bold text-slate-900">${s.site_name} (${s.site_id})</td>
            <td class="px-4 py-3 text-slate-500">${s.city} &bull; ${s.location_type}</td>
            <td class="px-4 py-3 text-right">£${s.quoted_rent_gbp_month.toLocaleString()}</td>
            <td class="px-4 py-3 text-right font-medium">£${s.rent_per_sqft_gbp}/sqft</td>
            <td class="px-4 py-3 text-right font-semibold">${s.daily_footfall.toLocaleString()}</td>
            <td class="px-4 py-3 text-right">£${s.est_fitout_gbp.toLocaleString()}</td>
            <td class="px-4 py-3 text-center font-black text-sm">${s.composite_score}</td>
            <td class="px-4 py-3 text-center">
                <span class="px-2.5 py-1 rounded text-[10px] font-extrabold border ${badgeMap[s.badge_color] || ''}">
                    ${s.recommendation}
                </span>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function renderSitesComparisonChart(sites) {
    const ctx = document.getElementById('sitesComparisonChart');
    if (!ctx) return;
    if (charts.sitesComparison) charts.sitesComparison.destroy();

    const labels = sites.map(s => s.site_name);
    const scores = sites.map(s => s.composite_score);
    const bgColors = sites.map(s => s.badge_color === 'emerald' ? 'rgba(5, 150, 105, 0.85)' : s.badge_color === 'red' ? 'rgba(225, 29, 72, 0.85)' : 'rgba(217, 119, 6, 0.7)');

    charts.sitesComparison = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Composite Evaluation Score (0-100)',
                data: scores,
                backgroundColor: bgColors,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { max: 100, title: { display: true, text: 'Composite Score' } }
            }
        }
    });
}
