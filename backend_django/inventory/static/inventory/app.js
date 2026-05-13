const $ = (id) => document.getElementById(id);

const state = {
    products: [],
    sales: [],
    productsPage: 1,
    productsPageSize: 10,
    productCategoryFilter: "",
    dashboardProductId: "",
    salesPage: 1,
    salesPageSize: 50,
    salesCount: 0,
    salesNext: null,
    salesPrevious: null,
    analyticsSales: [],
};

const ui = {
    productForm: $("productForm"),
    saleForm: $("saleForm"),
    productsTableBody: $("productsTableBody"),
    dashboardProduct: $("dashboardProduct"),
    productCategoryFilter: $("productCategoryFilter"),
    productsPrev: $("productsPrev"),
    productsNext: $("productsNext"),
    productsPageInfo: $("productsPageInfo"),
    salesTableBody: $("salesTableBody"),
    saleProduct: $("saleProduct"),
    filterProduct: $("filterProduct"),
    forecastProduct: $("forecastProduct"),
    forecastStartMonth: $("forecastStartMonth"),
    forecastBtn: $("forecastBtn"),
    forecastResult: $("forecastResult"),
    salesPrev: $("salesPrev"),
    salesNext: $("salesNext"),
    salesPageInfo: $("salesPageInfo"),
    statProducts: $("statProducts"),
    statSales: $("statSales"),
    statRisk: $("statRisk"),
    stockRiskTooltip: $("stockRiskTooltip"),
    salesTrendChart: $("salesTrendChart"),
    stockChart: $("stockChart"),
    topProductsChart: $("topProductsChart"),
    categoryChart: $("categoryChart"),
    dashboardInsights: $("dashboardInsights"),
    toast: $("toast"),
};

function getCookie(name) {
    const parts = document.cookie ? document.cookie.split(";") : [];
    for (const part of parts) {
        const cookie = part.trim();
        if (cookie.startsWith(`${name}=`)) {
            return decodeURIComponent(cookie.slice(name.length + 1));
        }
    }
    return "";
}

function showToast(message, type = "ok") {
    ui.toast.textContent = message;
    ui.toast.className = `toast show ${type}`;
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => {
        ui.toast.className = "toast";
    }, 2400);
}

function parseError(data) {
    if (!data || typeof data !== "object") {
        return "Error inesperado";
    }
    const messages = [];
    for (const [field, value] of Object.entries(data)) {
        if (Array.isArray(value)) {
            messages.push(`${field}: ${value.join(", ")}`);
        } else {
            messages.push(`${field}: ${String(value)}`);
        }
    }
    return messages.join(" | ") || "Error de validacion";
}

async function apiFetch(url, options = {}) {
    const headers = {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
    };

    const method = (options.method || "GET").toUpperCase();
    if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
        headers["X-CSRFToken"] = getCookie("csrftoken");
    }

    const response = await fetch(url, {
        ...options,
        headers,
    });

    let data = null;
    try {
        data = await response.json();
    } catch {
        data = null;
    }

    if (!response.ok) {
        throw new Error(parseError(data));
    }

    return data;
}

function todayIso() {
    return new Date().toISOString().slice(0, 10);
}

function money(value) {
    const n = Number(value || 0);
    return new Intl.NumberFormat("es-PE", {
        style: "currency",
        currency: "PEN",
    }).format(n);
}

function shortMoney(value) {
    const n = Number(value || 0);
    if (Math.abs(n) >= 1000) {
        return `S/ ${(n / 1000).toFixed(1)}k`;
    }
    return `S/ ${n.toFixed(0)}`;
}

function productById(id) {
    return state.products.find((p) => String(p.id) === String(id));
}

function setupCanvas(canvas) {
    if (!canvas) {
        return null;
    }
    const ratio = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(Math.floor(rect.width), 320);
    const height = Number(canvas.getAttribute("height") || 220);
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, width, height);
    return { ctx, width, height };
}

function drawEmptyChart(canvas, message) {
    const chart = setupCanvas(canvas);
    if (!chart) {
        return;
    }
    const { ctx, width, height } = chart;
    ctx.fillStyle = "#687d90";
    ctx.font = "600 14px Segoe UI, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(message, width / 2, height / 2);
}

function drawGrid(ctx, left, top, width, height) {
    ctx.strokeStyle = "#e6edf3";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i += 1) {
        const y = top + (height / 4) * i;
        ctx.beginPath();
        ctx.moveTo(left, y);
        ctx.lineTo(left + width, y);
        ctx.stroke();
    }
}

function drawBarChart(canvas, items, options = {}) {
    if (!items.length) {
        drawEmptyChart(canvas, options.empty || "Sin datos disponibles");
        return;
    }
    const chart = setupCanvas(canvas);
    if (!chart) {
        return;
    }
    const { ctx, width, height } = chart;
    const left = 38;
    const right = 12;
    const top = 18;
    const bottom = 44;
    const plotWidth = width - left - right;
    const plotHeight = height - top - bottom;
    const max = Math.max(...items.map((item) => Number(item.value || 0)), 1);
    const gap = 9;
    const barWidth = Math.max((plotWidth - gap * (items.length - 1)) / items.length, 10);

    drawGrid(ctx, left, top, plotWidth, plotHeight);

    items.forEach((item, index) => {
        const value = Number(item.value || 0);
        const barHeight = (value / max) * plotHeight;
        const x = left + index * (barWidth + gap);
        const y = top + plotHeight - barHeight;
        ctx.fillStyle = item.color || options.color || "#216e7a";
        ctx.fillRect(x, y, barWidth, barHeight);
        ctx.fillStyle = "#52677b";
        ctx.font = "600 11px Segoe UI, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(String(item.label).slice(0, 10), x + barWidth / 2, height - 18);
    });
}

function drawHorizontalBars(canvas, items, options = {}) {
    if (!items.length) {
        drawEmptyChart(canvas, options.empty || "Sin datos disponibles");
        return;
    }
    const chart = setupCanvas(canvas);
    if (!chart) {
        return;
    }
    const { ctx, width, height } = chart;
    const left = 104;
    const right = 16;
    const top = 16;
    const rowHeight = Math.min(34, (height - top - 16) / items.length);
    const max = Math.max(...items.map((item) => Number(item.value || 0)), 1);
    const barMaxWidth = width - left - right;

    items.forEach((item, index) => {
        const y = top + index * rowHeight;
        const barWidth = (Number(item.value || 0) / max) * barMaxWidth;
        ctx.fillStyle = "#52677b";
        ctx.font = "600 11px Segoe UI, sans-serif";
        ctx.textAlign = "right";
        ctx.fillText(String(item.label).slice(0, 16), left - 10, y + 18);
        ctx.fillStyle = "#e8f0f5";
        ctx.fillRect(left, y + 5, barMaxWidth, 12);
        ctx.fillStyle = item.color || options.color || "#216e7a";
        ctx.fillRect(left, y + 5, barWidth, 12);
        ctx.fillStyle = "#263d52";
        ctx.textAlign = "left";
        ctx.fillText(String(item.display ?? item.value), left + barWidth + 6, y + 17);
    });
}

function drawLineBarChart(canvas, items) {
    if (!items.length) {
        drawEmptyChart(canvas, "Sin ventas registradas");
        return;
    }
    const chart = setupCanvas(canvas);
    if (!chart) {
        return;
    }
    const { ctx, width, height } = chart;
    const left = 42;
    const right = 18;
    const top = 18;
    const bottom = 44;
    const plotWidth = width - left - right;
    const plotHeight = height - top - bottom;
    const maxUnits = Math.max(...items.map((item) => item.units), 1);
    const maxRevenue = Math.max(...items.map((item) => item.revenue), 1);
    const gap = 10;
    const barWidth = Math.max((plotWidth - gap * (items.length - 1)) / items.length, 12);

    drawGrid(ctx, left, top, plotWidth, plotHeight);

    const points = [];
    items.forEach((item, index) => {
        const x = left + index * (barWidth + gap);
        const barHeight = (item.units / maxUnits) * plotHeight;
        const y = top + plotHeight - barHeight;
        ctx.fillStyle = "#216e7a";
        ctx.fillRect(x, y, barWidth, barHeight);
        points.push({
            x: x + barWidth / 2,
            y: top + plotHeight - (item.revenue / maxRevenue) * plotHeight,
        });
        ctx.fillStyle = "#52677b";
        ctx.font = "600 11px Segoe UI, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(item.label, x + barWidth / 2, height - 18);
    });

    ctx.strokeStyle = "#b76617";
    ctx.lineWidth = 3;
    ctx.beginPath();
    points.forEach((point, index) => {
        if (index === 0) {
            ctx.moveTo(point.x, point.y);
        } else {
            ctx.lineTo(point.x, point.y);
        }
    });
    ctx.stroke();
    points.forEach((point) => {
        ctx.fillStyle = "#b76617";
        ctx.beginPath();
        ctx.arc(point.x, point.y, 4, 0, Math.PI * 2);
        ctx.fill();
    });

    ctx.fillStyle = "#216e7a";
    ctx.fillRect(left, 2, 10, 10);
    ctx.fillStyle = "#b76617";
    ctx.fillRect(left + 92, 2, 10, 10);
    ctx.fillStyle = "#52677b";
    ctx.font = "600 11px Segoe UI, sans-serif";
    ctx.textAlign = "left";
    ctx.fillText("Unidades", left + 15, 11);
    ctx.fillText("Ingresos", left + 107, 11);
}

function drawDonutChart(canvas, items) {
    if (!items.length) {
        drawEmptyChart(canvas, "Sin datos por categoria");
        return;
    }
    const chart = setupCanvas(canvas);
    if (!chart) {
        return;
    }
    const { ctx, width, height } = chart;
    const total = items.reduce((sum, item) => sum + Number(item.value || 0), 0) || 1;
    const radius = Math.min(width, height) * 0.27;
    const cx = width * 0.34;
    const cy = height * 0.48;
    let start = -Math.PI / 2;

    items.forEach((item) => {
        const slice = (Number(item.value || 0) / total) * Math.PI * 2;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, radius, start, start + slice);
        ctx.closePath();
        ctx.fillStyle = item.color;
        ctx.fill();
        start += slice;
    });

    ctx.globalCompositeOperation = "destination-out";
    ctx.beginPath();
    ctx.arc(cx, cy, radius * 0.58, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalCompositeOperation = "source-over";

    items.slice(0, 5).forEach((item, index) => {
        const y = 38 + index * 27;
        ctx.fillStyle = item.color;
        ctx.fillRect(width * 0.62, y - 9, 10, 10);
        ctx.fillStyle = "#263d52";
        ctx.font = "600 11px Segoe UI, sans-serif";
        ctx.textAlign = "left";
        ctx.fillText(`${item.label.slice(0, 14)} ${shortMoney(item.value)}`, width * 0.62 + 16, y);
    });
}

function drawForecastChart(items) {
    const canvas = $("forecastAnnualChart");
    const chartItems = (items || []).map((item) => ({
        label: monthLabel(item.month),
        value: Number(item.predicted_sales_units || 0),
        color: Number(item.recommended_restock || item.stock_shortage || 0) > 0 ? "#b76617" : "#216e7a",
    }));
    drawBarChart(canvas, chartItems, { empty: "Sin forecast anual" });
}

function updateStats() {
    ui.statProducts.textContent = String(state.products.length);
    ui.statSales.textContent = String(state.salesCount || state.sales.length);
    const riskProducts = state.products.filter((p) => Number(p.stock) <= 0);
    ui.statRisk.textContent = String(riskProducts.length);
    ui.stockRiskTooltip.innerHTML = riskProducts.length
        ? riskProducts.map((p) => `<span>${p.sku || "-"} - ${p.name || "-"}</span>`).join("")
        : "<span>Sin productos en riesgo</span>";
}

function monthLabel(monthKey) {
    const [, month] = monthKey.split("-");
    return ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"][Number(month) - 1] || monthKey;
}

function dashboardProducts() {
    if (!state.dashboardProductId) {
        return state.products;
    }
    const product = productById(Number(state.dashboardProductId));
    return product ? [product] : [];
}

function dashboardSales() {
    if (!state.dashboardProductId) {
        return state.analyticsSales;
    }
    return state.analyticsSales.filter((sale) => String(sale.product) === String(state.dashboardProductId));
}

function salesByMonth() {
    const grouped = new Map();
    dashboardSales().forEach((sale) => {
        const key = String(sale.date || "").slice(0, 7);
        if (!key) {
            return;
        }
        const current = grouped.get(key) || { units: 0, revenue: 0 };
        current.units += Number(sale.units_sold || 0);
        current.revenue += Number(sale.total_price || 0);
        grouped.set(key, current);
    });
    return Array.from(grouped.entries())
        .sort(([a], [b]) => a.localeCompare(b))
        .slice(-8)
        .map(([key, value]) => ({ label: monthLabel(key), ...value }));
}

function topProductsBySales() {
    const grouped = new Map();
    dashboardSales().forEach((sale) => {
        const product = productById(sale.product);
        const label = product ? product.sku || product.name : sale.product_sku || "Producto";
        grouped.set(label, (grouped.get(label) || 0) + Number(sale.units_sold || 0));
    });
    return Array.from(grouped.entries())
        .map(([label, value]) => ({ label, value, display: value.toFixed(0) }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 6);
}

function stockByProduct() {
    return [...dashboardProducts()]
        .sort((a, b) => Number(b.stock || 0) - Number(a.stock || 0))
        .slice(0, 6)
        .map((product) => ({
            label: product.sku || product.name,
            value: Number(product.stock || 0),
            display: Number(product.stock || 0).toFixed(0),
            color: Number(product.stock || 0) <= 0 ? "#b76617" : "#216e7a",
        }));
}

function salesByCategory() {
    const colors = ["#216e7a", "#247a52", "#b76617", "#576b95", "#7d5f98", "#8a6c3c"];
    const grouped = new Map();
    dashboardSales().forEach((sale) => {
        const product = productById(sale.product);
        const category = product && product.category ? product.category : "Sin categoria";
        grouped.set(category, (grouped.get(category) || 0) + Number(sale.total_price || 0));
    });
    return Array.from(grouped.entries())
        .sort((a, b) => b[1] - a[1])
        .slice(0, 6)
        .map(([label, value], index) => ({ label, value, color: colors[index % colors.length] }));
}

function renderDashboardInsights() {
    const sales = dashboardSales();
    const products = dashboardProducts();
    const selectedProduct = state.dashboardProductId ? productById(Number(state.dashboardProductId)) : null;
    const totalRevenue = sales.reduce((sum, sale) => sum + Number(sale.total_price || 0), 0);
    const totalUnits = sales.reduce((sum, sale) => sum + Number(sale.units_sold || 0), 0);
    const riskProducts = products.filter((product) => Number(product.stock) <= 0);
    const bestProduct = topProductsBySales()[0];
    const stockValue = products.reduce((sum, product) => sum + Number(product.stock || 0) * Number(product.price || 0), 0);

    ui.dashboardInsights.innerHTML = `
        <article class="insight-card">
            <p>Ingresos</p>
            <strong>${money(totalRevenue)}</strong>
            <span>${totalUnits.toFixed(0)} unidades</span>
        </article>
	        <article class="insight-card">
	            <p>${selectedProduct ? "Producto" : "Mayor venta"}</p>
	            <strong>${selectedProduct ? selectedProduct.sku : bestProduct ? bestProduct.label : "-"}</strong>
	            <span>${selectedProduct ? selectedProduct.name : bestProduct ? `${bestProduct.value.toFixed(0)} unidades` : "Sin ventas"}</span>
	        </article>
        <article class="insight-card">
            <p>Inventario</p>
            <strong>${money(stockValue)}</strong>
            <span>Valorizado</span>
        </article>
        <article class="insight-card">
            <p>Sin stock</p>
            <strong>${riskProducts.length}</strong>
            <span>${riskProducts.slice(0, 2).map((p) => p.sku || p.name).join(", ") || "Sin alertas"}</span>
        </article>
    `;
}

function renderDashboardVisuals() {
    drawLineBarChart(ui.salesTrendChart, salesByMonth());
    drawHorizontalBars(ui.stockChart, stockByProduct(), { empty: "Sin productos registrados" });
    drawHorizontalBars(ui.topProductsChart, topProductsBySales(), { color: "#247a52", empty: "Sin ventas registradas" });
    drawDonutChart(ui.categoryChart, salesByCategory());
    renderDashboardInsights();
}

function setProductSelectOptions() {
    const options = state.products
        .map((p) => `<option value="${p.id}">${p.sku} - ${p.name}</option>`)
        .join("");

    const placeholder = '<option value="">Selecciona producto</option>';
    ui.saleProduct.innerHTML = placeholder + options;
    ui.forecastProduct.innerHTML = placeholder + options;
    ui.filterProduct.innerHTML = '<option value="">Todos los productos</option>' + options;
    ui.dashboardProduct.innerHTML = '<option value="">Todos los productos</option>' + options;
    ui.dashboardProduct.value = state.dashboardProductId;
}

function setProductCategoryFilterOptions() {
    const current = ui.productCategoryFilter.value;
    const categories = [...new Set(state.products.map((p) => p.category).filter(Boolean))].sort((a, b) => a.localeCompare(b));
    ui.productCategoryFilter.innerHTML = '<option value="">Todas las categorias</option>' + categories
        .map((category) => `<option value="${category}">${category}</option>`)
        .join("");
    ui.productCategoryFilter.value = categories.includes(current) ? current : "";
    state.productCategoryFilter = ui.productCategoryFilter.value;
}

function filteredProducts() {
    if (!state.productCategoryFilter) {
        return state.products;
    }
    return state.products.filter((product) => product.category === state.productCategoryFilter);
}

function renderProductsPagination(totalProducts) {
    const totalPages = Math.max(1, Math.ceil(totalProducts / state.productsPageSize));
    state.productsPage = Math.min(Math.max(state.productsPage, 1), totalPages);
    ui.productsPageInfo.textContent = `Pagina ${state.productsPage} de ${totalPages} (${totalProducts} productos)`;
    ui.productsPrev.disabled = state.productsPage <= 1;
    ui.productsNext.disabled = state.productsPage >= totalPages;
}

function renderProducts() {
    const products = filteredProducts();
    renderProductsPagination(products.length);

    if (!products.length) {
        ui.productsTableBody.innerHTML = '<tr><td colspan="9" class="empty">Sin productos todavia.</td></tr>';
        updateStats();
        return;
    }

    const start = (state.productsPage - 1) * state.productsPageSize;
    const visibleProducts = products.slice(start, start + state.productsPageSize);

    ui.productsTableBody.innerHTML = visibleProducts
        .map((p) => {
            const warningClass = Number(p.stock) <= 0 ? "stock-alert" : "";
            return `
                <tr>
                    <td>${p.sku || "-"}</td>
                    <td>${p.name || "-"}</td>
                    <td>${p.category || "-"}</td>
                    <td>${money(p.price)}</td>
                    <td>${p.stock_initial ?? 0}</td>
                    <td>${p.stock_received_total ?? 0}</td>
                    <td>${p.units_sold_total ?? 0}</td>
                    <td class="${warningClass}">${p.stock}</td>
                    <td>
                        <button type="button" class="ghost restock-btn" data-product-id="${p.id}">
                            Reabastecer
                        </button>
                    </td>
                </tr>
            `;
        })
        .join("");

    updateStats();
}

function renderSales() {
    if (!state.sales.length) {
        ui.salesTableBody.innerHTML = '<tr><td colspan="7" class="empty">No hay ventas para este filtro.</td></tr>';
        renderSalesPagination();
        updateStats();
        return;
    }

    ui.salesTableBody.innerHTML = state.sales
        .map(
            (s) => `
                <tr>
                    <td>${s.id}</td>
                    <td>${s.date || "-"}</td>
                    <td>${s.product_sku || "-"}</td>
                    <td>${s.client_name || "-"}</td>
                    <td>${s.serial_number || "-"}</td>
                    <td>${Number(s.units_sold || 0).toFixed(0)}</td>
                    <td>${money(s.total_price)}</td>
                </tr>
            `,
        )
        .join("");

    renderSalesPagination();
    updateStats();
}

function renderSalesPagination() {
    const totalPages = Math.max(1, Math.ceil((state.salesCount || 0) / state.salesPageSize));
    ui.salesPageInfo.textContent = `Pagina ${state.salesPage} de ${totalPages} (${state.salesCount} ventas)`;
    ui.salesPrev.disabled = !state.salesPrevious;
    ui.salesNext.disabled = !state.salesNext;
}

async function loadProducts() {
    const data = await apiFetch("/api/products/");
    state.products = Array.isArray(data) ? data : data.results || [];
    setProductCategoryFilterOptions();
    renderProducts();
    setProductSelectOptions();
    renderDashboardVisuals();
}

async function handleRestock(productId) {
    const product = state.products.find((p) => String(p.id) === String(productId));
    const raw = window.prompt(`Cantidad a reabastecer para ${product ? product.sku : "producto"}`);
    if (raw === null) {
        return;
    }
    const quantity = Number(raw);
    if (!Number.isInteger(quantity) || quantity <= 0) {
        showToast("Ingresa una cantidad entera mayor que cero", "error");
        return;
    }

    await apiFetch(`/api/products/${productId}/restock/`, {
        method: "POST",
        body: JSON.stringify({ quantity, note: "Reabastecimiento desde panel operativo" }),
    });
    showToast("Stock reabastecido", "ok");
    await loadProducts();
}

function currentSalesFilterQuery() {
    const params = new URLSearchParams();

    const id = $("filterSaleId").value.trim();
    const productId = ui.filterProduct.value;
    const client = $("filterClient").value.trim();
    const date = $("filterDate").value;

    if (productId) {
        params.append("product", productId);
    }
    if (id) {
        params.append("id", id);
    }
    if (client) {
        params.append("client_name", client);
    }
    if (date) {
        params.append("date", date);
    }
    params.append("page", String(state.salesPage));
    params.append("page_size", String(state.salesPageSize));

    const query = params.toString();
    return query ? `?${query}` : "";
}

async function loadSales() {
    const data = await apiFetch(`/api/sales/${currentSalesFilterQuery()}`);
    state.sales = Array.isArray(data) ? data : data.results || [];
    state.salesCount = Array.isArray(data) ? data.length : data.count || 0;
    state.salesNext = Array.isArray(data) ? null : data.next;
    state.salesPrevious = Array.isArray(data) ? null : data.previous;
    renderSales();
}

async function loadAnalyticsSales() {
    let url = "/api/sales/";
    const sales = [];
    for (let page = 0; url && page < 40; page += 1) {
        const data = await apiFetch(url);
        if (Array.isArray(data)) {
            sales.push(...data);
            url = null;
        } else {
            sales.push(...(data.results || []));
            url = data.next ? new URL(data.next, window.location.origin).pathname + new URL(data.next, window.location.origin).search : null;
        }
    }
    state.analyticsSales = sales;
    renderDashboardVisuals();
}

function generateSerial() {
    return `WEB-${Date.now().toString().slice(-8)}`;
}

function renderForecast(data) {
    const historyList = (data.history || [])
        .slice(-6)
        .map((h) => `<li>${h.month}: ${h.total_units.toFixed(1)} unidades</li>`)
        .join("");
    const annualRows = (data.annual_forecast || [])
        .map(
            (item) => `
                <tr>
                    <td>${item.month}</td>
                    <td>${item.starting_stock ?? "-"}</td>
                    <td>${item.predicted_sales_units}</td>
                    <td>${item.stock_required}</td>
                    <td>${item.recommended_restock ?? item.stock_shortage}</td>
                    <td>${item.stock_after_month ?? "-"}</td>
                </tr>
            `,
        )
        .join("");
    const historyRows = (data.history || [])
        .map(
            (item) => `
                <tr>
                    <td>${item.month}</td>
                    <td>${item.total_units.toFixed(0)}</td>
                </tr>
            `,
        )
        .join("");

    ui.forecastResult.className = "forecast-box";
    ui.forecastResult.innerHTML = `
        <div class="forecast-grid">
            <div class="forecast-item">
                <p>Mes objetivo</p>
                <strong>${data.forecast_month || "-"}</strong>
            </div>
            <div class="forecast-item">
                <p>Unidades estimadas</p>
                <strong>${data.predicted_sales_units ?? 0}</strong>
            </div>
            <div class="forecast-item">
                <p>Stock actual</p>
                <strong>${data.current_stock ?? 0}</strong>
            </div>
            <div class="forecast-item">
                <p>Faltante estimado</p>
                <strong>${data.stock_shortage ?? 0}</strong>
            </div>
        </div>
        <div class="forecast-meta">
            <p><strong>SKU:</strong> ${data.sku || "-"}</p>
            <p><strong>Modelo:</strong> ${data.forecast_model || "-"}</p>
            <p><strong>Stock recomendado:</strong> ${data.stock_required ?? 0}</p>
            ${data.forecast_message ? `<p class="forecast-note"><strong>Nota:</strong> ${data.forecast_message}</p>` : ""}
        </div>
        ${historyList ? `<h3>Historico reciente</h3><ul class="mini-history">${historyList}</ul>` : "<p>Sin historico suficiente.</p>"}
        <h3>Forecast visual de unidades</h3>
        <div class="chart-card forecast-chart-card">
            <canvas id="forecastAnnualChart" height="220"></canvas>
        </div>
        ${
            historyRows
                ? `<h3>Unidades vendidas por mes</h3>
                    <div class="table-wrap forecast-table">
                        <table>
                            <thead>
                                <tr>
                                    <th>Mes</th>
                                    <th>Unidades vendidas</th>
                                </tr>
                            </thead>
                            <tbody>${historyRows}</tbody>
                        </table>
                    </div>`
                : ""
        }
        ${
            annualRows
                ? `<h3>Forecast anual de stock</h3>
                    <div class="table-wrap forecast-table">
                        <table>
                            <thead>
                                <tr>
                                    <th>Mes</th>
                                    <th>Stock inicial mes</th>
                                    <th>Unidades previstas</th>
                                    <th>Stock a tener</th>
                                    <th>Reposicion sugerida</th>
                                    <th>Stock final mes</th>
                                </tr>
                            </thead>
                            <tbody>${annualRows}</tbody>
                        </table>
                    </div>`
                : ""
        }
    `;
    drawForecastChart(data.annual_forecast || []);
}

async function handleCreateProduct(event) {
    event.preventDefault();

    const payload = {
        name: $("productName").value.trim(),
        category: $("productCategory").value.trim(),
        description: $("productDescription").value.trim(),
        price: Number($("productPrice").value),
        stock_initial: Number($("productStock").value),
    };

    const sku = $("productSku").value.trim();
    if (sku) {
        payload.sku = sku;
    }

    await apiFetch("/api/products/", {
        method: "POST",
        body: JSON.stringify(payload),
    });

    ui.productForm.reset();
    showToast("Producto creado", "ok");
    await loadProducts();
}

async function handleCreateSale(event) {
    event.preventDefault();

    const productId = Number(ui.saleProduct.value);
    if (!productId) {
        showToast("Selecciona un producto", "error");
        return;
    }

    const payload = {
        product: productId,
        date: $("saleDate").value || todayIso(),
        units_sold: Number($("saleQuantity").value || 1),
        serial_number: $("saleSerial").value.trim() || generateSerial(),
        client_name: $("saleClient").value.trim(),
        total_price: Number($("saleTotal").value),
    };

    await apiFetch("/api/sales/", {
        method: "POST",
        body: JSON.stringify(payload),
    });

    ui.saleForm.reset();
    $("saleDate").value = todayIso();
    $("saleQuantity").value = "1";
    showToast("Venta creada", "ok");
    await loadSales();
    await loadAnalyticsSales();
    await loadProducts();
}

async function handleForecast() {
    const productId = ui.forecastProduct.value;
    if (!productId) {
        showToast("Selecciona un producto", "error");
        return;
    }

    const params = new URLSearchParams();
    if (ui.forecastStartMonth.value) {
        params.append("start_month", ui.forecastStartMonth.value);
    }
    const query = params.toString();
    const data = await apiFetch(`/api/products/${productId}/forecast/${query ? `?${query}` : ""}`);
    renderForecast(data);
}

async function bootstrap() {
    $("saleDate").value = todayIso();

    ui.productForm.addEventListener("submit", (event) => {
        handleCreateProduct(event).catch((err) => showToast(err.message, "error"));
    });

    ui.saleForm.addEventListener("submit", (event) => {
        handleCreateSale(event).catch((err) => showToast(err.message, "error"));
    });

    $("applyFilters").addEventListener("click", () => {
        state.salesPage = 1;
        loadSales().catch((err) => showToast(err.message, "error"));
    });

    $("clearFilters").addEventListener("click", () => {
        $("filterSaleId").value = "";
        ui.filterProduct.value = "";
        $("filterClient").value = "";
        $("filterDate").value = "";
        state.salesPage = 1;
        loadSales().catch((err) => showToast(err.message, "error"));
    });

    ui.productsTableBody.addEventListener("click", (event) => {
        const button = event.target.closest(".restock-btn");
        if (!button) {
            return;
        }
        handleRestock(button.dataset.productId).catch((err) => showToast(err.message, "error"));
    });

    ui.productCategoryFilter.addEventListener("change", () => {
        state.productCategoryFilter = ui.productCategoryFilter.value;
        state.productsPage = 1;
        renderProducts();
    });

    ui.dashboardProduct.addEventListener("change", () => {
        state.dashboardProductId = ui.dashboardProduct.value;
        renderDashboardVisuals();
    });

    ui.productsPrev.addEventListener("click", () => {
        if (state.productsPage <= 1) {
            return;
        }
        state.productsPage -= 1;
        renderProducts();
    });

    ui.productsNext.addEventListener("click", () => {
        const totalPages = Math.max(1, Math.ceil(filteredProducts().length / state.productsPageSize));
        if (state.productsPage >= totalPages) {
            return;
        }
        state.productsPage += 1;
        renderProducts();
    });

    ui.salesPrev.addEventListener("click", () => {
        if (!state.salesPrevious || state.salesPage <= 1) {
            return;
        }
        state.salesPage -= 1;
        loadSales().catch((err) => showToast(err.message, "error"));
    });

    ui.salesNext.addEventListener("click", () => {
        if (!state.salesNext) {
            return;
        }
        state.salesPage += 1;
        loadSales().catch((err) => showToast(err.message, "error"));
    });

    ui.forecastBtn.addEventListener("click", () => {
        handleForecast().catch((err) => showToast(err.message, "error"));
    });

    window.addEventListener("resize", () => {
        window.clearTimeout(renderDashboardVisuals.resizeTimer);
        renderDashboardVisuals.resizeTimer = window.setTimeout(renderDashboardVisuals, 150);
    });

    try {
        await loadProducts();
        await Promise.all([loadSales(), loadAnalyticsSales()]);
    } catch (err) {
        showToast(err.message, "error");
    }
}

bootstrap();
