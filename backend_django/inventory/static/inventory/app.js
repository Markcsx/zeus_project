const $ = (id) => document.getElementById(id);

const state = {
    products: [],
    sales: [],
};

const ui = {
    productForm: $("productForm"),
    saleForm: $("saleForm"),
    productsTableBody: $("productsTableBody"),
    salesTableBody: $("salesTableBody"),
    saleProduct: $("saleProduct"),
    forecastProduct: $("forecastProduct"),
    forecastBtn: $("forecastBtn"),
    forecastResult: $("forecastResult"),
    statProducts: $("statProducts"),
    statSales: $("statSales"),
    statRisk: $("statRisk"),
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

function updateStats() {
    ui.statProducts.textContent = String(state.products.length);
    ui.statSales.textContent = String(state.sales.length);
    const risk = state.products.filter((p) => Number(p.stock) < Number(p.stock_min)).length;
    ui.statRisk.textContent = String(risk);
}

function setProductSelectOptions() {
    const options = state.products
        .map((p) => `<option value="${p.id}">${p.sku} - ${p.name}</option>`)
        .join("");

    const placeholder = '<option value="">Selecciona producto</option>';
    ui.saleProduct.innerHTML = placeholder + options;
    ui.forecastProduct.innerHTML = placeholder + options;
}

function renderProducts() {
    if (!state.products.length) {
        ui.productsTableBody.innerHTML = '<tr><td colspan="6" class="empty">Sin productos todavia.</td></tr>';
        updateStats();
        return;
    }

    ui.productsTableBody.innerHTML = state.products
        .map((p) => {
            const warningClass = Number(p.stock) < Number(p.stock_min) ? "stock-alert" : "";
            return `
                <tr>
                    <td>${p.sku || "-"}</td>
                    <td>${p.name || "-"}</td>
                    <td>${p.category || "-"}</td>
                    <td>${money(p.price)}</td>
                    <td class="${warningClass}">${p.stock}</td>
                    <td>${p.stock_min}</td>
                </tr>
            `;
        })
        .join("");

    updateStats();
}

function renderSales() {
    if (!state.sales.length) {
        ui.salesTableBody.innerHTML = '<tr><td colspan="6" class="empty">No hay ventas para este filtro.</td></tr>';
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
                    <td>${money(s.total_price)}</td>
                </tr>
            `,
        )
        .join("");

    updateStats();
}

async function loadProducts() {
    const data = await apiFetch("/api/products/");
    state.products = Array.isArray(data) ? data : data.results || [];
    renderProducts();
    setProductSelectOptions();
}

function currentSalesFilterQuery() {
    const params = new URLSearchParams();

    const id = $("filterSaleId").value.trim();
    const client = $("filterClient").value.trim();
    const date = $("filterDate").value;

    if (id) {
        params.append("id", id);
    }
    if (client) {
        params.append("client_name", client);
    }
    if (date) {
        params.append("date", date);
    }

    const query = params.toString();
    return query ? `?${query}` : "";
}

async function loadSales() {
    const data = await apiFetch(`/api/sales/${currentSalesFilterQuery()}`);
    state.sales = Array.isArray(data) ? data : data.results || [];
    renderSales();
}

function generateSerial() {
    return `WEB-${Date.now().toString().slice(-8)}`;
}

function renderForecast(data) {
    const historyList = (data.history || [])
        .slice(-6)
        .map((h) => `<li>${h.month}: ${h.total_units.toFixed(1)} unidades</li>`)
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
        <p><strong>SKU:</strong> ${data.sku || "-"}</p>
        <p><strong>Stock recomendado:</strong> ${data.stock_required ?? 0}</p>
        ${historyList ? `<p><strong>Historico (ultimos meses)</strong></p><ul class="mini-history">${historyList}</ul>` : "<p>Sin historico suficiente.</p>"}
    `;
}

async function handleCreateProduct(event) {
    event.preventDefault();

    const payload = {
        name: $("productName").value.trim(),
        category: $("productCategory").value.trim(),
        description: $("productDescription").value.trim(),
        price: Number($("productPrice").value),
        stock: Number($("productStock").value),
        stock_min: Number($("productStockMin").value),
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
    showToast("Venta creada", "ok");
    await loadSales();
}

async function handleForecast() {
    const productId = ui.forecastProduct.value;
    if (!productId) {
        showToast("Selecciona un producto", "error");
        return;
    }

    const data = await apiFetch(`/api/products/${productId}/forecast/`);
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
        loadSales().catch((err) => showToast(err.message, "error"));
    });

    $("clearFilters").addEventListener("click", () => {
        $("filterSaleId").value = "";
        $("filterClient").value = "";
        $("filterDate").value = "";
        loadSales().catch((err) => showToast(err.message, "error"));
    });

    ui.forecastBtn.addEventListener("click", () => {
        handleForecast().catch((err) => showToast(err.message, "error"));
    });

    try {
        await Promise.all([loadProducts(), loadSales()]);
    } catch (err) {
        showToast(err.message, "error");
    }
}

bootstrap();
