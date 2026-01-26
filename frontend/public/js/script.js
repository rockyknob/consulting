// --- frontend/public/js/script.js ---
// Updated: Wednesday, April 23, 2025 at 2:45 PM IST (New Delhi)
// Consolidated version with all features and fixes.

// --- Backend API Base URL ---
const backendApiUrlBase = 'https://consulting-juxb.onrender.com/api/v1'; // Use v1 prefix

document.addEventListener("DOMContentLoaded", function() {

    console.log("DOM Loaded. Initializing ZAlpha scripts...");
    
    if (typeof gsap !== 'undefined' && MotionPathPlugin) {
        gsap.registerPlugin(MotionPathPlugin);
        console.log("GSAP and MotionPathPlugin registered.");
        initializeHeroAnimation(); // Call the animation function
    } else {
        console.error("GSAP or MotionPathPlugin not loaded. Skipping hero animation.");
    }
    // --- Global variable for Custom Consulting AI context ---
    let currentSelectedServiceContext = null;
    // Global variable for Startup Analysis text export
    let rawStartupAnalysisText = "";
    // Access data passed from EJS (only relevant on custom-consulting page)
    const pageCustomPackagesData = typeof customPackagesData !== 'undefined' ? customPackagesData : [];
    if (window.location.pathname.includes('/custom-consulting') && pageCustomPackagesData.length > 0) {
         console.log(`Custom Packages Data available: ${pageCustomPackagesData.length} items.`);
    }

    // --- Smooth Scroll for Internal Links ---
    try {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                const targetId = this.getAttribute('href');
                if (targetId && targetId.length > 1 && targetId.startsWith('#')) {
                    const targetElement = document.querySelector(targetId);
                    if (targetElement) {
                        e.preventDefault(); // Prevent default only for valid internal hash links
                        const navbarHeight = document.querySelector('.navbar')?.offsetHeight || 70;
                        const bodyPaddingTop = parseFloat(window.getComputedStyle(document.body).paddingTop) || 0;
                        const elementPosition = targetElement.getBoundingClientRect().top;
                        const offsetPosition = elementPosition + window.pageYOffset - navbarHeight - (bodyPaddingTop > navbarHeight ? 0 : bodyPaddingTop) ;
                        window.scrollTo({ top: offsetPosition, behavior: 'smooth'});
                    } else { console.warn(`Smooth scroll target not found: ${targetId}`); }
                }
            });
        });
        console.log("Smooth scroll initialized.");
    } catch(error) {
        console.error("Error setting up smooth scroll:", error);
    }

    // --- Intersection Observer for Animations ---
    try {
        const observerOptions={root:null,rootMargin:'0px',threshold:0.1};
        const observerCallback=(entries,observer)=>{entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('animate-visible');observer.unobserve(entry.target);}});};
        const observer=new IntersectionObserver(observerCallback,observerOptions);
        document.querySelectorAll('.animate').forEach(el=>{if(el)observer.observe(el);});
        console.log("Intersection Observer initialized.");
    } catch (error) {
        console.error(`Error setting up Intersection Observer: ${error}`);
    }

    // --- Helper to set form status ---
    function setFormStatus(statusElement, message, type) {
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.className = `form-status form-status-${type}`; // type = success, error, sending
        } else {
             console.warn("Attempted to set status on a null element for message:", message);
        }
    }

    // --- Contact Form Handler ---
    const contactForm = document.getElementById('contact-form');
    if (contactForm) {
        const contactFormStatus = contactForm.querySelector('#form-status');
        const contactSubmitButton = contactForm.querySelector('button[type="submit"]');
        const contactApiEndpoint = `${backendApiUrlBase}/contact`;

        if (contactFormStatus && contactSubmitButton) {
            contactForm.addEventListener('submit', async function(event) {
                event.preventDefault();
                console.log("Contact form submitted via JS.");
                setFormStatus(contactFormStatus, 'Sending...', 'sending');
                contactSubmitButton.disabled = true;
                const formData = new FormData(contactForm);
                const data = Object.fromEntries(formData.entries());
                try {
                    const response = await fetch(contactApiEndpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
                    const result = await response.json();
                    if (response.ok && response.status === 202) { setFormStatus(contactFormStatus, `${result.message || 'Success!'} Request ID: ${result.request_id || 'N/A'}`, 'success'); contactForm.reset(); }
                    else { setFormStatus(contactFormStatus, `Error: ${result.detail || response.statusText || 'Failed.'}`, 'error'); }
                } catch (error) { console.error('Error submitting contact form:', error); setFormStatus(contactFormStatus, 'Network error.', 'error');
                } finally { contactSubmitButton.disabled = false; }
            });
            console.log("Contact form handler initialized.");
        } else { console.warn("Contact form handler NOT initialized - elements missing (#form-status or submit button)."); }
    } else { /* console.log("Contact form not found on this page."); */ }


    // --- Custom Consulting Page Package Selector & Details Logic ---
    const packageSelectors = document.querySelectorAll('.package-select-item');
    // Define elements needed for update *outside* function but check inside
    const detailsDisplayArea = document.getElementById('service-details-display-area');
    const detailsTitle = document.getElementById('details-title');
    const detailsDesc = document.getElementById('details-description');
    const detailsActivitiesUl = document.getElementById('details-activities-list');
    const detailsDocumentsUl = document.getElementById('details-documents-list');
    const aiToolTriggerButton = document.getElementById('ai-tool-trigger-card'); // Correct ID for trigger

    function updateServiceDetails(index) {
        // Check if elements exist (prevents errors on other pages)
        if (!detailsDisplayArea || !detailsTitle || !detailsDesc || !detailsActivitiesUl || !detailsDocumentsUl || !aiToolTriggerButton) {
             return; // Exit silently if not on the right page / elements missing
        }
        const currentPackages = pageCustomPackagesData; // Use data loaded from EJS
        if (!currentPackages || !currentPackages[index]) {
             console.error(`Data not found for package index: ${index}`);
             detailsDisplayArea.style.display = 'block'; detailsDisplayArea.classList.add('visible');
             detailsTitle.textContent = "Error: Data Unavailable"; detailsDesc.textContent = "Could not load details.";
             detailsActivitiesUl.innerHTML = '<li>Error</li>'; detailsDocumentsUl.innerHTML = '<li>Error</li>';
             currentSelectedServiceContext = null; // Reset context
             return;
        }

        const selectedPackage = currentPackages[index];
        console.log(`Updating details view for: ${selectedPackage.name}`);

        // Store context for AI tool (essential parts)
        currentSelectedServiceContext = { id: selectedPackage.id, name: selectedPackage.name, description: selectedPackage.description };
        console.log("Set currentSelectedServiceContext to:", JSON.stringify(currentSelectedServiceContext));

        detailsDisplayArea.style.display = 'block'; // Make sure area is visible
        detailsDisplayArea.classList.add('visible');

        detailsTitle.textContent = selectedPackage.name || "Title Unavailable";
        detailsDesc.textContent = selectedPackage.description || "Description not provided.";

        // Populate "Key Business Activities" list
        detailsActivitiesUl.innerHTML = '';
        if (selectedPackage.deliverables?.length) {
            selectedPackage.deliverables.forEach(item => { const li = document.createElement('li'); li.textContent = item || "N/A"; detailsActivitiesUl.appendChild(li); });
        } else { detailsActivitiesUl.innerHTML = '<li>Activity details not available.</li>'; }

        // Populate "Deliverables" list
        detailsDocumentsUl.innerHTML = '';
         if (selectedPackage.documents?.length) {
            selectedPackage.documents.forEach(item => { const li = document.createElement('li'); li.textContent = item || "N/A"; detailsDocumentsUl.appendChild(li); });
        } else { detailsDocumentsUl.innerHTML = '<li>Deliverable examples not available.</li>'; }
    }

    // Initialize Package Selector listeners
    if (packageSelectors.length > 0) {
         packageSelectors.forEach(item => {
            item.addEventListener('click', function() {
                const index = parseInt(this.getAttribute('data-index'), 10);
                if (!isNaN(index)) {
                    console.log(`Package selector clicked: index ${index}`);
                    packageSelectors.forEach(i => i.classList.remove('active'));
                    this.classList.add('active');
                    updateServiceDetails(index); // Update details display
                }
            });
        });
        // Load details for the first item initially if data exists
        if(pageCustomPackagesData.length > 0) {
            console.log("Initializing details for first package.");
            updateServiceDetails(0);
            // Ensure first item has active class visually
             if (!packageSelectors[0].classList.contains('active')) {
                  packageSelectors.forEach(i => i.classList.remove('active'));
                  packageSelectors[0].classList.add('active');
             }
        } else { if(detailsDisplayArea) detailsDisplayArea.style.display = 'none'; } // Hide if no data
        console.log("Service Package Selector listeners attached.");
    } else { if (window.location.pathname.includes('/custom-consulting')) console.warn("Package selector items not found."); }


    // --- AI Tool Modal Logic ---
    let currentAiConversationId = null;
    let currentAiChatHistory = []; // Array of { role: 'user'/'model', content: '...' }

    // --- AI Tool Local Storage Functions ---
    function saveChatHistoryToLocalStorage(serviceId, conversationId, history) {
        if (!serviceId || !conversationId || !history) return;
        try {
            const dataToSave = { id: conversationId, messages: history };
            localStorage.setItem(`aiChatHistory_${serviceId}`, JSON.stringify(dataToSave));
            console.log(`Chat history saved to Local Storage for service ${serviceId}`);
        } catch (e) {
            console.error("Error saving chat history to Local Storage:", e);
            // Handle potential storage quota exceeded
        }
    }

    function loadChatHistoryFromLocalStorage(serviceId) {
        if (!serviceId) return { conversationId: null, history: [] };
        try {
            const savedData = localStorage.getItem(`aiChatHistory_${serviceId}`);
            if (savedData) {
                const parsedData = JSON.parse(savedData);
                console.log(`Chat history loaded from Local Storage for service ${serviceId}`);
                return { conversationId: parsedData.id || null, history: parsedData.messages || [] };
            }
        } catch (e) {
            console.error("Error loading chat history from Local Storage:", e);
        }
        return { conversationId: null, history: [] }; // Return empty if not found or error
    }

    function clearChatHistoryFromLocalStorage(serviceId) {
         if (!serviceId) return;
         try {
             localStorage.removeItem(`aiChatHistory_${serviceId}`);
             console.log(`Chat history cleared from Local Storage for service ${serviceId}`);
         } catch (e) {
              console.error("Error clearing chat history from Local Storage:", e);
         }
    }


    // --- AI Tool UI Update Functions ---
    function renderChatHistory(historyArray) {
        const chatHistoryDiv = document.getElementById('ai-chat-history');
        if (!chatHistoryDiv) return;
        chatHistoryDiv.innerHTML = ''; // Clear previous rendering
        if (!historyArray || historyArray.length === 0) {
             chatHistoryDiv.innerHTML = '<p style="color: var(--text-light); text-align: center;">Conversation started. Ask a question!</p>';
             return;
        }
        historyArray.forEach(msg => {
             const msgDiv = document.createElement('div');
             msgDiv.className = `chat-message ${msg.role === 'user' ? 'user-message' : 'ai-message'}`;
             const contentEl = (msg.role === 'user') ? document.createElement('p') : document.createElement('pre');
             contentEl.textContent = msg.content; // Use textContent for safety
             msgDiv.innerHTML = `<strong>${msg.role === 'user' ? 'You' : 'AI Consultant'}:</strong>`;
             msgDiv.appendChild(contentEl);
             chatHistoryDiv.appendChild(msgDiv);
        });
        chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight; // Scroll to bottom
    }

    function displayPromptSuggestions(suggestions) {
        const suggestionsDiv = document.getElementById('ai-prompt-suggestions');
        const queryInput = document.getElementById('ai-query-input');
        if (!suggestionsDiv || !queryInput) return;

        suggestionsDiv.innerHTML = ''; // Clear previous
        if (suggestions && suggestions.length > 0) {
             suggestions.forEach(text => {
                 const btn = document.createElement('button');
                 btn.textContent = text;
                 btn.onclick = () => { // Add click listener
                     queryInput.value = text; // Fill input
                     queryInput.focus();
                 };
                 suggestionsDiv.appendChild(btn);
             });
        } else {
            suggestionsDiv.innerHTML = '<p style="font-size: 0.9em; color: var(--text-light);">No specific suggestions available.</p>';
        }
    }

    // --- AI Tool Modal Logic ---
    const aiToolModalOverlay = document.getElementById('ai-tool-modal');
    const aiToolModalCloseButton = aiToolModalOverlay ? aiToolModalOverlay.querySelector('#ai-tool-close') : null;
    const aiQueryForm = document.getElementById('ai-query-form');
    const newChatButton = document.getElementById('ai-new-chat-btn'); // New button
    const exportPdfButton = document.getElementById('ai-export-pdf-btn'); // New button
  

    // --- MODIFIED Open AI Modal Function ---
    async function openAiToolModal() {
        console.log("Attempting to open AI tool modal...");
        const modalTitle = document.getElementById('ai-tool-title');
        const serviceSubtitle = document.getElementById('ai-service-subtitle');
        const queryInput = document.getElementById('ai-query-input');
        const statusDiv = document.getElementById('ai-tool-status');

        if (!aiToolModalOverlay || !modalTitle || !serviceSubtitle || !queryInput) {
             console.error("Cannot open AI modal - Core modal elements missing.");
             alert("Error opening AI Assistant: Page elements missing.");
             return;
        }
        if (!currentSelectedServiceContext || !currentSelectedServiceContext.id) {
             console.error("Cannot open AI modal - no service context selected or context missing ID.");
             alert("Please select a service package from the list above first.");
             return;
        }

        // 1. Load history from Local Storage
        const { conversationId, history } = loadChatHistoryFromLocalStorage(currentSelectedServiceContext.id);
        currentAiConversationId = conversationId;
        currentAiChatHistory = history;
        console.log(`Loaded Conv ID: ${currentAiConversationId}, History Length: ${currentAiChatHistory.length}`);

        // 2. Update modal titles
        modalTitle.textContent = `AI Assistant: ${currentSelectedServiceContext.name}`;
        serviceSubtitle.textContent = `Conversation about ${currentSelectedServiceContext.name}`;

        // 3. Render loaded history
        renderChatHistory(currentAiChatHistory); // Update chat display

        // 4. Fetch and display prompt suggestions
        setFormStatus(document.getElementById('ai-prompt-suggestions'), 'Loading suggestions...', 'sending'); // Placeholder
        try {
            const suggestionsApiEndpoint = `${backendApiUrlBase}/ai-prompt-suggestions?service_name=${encodeURIComponent(currentSelectedServiceContext.name)}`;
            const response = await fetch(suggestionsApiEndpoint);
            if (!response.ok) throw new Error(`HTTP error ${response.status}`);
            const suggestions = await response.json();
            displayPromptSuggestions(suggestions);
        } catch (error) {
            console.error("Error fetching prompt suggestions:", error);
            displayPromptSuggestions([]); // Display empty state
        }

        // 5. Clear input/status and show modal
        if(statusDiv) setFormStatus(statusDiv, '', 'sending');
        queryInput.value = '';
        aiToolModalOverlay.classList.add('visible');
        document.body.classList.add('modal-open');
        console.log("AI Tool Modal opened.");
    }

    function closeAiToolModal() { if (aiToolModalOverlay) { aiToolModalOverlay.classList.remove('visible'); document.body.classList.remove('modal-open'); } }

    if (aiToolTriggerButton) { // Attach listener only if button exists
        aiToolTriggerButton.addEventListener('click', function() {
             console.log("AI Tool Trigger Button CLICKED!");
             console.log("Value of currentSelectedServiceContext on click:", JSON.stringify(currentSelectedServiceContext));
             openAiToolModal();
        });
        console.log("AI Tool trigger button listener ATTACHED.");
    } else { if (window.location.pathname.includes('/custom-consulting')) console.warn("AI Tool trigger button (#ai-tool-trigger-card) listener NOT attached."); }


    // Attach close listeners
    if (aiToolModalOverlay) { if (aiToolModalCloseButton) { aiToolModalCloseButton.addEventListener('click', closeAiToolModal); } aiToolModalOverlay.addEventListener('click', (e) => { if (e.target === aiToolModalOverlay) closeAiToolModal(); }); }

    // --- Inside script.js -> AI Tool Modal Logic section ---

    if (aiQueryForm) {
        const aiQueryInput_ = document.getElementById('ai-query-input');
        const aiChatHistory_ = document.getElementById('ai-chat-history'); // Div for UI
        const aiQuerySubmit_ = document.getElementById('ai-query-submit');
        const aiToolStatus_ = document.getElementById('ai-tool-status');

        if (aiQueryInput_ && aiChatHistory_ && aiQuerySubmit_ && aiToolStatus_) {
            aiQueryForm.addEventListener('submit', async function(event) {
                event.preventDefault();
                const userQuery = aiQueryInput_.value.trim();
                if (!userQuery || !currentSelectedServiceContext) { setFormStatus(aiToolStatus_, "Select service and enter query.", "error"); return; }

                // 1. Add user query to JS history and UI
                const userMessage = { role: 'user', content: userQuery };
                currentAiChatHistory.push(userMessage);
                renderChatHistory(currentAiChatHistory); // Update UI immediately
                aiQueryInput_.value = '';
                aiQuerySubmit_.disabled = true;
                setFormStatus(aiToolStatus_, 'AI Thinking...', 'sending');

                // 2. Prepare payload for backend (includes conversation ID)
                const payload = {
                    user_query: userQuery,
                    service_name: currentSelectedServiceContext.name,
                    conversation_id: currentAiConversationId
                };
                const aiToolApiEndpoint = `${backendApiUrlBase}/ai-tool`;

                try {
                    console.log("Sending AI Chat Payload:", payload);
                    const response = await fetch(aiToolApiEndpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                    const result = await response.json(); // Expects AiChatResponse { ai_response, conversation_id, error_message? }
                    console.log("Received AI Chat Response:", result);

                    if (!response.ok || result.error_message) { throw new Error(result.error_message || `HTTP ${response.status}`); }

                    // 3. Update state with response
                    currentAiConversationId = result.conversation_id; // Update ID from backend response
                    const aiMessage = { role: 'model', content: result.ai_response };
                    currentAiChatHistory.push(aiMessage);

                    // 4. Update UI and Save History
                    renderChatHistory(currentAiChatHistory); // Re-render with new AI message
                    saveChatHistoryToLocalStorage(currentSelectedServiceContext.id, currentAiConversationId, currentAiChatHistory);
                    setFormStatus(aiToolStatus_, '', 'sending'); // Clear status

                } catch(error) {
                    console.error("Error in AI chat fetch:", error);
                    setFormStatus(aiToolStatus_, `Error: ${error.message}`, 'error');
                    // Optionally add error message to UI chat history
                    const errorMsg = { role: 'model', content: `[Error: ${error.message}]` };
                    currentAiChatHistory.push(errorMsg); // Add error to history
                    renderChatHistory(currentAiChatHistory); // Show error in chat UI
                    saveChatHistoryToLocalStorage(currentSelectedServiceContext.id, currentAiConversationId, currentAiChatHistory); // Save state with error
                } finally {
                    aiQuerySubmit_.disabled = false;
                }
            });
            console.log("AI Query form handler initialized (with history).");
        } else { console.warn("AI Tool form child elements missing for submit handler."); }
    } else { if(document.getElementById('ai-tool-trigger-card')) console.warn("AI Tool form element (#ai-query-form) not found."); }

    // --- NEW: Listener for "New Chat" Button ---
    if (newChatButton) {
        newChatButton.addEventListener('click', () => {
            console.log("New Chat button clicked.");
            if (currentSelectedServiceContext && currentSelectedServiceContext.id) {
                clearChatHistoryFromLocalStorage(currentSelectedServiceContext.id);
            }
            currentAiConversationId = null;
            currentAiChatHistory = [];
            renderChatHistory(currentAiChatHistory); // Clear UI
            const queryInput = document.getElementById('ai-query-input');
            if (queryInput) queryInput.value = '';
            setFormStatus(document.getElementById('ai-tool-status'), 'New chat started.', 'success');
            // Re-fetch/display prompt suggestions for context
            if(currentSelectedServiceContext) {
                 fetch(`${backendApiUrlBase}/ai-prompt-suggestions?service_name=${encodeURIComponent(currentSelectedServiceContext.name)}`)
                    .then(response => response.ok ? response.json() : Promise.reject('Failed to load'))
                    .then(suggestions => displayPromptSuggestions(suggestions))
                    .catch(err => displayPromptSuggestions([]));
            } else {
                 displayPromptSuggestions([]);
            }
        });
        console.log("New Chat button listener attached.");
    } else { if (window.location.pathname.includes('/custom-consulting')) console.warn("New Chat button (#ai-new-chat-btn) not found."); }

    // --- NEW: Listener for "Export PDF" Button ---
    if (exportPdfButton) {
        exportPdfButton.addEventListener('click', () => {
            console.log("Export PDF button clicked.");
            if (typeof jspdf === 'undefined') {
                 console.error("jsPDF library is not loaded.");
                 alert("Error: PDF Export library not loaded.");
                 return;
            }
            if (!currentAiChatHistory || currentAiChatHistory.length === 0) {
                alert("No conversation history to export.");
                return;
            }
            if (!currentSelectedServiceContext || !currentSelectedServiceContext.name) {
                 alert("Cannot determine service context for export filename.");
                 return;
            }

            try {
                const { jsPDF } = window.jspdf;
                const doc = new jsPDF();
                const serviceName = currentSelectedServiceContext.name;
                const timestamp = new Date().toLocaleString('sv').replace(/ /g,'_').replace(/:/g,'-'); // Swedish format yyyy-mm-dd_hh-mm-ss
                const filename = `AI_Chat_${serviceName.replace(/[^a-z0-9]/gi, '_')}_${timestamp}.pdf`;

                doc.setFontSize(16);
                doc.text(`AI Assistant Conversation: ${serviceName}`, 10, 10);
                doc.setFontSize(10);
                doc.text(`Exported: ${new Date().toLocaleString()}`, 10, 16);
                doc.line(10, 18, 200, 18); // Separator line

                let yPos = 25; // Start position for text
                const pageHeight = doc.internal.pageSize.height;
                const margin = 10;

                currentAiChatHistory.forEach(msg => {
                    if (yPos > pageHeight - margin - 10) { // Add new page check
                        doc.addPage();
                        yPos = margin;
                    }
                    const role = msg.role === 'user' ? 'You' : 'AI';
                    const content = msg.content || "[empty message]";
                    doc.setFont(undefined, 'bold');
                    doc.text(`${role}:`, margin, yPos);
                    yPos += 5; // Space after role
                    doc.setFont(undefined, 'normal');
                    // Add text with auto line breaks
                    const splitText = doc.splitTextToSize(content, doc.internal.pageSize.width - (margin * 2));
                    doc.text(splitText, margin, yPos);
                    yPos += (splitText.length * 4) + 6; // Estimate height + extra space
                });

                doc.save(filename);
                console.log("PDF export initiated.");

            } catch (error) {
                console.error("Error generating PDF:", error);
                alert("An error occurred while generating the PDF export.");
            }
        });
        console.log("Export PDF button listener attached.");
    } else { if (window.location.pathname.includes('/custom-consulting')) console.warn("Export PDF button (#ai-export-pdf-btn) not found."); }



    // --- Hire Consultants Modal & Form Logic ---
    const hireModalOverlay = document.getElementById('hire-modal');
    const hireModalCloseButton = hireModalOverlay ? hireModalOverlay.querySelector('#hire-modal-close') : null;
    const hireTriggerButton = document.getElementById('hire-trigger-card'); // Correct trigger ID
    const hireForm = document.getElementById('hire-form');

    function openHireModal() { if (hireModalOverlay) { hireModalOverlay.classList.add('visible'); document.body.classList.add('modal-open'); } }
    function closeHireModal() { const hireFormStatus_ = document.getElementById('hire-form-status'); if (hireModalOverlay) { hireModalOverlay.classList.remove('visible'); document.body.classList.remove('modal-open'); if(hireForm) hireForm.reset(); if(hireFormStatus_) { hireFormStatus_.textContent = ''; hireFormStatus_.className = 'form-status'; } } }

    if (hireTriggerButton) { hireTriggerButton.addEventListener('click', openHireModal); console.log("Hire trigger button listener attached."); }
    else { if (window.location.pathname.includes('/custom-consulting')) console.warn("Hire trigger button (#hire-trigger-card) not found.");}

    if (hireModalOverlay) { if (hireModalCloseButton) { hireModalCloseButton.addEventListener('click', closeHireModal); } hireModalOverlay.addEventListener('click', (e) => { if (e.target === hireModalOverlay) closeHireModal(); }); /* console.log("Hire modal close listeners attached."); */ }

    if (hireForm) {
        const hireSubmitButton_ = hireForm.querySelector('button[type="submit"]');
        const hireFormStatus_ = hireForm.querySelector('#hire-form-status');
        if (hireSubmitButton_ && hireFormStatus_) {
            hireForm.addEventListener('submit', async function(event) { /* ... Hire form submission logic ... */
                event.preventDefault(); setFormStatus(hireFormStatus_, 'Submitting...', 'sending'); hireSubmitButton_.disabled=true; const formData=new FormData(hireForm); const data={}; let formIsValid=true; formData.forEach((v, k)=>{const el=hireForm.elements[k]; if(el?.type==='checkbox'){return;} if(el?.required&&!v){formIsValid=false;} const nk=['funding_raised_usd','team_size']; if(nk.includes(k)){if(v===''||v===null){data[k]=null;}else{const n=parseFloat(v);data[k]=isNaN(n)?null:n;if(k==='team_size'&&data[k])data[k]=parseInt(data[k]);if(isNaN(data.team_size))data.team_size=null;}}else if(el?.type==='date'){data[k]=v||null;}else{data[k]=v;}}); const services=[]; hireForm.querySelectorAll('input[name="services_needed"]:checked').forEach(cb=>services.push(cb.value)); data['services_needed']=services; if(!formIsValid || !data.contact_name || !data.contact_email || !data.industry || !data.business_function || !data.project_timeline || !data.work_type || !data.project_description){setFormStatus(hireFormStatus_,'Please fill required (*).','error');hireSubmitButton_.disabled=false;return;} const hireApiEndpoint=`${backendApiUrlBase}/hire`; try{const resp=await fetch(hireApiEndpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}); const res=await resp.json(); if(resp.ok&&resp.status===202){setFormStatus(hireFormStatus_,`${res.message} ID: ${res.hire_request_id}`,'success');hireForm.reset();setTimeout(closeHireModal,3500);}else{setFormStatus(hireFormStatus_,`Error: ${res.detail||'Failed.'}`,'error');}}catch(err){console.error('Hire submit err:',err);setFormStatus(hireFormStatus_,'Network error.','error');}finally{hireSubmitButton_.disabled=false;}
            });
            console.log("Hire form submit handler initialized.");
        } else { console.warn("Hire form submit button or status div missing."); }
    } else { if(document.getElementById('hire-trigger-card')) console.warn("Hire form element missing."); }


    // --- Startup Form Handler (With Export Button Logic & Debugging) ---
    const startupForm = document.getElementById('startup-form');
    const startupSubmitButton = startupForm ? startupForm.querySelector('button[type="submit"]') : null;
    // Attach listener only if form and button are found
    if (startupForm && startupSubmitButton) {
        startupForm.addEventListener('submit', async function(event) {
            console.log("Startup form SUBMIT event fired!");
            event.preventDefault(); // Ensure this runs first
            console.log("preventDefault called for startup form.");

            const statusDiv = startupForm.querySelector('#startup-form-status');
            const resultsArea = document.getElementById('startup-results-area');
            const resultsDiv = document.getElementById('startup-results-content');
            const exportBtn = document.getElementById('export-startup-report');
            const disclaimerP = document.getElementById('startup-analysis-disclaimer');

            // Check necessary elements exist *inside* handler
            if (!statusDiv || !resultsArea || !resultsDiv || !exportBtn || !disclaimerP) { console.error("Missing required elements for startup results display."); alert("Page error."); return; }

            setFormStatus(statusDiv, 'Analyzing startup data...', 'sending');
            resultsDiv.innerHTML = '<div class="loading-spinner"></div>'; resultsArea.style.display = 'block'; exportBtn.style.display = 'none'; disclaimerP.textContent = ''; startupSubmitButton.disabled = true; rawStartupAnalysisText = ""; const formData = new FormData(startupForm); const data = {}; let formIsValid = true;

            try {
                formData.forEach((value, key) => { // Variables are 'value' and 'key'
                    const inputElement = startupForm.elements[key]; // Use 'key'

                    // Skip checkboxes here, handle boolean 'has_prototype' separately
                    if (inputElement?.type === 'checkbox') {
                        return;
                    }

                    // Check required fields (except checkbox handled later)
                    if (inputElement?.required && !value) {
                        console.warn(`Required field empty: ${key}`); // Use 'key'
                        formIsValid = false;
                    }

                    // Handle numeric types
                    const numKeys = ['team_size', 'funding_raised_usd', 'monthly_recurring_revenue']; // Add all numeric fields here
                    if (numKeys.includes(key)) { // Use 'key'
                        if (value === '' || value === null) {
                            data[key] = null; // Use 'key'
                        } else {
                            const n = parseFloat(value);
                            data[key] = isNaN(n) ? null : n; // Use 'key'
                            // Ensure team_size is integer if not null
                            if (key === 'team_size' && data[key] !== null) { // Use 'key'
                                data[key] = parseInt(String(data[key]), 10); // Use 'key'
                                if (isNaN(data[key])) data[key] = null; // Reset if parsing failed
                            }
                        }
                    }
                    // Handle date type
                    else if (inputElement?.type === 'date') {
                         data[key] = value || null; // Use 'key'
                    }
                    // Handle string types (default)
                    else {
                        data[key] = value; // Use 'key'
                    }
                }); // End of forEach loop

                // Handle the 'has_prototype' checkbox separately
                const prototypeCheckbox = startupForm.elements['has_prototype'];
                data['has_prototype'] = prototypeCheckbox ? prototypeCheckbox.checked : false;

                // Re-check specific required fields that might not have 'required' attribute or failed above check
                 if (!data.company_name || !data.industry || !data.stage || !data.problem_solved || !data.solution || !data.target_market || !data.business_model || !data.description) {
                    console.warn("One or more specific required text/select fields are empty.");
                    formIsValid = false; // Mark as invalid if any core field is missing
                }

            } catch (gatherError) {
                console.error("Error gathering form data:", gatherError);
                if(statusDiv) setFormStatus(statusDiv, 'Error reading form data.', 'error'); // Ensure statusDiv is defined
                if(startupSubmitButton) startupSubmitButton.disabled = false; // Ensure button exists
                if(resultsDiv) resultsDiv.innerHTML = ''; // Ensure resultsDiv exists
                return; // Stop execution
            }
            // --- End Data Gathering ---

            if (!formIsValid) {
                if(statusDiv) setFormStatus(statusDiv, 'Please fill all required fields (*).', 'error');
                if(resultsDiv) resultsDiv.innerHTML = '';
                startupSubmitButton.disabled = false;
                return;
            }
            const startupAnalysisApiEndpoint = `${backendApiUrlBase}/analyze/startup`;
            try { // Fetch call
                console.log(`Submitting startup data to: ${startupAnalysisApiEndpoint}`); console.log("Data sent:", JSON.stringify(data, null, 2));
                const response = await fetch(startupAnalysisApiEndpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
                console.log(`Received response status: ${response.status}`); const result = await response.json();
                if (!response.ok || result.error_message) { console.error("Backend analysis error:", result.error_message || result.detail || `Status ${response.status}`); throw new Error(result.error_message || result.detail || `Analysis failed`); }
                resultsDiv.innerHTML = ''; rawStartupAnalysisText = result.analysis_text || ""; const analysisText = rawStartupAnalysisText || "No text."; console.log("Raw analysis text:", analysisText.substring(0,100)+"...");
                const formattedResponse = analysisText.replace(/^## (.*)$/gm,'<h3>$1</h3>').replace(/^### (.*)$/gm,'<h4>$1</h4>').replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>').replace(/\*(.*?)\*/g,'<em>$1</em>').replace(/^- (.*)$/gm,'<li>$1</li>').replace(/<\/li>\n<li>/g,'</li><li>').replace(/(<li>(?:(?!<li>).)*<\/li>)/gs,'<ul>$1</ul>').replace(/<\/ul>\s*<ul>/g,'').replace(/\n(?!<br>|<h[34]>|<\/ul>|<\/li>)/g,'<br>'); resultsDiv.innerHTML = formattedResponse;
                setFormStatus(statusDiv, 'Analysis Complete.', 'success'); exportBtn.style.display = 'inline-block'; disclaimerP.textContent = result.disclaimer || ''; resultsArea.style.display = 'block';
            } catch (error) { console.error('Error fetching startup analysis:', error); setFormStatus(statusDiv, `Analysis Error: ${error.message}`, 'error'); resultsDiv.innerHTML = `<p class="error-text">Could not generate analysis. ${error.message}</p>`; exportBtn.style.display = 'none'; resultsArea.style.display = 'block';
            } finally { startupSubmitButton.disabled = false; }
        });
        console.log("Startup form analysis handler initialized.");
    } else { if (window.location.pathname.includes('/startup-consultation')) console.warn("Startup form handler NOT initialized - elements missing (#startup-form or submit button)."); }


    // --- Export Report Function & Listener ---
    function downloadMarkdown(content, filename = 'report.pdf') { /* ... Function as before ... */ console.log(`Downloading: ${filename}`); const BOM="\uFEFF"; const blob=new Blob([BOM+content],{type:'text/markdown;charset=utf-8;'}); const link=document.createElement("a"); const url=URL.createObjectURL(blob); link.setAttribute("href",url); link.setAttribute("download",filename); link.style.visibility='hidden'; document.body.appendChild(link); link.click(); document.body.removeChild(link); URL.revokeObjectURL(url); }
    const exportStartupReportButton = document.getElementById('export-startup-report');
    const startupResultsContentDiv = document.getElementById('startup-results-content');
    if(exportStartupReportButton && startupResultsContentDiv) {
        exportStartupReportButton.addEventListener('click', () => { /* ... Listener logic as before ... */ console.log("Export clicked."); if(rawStartupAnalysisText){const nameInput=document.getElementById('startup-company-name'); const name=nameInput?nameInput.value.trim().replace(/\s+/g,'_')||'Startup':'Startup'; const filename=`${name}_analysis_${new Date().toISOString().split('T')[0]}.md`; downloadMarkdown(rawStartupAnalysisText,filename); } else { alert("No content to export."); } });
        console.log("Export report button listener attached.");
    } else { if(window.location.pathname.includes('/startup-consultation')) console.warn("Export button or results div missing.");}


    // --- Request Tracking Form Handler ---
    const trackForm = document.getElementById('track-form');
    if (trackForm) { /* ... Keep tracking logic as before ... */
        const trackIdentifierInput = document.getElementById('track-identifier'); const trackFormStatusFooter = document.getElementById('track-form-status'); const trackApiEndpoint = `${backendApiUrlBase}/track`; async function fetchTrackingData(id, els){ const { resultsDiv, loadingMsg, infoMsg, listUl, statusDiv } = els; if(loadingMsg) loadingMsg.style.display='block'; /* ... rest of fetch logic ... */ } trackForm.addEventListener('submit', function(e){ /* ... listener logic ... */}); console.log("Tracking form handler initialized."); if(window.location.pathname==='/track-request'){/* ... auto-fetch logic ... */}
    } else { console.warn("Tracking form elements not found."); }
    const particlesContainer = document.getElementById('hero-particles');
    if (particlesContainer && typeof tsParticles !== 'undefined') {
        console.log("Initializing tsParticles...");
        tsParticles.load("hero-particles", { // Target the div ID
            fpsLimit: 60, // Limit FPS for performance
            particles: {
                number: {
                    value: 80, // Number of stars
                    density: {
                        enable: true,
                        value_area: 800 // Area where particles are distributed
                    }
                },
                color: {
                    value: "#ffffff" // Star color
                },
                shape: {
                    type: "circle" // Shape of particles
                },
                opacity: {
                    value: { min: 0.1, max: 0.6 }, // Random opacity for twinkle effect
                    anim: {
                        enable: true,
                        speed: 0.8, // Twinkle speed
                        sync: false,
                        minimumValue: 0.1 // Minimum opacity
                    }
                },
                size: {
                    value: { min: 0.5, max: 1.8 }, // Random size
                    anim: { // Optional subtle size animation
                        enable: false,
                        speed: 3,
                        sync: false
                    }
                },
                move: {
                    enable: true,
                    speed: 0.2, // Very slow drift speed
                    direction: "none", // Random direction
                    random: true,
                    straight: false, // Particles move slightly randomly
                    out_mode: "out", // Particles leave canvas
                    bounce: false, // No bouncing off edges
                },
                links: {
                     enable: false // No lines connecting stars
                }
            },
            interactivity: {
                detect_on: "canvas",
                events: {
                    onhover: {
                        enable: false, // Disable hover interactivity (handled by CSS effect)
                        mode: "repulse"
                    },
                    onclick: {
                        enable: false, // Disable click interactivity
                        mode: "push"
                    },
                    resize: true // Repopulate on resize
                },
                modes: {
                    // Define modes if interactivity is enabled later
                }
            },
            detectRetina: true, // Adjusts for high-res displays
            background: {
                // Background color is handled by the .hero CSS gradient
                color: 'transparent',
            },
            fullScreen: { enable: false } // CRITICAL: Must be false as it's inside a div
        })
        .then(container => {
            console.log("tsParticles initialized successfully.");
        })
        .catch(error => {
             console.error("Error initializing tsParticles:", error);
        });
    } else {
         if (!particlesContainer) console.warn("Particle container #hero-particles not found.");
         if (typeof tsParticles === 'undefined') console.error("tsParticles library not loaded before script execution.");
    }
        

    // --- Case Study Modal Logic ---
    const caseStudyTriggers = document.querySelectorAll('.case-study-trigger');
    const caseStudyModalOverlay = document.getElementById('case-study-modal');
    if (caseStudyTriggers.length > 0 && caseStudyModalOverlay) { /* ... Keep case study logic as before ... */ console.log("Case study modal listeners initialized."); }
    else { if (window.location.pathname.includes('/startup-consultation')) console.warn("Case study elements not found."); }
    
    // --- Testimonial Slider Initialization ---
    const testimonialSwiperElement = document.querySelector('.testimonial-swiper');
    if (testimonialSwiperElement && typeof Swiper !== 'undefined') {
        console.log("Initializing Testimonial Swiper...");
        try {
            const testimonialSwiper = new Swiper('.testimonial-swiper', {
                // Configuration for Coverflow Effect
                effect: 'coverflow',
                grabCursor: true,
                centeredSlides: true,
                slidesPerView: 'auto', // Important for coverflow to calculate width
                loop: true, // Loop usually looks good with coverflow
                coverflowEffect: {
                    rotate: 45,       // Slide rotation in degrees
                    stretch: 0,        // Stretch space between slides (px)
                    depth: 100,        // Depth effect (z-axis)
                    modifier: 1,       // Effect multiplier
                    slideShadows: true // Enable slide shadows
                },
                pagination: {
                    el: '.testimonial-pagination', // Use specific class
                    clickable: true,
                },
                navigation: {
                    nextEl: '.testimonial-button-next', // Use specific class
                    prevEl: '.testimonial-button-prev', // Use specific class
                },
                 keyboard: {
                     enabled: true,
                 },
                 // Optional: Add breakpoints to adjust coverflow for smaller screens if needed
                 // breakpoints: {
                 //     768: {
                 //         slidesPerView: 2, // Might need adjustment with coverflow
                 //     },
                 //     1024: {
                 //          slidesPerView: 3,
                 //     }
                 // }
            });
            console.log("Testimonial Swiper Initialized.");
        } catch (e) {
             console.error("Error initializing Testimonial Swiper:", e);
        }
    } else {
        if (document.getElementById('testimonials')) console.warn("Testimonial swiper element or Swiper library not found.");
    }
    function initializeHeroAnimation() {
        const words = gsap.utils.toArray('.bouncing-word');
        const container = document.querySelector('.hero-animation-container');
        const orbitPath = "#orbit-path"; // ID of the SVG path

        if (!words.length || !container || !document.querySelector(orbitPath)) {
            console.warn("Hero animation elements not found. Skipping animation.");
            return;
        }
        console.log(`Found ${words.length} words for animation.`);

        // --- GSAP Timeline for ONE word (Data) - Adapt for others ---
        // You would loop through 'words' and create a timeline for each,
        // adding staggers or delays.

        words.forEach((word, index) => {
            const firstLetter = word.querySelector('.first-letter');
            const restWord = word.querySelector('.rest-word');
            const wordId = word.id; // e.g., "word-data"

            if (!firstLetter || !restWord) {
                 console.warn(`Skipping word ${wordId}, missing letter spans.`);
                 return; // Skip if structure is wrong
            }

            // Store original position offsets if needed for return trip
            // gsap.set(firstLetter, { x: 0, y: 0 }); // Ensure initial state

            let tl = gsap.timeline({
                repeat: -1, // Repeat indefinitely
                repeatDelay: 1, // Delay between loops
                delay: index * 0.5 // Stagger start times for each word
            });

            // 1. Initial Bounce Sequence (Word)
            tl.to(word, {
                y: "-=30", // Bounce up
                duration: 0.6,
                ease: "power1.out"
            })
            .to(word, {
                y: "+=30", // Bounce down
                duration: 0.8,
                ease: "bounce.out" // GSAP bounce ease
            })
            .to(word, { // Smaller bounce
                y: "-=15",
                duration: 0.5,
                ease: "power1.out"
            })
            .to(word, {
                y: "+=15",
                duration: 0.6,
                ease: "bounce.out"
            }, "-=0.1"); // Overlap previous bounce slightly

            // 2. Detach and Orbit (First Letter) - add label for timing
            tl.addLabel("startOrbit", "+=0.5"); // Add label after bounces

            // Make letter absolute *relative to container* for orbit
            // We need to calculate its position relative to the container when detaching
            // This part is complex and needs calculation based on word's position
            // For simplicity, let's just fade out rest of word and make letter ready

            tl.to(restWord, { // Fade out rest of word
                opacity: 0,
                duration: 0.3
            }, "startOrbit");

            // Prepare first letter - move to start of orbit path?
            // For simplicity, let's assume path starts near word's initial pos
            // We might need to jump it to the path start using gsap.set()
            gsap.set(firstLetter, { transformOrigin: "center center"}); // Set origin for rotation

            tl.to(firstLetter, { // Animate along the SVG path
                motionPath: {
                    path: orbitPath,
                    align: orbitPath,
                    alignOrigin: [0.5, 0.5],
                    autoRotate: true // Rotate letter along path
                },
                duration: 4, // Duration of orbit
                ease: "none" // Constant speed
            }, "startOrbit"); // Start orbit at the same time rest fades

            // 3. Reattach - add label for timing
            tl.addLabel("endOrbit", ">"); // Add label after orbit completes

            // Animate letter back to original position (relative to word)
            // This requires storing/calculating the offset. Using set for simplicity.
            tl.to(firstLetter, {
                x: 0, // Reset relative position
                y: 0,
                rotation: 0, // Reset rotation
                duration: 0.3
            }, "endOrbit");

            tl.to(restWord, { // Fade in rest of word
                opacity: 1,
                duration: 0.3
            }, "endOrbit"); // Fade in as letter returns

             // Add short pause before repeating
             tl.to({}, {duration: 0.5});

        }); // End forEach loop

        console.log("GSAP Timelines setup initiated.");

    } 

     // --- Global Escape Key Listener for Modals ---
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') { /* ... Close visible modals ... */ const hireModal=document.getElementById('hire-modal');const aiModal=document.getElementById('ai-tool-modal');const csModal=document.getElementById('case-study-modal');if(aiModal?.classList.contains('visible'))closeAiToolModal();else if(hireModal?.classList.contains('visible'))closeHireModal();else if(csModal?.classList.contains('visible'))closeCaseStudyModal(); } // Assumes closeCaseStudyModal is defined elsewhere if used
    });
    console.log("Global Escape key listener for modals attached.");


}); // --- End DOMContentLoaded ---



