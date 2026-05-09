const $ = (id) => document.getElementById(id);

const state = {
    products: [],
    sales: [],
    salesPage: 1,
    salesPageSize: 50,
    salesCount: 0,
    salesNext: null,
    salesPrevious: null,
};

const ui = {
    productForm: $("productForm"),
    saleForm: $("saleForm"),
    productsTableBody: $("productsTableBody"),
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
    ui.statSales.textContent = String(state.salesCount || state.sales.length);
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
    ui.filterProduct.innerHTML = '<option value="">Todos los productos</option>' + options;
}

function renderProducts() {
    if (!state.products.length) {
        ui.productsTableBody.innerHTML = '<tr><td colspan="10" class="empty">Sin productos todavia.</td></tr>';
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
                    <td>${p.stock_initial ?? 0}</td>
                    <td>${p.stock_received_total ?? 0}</td>
                    <td>${p.units_sold_total ?? 0}</td>
                    <td class="${warningClass}">${p.stock}</td>
                    <td>${p.stock_min}</td>
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
    renderProducts();
    setProductSelectOptions();
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
        <p><strong>SKU:</strong> ${data.sku || "-"}</p>
        <p><strong>Modelo:</strong> ${data.forecast_model || "-"}</p>
        ${data.forecast_message ? `<p><strong>Nota:</strong> ${data.forecast_message}</p>` : ""}
        <p><strong>Stock recomendado:</strong> ${data.stock_required ?? 0}</p>
        ${historyList ? `<p><strong>Historico (ultimos meses)</strong></p><ul class="mini-history">${historyList}</ul>` : "<p>Sin historico suficiente.</p>"}
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
}

async function handleCreateProduct(event) {
    event.preventDefault();

    const payload = {
        name: $("productName").value.trim(),
        category: $("productCategory").value.trim(),
        description: $("productDescription").value.trim(),
        price: Number($("productPrice").value),
        stock_initial: Number($("productStock").value),
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

    try {
        await Promise.all([loadProducts(), loadSales()]);
    } catch (err) {
        showToast(err.message, "error");
    }
}

bootstrap();
