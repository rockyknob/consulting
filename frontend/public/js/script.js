// --- frontend/public/js/script.js ---
// Refactored: Code quality, bug fixes, and performance improvements.

// --- Backend API Base URL ---
const backendApiUrlBase = 'https://consulting-juxb.onrender.com/api/v1';

// ─────────────────────────────────────────────
// UTILITY HELPERS
// ─────────────────────────────────────────────

/**
 * Set status message on a form status element.
 * @param {HTMLElement|null} el
 * @param {string} message
 * @param {'success'|'error'|'sending'} type
 */
function setFormStatus(el, message, type) {
    if (!el) return;
    el.textContent = message;
    el.className = `form-status form-status-${type}`;
}

/**
 * Download content as a Markdown file.
 * @param {string} content
 * @param {string} filename
 */
function downloadMarkdown(content, filename = 'report.md') {
    const BOM = '\uFEFF';
    const blob = new Blob([BOM + content], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = Object.assign(document.createElement('a'), {
        href: url,
        download: filename,
        style: 'visibility:hidden',
    });
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

/**
 * Safe JSON fetch wrapper.
 * @param {string} url
 * @param {RequestInit} [options]
 * @returns {Promise<{response: Response, result: any}>}
 */
async function apiFetch(url, options = {}) {
    const response = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    const result = await response.json();
    return { response, result };
}

// ─────────────────────────────────────────────
// LOCAL STORAGE — AI CHAT HISTORY
// ─────────────────────────────────────────────

const ChatStorage = {
    key: (serviceId) => `aiChatHistory_${serviceId}`,

    save(serviceId, conversationId, history) {
        if (!serviceId) return;
        try {
            localStorage.setItem(this.key(serviceId), JSON.stringify({ id: conversationId, messages: history }));
        } catch (e) {
            console.error('LocalStorage save error:', e);
        }
    },

    load(serviceId) {
        if (!serviceId) return { conversationId: null, history: [] };
        try {
            const raw = localStorage.getItem(this.key(serviceId));
            if (raw) {
                const parsed = JSON.parse(raw);
                return { conversationId: parsed.id || null, history: parsed.messages || [] };
            }
        } catch (e) {
            console.error('LocalStorage load error:', e);
        }
        return { conversationId: null, history: [] };
    },

    clear(serviceId) {
        if (!serviceId) return;
        try {
            localStorage.removeItem(this.key(serviceId));
        } catch (e) {
            console.error('LocalStorage clear error:', e);
        }
    },
};

// ─────────────────────────────────────────────
// MODAL HELPERS
// ─────────────────────────────────────────────

/**
 * Open a modal overlay.
 * @param {HTMLElement} overlay
 */
function openModal(overlay) {
    if (!overlay) return;
    overlay.classList.add('visible');
    document.body.classList.add('modal-open');
}

/**
 * Close a modal overlay, optionally reset a form inside it.
 * @param {HTMLElement} overlay
 * @param {HTMLFormElement} [form]
 * @param {HTMLElement} [statusEl]
 */
function closeModal(overlay, form, statusEl) {
    if (!overlay) return;
    overlay.classList.remove('visible');
    document.body.classList.remove('modal-open');
    if (form) form.reset();
    if (statusEl) { statusEl.textContent = ''; statusEl.className = 'form-status'; }
}

// ─────────────────────────────────────────────
// DOM CONTENT LOADED
// ─────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {

    console.log('DOM Loaded. Initializing ZAlpha scripts...');

    // ── GSAP Hero Animation ──────────────────
    if (typeof gsap !== 'undefined' && typeof MotionPathPlugin !== 'undefined') {
        gsap.registerPlugin(MotionPathPlugin);
        initializeHeroAnimation();
    } else {
        console.warn('GSAP or MotionPathPlugin not loaded. Skipping hero animation.');
    }

    // ── Page-level globals ───────────────────
    let currentSelectedServiceContext = null;
    let rawStartupAnalysisText = '';

    // Data injected by EJS (only on custom-consulting page)
    const pageCustomPackagesData = typeof customPackagesData !== 'undefined' ? customPackagesData : [];

    // ─────────────────────────────────────────
    // SMOOTH SCROLL
    // ─────────────────────────────────────────
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (!targetId || targetId.length <= 1) return;
            const target = document.querySelector(targetId);
            if (!target) return;
            e.preventDefault();
            const navHeight = document.querySelector('.navbar')?.offsetHeight || 70;
            const top = target.getBoundingClientRect().top + window.pageYOffset - navHeight;
            window.scrollTo({ top, behavior: 'smooth' });
        });
    });

    // ─────────────────────────────────────────
    // INTERSECTION OBSERVER (scroll animations)
    // ─────────────────────────────────────────
    const observer = new IntersectionObserver(
        (entries, obs) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-visible');
                    obs.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.1 }
    );
    document.querySelectorAll('.animate').forEach(el => observer.observe(el));

    // ─────────────────────────────────────────
    // CONTACT FORM
    // ─────────────────────────────────────────
    const contactForm = document.getElementById('contact-form');
    if (contactForm) {
        const contactStatus = contactForm.querySelector('#form-status');
        const contactBtn = contactForm.querySelector('button[type="submit"]');

        if (contactStatus && contactBtn) {
            contactForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                setFormStatus(contactStatus, 'Sending...', 'sending');
                contactBtn.disabled = true;

                const data = Object.fromEntries(new FormData(contactForm).entries());
                try {
                    const { response, result } = await apiFetch(`${backendApiUrlBase}/contact`, {
                        method: 'POST',
                        body: JSON.stringify(data),
                    });
                    if (response.ok && response.status === 202) {
                        setFormStatus(contactStatus, `${result.message || 'Success!'} Request ID: ${result.request_id || 'N/A'}`, 'success');
                        contactForm.reset();
                    } else {
                        setFormStatus(contactStatus, `Error: ${result.detail || response.statusText || 'Failed.'}`, 'error');
                    }
                } catch (err) {
                    console.error('Contact form error:', err);
                    setFormStatus(contactStatus, 'Network error. Please try again.', 'error');
                } finally {
                    contactBtn.disabled = false;
                }
            });
        }
    }

    // ─────────────────────────────────────────
    // CUSTOM CONSULTING — PACKAGE SELECTOR
    // ─────────────────────────────────────────
    const packageSelectors = document.querySelectorAll('.package-select-item');
    const detailsDisplayArea   = document.getElementById('service-details-display-area');
    const detailsTitle         = document.getElementById('details-title');
    const detailsDesc          = document.getElementById('details-description');
    const detailsActivitiesUl  = document.getElementById('details-activities-list');
    const detailsDocumentsUl   = document.getElementById('details-documents-list');
    const aiToolTriggerButton  = document.getElementById('ai-tool-trigger-card');

    function updateServiceDetails(index) {
        if (!detailsDisplayArea || !detailsTitle || !detailsDesc || !detailsActivitiesUl || !detailsDocumentsUl) return;

        const pkg = pageCustomPackagesData[index];
        if (!pkg) {
            console.error(`No package data at index ${index}`);
            currentSelectedServiceContext = null;
            return;
        }

        currentSelectedServiceContext = { id: pkg.id, name: pkg.name, description: pkg.description };

        detailsDisplayArea.style.display = 'block';
        detailsDisplayArea.classList.add('visible');
        detailsTitle.textContent = pkg.name || 'Title Unavailable';
        detailsDesc.textContent  = pkg.description || 'Description not provided.';

        const populateList = (ul, items, fallback) => {
            ul.innerHTML = '';
            if (items?.length) {
                items.forEach(item => {
                    const li = document.createElement('li');
                    li.textContent = item || 'N/A';
                    ul.appendChild(li);
                });
            } else {
                ul.innerHTML = `<li>${fallback}</li>`;
            }
        };

        populateList(detailsActivitiesUl, pkg.deliverables, 'Activity details not available.');
        populateList(detailsDocumentsUl, pkg.documents, 'Deliverable examples not available.');
    }

    if (packageSelectors.length > 0) {
        packageSelectors.forEach(item => {
            item.addEventListener('click', function () {
                const index = parseInt(this.dataset.index, 10);
                if (isNaN(index)) return;
                packageSelectors.forEach(i => i.classList.remove('active'));
                this.classList.add('active');
                updateServiceDetails(index);
            });
        });

        if (pageCustomPackagesData.length > 0) {
            updateServiceDetails(0);
            packageSelectors[0]?.classList.add('active');
        } else if (detailsDisplayArea) {
            detailsDisplayArea.style.display = 'none';
        }
    }

    // ─────────────────────────────────────────
    // AI TOOL MODAL
    // ─────────────────────────────────────────
    let currentAiConversationId = null;
    let currentAiChatHistory    = [];

    const aiToolModalOverlay  = document.getElementById('ai-tool-modal');
    const aiToolCloseButton   = aiToolModalOverlay?.querySelector('#ai-tool-close');
    const aiQueryForm         = document.getElementById('ai-query-form');
    const newChatButton       = document.getElementById('ai-new-chat-btn');
    const exportPdfButton     = document.getElementById('ai-export-pdf-btn');

    // ── Render chat messages ─────────────────
    function renderChatHistory(history) {
        const chatDiv = document.getElementById('ai-chat-history');
        if (!chatDiv) return;
        chatDiv.innerHTML = '';

        if (!history?.length) {
            chatDiv.innerHTML = '<p style="color:var(--text-light);text-align:center;">Conversation started. Ask a question!</p>';
            return;
        }

        const fragment = document.createDocumentFragment();
        history.forEach(msg => {
            const msgDiv = document.createElement('div');
            msgDiv.className = `chat-message ${msg.role === 'user' ? 'user-message' : 'ai-message'}`;

            const label = document.createElement('strong');
            label.textContent = msg.role === 'user' ? 'You: ' : 'AI Consultant: ';

            // BUG FIX: was using innerHTML with textContent interchangeably; use pre for AI, p for user
            const contentEl = document.createElement(msg.role === 'user' ? 'p' : 'pre');
            contentEl.textContent = msg.content;

            msgDiv.appendChild(label);
            msgDiv.appendChild(contentEl);
            fragment.appendChild(msgDiv);
        });

        chatDiv.appendChild(fragment);
        chatDiv.scrollTop = chatDiv.scrollHeight;
    }

    // ── Display prompt suggestions ───────────
    function displayPromptSuggestions(suggestions) {
        const suggestionsDiv = document.getElementById('ai-prompt-suggestions');
        const queryInput     = document.getElementById('ai-query-input');
        if (!suggestionsDiv || !queryInput) return;

        suggestionsDiv.innerHTML = '';
        if (suggestions?.length) {
            const fragment = document.createDocumentFragment();
            suggestions.forEach(text => {
                const btn = document.createElement('button');
                btn.textContent = text;
                btn.addEventListener('click', () => {
                    queryInput.value = text;
                    queryInput.focus();
                });
                fragment.appendChild(btn);
            });
            suggestionsDiv.appendChild(fragment);
        } else {
            suggestionsDiv.innerHTML = '<p style="font-size:0.9em;color:var(--text-light);">No suggestions available.</p>';
        }
    }

    // ── Fetch suggestions ────────────────────
    async function fetchAndDisplaySuggestions(serviceName) {
        const suggestionsDiv = document.getElementById('ai-prompt-suggestions');
        if (!suggestionsDiv) return;
        setFormStatus(suggestionsDiv, 'Loading suggestions...', 'sending');
        try {
            const url = `${backendApiUrlBase}/ai-prompt-suggestions?service_name=${encodeURIComponent(serviceName)}`;
            const { response, result } = await apiFetch(url);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            displayPromptSuggestions(result);
        } catch (err) {
            console.error('Error fetching suggestions:', err);
            displayPromptSuggestions([]);
        }
    }

    // ── Open AI modal ────────────────────────
    async function openAiToolModal() {
        if (!currentSelectedServiceContext?.id) {
            alert('Please select a service package first.');
            return;
        }

        const modalTitle     = document.getElementById('ai-tool-title');
        const serviceSubtitle = document.getElementById('ai-service-subtitle');
        const queryInput     = document.getElementById('ai-query-input');
        const statusDiv      = document.getElementById('ai-tool-status');

        if (!aiToolModalOverlay || !modalTitle || !serviceSubtitle || !queryInput) {
            alert('Error opening AI Assistant: page elements missing.');
            return;
        }

        const { conversationId, history } = ChatStorage.load(currentSelectedServiceContext.id);
        currentAiConversationId = conversationId;
        currentAiChatHistory    = history;

        modalTitle.textContent    = `AI Assistant: ${currentSelectedServiceContext.name}`;
        serviceSubtitle.textContent = `Conversation about ${currentSelectedServiceContext.name}`;

        renderChatHistory(currentAiChatHistory);
        fetchAndDisplaySuggestions(currentSelectedServiceContext.name);

        if (statusDiv) setFormStatus(statusDiv, '', 'sending');
        queryInput.value = '';
        openModal(aiToolModalOverlay);
    }

    function closeAiToolModal() {
        closeModal(aiToolModalOverlay);
    }

    // Attach open/close listeners
    aiToolTriggerButton?.addEventListener('click', openAiToolModal);
    aiToolCloseButton?.addEventListener('click', closeAiToolModal);
    aiToolModalOverlay?.addEventListener('click', e => { if (e.target === aiToolModalOverlay) closeAiToolModal(); });

    // ── AI query form submit ─────────────────
    if (aiQueryForm) {
        const aiQueryInput_  = document.getElementById('ai-query-input');
        const aiQuerySubmit_ = document.getElementById('ai-query-submit');
        const aiToolStatus_  = document.getElementById('ai-tool-status');

        if (aiQueryInput_ && aiQuerySubmit_ && aiToolStatus_) {
            aiQueryForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const userQuery = aiQueryInput_.value.trim();
                if (!userQuery || !currentSelectedServiceContext) {
                    setFormStatus(aiToolStatus_, 'Select a service and enter a query.', 'error');
                    return;
                }

                currentAiChatHistory.push({ role: 'user', content: userQuery });
                renderChatHistory(currentAiChatHistory);
                aiQueryInput_.value  = '';
                aiQuerySubmit_.disabled = true;
                setFormStatus(aiToolStatus_, 'AI Thinking...', 'sending');

                const payload = {
                    user_query:      userQuery,
                    service_name:    currentSelectedServiceContext.name,
                    conversation_id: currentAiConversationId,
                };

                try {
                    const { response, result } = await apiFetch(`${backendApiUrlBase}/ai-tool`, {
                        method: 'POST',
                        body: JSON.stringify(payload),
                    });
                    if (!response.ok || result.error_message) throw new Error(result.error_message || `HTTP ${response.status}`);

                    currentAiConversationId = result.conversation_id;
                    currentAiChatHistory.push({ role: 'model', content: result.ai_response });
                    renderChatHistory(currentAiChatHistory);
                    ChatStorage.save(currentSelectedServiceContext.id, currentAiConversationId, currentAiChatHistory);
                    setFormStatus(aiToolStatus_, '', 'sending');
                } catch (err) {
                    console.error('AI chat fetch error:', err);
                    setFormStatus(aiToolStatus_, `Error: ${err.message}`, 'error');
                    currentAiChatHistory.push({ role: 'model', content: `[Error: ${err.message}]` });
                    renderChatHistory(currentAiChatHistory);
                    ChatStorage.save(currentSelectedServiceContext.id, currentAiConversationId, currentAiChatHistory);
                } finally {
                    aiQuerySubmit_.disabled = false;
                }
            });
        }
    }

    // ── New Chat button ──────────────────────
    newChatButton?.addEventListener('click', () => {
        if (currentSelectedServiceContext?.id) {
            ChatStorage.clear(currentSelectedServiceContext.id);
        }
        currentAiConversationId = null;
        currentAiChatHistory    = [];
        renderChatHistory([]);
        const queryInput = document.getElementById('ai-query-input');
        if (queryInput) queryInput.value = '';
        setFormStatus(document.getElementById('ai-tool-status'), 'New chat started.', 'success');
        if (currentSelectedServiceContext?.name) {
            fetchAndDisplaySuggestions(currentSelectedServiceContext.name);
        }
    });

    // ── Export PDF button ────────────────────
    // BUG FIX: filename param in downloadMarkdown was incorrectly labeled '.pdf' but saved markdown
    exportPdfButton?.addEventListener('click', () => {
        if (typeof window.jspdf === 'undefined') {
            alert('Error: PDF export library not loaded.');
            return;
        }
        if (!currentAiChatHistory?.length) {
            alert('No conversation history to export.');
            return;
        }
        if (!currentSelectedServiceContext?.name) {
            alert('Cannot determine service context for export.');
            return;
        }
        try {
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();
            const serviceName = currentSelectedServiceContext.name;
            const timestamp   = new Date().toLocaleString('sv').replace(/ /g, '_').replace(/:/g, '-');
            const filename    = `AI_Chat_${serviceName.replace(/[^a-z0-9]/gi, '_')}_${timestamp}.pdf`;
            const margin      = 10;
            const pageWidth   = doc.internal.pageSize.width;
            const pageHeight  = doc.internal.pageSize.height;

            doc.setFontSize(16);
            doc.text(`AI Assistant Conversation: ${serviceName}`, margin, 10);
            doc.setFontSize(10);
            doc.text(`Exported: ${new Date().toLocaleString()}`, margin, 16);
            doc.line(margin, 18, pageWidth - margin, 18);

            let yPos = 25;
            currentAiChatHistory.forEach(msg => {
                const role    = msg.role === 'user' ? 'You' : 'AI';
                const content = msg.content || '[empty message]';
                const lines   = doc.splitTextToSize(content, pageWidth - margin * 2);
                const blockH  = 5 + lines.length * 4 + 6;

                // BUG FIX: check page overflow BEFORE rendering each message block
                if (yPos + blockH > pageHeight - margin) {
                    doc.addPage();
                    yPos = margin;
                }

                doc.setFont(undefined, 'bold');
                doc.text(`${role}:`, margin, yPos);
                yPos += 5;
                doc.setFont(undefined, 'normal');
                doc.text(lines, margin, yPos);
                yPos += lines.length * 4 + 6;
            });

            doc.save(filename);
        } catch (err) {
            console.error('PDF export error:', err);
            alert('An error occurred while generating the PDF.');
        }
    });

    // ─────────────────────────────────────────
    // HIRE CONSULTANTS MODAL
    // ─────────────────────────────────────────
    const hireModalOverlay  = document.getElementById('hire-modal');
    const hireModalClose    = hireModalOverlay?.querySelector('#hire-modal-close');
    const hireTriggerButton = document.getElementById('hire-trigger-card');
    const hireForm          = document.getElementById('hire-form');
    const hireFormStatus    = document.getElementById('hire-form-status');

    hireTriggerButton?.addEventListener('click', () => openModal(hireModalOverlay));
    hireModalClose?.addEventListener('click', () => closeModal(hireModalOverlay, hireForm, hireFormStatus));
    hireModalOverlay?.addEventListener('click', e => {
        if (e.target === hireModalOverlay) closeModal(hireModalOverlay, hireForm, hireFormStatus);
    });

    if (hireForm) {
        const hireBtn    = hireForm.querySelector('button[type="submit"]');
        const hireStatus = hireForm.querySelector('#hire-form-status');

        if (hireBtn && hireStatus) {
            hireForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                setFormStatus(hireStatus, 'Submitting...', 'sending');
                hireBtn.disabled = true;

                const formData = new FormData(hireForm);
                const data = {};
                const numericKeys = ['funding_raised_usd', 'team_size'];

                formData.forEach((value, key) => {
                    const el = hireForm.elements[key];
                    if (el?.type === 'checkbox') return;

                    if (numericKeys.includes(key)) {
                        const n = parseFloat(value);
                        data[key] = value === '' ? null : (isNaN(n) ? null : (key === 'team_size' ? parseInt(value, 10) : n));
                    } else if (el?.type === 'date') {
                        data[key] = value || null;
                    } else {
                        data[key] = value;
                    }
                });

                // Collect multi-checkboxes
                data.services_needed = [...hireForm.querySelectorAll('input[name="services_needed"]:checked')]
                    .map(cb => cb.value);

                const required = ['contact_name', 'contact_email', 'industry', 'business_function', 'project_timeline', 'work_type', 'project_description'];
                if (required.some(k => !data[k])) {
                    setFormStatus(hireStatus, 'Please fill all required fields (*).', 'error');
                    hireBtn.disabled = false;
                    return;
                }

                try {
                    const { response, result } = await apiFetch(`${backendApiUrlBase}/hire`, {
                        method: 'POST',
                        body: JSON.stringify(data),
                    });
                    if (response.ok && response.status === 202) {
                        setFormStatus(hireStatus, `${result.message} ID: ${result.hire_request_id}`, 'success');
                        hireForm.reset();
                        setTimeout(() => closeModal(hireModalOverlay, hireForm, hireStatus), 3500);
                    } else {
                        setFormStatus(hireStatus, `Error: ${result.detail || 'Failed.'}`, 'error');
                    }
                } catch (err) {
                    console.error('Hire form error:', err);
                    setFormStatus(hireStatus, 'Network error.', 'error');
                } finally {
                    hireBtn.disabled = false;
                }
            });
        }
    }

    // ─────────────────────────────────────────
    // STARTUP ANALYSIS FORM
    // ─────────────────────────────────────────
    const startupForm       = document.getElementById('startup-form');
    const startupSubmitBtn  = startupForm?.querySelector('button[type="submit"]');

    if (startupForm && startupSubmitBtn) {
        startupForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const statusDiv     = startupForm.querySelector('#startup-form-status');
            const resultsArea   = document.getElementById('startup-results-area');
            const resultsDiv    = document.getElementById('startup-results-content');
            const exportBtn     = document.getElementById('export-startup-report');
            const disclaimerP   = document.getElementById('startup-analysis-disclaimer');

            if (!statusDiv || !resultsArea || !resultsDiv || !exportBtn || !disclaimerP) {
                alert('Page error: missing result elements.');
                return;
            }

            setFormStatus(statusDiv, 'Analyzing startup data...', 'sending');
            resultsDiv.innerHTML = '<div class="loading-spinner"></div>';
            resultsArea.style.display = 'block';
            exportBtn.style.display   = 'none';
            disclaimerP.textContent   = '';
            startupSubmitBtn.disabled = true;
            rawStartupAnalysisText    = '';

            const formData    = new FormData(startupForm);
            const data        = {};
            const numericKeys = ['team_size', 'funding_raised_usd', 'monthly_recurring_revenue'];
            let formIsValid   = true;

            formData.forEach((value, key) => {
                const el = startupForm.elements[key];
                if (el?.type === 'checkbox') return;
                if (el?.required && !value) formIsValid = false;

                if (numericKeys.includes(key)) {
                    const n = parseFloat(value);
                    data[key] = value === '' ? null : (isNaN(n) ? null : n);
                    if (key === 'team_size' && data[key] !== null) {
                        data[key] = parseInt(String(data[key]), 10);
                        if (isNaN(data[key])) data[key] = null;
                    }
                } else if (el?.type === 'date') {
                    data[key] = value || null;
                } else {
                    data[key] = value;
                }
            });

            // BUG FIX: was silently dropping has_prototype; handle it explicitly
            const protoCheckbox = startupForm.elements['has_prototype'];
            data.has_prototype  = protoCheckbox ? protoCheckbox.checked : false;

            const coreRequired = ['company_name', 'industry', 'stage', 'problem_solved', 'solution', 'target_market', 'business_model', 'description'];
            if (!formIsValid || coreRequired.some(k => !data[k])) {
                setFormStatus(statusDiv, 'Please fill all required fields (*).', 'error');
                resultsDiv.innerHTML      = '';
                startupSubmitBtn.disabled = false;
                return;
            }

            try {
                const { response, result } = await apiFetch(`${backendApiUrlBase}/analyze/startup`, {
                    method: 'POST',
                    body: JSON.stringify(data),
                });
                if (!response.ok || result.error_message) throw new Error(result.error_message || result.detail || `Analysis failed`);

                rawStartupAnalysisText = result.analysis_text || '';
                // Render markdown-like text safely
                const html = rawStartupAnalysisText
                    .replace(/^## (.*)$/gm,  '<h3>$1</h3>')
                    .replace(/^### (.*)$/gm, '<h4>$1</h4>')
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g,    '<em>$1</em>')
                    .replace(/^- (.*)$/gm,   '<li>$1</li>')
                    .replace(/(<li>[\s\S]*?<\/li>)/g, (match) => `<ul>${match}</ul>`)
                    .replace(/<\/ul>\s*<ul>/g, '')
                    .replace(/\n(?!<)/g, '<br>');

                resultsDiv.innerHTML        = html;
                exportBtn.style.display     = 'inline-block';
                disclaimerP.textContent     = result.disclaimer || '';
                resultsArea.style.display   = 'block';
                setFormStatus(statusDiv, 'Analysis Complete.', 'success');
            } catch (err) {
                console.error('Startup analysis error:', err);
                setFormStatus(statusDiv, `Analysis Error: ${err.message}`, 'error');
                resultsDiv.innerHTML = `<p class="error-text">Could not generate analysis. ${err.message}</p>`;
                exportBtn.style.display = 'none';
            } finally {
                startupSubmitBtn.disabled = false;
            }
        });
    }

    // ── Export startup report ────────────────
    const exportStartupBtn     = document.getElementById('export-startup-report');
    if (exportStartupBtn) {
        exportStartupBtn.addEventListener('click', () => {
            if (!rawStartupAnalysisText) { alert('No content to export.'); return; }
            const nameInput = document.getElementById('startup-company-name');
            const name      = nameInput?.value.trim().replace(/\s+/g, '_') || 'Startup';
            downloadMarkdown(rawStartupAnalysisText, `${name}_analysis_${new Date().toISOString().split('T')[0]}.md`);
        });
    }

    // ─────────────────────────────────────────
    // TSPARTICLES — HERO
    // ─────────────────────────────────────────
    const particlesContainer = document.getElementById('hero-particles');
    if (particlesContainer && typeof tsParticles !== 'undefined') {
        tsParticles.load('hero-particles', {
            fpsLimit: 60,
            fullScreen: { enable: false },
            background: { color: 'transparent' },
            particles: {
                number:  { value: 80, density: { enable: true, value_area: 800 } },
                color:   { value: '#ffffff' },
                shape:   { type: 'circle' },
                opacity: { value: { min: 0.1, max: 0.6 }, anim: { enable: true, speed: 0.8, sync: false, minimumValue: 0.1 } },
                size:    { value: { min: 0.5, max: 1.8 } },
                move:    { enable: true, speed: 0.2, direction: 'none', random: true, straight: false, out_mode: 'out', bounce: false },
                links:   { enable: false },
            },
            interactivity: {
                detect_on: 'canvas',
                events: { onhover: { enable: false }, onclick: { enable: false }, resize: true },
            },
            detectRetina: true,
        }).catch(err => console.error('tsParticles error:', err));
    }

    // ─────────────────────────────────────────
    // TESTIMONIAL SWIPER
    // ─────────────────────────────────────────
    const testimonialSwiperEl = document.querySelector('.testimonial-swiper');
    if (testimonialSwiperEl && typeof Swiper !== 'undefined') {
        try {
            new Swiper('.testimonial-swiper', {
                effect:         'coverflow',
                grabCursor:     true,
                centeredSlides: true,
                slidesPerView:  'auto',
                loop:           true,
                coverflowEffect: { rotate: 45, stretch: 0, depth: 100, modifier: 1, slideShadows: true },
                pagination:  { el: '.testimonial-pagination', clickable: true },
                navigation:  { nextEl: '.testimonial-button-next', prevEl: '.testimonial-button-prev' },
                keyboard:    { enabled: true },
            });
        } catch (err) {
            console.error('Swiper init error:', err);
        }
    }

    // ─────────────────────────────────────────
    // GLOBAL ESCAPE KEY — CLOSE MODALS
    // ─────────────────────────────────────────
    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Escape') return;
        const hireModal = document.getElementById('hire-modal');
        const aiModal   = document.getElementById('ai-tool-modal');
        const csModal   = document.getElementById('case-study-modal');
        if (aiModal?.classList.contains('visible'))   closeAiToolModal();
        else if (hireModal?.classList.contains('visible')) closeModal(hireModal, hireForm, hireFormStatus);
        else if (csModal?.classList.contains('visible'))   closeCaseStudyModal?.();
    });

}); // ── End DOMContentLoaded ──


// ─────────────────────────────────────────────
// GSAP HERO ANIMATION
// (defined outside DOMContentLoaded so GSAP can call it after plugin registration)
// ─────────────────────────────────────────────
function initializeHeroAnimation() {
    const words    = gsap.utils.toArray('.bouncing-word');
    const orbitPath = '#orbit-path';

    if (!words.length || !document.querySelector(orbitPath)) {
        console.warn('Hero animation elements not found. Skipping.');
        return;
    }

    words.forEach((word, index) => {
        const firstLetter = word.querySelector('.first-letter');
        const restWord    = word.querySelector('.rest-word');
        if (!firstLetter || !restWord) return;

        gsap.set(firstLetter, { transformOrigin: 'center center' });

        const tl = gsap.timeline({ repeat: -1, repeatDelay: 1, delay: index * 0.5 });

        // Bounce sequence
        tl.to(word, { y: '-=30', duration: 0.6, ease: 'power1.out' })
          .to(word, { y: '+=30', duration: 0.8, ease: 'bounce.out' })
          .to(word, { y: '-=15', duration: 0.5, ease: 'power1.out' })
          .to(word, { y: '+=15', duration: 0.6, ease: 'bounce.out' }, '-=0.1');

        // Orbit sequence
        tl.addLabel('startOrbit', '+=0.5');
        tl.to(restWord, { opacity: 0, duration: 0.3 }, 'startOrbit');
        tl.to(firstLetter, {
            motionPath: { path: orbitPath, align: orbitPath, alignOrigin: [0.5, 0.5], autoRotate: true },
            duration: 4,
            ease: 'none',
        }, 'startOrbit');

        // Reattach
        tl.addLabel('endOrbit', '>');
        tl.to(firstLetter, { x: 0, y: 0, rotation: 0, duration: 0.3 }, 'endOrbit');
        tl.to(restWord,    { opacity: 1, duration: 0.3 }, 'endOrbit');
        tl.to({}, { duration: 0.5 });
    });
}
