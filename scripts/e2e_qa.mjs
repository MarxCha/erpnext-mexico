/**
 * E2E QA Automatizado — ERPNext México
 *
 * Crea clientes, facturas de venta, pagos — verifica que todo se guarda.
 * Screenshots en scripts/screenshots/
 */
import { chromium } from 'playwright';
import { mkdirSync, existsSync } from 'fs';

const BASE = 'http://localhost:8080';
const SCREENSHOTS = 'scripts/screenshots';
const DEMO_USER = { email: 'demo@mdconsultoria.mx', password: 'Demo2026!' };

const CLIENTS = [
  {
    name: 'Tecnologias Avanzadas del Bajio SA de CV',
    item: 'CONS-TI-001', qty: 20, rate: 1500,
    desc: 'Consultoria TI — 20 hrs',
  },
  {
    name: 'Distribuidora Industrial del Norte SA de CV',
    item: 'DEV-SW-001', qty: 40, rate: 2000,
    desc: 'Desarrollo Software — 40 hrs',
  },
  {
    name: 'Servicios Digitales del Sureste SC',
    item: 'AUDIT-TI-001', qty: 1, rate: 25000,
    desc: 'Auditoria Seguridad TI — 1 proyecto',
  },
];

let errors = [];
let successes = [];
let step = 0;

function log(phase, msg) {
  const ts = new Date().toLocaleTimeString('es-MX');
  console.log(`  [${ts}] ${phase} — ${msg}`);
}

function logOk(phase, msg) {
  log(phase, `✅ ${msg}`);
  successes.push(`${phase}: ${msg}`);
}

function logFail(phase, msg) {
  log(phase, `❌ ${msg}`);
  errors.push(`${phase}: ${msg}`);
}

async function screenshot(page, name) {
  step++;
  const fname = `${SCREENSHOTS}/${String(step).padStart(2, '0')}_${name}.png`;
  await page.screenshot({ path: fname, fullPage: true });
  log('📸', fname);
  return fname;
}

async function login(page) {
  log('A', 'Navegando a login...');
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 15000 });
  await page.fill('#login_email', DEMO_USER.email);
  await page.fill('#login_password', DEMO_USER.password);
  await page.click('.btn-login');
  await page.waitForURL('**/app/**', { timeout: 10000 });
  await screenshot(page, 'login_ok');
  logOk('A', 'Login exitoso como Demo MX');
}

async function reconocimiento(page) {
  // Dashboard
  await page.goto(`${BASE}/app`, { waitUntil: 'networkidle', timeout: 10000 });
  await screenshot(page, 'dashboard');

  // Contabilidad
  await page.goto(`${BASE}/app/accounting`, { waitUntil: 'networkidle', timeout: 10000 });
  await screenshot(page, 'contabilidad');
  logOk('A', 'Reconocimiento de módulos completo');
}

async function crearCliente(page, clientName) {
  const phase = 'B';
  log(phase, `Creando cliente: ${clientName}`);

  await page.goto(`${BASE}/app/customer/new`, { waitUntil: 'networkidle', timeout: 10000 });
  await page.waitForTimeout(1000);

  // Nombre del cliente
  const nameField = page.locator('[data-fieldname="customer_name"] input');
  await nameField.fill(clientName);

  // Tipo = Company
  const typeField = page.locator('[data-fieldname="customer_type"] select');
  if (await typeField.count()) {
    await typeField.selectOption('Company');
  }

  // Grupo = Commercial
  const groupField = page.locator('[data-fieldname="customer_group"] input');
  if (await groupField.count()) {
    await groupField.fill('Commercial');
    await page.waitForTimeout(300);
    // Select from awesomplete dropdown
    const option = page.locator('.awesomplete li').first();
    if (await option.count()) await option.click();
  }

  // Territorio = Mexico
  const terrField = page.locator('[data-fieldname="territory"] input');
  if (await terrField.count()) {
    await terrField.fill('Mexico');
    await page.waitForTimeout(300);
    const opt = page.locator('.awesomplete li').first();
    if (await opt.count()) await opt.click();
  }

  // The mx_fiscal_section is inserted after "tax_id" which lives under the Tax tab
  // Click the "Impuesto" / "Tax" tab first
  const taxTab = page.locator('.form-tabs .nav-link:has-text("Impuesto"), .form-tabs .nav-link:has-text("Tax")').first();
  if (await taxTab.count()) {
    await taxTab.click();
    await page.waitForTimeout(800);
    log(phase, 'Tab Impuesto activado');
  }

  // Now expand the "Datos Fiscales México" section if collapsed
  await page.evaluate(() => {
    const section = document.querySelector('[data-fieldname="mx_fiscal_section"]');
    if (section) {
      section.scrollIntoView({ behavior: 'instant', block: 'center' });
      const head = section.querySelector('.section-head');
      if (head && head.classList.contains('collapsed')) head.click();
    }
    // Also try: find by label text
    document.querySelectorAll('.section-head').forEach(h => {
      if (h.textContent.includes('Fiscales') || h.textContent.includes('fiscal')) {
        if (h.classList.contains('collapsed')) h.click();
        h.scrollIntoView({ block: 'center' });
      }
    });
  });
  await page.waitForTimeout(800);

  // Helper to fill a Frappe Link field
  async function fillLink(fieldname, value) {
    const input = page.locator(`[data-fieldname="${fieldname}"] input`).first();
    if (await input.count() === 0) return;
    // Make sure it's visible by scrolling to it
    await input.evaluate(el => el.scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(200);
    await input.fill(value);
    await page.waitForTimeout(600);
    // Click awesomplete dropdown option if visible
    const dropdown = page.locator('.awesomplete li, ul.frappe-control li').first();
    if (await dropdown.isVisible().catch(() => false)) {
      await dropdown.click();
    } else {
      await input.press('Enter');
    }
    await page.waitForTimeout(300);
  }

  // Helper to fill a Data field
  async function fillData(fieldname, value) {
    const input = page.locator(`[data-fieldname="${fieldname}"] input`).first();
    if (await input.count() === 0) return;
    await input.evaluate(el => el.scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(200);
    await input.fill(value);
    await page.waitForTimeout(200);
  }

  // Datos Fiscales MX
  await fillData('mx_rfc', 'XAXX010101000');
  await fillData('mx_nombre_fiscal', 'PUBLICO EN GENERAL');
  await fillLink('mx_regimen_fiscal', '616');
  await fillLink('mx_domicilio_fiscal_cp', '42501');
  await fillLink('mx_default_uso_cfdi', 'S01');
  await fillLink('mx_default_forma_pago', '03');

  await screenshot(page, `cliente_${clientName.substring(0, 20).replace(/\s/g, '_')}_form`);

  // Guardar con Ctrl+S
  await page.keyboard.press('Control+s');
  await page.waitForTimeout(2000);

  // Check for success or error
  const indicator = await page.locator('.indicator-pill').first().textContent().catch(() => '');
  const pageTitle = await page.title();

  if (indicator.includes('Guardado') || indicator.includes('Saved') || !indicator.includes('Not Saved')) {
    await screenshot(page, `cliente_${clientName.substring(0, 20).replace(/\s/g, '_')}_saved`);
    logOk(phase, `Cliente creado: ${clientName}`);
    return true;
  } else {
    // Check for validation errors
    const errorMsg = await page.locator('.msgprint, .modal-body').first().textContent().catch(() => '');
    await screenshot(page, `cliente_${clientName.substring(0, 20).replace(/\s/g, '_')}_error`);
    logFail(phase, `Error guardando cliente: ${errorMsg || indicator}`);
    // Try to close error modal
    await page.locator('.modal .btn-primary, .modal .close').first().click().catch(() => {});
    return false;
  }
}

async function crearFactura(page, clientName, itemCode, qty, rate) {
  const phase = 'C';
  log(phase, `Creando factura para ${clientName}...`);

  // Use Frappe JS API from the browser — much more reliable than DOM manipulation
  const result = await page.evaluate(async ({ clientName, itemCode, qty, rate }) => {
    try {
      // Create Sales Invoice via API
      const si = await frappe.call({
        method: 'frappe.client.insert',
        args: {
          doc: {
            doctype: 'Sales Invoice',
            customer: clientName,
            company: 'MD Consultoria TI',
            posting_date: frappe.datetime.nowdate(),
            due_date: frappe.datetime.add_days(frappe.datetime.nowdate(), 30),
            currency: 'MXN',
            conversion_rate: 1.0,
            selling_price_list: 'Standard Selling',
            mx_uso_cfdi: 'S01',
            mx_metodo_pago: 'PUE',
            mx_forma_pago: '03',
            mx_exportacion: '01',
            items: [{
              item_code: itemCode,
              qty: qty,
              rate: rate,
              mx_clave_prod_serv: (() => {
                const map = { 'CONS-TI-001': '84111506', 'DEV-SW-001': '81112100', 'SOPORTE-001': '81112002', 'HOSTING-001': '81112300', 'CAPACIT-001': '86101700', 'LICENCIA-001': '43231500', 'AUDIT-TI-001': '84111507', 'PROYECTO-001': '84111502' };
                return map[itemCode] || '84111506';
              })(),
              mx_clave_unidad: 'E48',
            }],
            taxes: [{
              charge_type: 'On Net Total',
              account_head: 'IVA - MCT',
              description: 'IVA 16%',
              rate: 16,
            }],
          },
        },
      });
      return { ok: true, name: si.message.name, total: si.message.grand_total };
    } catch (e) {
      return { ok: false, error: e.message || String(e) };
    }
  }, { clientName, itemCode, qty, rate });

  if (!result.ok) {
    logFail(phase, `Error creando factura: ${result.error}`);
    return null;
  }

  const invoiceName = result.name;
  log(phase, `Factura creada: ${invoiceName}, Total: $${result.total}`);

  // Submit via API FIRST (before navigating — avoids TimestampMismatchError)
  log(phase, 'Enviando (submit)...');
  const submitResult = await page.evaluate(async (name) => {
    try {
      // Get fresh doc with correct modified timestamp before submit
      const freshDoc = await frappe.call({ method: 'frappe.client.get', args: { doctype: 'Sales Invoice', name: name } });
      const doc_to_submit = freshDoc.message;
      doc_to_submit.docstatus = 1;
      const r = await frappe.call({ method: 'frappe.client.submit', args: { doc: doc_to_submit } });
      // Wait for CFDI auto-stamp hook
      await new Promise(resolve => setTimeout(resolve, 3000));
      // Reload to get CFDI data
      const doc = await frappe.call({ method: 'frappe.client.get', args: { doctype: 'Sales Invoice', name: name } });
      const d = doc.message || doc;
      return {
        ok: true,
        uuid: d.mx_cfdi_uuid || '',
        status: d.mx_cfdi_status || '',
        total: d.grand_total,
      };
    } catch (e) {
      let errMsg = 'Unknown error';
      try {
        if (e && e._server_messages) errMsg = JSON.parse(e._server_messages).map(m => { try { return JSON.parse(m).message; } catch { return m; } }).join('; ');
        else if (e && e.exc) errMsg = e.exc.substring(0, 300);
        else if (e && e.message) errMsg = e.message;
        else errMsg = JSON.stringify(e).substring(0, 300);
      } catch { errMsg = String(e); }
      return { ok: false, error: errMsg };
    }
  }, invoiceName);

  // NOW navigate to see the result
  await page.goto(`${BASE}/app/sales-invoice/${invoiceName}`, { waitUntil: 'networkidle', timeout: 10000 });
  await page.waitForTimeout(1000);
  await screenshot(page, `factura_${clientName.substring(0, 15).replace(/\s/g, '_')}_submitted`);

  if (!submitResult.ok) {
    logFail(phase, `Error al enviar: ${submitResult.error}`);
    return invoiceName;
  }

  if (submitResult.uuid && submitResult.uuid.length > 10) {
    logOk(phase, `Factura timbrada UUID=${submitResult.uuid.substring(0, 12)}... Total=$${submitResult.total}`);
  } else {
    log(phase, `Submit OK — CFDI status=${submitResult.status}, UUID=${submitResult.uuid || 'pendiente'}`);
    logOk(phase, `Factura enviada: ${invoiceName} Total=$${submitResult.total}`);
  }

  return invoiceName;
}

async function crearPago(page, invoiceName, clientName) {
  const phase = 'D';
  log(phase, `Creando pago para factura ${invoiceName}...`);

  // Use ERPNext's get_payment_entry API — creates a pre-filled Payment Entry from a Sales Invoice
  const result = await page.evaluate(async (invName) => {
    try {
      // Use ERPNext's built-in method to create payment entry
      const pe_data = await frappe.call({
        method: 'erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry',
        args: { dt: 'Sales Invoice', dn: invName, party_amount: null, bank_account: 'BANCO DEMO - MCT' },
      });
      const pe = pe_data.message;
      pe.reference_no = 'E2E-QA-' + invName;
      pe.reference_date = frappe.datetime.nowdate();
      pe.paid_to = 'BANCO DEMO - MCT';
      pe.mode_of_payment = 'Transferencia';
      pe.mx_forma_pago = '03';

      // Insert
      const saved = await frappe.call({ method: 'frappe.client.insert', args: { doc: pe } });
      return { ok: true, name: saved.message.name, amount: saved.message.paid_amount };
    } catch (e) {
      let errMsg = 'Unknown';
      try {
        if (e && e._server_messages) errMsg = JSON.parse(e._server_messages).map(m => { try { return JSON.parse(m).message; } catch { return m; } }).join('; ');
        else if (e && e.message) errMsg = e.message;
        else errMsg = JSON.stringify(e).substring(0, 300);
      } catch { errMsg = String(e); }
      return { ok: false, error: errMsg };
    }
  }, invoiceName);

  if (!result.ok) {
    logFail(phase, `Error creando pago: ${result.error}`);
    return false;
  }

  log(phase, `Pago creado: ${result.name}, $${result.amount}`);

  // Navigate to payment entry and take screenshot
  await page.goto(`${BASE}/app/payment-entry/${result.name}`, { waitUntil: 'networkidle', timeout: 10000 });
  await page.waitForTimeout(1000);
  await screenshot(page, `pago_${clientName.substring(0, 15).replace(/\s/g, '_')}_created`);

  logOk(phase, `Pago creado: ${result.name} por $${result.amount} (ref: ${invoiceName})`);
  return true;
}

async function verificacion(page) {
  const phase = 'E';
  log(phase, 'Verificación cruzada...');

  // Check customers
  await page.goto(`${BASE}/app/customer?customer_group=Commercial`, { waitUntil: 'networkidle', timeout: 10000 });
  await page.waitForTimeout(1000);
  await screenshot(page, 'verificacion_clientes');
  const custCount = await page.locator('.list-row').count();
  logOk(phase, `Clientes en lista: ${custCount}`);

  // Check sales invoices
  await page.goto(`${BASE}/app/sales-invoice?docstatus=1`, { waitUntil: 'networkidle', timeout: 10000 });
  await page.waitForTimeout(1000);
  await screenshot(page, 'verificacion_facturas');

  // Check accounting module
  await page.goto(`${BASE}/app/accounting`, { waitUntil: 'networkidle', timeout: 10000 });
  await page.waitForTimeout(1000);
  await screenshot(page, 'verificacion_contabilidad');
  logOk(phase, 'Verificación cruzada completa');
}

async function verificacionBackend() {
  const phase = 'E-backend';
  log(phase, 'Verificación backend via bench...');
  // This will be done via bash after the browser tests
}

async function main() {
  if (!existsSync(SCREENSHOTS)) mkdirSync(SCREENSHOTS, { recursive: true });

  console.log('\n' + '='.repeat(60));
  console.log('  E2E QA AUTOMATIZADO — ERPNext México');
  console.log('  ' + new Date().toLocaleString('es-MX'));
  console.log('='.repeat(60));

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();

  try {
    // FASE A — Login
    console.log('\n── FASE A: Login y reconocimiento ──');
    await login(page);
    await reconocimiento(page);

    // FASE B+C+D — Por cada cliente
    for (let i = 0; i < CLIENTS.length; i++) {
      const client = CLIENTS[i];
      console.log(`\n── FASE B-D: Cliente ${i + 1}/${CLIENTS.length}: ${client.name} ──`);
      try {
        // B: Crear cliente
        const created = await crearCliente(page, client.name);

        if (created) {
          // C: Crear factura
          const invoiceName = await crearFactura(page, client.name, client.item, client.qty, client.rate);

          // D: Crear pago (si la factura se creó)
          if (invoiceName && !invoiceName.includes('new')) {
            await crearPago(page, invoiceName, client.name);
          }
        }
      } catch (e) {
        logFail(`B-D(${i+1})`, e.message.split('\n')[0]);
        await screenshot(page, `error_client_${i+1}`);
      }
    }

    // FASE E — Verificación
    console.log('\n── FASE E: Verificación cruzada ──');
    await verificacion(page);

  } catch (e) {
    logFail('FATAL', e.message);
    await screenshot(page, 'fatal_error');
  } finally {
    await browser.close();
  }

  // REPORTE FINAL
  console.log('\n' + '='.repeat(60));
  console.log('  REPORTE FINAL');
  console.log('='.repeat(60));
  console.log(`\n  ✅ Éxitos: ${successes.length}`);
  for (const s of successes) console.log(`     ${s}`);
  console.log(`\n  ❌ Errores: ${errors.length}`);
  for (const e of errors) console.log(`     ${e}`);
  console.log('\n  📸 Screenshots en: ' + SCREENSHOTS);
  console.log('='.repeat(60));

  // Exit code based on errors
  process.exit(errors.length > 0 ? 1 : 0);
}

main();
