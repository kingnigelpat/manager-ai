document.addEventListener('DOMContentLoaded', () => {

    // Elements
    const businessInput = document.getElementById('business-input');
    const platformInput = document.getElementById('platform-input');
    const moodInput = document.getElementById('mood-input');
    const goalInput = document.getElementById('goal-input');
    const peopleInput = document.getElementById('people-input');
    const languageInput = document.getElementById('language-input');
    const generateBtn = document.getElementById('generate-btn');

    const resultSection = document.getElementById('result-section');
    const ideaText = document.getElementById('idea-text');
    const copyBtn = document.getElementById('copy-btn');

    // Refinement Elements
    const refineInput = document.getElementById('refine-input');
    const refineBtn = document.getElementById('refine-btn');

    let currentRawIdea = ""; // Store the raw markdown for context

    // Theme Toggle
    const themeBtn = document.getElementById('theme-btn');

    // Function to set theme
    const setTheme = (theme) => {
        if (theme === 'light') {
            document.body.setAttribute('data-theme', 'light');
            if (themeBtn) themeBtn.innerHTML = '<i class="fa-solid fa-moon"></i>';
            localStorage.setItem('theme', 'light');
        } else {
            document.body.removeAttribute('data-theme'); // Default is dark
            if (themeBtn) themeBtn.innerHTML = '<i class="fa-solid fa-sun"></i>';
            localStorage.setItem('theme', 'dark');
        }
    };

    // Check local storage or system preference
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        setTheme(savedTheme);
    } else {
        // Check system preference
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        setTheme(systemPrefersDark ? 'dark' : 'light');
    }

    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const currentTheme = document.body.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
            setTheme(currentTheme === 'light' ? 'dark' : 'light');
        });
    }

    // Helper to process and display result
    const displayResult = (data) => {
        const rawText = data.idea;
        currentRawIdea = rawText; // Update context for refinement/copy

        // Configure marked for safe and clean rendering
        marked.setOptions({
            breaks: true,
            gfm: true,
            headerIds: false
        });

        // Render Markdown to HTML
        const htmlContent = marked.parse(rawText);

        // Construct the result container
        ideaText.innerHTML = `
            <div class="result-markdown-body">
                ${htmlContent}
            </div>
        `;

        resultSection.classList.remove('hidden');

        // Scroll to results seamlessly
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

    const locationInput = document.getElementById('location-input');

    // Helper to call API for different modes
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
                displayResult(data);
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
                        Swal.fire({ icon: 'success', title: 'Saved!', text: 'Your brand tone is now memorized and will be used for all ideas.' });
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

    // Refinement Logic (Updated to use callAI if needed, but existing is fine for now)
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
                const originalText = copyBtn.innerHTML;
                copyBtn.innerHTML = '<span class="icon"><i class="fa-solid fa-check"></i></span> Copied!';
                setTimeout(() => { copyBtn.innerHTML = originalText; }, 2000);
            });
        });
    }

});
