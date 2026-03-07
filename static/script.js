document.addEventListener('DOMContentLoaded', () => {

    // Main Elements
    const businessInput = document.getElementById('business-input');
    const platformInput = document.getElementById('platform-input');
    const moodInput = document.getElementById('mood-input');
    const goalInput = document.getElementById('goal-input');
    const peopleInput = document.getElementById('people-input');
    const languageInput = document.getElementById('language-input');
    const locationInput = document.getElementById('location-input');
    const generateBtn = document.getElementById('generate-btn');

    // Sidebar Elements
    const sidebar = document.getElementById('sidebar');
    const menuToggleBtn = document.getElementById('menu-toggle-btn');
    const sidebarCloseBtn = document.getElementById('sidebar-close-btn');
    const contentOverlay = document.getElementById('content-overlay');
    const historyList = document.getElementById('history-list');

    // Display Area
    const resultSection = document.getElementById('result-section');
    const ideaText = document.getElementById('idea-text');
    const copyBtn = document.getElementById('copy-btn');

    // Refinement Elements
    const refineInput = document.getElementById('refine-input');
    const refineBtn = document.getElementById('refine-btn');

    let currentRawIdea = "";

    // Sidebar Functions
    const toggleSidebar = () => {
        sidebar.classList.toggle('open');
        contentOverlay.classList.toggle('active');
    };

    if (menuToggleBtn) menuToggleBtn.addEventListener('click', toggleSidebar);
    if (sidebarCloseBtn) sidebarCloseBtn.addEventListener('click', toggleSidebar);
    if (contentOverlay) contentOverlay.addEventListener('click', toggleSidebar);

    // History Logic
    const loadHistory = () => {
        fetch('/api/history')
            .then(res => res.json())
            .then(data => {
                if (data.history) {
                    historyList.innerHTML = '';
                    if (data.history.length === 0) {
                        historyList.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 0.8rem;">No history yet.</div>';
                        return;
                    }
                    data.history.forEach(item => {
                        const div = document.createElement('div');
                        div.className = 'history-item';
                        div.id = `hist-${item.id}`;
                        div.innerHTML = `
                            <div class="h-info">
                                <span class="h-biz">${item.business}</span>
                                <span class="h-time">${item.time}</span>
                            </div>
                            <button class="h-delete" title="Delete Idea">
                                <i class="fa-solid fa-trash-can"></i>
                            </button>
                        `;

                        div.addEventListener('click', () => {
                            displayResult({ idea: item.content });
                            if (window.innerWidth <= 900) toggleSidebar();
                        });

                        const delBtn = div.querySelector('.h-delete');
                        delBtn.addEventListener('click', (e) => {
                            e.stopPropagation();
                            deleteHistoryItem(item.id, div.id);
                        });

                        historyList.appendChild(div);
                    });
                } else if (data.error === "FIREBASE_DISABLED") {
                    historyList.innerHTML = `<div style="padding: 20px; text-align: center; color: #ef4444; font-size: 0.75rem;">
                        <i class="fa-solid fa-triangle-exclamation"></i><br>
                        Firebase History is not enabled.<br>
                        <a href="https://console.firebase.google.com" target="_blank" style="color: inherit; text-decoration: underline;">Enable Firestore</a>
                    </div>`;
                }
            });
    };

    // History Delete Function
    const deleteHistoryItem = (id, elementId) => {
        Swal.fire({
            title: 'Delete this idea?',
            text: "This will remove it from your history forever.",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#ef4444',
            confirmButtonText: 'Yes, delete it',
            cancelButtonText: 'Cancel',
            background: 'var(--card-bg)',
            color: 'var(--text-main)'
        }).then((result) => {
            if (result.isConfirmed) {
                const el = document.getElementById(elementId);
                if (el) el.style.opacity = '0.3';

                fetch(`/api/history/delete/${id}`, {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' }
                })
                    .then(async res => {
                        const data = await res.json();
                        if (res.ok && data.success) {
                            if (el) el.remove();
                            // If sidebar is empty after delete
                            if (historyList.children.length === 0) {
                                historyList.innerHTML = '<div class="history-empty">No history yet. Start generating!</div>';
                            }
                        } else {
                            throw new Error(data.message || data.error || 'Failed to delete');
                        }
                    })
                    .catch(err => {
                        if (el) el.style.opacity = '1';
                        console.error('Delete error:', err);
                        Swal.fire({
                            icon: 'error',
                            title: 'Delete Failed',
                            text: err.message || 'Check your internet connection and try again.',
                            background: 'var(--card-bg)',
                            color: 'var(--text-main)'
                        });
                    });
            }
        });
    };

    // Make it globally accessible if needed (for potential inline calls)
    window.deleteHistoryItem = deleteHistoryItem;

    // Theme Toggle
    const themeBtn = document.getElementById('theme-btn');
    const setTheme = (theme) => {
        if (theme === 'light') {
            document.body.setAttribute('data-theme', 'light');
            if (themeBtn) themeBtn.innerHTML = '<i class="fa-solid fa-moon"></i>';
            localStorage.setItem('theme', 'light');
        } else {
            document.body.removeAttribute('data-theme');
            if (themeBtn) themeBtn.innerHTML = '<i class="fa-solid fa-sun"></i>';
            localStorage.setItem('theme', 'dark');
        }
    };

    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) { setTheme(savedTheme); }
    else { setTheme(window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); }

    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const currentTheme = document.body.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
            setTheme(currentTheme === 'light' ? 'dark' : 'light');
        });
    }

    // Helper to process and display result
    const displayResult = (data) => {
        const rawText = data.idea;
        currentRawIdea = rawText;

        marked.setOptions({ breaks: true, gfm: true, headerIds: false });
        const htmlContent = DOMPurify.sanitize(marked.parse(rawText));

        ideaText.innerHTML = `<div class="result-markdown-body">${htmlContent}</div>`;
        resultSection.classList.remove('hidden');

        setTimeout(() => {
            const topOffset = resultSection.getBoundingClientRect().top + window.pageYOffset - 100;
            window.scrollTo({ top: topOffset, behavior: 'smooth' });
        }, 100);
    };

    // Pro Tools Elements
    const weeklyPlanBtn = document.getElementById('weekly-plan-btn');
    const optimizeCtaBtn = document.getElementById('optimize-cta-btn');
    const rewriteHookBtn = document.getElementById('rewrite-hook-btn');
    const saveToneBtn = document.getElementById('save-tone-btn');
    const brandToneInput = document.getElementById('brand-tone-input');

    // Helper to call API
    const callAI = (mode, payload = {}) => {
        const loadingOverlay = document.getElementById('loading-overlay');
        loadingOverlay.classList.remove('hidden');
        document.querySelector('.loading-text').innerText = "Working Magic...";

        return fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mode: mode,
                businessType: businessInput.value.trim(),
                location: locationInput.value.trim(),
                platform: platformInput.value,
                mood: moodInput.value,
                goal: goalInput.value,
                people: peopleInput.value,
                language: languageInput.value,
                ...payload
            })
        })
            .then(res => res.json())
            .then(data => {
                loadingOverlay.classList.add('hidden');
                if (data.error) {
                    if (data.error === "LIMIT_REACHED") {
                        Swal.fire({
                            icon: 'info',
                            title: 'Limit Reached',
                            text: data.message,
                            showCancelButton: true,
                            confirmButtonText: 'Upgrade Now',
                            confirmButtonColor: '#f59e0b'
                        }).then((result) => { if (result.isConfirmed) window.location.href = '/pricing'; });
                    } else if (data.error === "UPGRADE_REQUIRED") {
                        Swal.fire({ icon: 'warning', title: 'Upgrade Required', text: data.message });
                    } else {
                        Swal.fire({ icon: 'error', title: 'Error', text: data.error });
                    }
                    throw new Error(data.error);
                }
                return data;
            })
            .catch(err => {
                loadingOverlay.classList.add('hidden');
                console.error(err);
                if (!err.message.includes("LIMIT_REACHED") && !err.message.includes("UPGRADE_REQUIRED")) {
                    Swal.fire({ icon: 'error', title: 'Oops...', text: 'Something went wrong.' });
                }
                throw err;
            });
    };

    // Generate Logic
    if (generateBtn) {
        generateBtn.addEventListener('click', () => {
            if (!businessInput.value.trim()) {
                Swal.fire({ icon: 'warning', title: 'Missing Info', text: 'Please tell us about your business first!' });
                return;
            }
            generateBtn.disabled = true;
            callAI('idea').then(data => {
                displayResult(data);
                loadHistory(); // Refresh history
                generateBtn.disabled = false;
            }).catch(() => { generateBtn.disabled = false; });
        });
    }

    // Weekly Plan Logic
    if (weeklyPlanBtn) {
        weeklyPlanBtn.addEventListener('click', () => {
            if (!businessInput.value.trim()) {
                Swal.fire({ icon: 'warning', title: 'Missing Info', text: 'Please tell us about your business first!' });
                return;
            }
            callAI('weekly_plan').then(data => {
                const rawPlan = data.idea;
                marked.setOptions({ breaks: true, gfm: true, headerIds: false });
                const htmlPlan = marked.parse(rawPlan);

                Swal.fire({
                    title: '🗓️ 7-Day Strategy Plan',
                    html: `
                        <div class="result-markdown-body" style="text-align: left; max-height: 50vh; overflow-y: auto; padding: 15px; margin-bottom: 20px; border: 1px solid var(--border-color); background: rgba(0,0,0,0.2); font-size: 0.9rem;">
                            ${htmlPlan}
                        </div>
                        <div style="background: rgba(99, 102, 241, 0.05); padding: 15px; border-radius: 12px; border: 1px dashed var(--primary-color);">
                            <button id="modal-copy-btn" class="primary-btn" style="width: 100%; padding: 14px; font-size: 1rem;">
                                <i class="fa-solid fa-copy" style="margin-right: 8px;"></i> Copy Full Strategy
                            </button>
                        </div>
                    `,
                    width: '800px',
                    showConfirmButton: false,
                    showCloseButton: true,
                    background: 'var(--card-bg)',
                    color: 'var(--text-main)',
                    didOpen: () => {
                        const copyBtn = document.getElementById('modal-copy-btn');
                        if (copyBtn) {
                            copyBtn.addEventListener('click', () => {
                                navigator.clipboard.writeText(rawPlan).then(() => {
                                    copyBtn.innerHTML = '<i class="fa-solid fa-check" style="margin-right: 8px;"></i> Strategy Copied!';
                                    setTimeout(() => { copyBtn.innerHTML = '<i class="fa-solid fa-copy" style="margin-right: 8px;"></i> Copy Full Strategy'; }, 3000);
                                });
                            });
                        }
                    }
                });
            });
        });
    }

    // CTA Optimization Logic
    if (optimizeCtaBtn) {
        optimizeCtaBtn.addEventListener('click', () => {
            callAI('cta', { content: currentRawIdea }).then(data => {
                Swal.fire({ title: 'Optimized CTAs', html: `<div style="text-align: left;">${marked.parse(data.idea)}</div>`, icon: 'success' });
            });
        });
    }

    // Hook Rewriting Logic
    if (rewriteHookBtn) {
        rewriteHookBtn.addEventListener('click', () => {
            callAI('hook', { content: currentRawIdea }).then(data => {
                Swal.fire({ title: 'Viral Hooks', html: `<div style="text-align: left;">${marked.parse(data.idea)}</div>`, icon: 'success' });
            });
        });
    }

    // Brand Tone Saving
    if (saveToneBtn) {
        saveToneBtn.addEventListener('click', () => {
            const tone = brandToneInput.value.trim();
            saveToneBtn.disabled = true;
            fetch('/api/save_brand_tone', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ brandTone: tone })
            })
                .then(res => res.json())
                .then(data => {
                    saveToneBtn.disabled = false;
                    if (data.success) {
                        Swal.fire({ icon: 'success', title: 'Saved!', text: 'Your brand tone is now memorized!' });
                    } else {
                        Swal.fire({ icon: 'error', title: 'Error', text: data.error });
                    }
                })
                .catch(err => {
                    saveToneBtn.disabled = false;
                    Swal.fire({ icon: 'error', title: 'Error', text: 'Failed to save tone.' });
                });
        });
    }

    // Refinement Logic
    if (refineBtn) {
        refineBtn.addEventListener('click', () => {
            const refinement = refineInput.value.trim();
            if (!refinement || !currentRawIdea) return;

            refineBtn.disabled = true;
            callAI('idea', { refinement: refinement, previous_idea: currentRawIdea }).then(data => {
                displayResult(data);
                refineBtn.disabled = false;
                refineInput.value = "";
            }).catch(() => { refineBtn.disabled = false; });
        });
    }

    // Copy Logic
    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(ideaText.innerText).then(() => {
                copyBtn.innerHTML = '<i class="fa-solid fa-check"></i>';
                setTimeout(() => { copyBtn.innerHTML = '<i class="fa-solid fa-copy"></i>'; }, 2000);
            });
        });
    }

    // Logout Handler
    const logoutLink = document.querySelector('.logout-link');
    if (logoutLink) {
        logoutLink.addEventListener('click', async (e) => {
            e.preventDefault();
            const target = logoutLink.href;

            try {
                if (typeof firebase !== 'undefined' && firebase.auth()) {
                    await firebase.auth().signOut();
                }
            } catch (err) {
                console.error("Firebase signout error:", err);
            }
            window.location.href = target;
        });
    }

    loadHistory(); // Initial history load
});

// --- Fixed PWA Installation Logic ---
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    console.log('✅ PWA Install Prompt captured!');

    document.querySelectorAll('.rae-logo').forEach(logo => {
        logo.style.cursor = 'pointer';
        logo.title = 'Click logo to Install App';
        // Visual hint already in CSS
    });
});

document.addEventListener('click', async (e) => {
    if (e.target.classList.contains('rae-logo') || e.target.closest('.rae-logo')) {
        console.log('Logo clicked. Prompt state:', deferredPrompt ? 'Available' : 'Unavailable');

        if (deferredPrompt) {
            deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;
            console.log(`User Choice: ${outcome}`);
            deferredPrompt = null;
        } else {
            // Better UX: Tell them how to install if browser prompt hasn't fired
            Swal.fire({
                title: 'How to Install',
                html: `
                        <div style="text-align: left; font-size: 0.95rem;">
                            <p>To install <b>Manager AI</b> as an app:</p>
                            <ol>
                                <li>Tap your browser's <b>Menu</b> (⋮ or <i class="fa-solid fa-arrow-up-from-bracket"></i>)</li>
                                <li>Select <b>"Add to Home Screen"</b> or <b>"Install App"</b></li>
                            </ol>
                            <p style="font-size: 0.8rem; color: var(--text-muted);">Note: Ensure you are using Chrome or Safari for the best experience.</p>
                        </div>
                    `,
                icon: 'info',
                background: 'var(--card-bg)',
                color: 'var(--text-main)',
                confirmButtonColor: 'var(--primary-color)'
            });
        }
    }
});

window.addEventListener('appinstalled', () => {
    console.log('🚀 App Installed Successfully');
    Swal.fire({
        icon: 'success',
        title: 'Great Success!',
        text: 'Manager AI has been added to your Home Screen.',
        timer: 4000,
        showConfirmButton: false
    });
});
