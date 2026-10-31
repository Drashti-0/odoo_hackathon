(function () {
    'use strict';

    const STORAGE_KEY = 'brightloop.subscription-demo.v1';
    const EMAIL_KEY = 'brightloop.subscription-demo.email';
    const allowedScreens = {
        admin: ['admin_dashboard', 'customer_dashboard', 'customer_portal', 'financial_reports', 'subscription_mgmt', 'invoice_mgmt', 'payment_mgmt', 'discount_mgmt', 'product_mgmt', 'plan_mgmt', 'customer_mgmt', 'user_mgmt', 'auth_screen'],
        staff: ['subscription_mgmt', 'invoice_mgmt', 'payment_mgmt', 'customer_mgmt'],
        customer: ['customer_dashboard', 'customer_portal', 'subscription_mgmt', 'invoice_mgmt']
    };
    const titles = {
        admin_dashboard: 'Executive Dashboard — Demo Data',
        customer_dashboard: 'Customer Dashboard',
        customer_portal: 'Customer Portal — Demo Data',
        financial_reports: 'Demo Financial Analytics',
        subscription_mgmt: 'Subscription Contracts',
        invoice_mgmt: 'Demo Invoices',
        payment_mgmt: 'Simulated Payments',
        discount_mgmt: 'Demo Discounts & Coupons',
        product_mgmt: 'Demo Product Catalog',
        plan_mgmt: 'Demo Subscription Plans',
        customer_mgmt: 'Demo Customer Directory',
        user_mgmt: 'Demo User Registry',
        auth_screen: 'Demo Security Information'
    };
    const demoCredentials = {
        'admin@brightloop.com': { password: 'admin123', role: 'admin', name: 'Brightloop Admin' },
        'staff@brightloop.com': { password: 'staff123', role: 'staff', name: 'Brightloop Staff' },
        'alice@customer.com': { password: 'alice123', role: 'customer', name: 'Alice Customer', customerId: 'cust-alice' }
    };
    const temporarySignupCredentials = Object.create(null);
    let data;
    let currentRole = null;
    let currentUser = null;
    let mrrChart = null;
    let planChart = null;
    let activeStatusFilter = 'All';

    function initialData() {
        return {
            version: 1,
            products: [
                { id: 'prod-hosting', name: 'Cloud ERP Dedicated Hosting', price: 1560, description: 'High-availability hosting and backups.', custom: false },
                { id: 'prod-support', name: '24/7 Priority Support Tier', price: 300, description: 'Priority technical support.', custom: false },
                { id: 'prod-api', name: 'API Sync & Webhook Engine', price: 200, description: 'Integration and event streaming.', custom: false }
            ],
            plans: [
                { id: 'plan-daily', name: 'Daily Sandbox', price: 10, cadence: 'day' },
                { id: 'plan-weekly', name: 'Weekly Starter', price: 50, cadence: 'week' },
                { id: 'plan-monthly', name: 'Monthly Professional', price: 150, cadence: 'month' },
                { id: 'plan-enterprise', name: 'Enterprise Monthly SaaS', price: 3320, cadence: 'month' },
                { id: 'plan-annual', name: 'Annual Enterprise', price: 1500, cadence: 'year' }
            ],
            customers: [
                { id: 'cust-alice', name: 'Alice Customer', email: 'alice@customer.com', company: 'Alice Corp Ltd', phone: '' },
                { id: 'cust-bob', name: 'Bob Customer', email: 'bob@customer.com', company: 'Bob Solutions LLC', phone: '' },
                { id: 'cust-global', name: 'Global Tech Lead', email: 'billing@globaltech.com', company: 'Global Tech Industries', phone: '' }
            ],
            subscriptions: [
                { id: 'SUB-2026-001', customerId: 'cust-alice', planId: 'plan-enterprise', planName: 'Enterprise Monthly SaaS', cadence: 'month', amount: 2656, discountAmount: 664, renewals: 0, status: 'Active', couponCode: 'LAUNCH20', period: '2026-10' },
                { id: 'SUB-2026-002', customerId: 'cust-bob', planId: 'plan-annual', planName: 'Annual Enterprise', cadence: 'year', amount: 1500, status: 'Active', couponCode: '', period: '2026-10' },
                { id: 'SUB-2026-003', customerId: 'cust-global', planId: 'plan-monthly', planName: 'Monthly Pro Tier', cadence: 'month', amount: 450, status: 'Paused', couponCode: '', period: '2026-10' },
                { id: 'SUB-2026-004', customerId: 'cust-global', planId: 'plan-daily', planName: 'Daily Sandbox Tier', cadence: 'day', amount: 10, status: 'Draft', couponCode: '', period: '2026-10' }
            ],
            coupons: [
                { id: 'coupon-launch20', code: 'LAUNCH20', name: 'Launch Special 20% Off', type: 'percent', value: 20, minAmount: 50, maxUses: 100, uses: 1, expires: '2026-12-31', active: true },
                { id: 'coupon-welcome50', code: 'WELCOME50', name: 'Welcome Fixed $50 Off', type: 'fixed', value: 50, minAmount: 200, maxUses: 50, uses: 0, expires: '2026-11-30', active: true }
            ],
            invoices: [
                { id: 'INV-2026-001', customerId: 'cust-alice', subscriptionId: 'SUB-2026-001', period: '2026-10', date: '2026-10-31', total: 2656, paid: 2656 },
                { id: 'INV-2026-002', customerId: 'cust-bob', subscriptionId: 'SUB-2026-002', period: '2026-11', date: '2026-11-01', total: 1500, paid: 500 },
                { id: 'INV-2026-003', customerId: 'cust-global', subscriptionId: 'SUB-2026-003', period: '2026-11', date: '2026-11-01', total: 450, paid: 0 }
            ],
            payments: [
                { id: 'TXN-CC-1001', invoiceId: 'INV-2026-001', amount: 1000, method: 'Credit Card (Demo)', date: '2026-10-31' },
                { id: 'TXN-DEMO-1002', invoiceId: 'INV-2026-001', amount: 1656, method: 'Bank Wire (Demo)', date: '2026-10-31' },
                { id: 'TXN-WIRE-1003', invoiceId: 'INV-2026-002', amount: 500, method: 'Bank Wire (Demo)', date: '2026-10-30' }
            ]
        };
    }

    function persist() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
            return true;
        } catch (error) {
            console.error('Unable to save Brightloop demo data to localStorage.', error);
            showToast('Could not save demo changes', 'Browser storage is unavailable or full. Changes may not survive a refresh.', 'warning');
            return false;
        }
    }

    function loadData() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return initialData();
            const parsed = JSON.parse(raw);
            const required = ['products', 'plans', 'customers', 'subscriptions', 'coupons', 'invoices', 'payments'];
            if (parsed.version !== 1 || required.some(key => !Array.isArray(parsed[key]))) {
                throw new Error('Stored demo data has an unsupported shape.');
            }
            return parsed;
        } catch (error) {
            console.error('Stored Brightloop demo data could not be loaded.', error);
            showToast('Demo data was reset', 'The saved browser data was invalid. A fresh sample dataset is in use.', 'warning');
            return initialData();
        }
    }

    function escapeHtml(value) {
        return String(value == null ? '' : value).replace(/[&<>"']/g, char => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        })[char]);
    }

    function money(value) {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(value) || 0);
    }

    function localDate() {
        const now = new Date();
        return now.toISOString().slice(0, 10);
    }

    function currentPeriod() {
        return localDate().slice(0, 7);
    }

    function customerFor(id) {
        return data.customers.find(customer => customer.id === id);
    }

    function invoiceFor(id) {
        return data.invoices.find(invoice => invoice.id === id);
    }

    function subscriptionFor(id) {
        return data.subscriptions.find(subscription => subscription.id === id);
    }

    function residual(invoice) {
        return Math.max(0, Number(invoice.total) - Number(invoice.paid));
    }

    function statusMarkup(status) {
        const styles = {
            Active: 'bg-emerald-100 text-emerald-800',
            Paused: 'bg-amber-100 text-amber-800',
            Draft: 'bg-slate-100 text-slate-700',
            Closed: 'bg-rose-100 text-rose-800'
        };
        return '<span class="px-2.5 py-1 rounded-full font-bold ' + (styles[status] || styles.Draft) + '">' + escapeHtml(status) + '</span>';
    }

    function ensureSignedIn() {
        if (!currentRole || !currentUser) {
            showAuthScreen('login');
            showToast('Sign in required', 'Please sign in with a demo account to continue.', 'warning');
            return false;
        }
        return true;
    }

    function canAccess(screenId) {
        return Boolean(currentRole && allowedScreens[currentRole].includes(screenId));
    }

    function visibleRecords(items, customerIdKey) {
        return currentRole === 'customer'
            ? items.filter(item => item[customerIdKey] === currentUser.customerId)
            : items;
    }

    function showAuthScreen(type) {
        const login = document.getElementById('screen_login');
        const signup = document.getElementById('screen_signup');
        const shell = document.getElementById('app_shell');
        const auth = document.getElementById('auth_container');
        if (shell) shell.classList.add('hidden');
        if (auth) auth.classList.remove('hidden');
        if (login) login.classList.toggle('hidden', type === 'signup');
        if (signup) signup.classList.toggle('hidden', type !== 'signup');
        hideLoginError();
        hideSignupError();
    }

    function showLoginError(message) {
        const banner = document.getElementById('login_error');
        const text = document.getElementById('login_error_text');
        if (!banner || !text) return;
        text.textContent = message;
        banner.classList.remove('hidden');
        banner.classList.add('flex');
    }

    function hideLoginError() {
        const banner = document.getElementById('login_error');
        if (banner) {
            banner.classList.add('hidden');
            banner.classList.remove('flex');
        }
    }

    function showSignupError(message) {
        const banner = document.getElementById('signup_error');
        if (!banner) return;
        banner.textContent = message;
        banner.classList.remove('hidden');
    }

    function hideSignupError() {
        const banner = document.getElementById('signup_error');
        if (banner) {
            banner.textContent = '';
            banner.classList.add('hidden');
        }
    }

    function quickFillLogin(role) {
        const account = Object.entries(demoCredentials).find(([, user]) => user.role === role);
        if (!account) return;
        document.getElementById('login_email').value = account[0];
        document.getElementById('login_password').value = account[1].password;
        hideLoginError();
    }

    function handleLogin(event) {
        if (event) event.preventDefault();
        const email = document.getElementById('login_email').value.trim().toLowerCase();
        const password = document.getElementById('login_password').value;
        if (!email || !password) {
            showLoginError('Enter both your email address and password.');
            return;
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            showLoginError('Enter a valid email address, such as name@example.com.');
            return;
        }
        let account = demoCredentials[email];
        if (account && account.password !== password) account = null;
        if (!account && temporarySignupCredentials[email] === password) {
            const customer = data.customers.find(item => item.email.toLowerCase() === email);
            account = customer ? { role: 'customer', name: customer.name, customerId: customer.id } : null;
            delete temporarySignupCredentials[email];
        }
        if (!account) {
            showLoginError('Email or password is incorrect. Use a demo account or register in this browser session.');
            return;
        }

        hideLoginError();
        currentRole = account.role;
        currentUser = {
            role: account.role,
            name: account.name,
            email,
            customerId: account.customerId || (account.role === 'customer' ? 'cust-alice' : null)
        };
        if (document.getElementById('remember_session').checked) {
            try {
                localStorage.setItem(EMAIL_KEY, email);
            } catch (error) {
                console.warn('Remember email is unavailable in this browser.', error);
            }
        } else {
            try {
                localStorage.removeItem(EMAIL_KEY);
            } catch (error) {
                console.warn('Could not clear the remembered demo email.', error);
            }
        }
        document.getElementById('login_password').value = '';
        document.getElementById('auth_container').classList.add('hidden');
        document.getElementById('app_shell').classList.remove('hidden');
        updateIdentity();
        const landing = account.role === 'admin' ? 'admin_dashboard' : account.role === 'staff' ? 'subscription_mgmt' : 'customer_dashboard';
        showScreen(landing);
        initCharts();
        showToast('Welcome', 'Signed in to the local ' + account.role + ' demo. This is not Odoo authentication.', 'success');
    }

    function handleSignup(event) {
        if (event) event.preventDefault();
        const name = document.getElementById('reg_name').value.trim();
        const email = document.getElementById('reg_email').value.trim().toLowerCase();
        const company = document.getElementById('reg_company').value.trim();
        const phone = document.getElementById('reg_phone').value.trim();
        const password = document.getElementById('reg_password').value;
        const confirmation = document.getElementById('reg_confirm_password').value;
        if (!name || !email || !password || !confirmation) return showSignupError('Complete all required fields.');
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return showSignupError('Enter a valid email address.');
        if (data.customers.some(customer => customer.email.toLowerCase() === email)) return showSignupError('An account with this email is already registered in this demo.');
        if (password.length < 8 || !/[A-Z]/.test(password) || !/[a-z]/.test(password) || !/[0-9]/.test(password) || !/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
            return showSignupError('Use at least 8 characters with uppercase, lowercase, a number, and a special symbol.');
        }
        if (password !== confirmation) return showSignupError('Passwords do not match.');
        if (!document.getElementById('reg_terms').checked) return showSignupError('Please accept the demo terms to continue.');

        const customer = {
            id: 'cust-' + Date.now().toString(36),
            name,
            email,
            company,
            phone
        };
        data.customers.push(customer);
        temporarySignupCredentials[email] = password;
        persist();
        document.getElementById('reg_password').value = '';
        document.getElementById('reg_confirm_password').value = '';
        document.getElementById('login_email').value = email;
        document.getElementById('login_password').value = '';
        hideSignupError();
        showAuthScreen('login');
        renderAll();
        showToast('Demo registration saved', 'Profile saved locally. Sign in now; password is kept only in memory until this page is refreshed. No Odoo account was created.', 'success');
    }

    function handleLogout() {
        currentRole = null;
        currentUser = null;
        document.getElementById('app_shell').classList.add('hidden');
        document.getElementById('auth_container').classList.remove('hidden');
        showAuthScreen('login');
        showToast('Signed out', 'You are back at the standalone demo sign-in screen.', 'info');
    }

    function updateIdentity() {
        const displayRole = currentRole === 'admin' ? 'Demo Administrator' : currentRole === 'staff' ? 'Demo Staff' : 'Demo Customer';
        document.getElementById('user_display_name').textContent = currentUser.name;
        document.getElementById('user_display_role').textContent = displayRole;
        document.getElementById('user_avatar').textContent = currentUser.name.split(/\s+/).map(part => part[0]).join('').slice(0, 2).toUpperCase();
        const roleBar = document.querySelector('#app_shell header .flex.items-center.bg-slate-100');
        if (roleBar) roleBar.classList.toggle('hidden', currentRole !== 'admin');
        document.querySelectorAll('.nav-item').forEach(link => {
            const target = link.id.replace(/^nav_/, '');
            link.classList.toggle('hidden', !canAccess(target));
        });
        const billing = document.querySelectorAll('button[onclick="triggerBillingCron()"]');
        billing.forEach(button => button.classList.toggle('hidden', currentRole === 'customer'));
    }

    function showScreen(screenId) {
        if (!ensureSignedIn()) return;
        if (!canAccess(screenId)) {
            showToast('Access restricted', 'This demo role cannot open that management screen.', 'warning');
            return;
        }
        document.querySelectorAll('.screen-view').forEach(screen => screen.classList.add('hidden'));
        const target = document.getElementById('screen_' + screenId);
        if (!target) {
            showToast('Screen unavailable', 'The requested screen was not found.', 'warning');
            return;
        }
        target.classList.remove('hidden');
        document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('nav-active'));
        const activeNav = document.getElementById('nav_' + screenId);
        if (activeNav) activeNav.classList.add('nav-active');
        document.getElementById('screen_title').textContent = titles[screenId] || 'Brightloop Demo';
        renderScreen(screenId);
        if (screenId === 'admin_dashboard' && mrrChart) mrrChart.resize();
    }

    function switchRole(role) {
        if (!currentRole || currentRole !== 'admin' || !['admin', 'staff', 'customer'].includes(role)) {
            showToast('Role switch unavailable', 'Only the administrator demo can switch personas. Sign out to select another demo account.', 'warning');
            return;
        }
        currentRole = role;
        if (role === 'admin') currentUser = { role, name: 'Brightloop Admin', email: 'admin@brightloop.com' };
        if (role === 'staff') currentUser = { role, name: 'Brightloop Staff', email: 'staff@brightloop.com' };
        if (role === 'customer') currentUser = { role, name: 'Alice Customer', email: 'alice@customer.com', customerId: 'cust-alice' };
        document.querySelectorAll('[id^="role_btn_"]').forEach(button => {
            button.className = 'px-2.5 py-1 rounded text-slate-600 hover:text-slate-900 transition-all';
        });
        const active = document.getElementById('role_btn_' + role);
        if (active) active.className = 'px-2.5 py-1 rounded bg-white text-brand-700 shadow-sm font-semibold transition-all';
        updateIdentity();
        showScreen(role === 'admin' ? 'admin_dashboard' : role === 'staff' ? 'subscription_mgmt' : 'customer_dashboard');
    }

    function renderSubscriptionRows() {
        const rows = visibleRecords(data.subscriptions, 'customerId').filter(subscription =>
            currentRole !== 'customer' || subscription.customerId === currentUser.customerId
        );
        const html = rows.length ? rows.map(subscription => {
            const customer = customerFor(subscription.customerId);
            const actions = currentRole === 'customer'
                ? (subscription.status === 'Active'
                    ? '<button onclick="toggleSubscriptionState(\'' + escapeHtml(subscription.id) + '\', \'Paused\')" class="px-2 py-1 bg-amber-50 text-amber-700 rounded">Pause</button>'
                    : subscription.status === 'Paused'
                        ? '<button onclick="toggleSubscriptionState(\'' + escapeHtml(subscription.id) + '\', \'Active\')" class="px-2 py-1 bg-emerald-50 text-emerald-700 rounded">Resume</button>'
                        : '<span class="text-slate-500">No customer action available</span>')
                : (subscription.status === 'Active'
                    ? '<button onclick="triggerManualInvoice(\'' + escapeHtml(subscription.id) + '\')" class="px-2 py-1 bg-brand-50 text-brand-700 rounded">Invoice</button> <button onclick="toggleSubscriptionState(\'' + escapeHtml(subscription.id) + '\', \'Paused\')" class="px-2 py-1 bg-amber-50 text-amber-700 rounded">Pause</button> <button onclick="toggleSubscriptionState(\'' + escapeHtml(subscription.id) + '\', \'Closed\')" class="px-2 py-1 bg-rose-50 text-rose-700 rounded">Close</button>'
                    : subscription.status === 'Paused'
                        ? '<button onclick="toggleSubscriptionState(\'' + escapeHtml(subscription.id) + '\', \'Active\')" class="px-2 py-1 bg-emerald-50 text-emerald-700 rounded">Resume</button>'
                        : subscription.status === 'Draft'
                            ? '<button onclick="toggleSubscriptionState(\'' + escapeHtml(subscription.id) + '\', \'Active\')" class="px-2 py-1 bg-indigo-50 text-indigo-700 rounded">Activate</button>'
                            : '<span class="text-slate-400">No actions</span>');
            const coupon = data.coupons.find(item => item.code === subscription.couponCode);
            return '<tr class="hover:bg-slate-50/60"><td class="py-3 px-4 font-mono font-bold text-brand-700">' + escapeHtml(subscription.id) + '</td>' +
                '<td class="py-3 px-4">' + escapeHtml(customer ? customer.name : 'Customer') + '</td><td class="py-3 px-4">' + escapeHtml(subscription.planName) + '</td>' +
                '<td class="py-3 px-4">' + escapeHtml(subscription.cadence) + '</td><td class="py-3 px-4">' + (coupon ? escapeHtml(coupon.code) : '—') + '</td>' +
                '<td class="py-3 px-4 font-bold">' + money(subscription.amount) + '</td><td class="py-3 px-4">' + statusMarkup(subscription.status) + '</td>' +
                '<td class="py-3 px-4 text-right space-x-1">' + actions + '</td></tr>';
        }).join('') : '<tr><td colspan="8" class="p-8 text-center text-slate-500">No subscriptions for this customer yet.</td></tr>';
        for (const id of ['full_sub_table_body', 'admin_sub_table_body']) {
            const body = document.getElementById(id);
            if (body) body.innerHTML = html;
        }
    }

    function renderCoupons() {
        const body = document.getElementById('coupon_table_body');
        if (!body) return;
        body.innerHTML = data.coupons.length ? data.coupons.map(coupon =>
            '<tr><td class="py-3 px-4 font-mono font-bold text-indigo-600">' + escapeHtml(coupon.code) + '</td>' +
            '<td class="py-3 px-4">' + escapeHtml(coupon.name) + '</td><td class="py-3 px-4">' + (coupon.type === 'percent' ? 'Percentage' : 'Fixed amount') + '</td>' +
            '<td class="py-3 px-4 font-bold">' + (coupon.type === 'percent' ? escapeHtml(coupon.value) + '%' : money(coupon.value)) + '</td>' +
            '<td class="py-3 px-4">' + coupon.uses + ' / ' + (coupon.maxUses || '∞') + '</td><td class="py-3 px-4">' + money(coupon.minAmount) + '</td>' +
            '<td class="py-3 px-4">' + escapeHtml(coupon.expires || 'No expiry') + '</td><td class="py-3 px-4 text-right">' +
            '<span class="px-2 py-1 rounded-full ' + (coupon.active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-500') + '">' + (coupon.active ? 'Active' : 'Inactive') + '</span></td></tr>'
        ).join('') : '<tr><td colspan="8" class="p-6 text-center text-slate-500">No coupons yet. Add one to apply it to a new demo subscription.</td></tr>';
    }

    function renderInvoices() {
        const body = document.getElementById('invoice_table_body');
        if (!body) return;
        const invoices = visibleRecords(data.invoices, 'customerId');
        body.innerHTML = invoices.length ? invoices.map(invoice => {
            const customer = customerFor(invoice.customerId);
            const balance = residual(invoice);
            const paidStatus = balance === 0 ? 'Fully Paid' : invoice.paid > 0 ? 'Partially Paid' : 'Unpaid';
            const statusClass = balance === 0 ? 'bg-emerald-100 text-emerald-800' : invoice.paid > 0 ? 'bg-amber-100 text-amber-800' : 'bg-rose-100 text-rose-800';
            return '<tr><td class="py-3 px-4 font-mono font-bold">' + escapeHtml(invoice.id) + '</td><td class="py-3 px-4">' + escapeHtml(customer ? customer.name : '') + '</td>' +
                '<td class="py-3 px-4 font-mono">' + escapeHtml(invoice.period) + '</td><td class="py-3 px-4 font-bold">' + money(invoice.total) + '</td>' +
                '<td class="py-3 px-4 text-emerald-700 font-bold">' + money(invoice.paid) + '</td><td class="py-3 px-4 font-mono">' + money(balance) + '</td>' +
                '<td class="py-3 px-4"><span class="px-2 py-1 rounded-full ' + statusClass + '">' + paidStatus + '</span></td><td class="py-3 px-4 text-right">' +
                (balance > 0 && currentRole !== 'customer' ? '<button onclick="openPaymentModal(\'' + escapeHtml(invoice.id) + '\')" class="px-2.5 py-1 bg-brand-50 text-brand-700 rounded">Record demo payment</button>' : '<button onclick="downloadDemoReceipt(\'' + escapeHtml(invoice.id) + '\')" class="px-2.5 py-1 bg-slate-100 rounded">Demo receipt</button>') +
                '</td></tr>';
        }).join('') : '<tr><td colspan="8" class="p-8 text-center text-slate-500">No invoices are available for this account.</td></tr>';

        const portalBody = document.getElementById('portal_invoice_table_body');
        if (portalBody) portalBody.innerHTML = invoices.length ? invoices.map(invoice =>
            '<tr><td class="py-3 px-4 font-mono font-bold">' + escapeHtml(invoice.id) + '</td><td class="py-3 px-4">' + escapeHtml(invoice.date) + '</td>' +
            '<td class="py-3 px-4 font-bold">' + money(invoice.total) + '</td><td class="py-3 px-4">' + (residual(invoice) === 0 ? 'Paid' : 'Balance due') + '</td>' +
            '<td class="py-3 px-4 text-right"><button onclick="downloadDemoReceipt(\'' + escapeHtml(invoice.id) + '\')" class="px-2 py-1 bg-slate-100 rounded">Download demo receipt</button></td></tr>'
        ).join('') : '<tr><td colspan="5" class="p-6 text-center text-slate-500">No demo invoices yet.</td></tr>';
    }

    function renderPayments() {
        const body = document.getElementById('payment_table_body');
        if (!body) return;
        const payments = currentRole === 'customer'
            ? data.payments.filter(payment => {
                const invoice = invoiceFor(payment.invoiceId);
                return invoice && invoice.customerId === currentUser.customerId;
            })
            : data.payments;
        body.innerHTML = payments.length ? payments.map(payment => {
            const invoice = invoiceFor(payment.invoiceId);
            const customer = invoice && customerFor(invoice.customerId);
            return '<tr><td class="py-3 px-4 font-mono font-bold text-brand-700">' + escapeHtml(payment.id) + '</td>' +
                '<td class="py-3 px-4 font-mono">' + escapeHtml(payment.invoiceId) + '</td><td class="py-3 px-4">' + escapeHtml(customer ? customer.name : '') + '</td>' +
                '<td class="py-3 px-4">' + escapeHtml(payment.method) + '</td><td class="py-3 px-4 font-bold">' + money(payment.amount) + '</td>' +
                '<td class="py-3 px-4"><span class="px-2 py-1 rounded-full bg-emerald-100 text-emerald-800">Recorded (Demo)</span></td>' +
                '<td class="py-3 px-4 text-right">' + escapeHtml(payment.date) + '</td></tr>';
        }).join('') : '<tr><td colspan="7" class="p-6 text-center text-slate-500">No simulated payments yet.</td></tr>';
    }

    function renderCustomers() {
        const body = document.getElementById('customer_table_body');
        if (!body) return;
        body.innerHTML = data.customers.length ? data.customers.map(customer => {
            const count = data.subscriptions.filter(subscription => subscription.customerId === customer.id && subscription.status === 'Active').length;
            const monthly = data.subscriptions.filter(subscription => subscription.customerId === customer.id && subscription.status === 'Active').reduce((total, subscription) => total + monthlyAmount(subscription.amount, subscription.cadence), 0);
            const initials = customer.name.split(/\s+/).map(part => part[0]).join('').slice(0, 2).toUpperCase();
            return '<tr><td class="py-3 px-4"><div class="font-bold">' + escapeHtml(customer.name) + '</div><div class="text-slate-500">' + escapeHtml(customer.email) + '</div></td>' +
                '<td class="py-3 px-4">' + escapeHtml(customer.company || '—') + '</td><td class="py-3 px-4">' + count + ' active</td><td class="py-3 px-4 font-bold">' + money(monthly) + ' / mo</td>' +
                '<td class="py-3 px-4">' + data.subscriptions.filter(subscription => subscription.customerId === customer.id).length + '</td>' +
                '<td class="py-3 px-4"><span class="px-2 py-1 bg-slate-100 rounded-full">Demo Customer</span></td>' +
                '<td class="py-3 px-4 text-right"><button onclick="openDemoDialog(\'customer\', \'' + escapeHtml(customer.id) + '\')" class="px-2.5 py-1 bg-slate-100 rounded">Edit profile</button></td></tr>';
        }).join('') : '<tr><td colspan="7" class="p-6 text-center text-slate-500">No demo customers yet.</td></tr>';
    }

    function monthlyAmount(amount, cadence) {
        if (cadence === 'year') return amount / 12;
        if (cadence === 'week') return amount * 52 / 12;
        if (cadence === 'day') return amount * 30;
        return amount;
    }

    function renderDynamicCards() {
        const productsGrid = document.getElementById('product_cards_grid');
        if (productsGrid) {
            productsGrid.querySelectorAll('.added-demo-product').forEach(card => card.remove());
            data.products.filter(item => item.custom).forEach(product => {
                const card = document.createElement('article');
                card.className = 'added-demo-product glass-panel p-5 rounded-2xl border border-slate-200 flex flex-col justify-between';
                card.innerHTML = '<div><span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-brand-100 text-brand-800">Demo Product</span><h3 class="font-bold mt-3">' +
                    escapeHtml(product.name) + '</h3><p class="text-xs text-slate-500 mt-1">' + escapeHtml(product.description) + '</p><p class="mt-4 font-bold">' +
                    money(product.price) + '</p></div><p class="text-[10px] text-slate-400 mt-3">Local demo record only</p>';
                productsGrid.appendChild(card);
            });
        }
        const plansGrid = document.getElementById('plan_cards_grid');
        if (plansGrid) {
            plansGrid.querySelectorAll('.added-demo-plan').forEach(card => card.remove());
            data.plans.filter(item => item.custom).forEach(plan => {
                const card = document.createElement('article');
                card.className = 'added-demo-plan glass-panel p-5 rounded-2xl border border-slate-200';
                card.innerHTML = '<span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-brand-100 text-brand-800">Demo Plan</span><div class="text-xl font-extrabold my-2">' +
                    money(plan.price) + ' <span class="text-xs font-normal text-slate-500">/ ' + escapeHtml(plan.cadence) + '</span></div><p class="font-bold">' +
                    escapeHtml(plan.name) + '</p><p class="text-xs text-slate-500 mt-2">Local demo plan; no billing is connected.</p>';
                plansGrid.appendChild(card);
            });
        }
    }

    function updateSubscriptionModalOptions() {
        const customerSelect = document.getElementById('modal_sub_customer');
        const planSelect = document.getElementById('modal_sub_plan');
        if (customerSelect) {
            customerSelect.innerHTML = data.customers.map(customer =>
                '<option value="' + escapeHtml(customer.id) + '">' + escapeHtml(customer.name) + ' (' + escapeHtml(customer.company || customer.email) + ')</option>'
            ).join('');
            if (currentRole === 'customer' && currentUser) {
                customerSelect.value = currentUser.customerId;
                customerSelect.disabled = true;
            } else customerSelect.disabled = false;
        }
        if (planSelect) {
            planSelect.innerHTML = data.plans.map(plan =>
                '<option value="' + escapeHtml(plan.id) + '">' + escapeHtml(plan.name) + ' (' + money(plan.price) + '/' + escapeHtml(plan.cadence) + ')</option>'
            ).join('');
        }
    }

    function updatePaymentModalOptions(invoiceId) {
        const select = document.getElementById('payment_invoice');
        const amount = document.getElementById('payment_amount');
        if (!select || !amount) return;
        const open = visibleRecords(data.invoices, 'customerId').filter(invoice => residual(invoice) > 0);
        select.innerHTML = open.map(invoice => {
            const customer = customerFor(invoice.customerId);
            return '<option value="' + escapeHtml(invoice.id) + '">' + escapeHtml(invoice.id) + ' — ' +
                escapeHtml(customer ? customer.name : '') + ' (' + money(residual(invoice)) + ' due)</option>';
        }).join('');
        if (invoiceId && open.some(invoice => invoice.id === invoiceId)) select.value = invoiceId;
        const selected = invoiceFor(select.value);
        amount.value = selected ? residual(selected).toFixed(2) : '';
        select.onchange = () => {
            const chosen = invoiceFor(select.value);
            amount.value = chosen ? residual(chosen).toFixed(2) : '';
        };
    }

    function renderCustomerWidgets() {
        if (!currentUser) return;
        const ownCustomer = currentUser && currentUser.customerId ? customerFor(currentUser.customerId) : null;
        const ownSubs = ownCustomer ? data.subscriptions.filter(item => item.customerId === ownCustomer.id) : [];
        const ownInvoices = ownCustomer ? data.invoices.filter(item => item.customerId === ownCustomer.id) : [];
        const dashboard = document.getElementById('screen_customer_dashboard');
        if (!dashboard) return;
        const heading = dashboard.querySelector('h2');
        if (heading) heading.textContent = 'Welcome back, ' + (ownCustomer ? ownCustomer.name : currentUser.name) + '!';
        const loggedIn = dashboard.querySelector('.text-\\[11px\\].text-slate-400.mt-1');
        if (loggedIn) loggedIn.textContent = 'Signed in as: ' + currentUser.email + ' (demo only)';
        const activeSubs = ownSubs.filter(subscription => subscription.status === 'Active');
        const firstSummary = dashboard.querySelector('#customer_summary_cards > div:first-child .text-3xl');
        if (firstSummary) firstSummary.textContent = activeSubs.length + (activeSubs.length === 1 ? ' Contract' : ' Contracts');
        const balance = ownInvoices.reduce((total, invoice) => total + residual(invoice), 0);
        const balanceNode = document.getElementById('alice_balance');
        if (balanceNode) balanceNode.textContent = money(balance);
        const balanceMessage = document.getElementById('customer_balance_message');
        if (balanceMessage) balanceMessage.textContent = balance > 0 ? 'Outstanding demo amount only; no real payment is due.' : 'No outstanding demo invoices.';
        const nextBilling = document.getElementById('customer_next_billing');
        if (nextBilling) nextBilling.textContent = ownSubs.length ? 'Billing cadence: ' + ownSubs[0].cadence + ' (demo)' : 'No billing cycle is configured.';
        const firstSubscription = ownSubs[0];
        const contractTitle = dashboard.querySelector('.glass-panel .p-6 .font-bold.text-slate-800.text-base');
        if (contractTitle) contractTitle.textContent = firstSubscription ? firstSubscription.planName : 'No subscription';
        const contractId = dashboard.querySelector('.glass-panel .p-6 .font-mono.font-bold.text-slate-700');
        if (contractId) contractId.textContent = firstSubscription ? firstSubscription.id : '—';
        const contractPrice = dashboard.querySelector('.glass-panel .p-6 .text-lg.font-extrabold');
        if (contractPrice) contractPrice.textContent = firstSubscription ? money(firstSubscription.amount) + ' / ' + firstSubscription.cadence : '—';
        const contractStatus = document.getElementById('customer_contract_status');
        if (contractStatus) contractStatus.textContent = firstSubscription ? 'Status: ' + firstSubscription.status : 'No subscription';
        const contractState = document.getElementById('customer_contract_state');
        if (contractState) {
            contractState.textContent = firstSubscription ? firstSubscription.status.toUpperCase() : 'NONE';
            contractState.className = 'px-2 py-0.5 text-xs font-bold rounded-full ' +
                (firstSubscription && firstSubscription.status === 'Active' ? 'bg-emerald-100 text-emerald-800' :
                    firstSubscription && firstSubscription.status === 'Paused' ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-700');
        }
        const savings = document.getElementById('customer_savings');
        if (savings) savings.textContent = money(ownSubs.reduce((total, subscription) => total + (Number(subscription.discountAmount) || 0), 0));
        const pauseButton = dashboard.querySelector('button[onclick^="toggleSubscriptionState"]');
        const renewButton = dashboard.querySelector('button[onclick^="renewSubscription"]');
        if (pauseButton) {
            const canChange = firstSubscription && ['Active', 'Paused'].includes(firstSubscription.status);
            pauseButton.classList.toggle('hidden', !canChange);
            if (canChange) {
                const nextStatus = firstSubscription.status === 'Active' ? 'Paused' : 'Active';
                pauseButton.textContent = nextStatus === 'Paused' ? 'Pause' : 'Resume';
                pauseButton.setAttribute('onclick', "toggleSubscriptionState('" + firstSubscription.id + "', '" + nextStatus + "')");
            }
        }
        if (renewButton) {
            renewButton.classList.toggle('hidden', !activeSubs.length);
            if (activeSubs.length) renewButton.setAttribute('onclick', "renewSubscription('" + activeSubs[0].id + "')");
        }

        const portal = document.getElementById('screen_customer_portal');
        const portalGrid = portal && portal.querySelector('.grid');
        if (portalGrid && ownCustomer) {
            const cards = portalGrid.querySelectorAll(':scope > div');
            if (cards[0]) {
                cards[0].innerHTML = '<h3 class="font-bold text-slate-800 text-base mb-4">Your Demo Subscriptions</h3>' +
                    (ownSubs.length ? '<ul class="space-y-3">' + ownSubs.map(subscription =>
                        '<li class="rounded-xl border bg-slate-50 p-3"><div class="font-bold">' + escapeHtml(subscription.planName) + '</div><div class="text-xs text-slate-500">' +
                        escapeHtml(subscription.id) + ' · ' + escapeHtml(subscription.status) + '</div><div class="font-semibold mt-1">' + money(subscription.amount) +
                        ' / ' + escapeHtml(subscription.cadence) + '</div></li>'
                    ).join('') + '</ul>' : '<p class="text-sm text-slate-500">No demo subscriptions yet.</p>');
            }
            if (cards[1]) {
                cards[1].innerHTML = '<h3 class="font-bold text-slate-800 text-base mb-4">Your Demo Invoices</h3>' +
                    (ownInvoices.length ? '<ul class="space-y-3">' + ownInvoices.map(invoice =>
                        '<li class="rounded-xl border bg-slate-50 p-3 flex items-center justify-between gap-3"><div><div class="font-bold font-mono">' +
                        escapeHtml(invoice.id) + '</div><div class="text-xs text-slate-500">' + escapeHtml(invoice.date) + ' · ' +
                        (residual(invoice) === 0 ? 'Paid' : money(residual(invoice)) + ' balance') + '</div></div><div class="text-right font-bold">' +
                        money(invoice.total) + '<br><button onclick="downloadDemoReceipt(this.dataset.invoiceId)" data-invoice-id="' + escapeHtml(invoice.id) + '" class="text-brand-600 text-xs underline">Demo receipt</button></div></li>'
                    ).join('') + '</ul>' : '<p class="text-sm text-slate-500">No demo invoices yet.</p>') +
                    '<p class="mt-4 text-xs text-amber-800">Demo records only. No official invoice, payment processor, or Odoo connection.</p>';
            }
        }
    }

    function updateMetrics() {
        const active = data.subscriptions.filter(subscription => subscription.status === 'Active');
        const mrr = active.reduce((total, subscription) => total + monthlyAmount(subscription.amount, subscription.cadence), 0);
        const outstanding = data.invoices.reduce((total, invoice) => total + residual(invoice), 0);
        document.getElementById('card_active_subs').textContent = active.length;
        document.getElementById('card_mrr').textContent = money(mrr);
        document.getElementById('card_arr').textContent = money(mrr * 12);
        document.getElementById('card_outstanding').textContent = money(outstanding);
        const outstandingLabel = document.getElementById('card_outstanding').parentElement.querySelector('.text-xs');
        if (outstandingLabel) outstandingLabel.textContent = data.invoices.filter(invoice => residual(invoice) > 0).length + ' demo invoices with a balance';
        const reportArpu = document.getElementById('report_arpu');
        if (reportArpu) reportArpu.textContent = active.length ? money(mrr / active.length) : money(0);
        const reportLtv = document.getElementById('report_ltv');
        if (reportLtv) reportLtv.textContent = 'Not available in sample data';
        const reportNrr = document.getElementById('report_nrr');
        if (reportNrr) reportNrr.textContent = 'Not available in sample data';
        const reportArr = document.getElementById('report_arr');
        if (reportArr) reportArr.textContent = money(mrr * 12);
        const reportMrr = document.getElementById('report_mrr');
        if (reportMrr) reportMrr.textContent = money(mrr);
        const reportDiscounts = document.getElementById('report_discounts');
        if (reportDiscounts) reportDiscounts.textContent = money(data.subscriptions.reduce((total, subscription) => total + (Number(subscription.discountAmount) || 0), 0));
        const reportCollected = document.getElementById('report_collected');
        if (reportCollected) reportCollected.textContent = money(data.payments.reduce((total, payment) => total + Number(payment.amount || 0), 0));
        const distribution = document.getElementById('plan_distribution_legend');
        if (distribution) {
            const colors = ['#4f46e5', '#a855f7', '#fbbf24', '#10b981', '#0ea5e9'];
            const counts = data.plans.map(plan => ({
                name: plan.name,
                count: active.filter(subscription => subscription.planId === plan.id).length
            })).filter(item => item.count);
            distribution.innerHTML = counts.length ? counts.map((item, index) =>
                '<div class="flex items-center justify-between"><span class="flex items-center"><span class="w-2.5 h-2.5 rounded-full mr-2" style="background:' +
                colors[index % colors.length] + '"></span>' + escapeHtml(item.name) + '</span><span class="font-bold">' + item.count + '</span></div>'
            ).join('') : '<p class="text-slate-500">No active subscriptions in the demo data.</p>';
        }
        if (mrrChart) {
            mrrChart.data.datasets[0].data = [0.55, 0.63, 0.71, 0.82, 0.91, 1].map(factor => Math.round(mrr * factor));
            mrrChart.update();
        }
        if (planChart) {
            const counts = data.plans.map(plan => active.filter(subscription => subscription.planId === plan.id).length);
            planChart.data.labels = data.plans.map(plan => plan.name);
            planChart.data.datasets[0].data = counts.some(Boolean) ? counts : [1];
            planChart.update();
        }
    }

    function renderAll() {
        renderSubscriptionRows();
        renderCoupons();
        renderInvoices();
        renderPayments();
        renderCustomers();
        renderDynamicCards();
        updateSubscriptionModalOptions();
        updatePaymentModalOptions();
        updateMetrics();
        renderCustomerWidgets();
    }

    function renderScreen(screenId) {
        if (['admin_dashboard', 'customer_dashboard', 'customer_portal', 'financial_reports', 'subscription_mgmt', 'invoice_mgmt', 'payment_mgmt', 'discount_mgmt', 'customer_mgmt'].includes(screenId)) {
            renderAll();
        } else if (['product_mgmt', 'plan_mgmt'].includes(screenId)) {
            renderDynamicCards();
        }
    }

    function filterTable(inputId, tableBodyId) {
        const input = document.getElementById(inputId);
        const body = document.getElementById(tableBodyId);
        if (!input || !body) return;
        const query = input.value.trim().toLowerCase();
        body.querySelectorAll('tr').forEach(row => {
            const matchesSearch = row.textContent.toLowerCase().includes(query);
            const matchesStatus = activeStatusFilter === 'All' || row.textContent.includes(activeStatusFilter);
            row.style.display = matchesSearch && matchesStatus ? '' : 'none';
        });
    }

    function filterTableByStatus(status) {
        activeStatusFilter = status;
        filterTable('sub_search_input', 'full_sub_table_body');
    }

    function openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;
        if (modalId === 'modal_new_subscription') updateSubscriptionModalOptions();
        if (modalId === 'modal_register_payment') updatePaymentModalOptions();
        modal.classList.remove('hidden');
    }

    function closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.add('hidden');
    }

    function couponDiscount(code, amount) {
        if (!code) return { coupon: null, discount: 0 };
        const coupon = data.coupons.find(item => item.code.toLowerCase() === code.trim().toLowerCase());
        if (!coupon || !coupon.active) throw new Error('Coupon is invalid or inactive.');
        if (coupon.expires && coupon.expires < localDate()) throw new Error('Coupon has expired.');
        if (coupon.maxUses > 0 && coupon.uses >= coupon.maxUses) throw new Error('Coupon usage limit has been reached.');
        if (amount < coupon.minAmount) throw new Error('Subscription amount does not meet the coupon minimum.');
        const discount = coupon.type === 'percent' ? amount * coupon.value / 100 : Math.min(amount, coupon.value);
        return { coupon, discount };
    }

    function nextId(prefix, list, field) {
        const next = String(list.length + 1).padStart(3, '0');
        return prefix === 'SUB' ? 'SUB-' + new Date().getFullYear() + '-' + next : prefix + '-' + next;
    }

    function submitNewSubscription(event) {
        event.preventDefault();
        if (!ensureSignedIn()) return;
        const customerId = document.getElementById('modal_sub_customer').value;
        const plan = data.plans.find(item => item.id === document.getElementById('modal_sub_plan').value);
        const code = document.getElementById('modal_sub_promo').value.trim();
        const customer = customerFor(customerId);
        if (!customer || !plan) return showToast('Subscription not created', 'Select a valid customer and plan.', 'warning');
        let coupon;
        let discount = 0;
        try {
            const result = couponDiscount(code, plan.price);
            coupon = result.coupon;
            discount = result.discount;
        } catch (error) {
            showToast('Coupon not applied', error.message, 'warning');
            return;
        }
        if (coupon) coupon.uses += 1;
        const subscription = {
            id: nextId('SUB', data.subscriptions, 'id'),
            customerId,
            planId: plan.id,
            planName: plan.name,
            cadence: plan.cadence,
            amount: Math.max(0, plan.price - discount),
            status: 'Active',
            couponCode: coupon ? coupon.code : '',
            discountAmount: discount,
            renewals: 0,
            period: currentPeriod()
        };
        data.subscriptions.push(subscription);
        persist();
        closeModal('modal_new_subscription');
        document.getElementById('modal_sub_promo').value = '';
        renderAll();
        showScreen('subscription_mgmt');
        showToast('Demo subscription created', subscription.id + ' was saved locally at ' + money(subscription.amount) + ' per ' + plan.cadence + '. No Odoo record was created.', 'success');
    }

    function toggleSubscriptionState(id, newStatus) {
        const subscription = subscriptionFor(id);
        if (!subscription) return showToast('Subscription not found', 'Refresh the page and try again.', 'warning');
        if (currentRole === 'customer' && subscription.customerId !== currentUser.customerId) return showToast('Access restricted', 'You can only view your own subscription records.', 'warning');
        if (!['Active', 'Paused', 'Closed'].includes(newStatus)) return showToast('Invalid status', 'That subscription status is not supported.', 'warning');
        subscription.status = newStatus;
        persist();
        renderAll();
        showToast('Demo subscription updated', id + ' is now ' + newStatus + '. This change is local to this browser.', 'success');
    }

    function createInvoice(subscriptionId, period) {
        const subscription = subscriptionFor(subscriptionId);
        if (!subscription || subscription.status !== 'Active') {
            showToast('Invoice not generated', 'Only an active demo subscription can be invoiced.', 'warning');
            return false;
        }
        period = period || currentPeriod();
        if (data.invoices.some(invoice => invoice.subscriptionId === subscriptionId && invoice.period === period)) {
            showToast('Invoice already exists', 'A demo invoice for this subscription and billing period already exists.', 'warning');
            return false;
        }
        const id = 'INV-' + new Date().getFullYear() + '-' + String(data.invoices.length + 1).padStart(3, '0');
        data.invoices.push({
            id,
            customerId: subscription.customerId,
            subscriptionId,
            period,
            date: localDate(),
            total: subscription.amount,
            paid: 0
        });
        persist();
        renderAll();
        showToast('Demo invoice generated', id + ' is a local sample record, not an Odoo/accounting invoice.', 'success');
        return true;
    }

    function triggerManualInvoice(subscriptionId) {
        if (currentRole === 'customer') return showToast('Access restricted', 'Customers cannot generate invoices in this demo.', 'warning');
        if (createInvoice(subscriptionId)) showScreen('invoice_mgmt');
    }

    function triggerBillingCron() {
        if (currentRole === 'customer') return showToast('Access restricted', 'Billing simulation is available to staff and admin demo roles only.', 'warning');
        let created = 0;
        data.subscriptions.filter(subscription => subscription.status === 'Active').forEach(subscription => {
            const existing = data.invoices.some(invoice => invoice.subscriptionId === subscription.id && invoice.period === currentPeriod());
            if (!existing) {
                const id = 'INV-' + new Date().getFullYear() + '-' + String(data.invoices.length + 1).padStart(3, '0');
                data.invoices.push({ id, customerId: subscription.customerId, subscriptionId: subscription.id, period: currentPeriod(), date: localDate(), total: subscription.amount, paid: 0 });
                created += 1;
            }

        });
        if (created) persist();
        renderAll();
        showToast('Demo billing run complete', created + ' local demo invoice(s) generated. No Odoo cron or external billing ran.', created ? 'success' : 'info');
    }

    function renewSubscription(subscriptionId) {
        const subscription = subscriptionFor(subscriptionId);
        if (!subscription || subscription.customerId !== currentUser.customerId) {
            return showToast('Renewal unavailable', 'A subscription belonging to this customer was not found.', 'warning');
        }
        if (subscription.status !== 'Active') {
            return showToast('Renewal unavailable', 'Only an active demo subscription can be renewed.', 'warning');
        }
        const nextCount = (subscription.renewals || 0) + 1;
        const period = currentPeriod() + '-R' + nextCount;
        if (!createInvoice(subscriptionId, period)) return;
        subscription.renewals = nextCount;
        persist();
        renderAll();
        showToast('Demo renewal recorded', 'A simulated renewal invoice was created. No automatic charge or Odoo action occurred.', 'success');
    }

    function openPaymentModal(invoiceId) {
        if (currentRole === 'customer') return showToast('Access restricted', 'Payment recording is an admin/staff demo operation.', 'warning');
        updatePaymentModalOptions(invoiceId);
        openModal('modal_register_payment');
    }

    function submitPayment(event) {
        event.preventDefault();
        if (!ensureSignedIn()) return;
        const invoice = invoiceFor(document.getElementById('payment_invoice').value);
        const amount = Number(document.getElementById('payment_amount').value);
        const method = document.getElementById('payment_method').value;
        if (!invoice) return showToast('Payment not recorded', 'Choose an invoice with an outstanding balance.', 'warning');
        if (!Number.isFinite(amount) || amount <= 0) return showToast('Payment not recorded', 'Enter a payment amount greater than zero.', 'warning');
        if (amount > residual(invoice) + 0.00001) return showToast('Payment not recorded', 'Amount exceeds the invoice balance of ' + money(residual(invoice)) + '.', 'warning');
        invoice.paid = Math.min(invoice.total, invoice.paid + amount);
        data.payments.push({
            id: 'TXN-DEMO-' + String(data.payments.length + 1).padStart(4, '0'),
            invoiceId: invoice.id,
            amount,
            method: method + ' (Simulated)',
            date: localDate()
        });
        persist();
        closeModal('modal_register_payment');
        renderAll();
        showScreen('payment_mgmt');
        showToast('Simulated payment recorded', money(amount) + ' applied to ' + invoice.id + '. No payment gateway was contacted.', 'success');
    }

    function refreshMetrics() {
        renderAll();
        showToast('Demo metrics refreshed', 'Dashboard values were recalculated from local sample records.', 'success');
    }

    function checkStrength(value) {
        const score = (value.length >= 8 ? 1 : 0) + (/[A-Z]/.test(value) && /[a-z]/.test(value) ? 1 : 0) + (/[0-9]/.test(value) && /[!@#$%^&*(),.?":{}|<>]/.test(value) ? 1 : 0);
        const text = document.getElementById('pass_strength_text');
        const segments = ['meter_seg1', 'meter_seg2', 'meter_seg3'].map(id => document.getElementById(id));
        segments.forEach((segment, index) => {
            if (segment) segment.className = 'h-full w-1/3 ' + (index < score ? (score === 3 ? 'bg-emerald-500' : 'bg-amber-400') : 'bg-slate-200');
        });
        if (text) text.textContent = score === 3 ? 'Password meets the demo password criteria.' : 'Use 8+ characters, upper and lowercase, a number, and a symbol.';
    }

    function togglePasswordVisibility(inputId, iconId) {
        const input = document.getElementById(inputId);
        const icon = document.getElementById(iconId);
        if (!input || !icon) return;
        input.type = input.type === 'password' ? 'text' : 'password';
        icon.className = input.type === 'password' ? 'fa-solid fa-eye text-xs' : 'fa-solid fa-eye-slash text-xs text-brand-600';
    }

    function showToast(title, message, type) {
        const container = document.getElementById('toast_container');
        if (!container) return;
        const toast = document.createElement('div');
        const color = type === 'success' ? 'border-emerald-200' : type === 'warning' ? 'border-amber-200' : 'border-blue-200';
        toast.className = 'toast-animate pointer-events-none bg-white/95 rounded-xl p-3.5 shadow-xl border ' + color + ' flex items-start space-x-3 max-w-sm text-xs';
        const content = document.createElement('div');
        content.innerHTML = '<div class="font-bold text-slate-800"></div><div class="text-slate-500 text-[11px] mt-0.5"></div>';
        content.children[0].textContent = title;
        content.children[1].textContent = message;
        toast.appendChild(content);
        container.appendChild(toast);
        window.setTimeout(() => toast.remove(), 4200);
    }

    function initCharts() {
        if (typeof Chart === 'undefined') {
            document.getElementById('mrrChart').style.display = 'none';
            document.getElementById('planChart').style.display = 'none';
            document.getElementById('mrr_chart_fallback').style.display = 'block';
            document.getElementById('plan_chart_fallback').style.display = 'block';
            return;
        }
        if (!mrrChart) {
            const labels = ['5 months ago', '4 months ago', '3 months ago', '2 months ago', 'Last month', 'Current'];
            mrrChart = new Chart(document.getElementById('mrrChart').getContext('2d'), {
                type: 'line',
                data: { labels, datasets: [{ label: 'Illustrative MRR', data: [0, 0, 0, 0, 0, 0], borderColor: '#4f46e5', backgroundColor: 'rgba(79,70,229,.08)', fill: true, tension: .35, borderWidth: 3 }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { callback: value => '$' + Number(value).toLocaleString() } }, x: { grid: { display: false } } } }
            });
            planChart = new Chart(document.getElementById('planChart').getContext('2d'), {
                type: 'doughnut',
                data: { labels: [], datasets: [{ data: [], backgroundColor: ['#4f46e5', '#a855f7', '#fbbf24', '#10b981', '#0ea5e9'], borderWidth: 0 }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: true, position: 'bottom' } }, cutout: '65%' }
            });
        }
        updateMetrics();
    }

    function openDemoDialog(type, recordId) {
        if (!ensureSignedIn()) return;
        const records = { product: data.products, plan: data.plans, coupon: data.coupons, customer: data.customers };
        const record = recordId ? records[type].find(item => item.id === recordId) : null;
        if (!records[type]) return;
        if (currentRole === 'customer' || (currentRole === 'staff' && ['product', 'plan', 'coupon'].includes(type))) {
            return showToast('Access restricted', 'This record type is not editable with the current demo role.', 'warning');
        }
        const fields = {
            product: [['name', 'Product name', 'text', record && record.name || ''], ['price', 'Recurring price ($)', 'number', record && record.price || ''], ['description', 'Description', 'text', record && record.description || '']],
            plan: [['name', 'Plan name', 'text', record && record.name || ''], ['price', 'Price per billing cycle ($)', 'number', record && record.price || ''], ['cadence', 'Billing cadence (day/week/month/year)', 'text', record && record.cadence || 'month']],
            coupon: [['code', 'Coupon code', 'text', record && record.code || ''], ['name', 'Promotion name', 'text', record && record.name || ''], ['type', 'Discount type (percent/fixed)', 'text', record && record.type || 'percent'], ['value', 'Discount value', 'number', record && record.value || ''], ['minAmount', 'Minimum subtotal ($)', 'number', record && record.minAmount || '0'], ['expires', 'Expiry date (YYYY-MM-DD, optional)', 'text', record && record.expires || '']],
            customer: [['name', 'Customer name', 'text', record && record.name || ''], ['email', 'Email address', 'email', record && record.email || ''], ['company', 'Company', 'text', record && record.company || ''], ['phone', 'Phone', 'text', record && record.phone || '']]
        }[type];
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 z-[60] bg-slate-900/60 flex items-center justify-center p-4';
        modal.innerHTML = '<div class="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl max-h-[90vh] overflow-y-auto"><div class="flex justify-between items-center mb-4"><h2 class="font-bold text-lg">' +
            (record ? 'Edit ' : 'Add ') + escapeHtml(type) + ' (Demo)</h2><button type="button" class="dialog-close text-slate-500" aria-label="Close dialog">✕</button></div>' +
            '<form class="demo-dialog-form space-y-3">' + fields.map(([key, label, inputType, value]) =>
                '<label class="block text-xs font-semibold text-slate-700">' + escapeHtml(label) +
                '<input class="mt-1 w-full border rounded-lg p-2" name="' + escapeHtml(key) + '" type="' + escapeHtml(inputType) + '" ' +
                (inputType === 'number' ? 'min="0" step="0.01"' : '') + ' value="' + escapeHtml(value) + '" required></label>'
            ).join('') + '<div class="dialog-error hidden text-rose-700 text-xs"></div><div class="flex justify-end gap-2 pt-2"><button type="button" class="dialog-cancel px-3 py-2 bg-slate-100 rounded">Cancel</button><button type="submit" class="px-4 py-2 bg-brand-600 text-white rounded font-bold">Save demo record</button></div></form>' +
            '<p class="text-[10px] text-slate-400 mt-3">Saved only in this browser; this does not create an Odoo record.</p></div>';
        document.body.appendChild(modal);
        modal.querySelectorAll('.dialog-close,.dialog-cancel').forEach(button => button.addEventListener('click', () => modal.remove()));
        modal.addEventListener('click', event => { if (event.target === modal) modal.remove(); });
        modal.querySelector('form').addEventListener('submit', event => {
            event.preventDefault();
            const values = Object.fromEntries(new FormData(event.currentTarget).entries());
            const error = modal.querySelector('.dialog-error');
            try {
                if (['product', 'plan'].includes(type) && (!values.name.trim() || !Number.isFinite(Number(values.price)) || Number(values.price) <= 0)) throw new Error('Name and a price greater than zero are required.');
                if (type === 'coupon') {
                    values.code = values.code.trim().toUpperCase();
                    if (!values.code || data.coupons.some(item => item.code === values.code && item.id !== (record && record.id))) throw new Error('Coupon code is required and must be unique.');
                    if (!['percent', 'fixed'].includes(values.type) || Number(values.value) <= 0 || (values.type === 'percent' && Number(values.value) > 100)) throw new Error('Choose percent or fixed and enter a valid discount value.');
                    if (values.expires && !/^\d{4}-\d{2}-\d{2}$/.test(values.expires)) throw new Error('Expiry date must use YYYY-MM-DD.');
                    values.value = Number(values.value);
                    values.minAmount = Number(values.minAmount) || 0;
                    values.active = true;
                    values.uses = record ? record.uses : 0;
                    values.maxUses = record ? record.maxUses : 100;
                }
                if (type === 'product' || type === 'plan') values.price = Number(values.price);
                if (type === 'plan' && !['day', 'week', 'month', 'year'].includes(values.cadence)) throw new Error('Cadence must be day, week, month, or year.');
                if (type === 'customer') {
                    values.email = values.email.trim().toLowerCase();
                    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email)) throw new Error('Enter a valid customer email address.');
                    if (data.customers.some(item => item.email.toLowerCase() === values.email && item.id !== (record && record.id))) throw new Error('A customer with that email already exists.');
                }
                if (record) Object.assign(record, values);
                else {
                    const prefix = { product: 'prod', plan: 'plan', coupon: 'coupon', customer: 'cust' }[type];
                    values.id = prefix + '-' + Date.now().toString(36);
                    if (type === 'product' || type === 'plan') values.custom = true;
                    records[type].push(values);
                }
                persist();
                modal.remove();
                renderAll();
                showToast('Demo record saved', 'Changes are local to this browser and are not sent to Odoo.', 'success');
            } catch (exception) {
                error.textContent = exception.message;
                error.classList.remove('hidden');
            }
        });
    }

    function downloadDemoReceipt(invoiceId) {
        const invoice = invoiceFor(invoiceId);
        if (!invoice) return showToast('Receipt unavailable', 'That demo invoice was not found.', 'warning');
        if (currentRole === 'customer' && invoice.customerId !== currentUser.customerId) return showToast('Access restricted', 'You can only access your own demo invoice.', 'warning');
        const customer = customerFor(invoice.customerId);
        const contents = 'BRIGHTLOOP SOFTWARE — DEMO RECEIPT\\nNOT A TAX INVOICE OR ACCOUNTING RECORD\\n\\nInvoice: ' + invoice.id +
            '\\nCustomer: ' + (customer ? customer.name : 'Unknown') + '\\nDate: ' + invoice.date + '\\nTotal: ' + money(invoice.total) +
            '\\nPaid: ' + money(invoice.paid) + '\\nBalance: ' + money(residual(invoice)) + '\\n\\nStandalone browser simulation only.';
        const url = URL.createObjectURL(new Blob([contents], { type: 'text/plain' }));
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = invoice.id + '-demo-receipt.txt';
        anchor.click();
        URL.revokeObjectURL(url);
        showToast('Demo receipt downloaded', 'This file is a text sample, not an official Odoo PDF invoice.', 'info');
    }

    function init() {
        data = loadData();
        let remember = '';
        try {
            remember = localStorage.getItem(EMAIL_KEY);
        } catch (error) {
            console.warn('Remember email is unavailable in this browser.', error);
        }
        if (remember) {
            document.getElementById('login_email').value = remember;
            document.getElementById('remember_session').checked = true;
        }
        document.getElementById('app_shell').classList.add('hidden');
        document.getElementById('auth_container').classList.remove('hidden');
        showAuthScreen('login');
        document.querySelectorAll('.nav-item').forEach(link => link.addEventListener('click', event => event.preventDefault()));
        document.getElementById('sub_search_input').addEventListener('input', () => filterTable('sub_search_input', 'full_sub_table_body'));
        updateSubscriptionModalOptions();
        renderAll();
    }

    Object.assign(window, {
        checkStrength,
        closeModal,
        downloadDemoReceipt,
        filterTable,
        filterTableByStatus,
        handleLogin,
        handleLogout,
        handleSignup,
        initCharts,
        openDemoDialog,
        openModal,
        openPaymentModal,
        quickFillLogin,
        refreshMetrics,
        renewSubscription,
        showAuthScreen,
        showScreen,
        showToast,
        submitNewSubscription,
        submitPayment,
        switchRole,
        togglePasswordVisibility,
        toggleSubscriptionState,
        triggerBillingCron,
        triggerManualInvoice
    });

    window.addEventListener('DOMContentLoaded', init);
})();
