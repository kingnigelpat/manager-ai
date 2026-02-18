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
        // Display Structured Logic
        const rawText = data.idea;
        currentRawIdea = rawText; // Update context

        // Simple parsing based on the prompt structure
        let bigIdea = "Cool Video Idea";
        let stepsHtml = "";
        let proTip = "";
        let caption = "";
        let hashtags = "";
        let bestTime = "";

        try {
            // Extract parts using regex or splitting
            const parts = rawText.split(/THE BIG IDEA|STEP-BY-STEP.*?|PRO TIP.*?|CAPTION|HASHTAGS|BEST TIME TO POST/i);

            if (parts.length >= 2) bigIdea = parts[1].trim();
            if (parts.length >= 3) {
                // Format steps as a list
                const stepsRaw = parts[2].trim();
                const stepsLines = stepsRaw.split('\n').filter(line => line.trim().length > 0);
                stepsHtml = `<ul class="step-list">`;
                stepsLines.forEach(line => {
                    stepsHtml += `<li>${line.replace(/^\d+\.\s*/, '')}</li>`; // Remove number prefix if present
                });
                stepsHtml += `</ul>`;
            }
            if (parts.length >= 4) proTip = parts[3].trim();
            if (parts.length >= 5) caption = parts[4].trim();
            if (parts.length >= 6) hashtags = parts[5].trim();
            if (parts.length >= 7) bestTime = parts[6].trim();
        } catch (e) {
            console.error("Parsing error", e);
            bigIdea = rawText;
        }

        // Construct HTML
        let finalHtml = `
            <div class="result-card">
                <div class="result-header"><i class="fa-solid fa-clapperboard"></i> The Big Idea</div>
                <div class="result-body">${bigIdea}</div>
            </div>
        `;

        if (stepsHtml) {
            finalHtml += `
                <div class="result-card">
                    <div class="result-header"><i class="fa-solid fa-shoe-prints"></i> Step-by-Step Plan</div>
                    <div class="result-body">${stepsHtml}</div>
                </div>
            `;
        }

        if (proTip) {
            finalHtml += `
                <div class="pro-tip-box" style="margin-bottom: 20px; padding: 15px; background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 12px; display: flex; align-items: center; gap: 15px;">
                    <div class="pro-tip-icon" style="font-size: 1.5rem; color: #f59e0b;"><i class="fa-solid fa-lightbulb"></i></div>
                    <div style="color: var(--text-main);"><strong>Pro Tip:</strong> ${proTip}</div>
                </div>
            `;
        }

        if (caption) {
            finalHtml += `
                <div class="result-card">
                    <div class="result-header"><i class="fa-solid fa-comment-dots"></i> Caption</div>
                    <div class="result-body" style="white-space: pre-wrap;">${caption}</div>
                </div>
            `;
        }

        if (hashtags) {
            finalHtml += `
                <div class="result-card">
                    <div class="result-header"><i class="fa-solid fa-hashtag"></i> Hashtags</div>
                    <div class="result-body" style="color: var(--primary-color); font-weight: 500;">${hashtags}</div>
                </div>
            `;
        }

        if (bestTime) {
            finalHtml += `
                <div class="result-card">
                    <div class="result-header"><i class="fa-regular fa-clock"></i> Best Time to Post</div>
                    <div class="result-body">${bestTime}</div>
                </div>
            `;
        }

        // If parsing failed significantly (no sections found), fallback to raw
        if (typeof parts === 'undefined' || parts.length < 2) {
            finalHtml = `
                <div class="result-card">
                    <div class="result-body" style="white-space: pre-wrap;">${rawText}</div>
                </div>
                `;
        }

        ideaText.innerHTML = finalHtml;
        resultSection.classList.remove('hidden');

        // Scroll to results seamlessly
        setTimeout(() => {
            resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    };

    // Generate Logic
    if (generateBtn) {
        generateBtn.addEventListener('click', () => {

            const business = businessInput.value.trim();
            const platform = platformInput.value;
            const mood = moodInput.value;
            const goal = goalInput.value;
            const people = peopleInput.value;
            const language = languageInput.value;

            if (!business) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Missing Info',
                    text: 'Please tell us about your business first!',
                    confirmButtonColor: '#f59e0b'
                });
                return;
            }

            // Clear old refinement input
            if (refineInput) refineInput.value = "";

            // Show Loading Overlay
            const loadingOverlay = document.getElementById('loading-overlay');
            loadingOverlay.classList.remove('hidden');
            document.querySelector('.loading-text').innerText = "Generating Your Strategy...";

            // Disable button
            generateBtn.disabled = true;

            fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    businessType: business,
                    platform: platform,
                    mood: mood,
                    goal: goal,
                    people: people,
                    language: language
                })
            })
                .then(res => res.json())
                .then(data => {
                    // Hide Loading Overlay
                    loadingOverlay.classList.add('hidden');
                    generateBtn.disabled = false;

                    if (data.error) {
                        if (data.error === "LIMIT_REACHED") {
                            // Upsell Modal
                            Swal.fire({
                                icon: 'info',
                                title: 'Free Limit Reached',
                                text: 'Upgrade to Premium for unlimited generations!',
                                showCancelButton: true,
                                confirmButtonText: 'Upgrade Now',
                                confirmButtonColor: '#f59e0b'
                            }).then((result) => {
                                if (result.isConfirmed) window.location.href = '/pricing';
                            });
                        } else {
                            Swal.fire({ icon: 'error', title: 'Error', text: data.error });
                        }
                        return;
                    }

                    displayResult(data);

                    // button feedback
                    const originalBtnText = generateBtn.innerHTML;
                    generateBtn.innerHTML = '<span class="btn-icon"><i class="fa-solid fa-check"></i></span> Idea Ready!';
                    setTimeout(() => {
                        generateBtn.innerHTML = originalBtnText;
                        generateBtn.disabled = false;
                    }, 3000);
                })
                .catch(err => {
                    loadingOverlay.classList.add('hidden');
                    generateBtn.disabled = false;
                    console.error(err);
                    Swal.fire({ icon: 'error', title: 'Oops...', text: 'Something went wrong generating content.' });
                });
        });
    }

    // Refinement Logic
    if (refineBtn) {
        refineBtn.addEventListener('click', () => {
            const refinement = refineInput.value.trim();
            if (!refinement) return;

            if (!currentRawIdea) {
                Swal.fire({ icon: 'info', title: 'No Idea Yet', text: 'Generate an idea first before refining!' });
                return;
            }

            // Use same inputs as before
            const business = businessInput.value.trim();
            const platform = platformInput.value;
            const mood = moodInput.value;
            const goal = goalInput.value;
            const people = peopleInput.value;
            const language = languageInput.value;

            // Show Loading Overlay
            const loadingOverlay = document.getElementById('loading-overlay');
            loadingOverlay.classList.remove('hidden');
            document.querySelector('.loading-text').innerText = "Refining Your Strategy...";

            refineBtn.disabled = true;

            fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    businessType: business,
                    platform: platform,
                    mood: mood,
                    goal: goal,
                    people: people,
                    language: language,
                    refinement: refinement,
                    previous_idea: currentRawIdea
                })
            })
                .then(res => res.json())
                .then(data => {
                    loadingOverlay.classList.add('hidden');
                    refineBtn.disabled = false;
                    refineInput.value = ""; // Clear input

                    if (data.error) {
                        Swal.fire({ icon: 'error', title: 'Error', text: data.error });
                        return;
                    }

                    displayResult(data);
                })
                .catch(err => {
                    loadingOverlay.classList.add('hidden');
                    refineBtn.disabled = false;
                    console.error(err);
                    Swal.fire({ icon: 'error', title: 'Oops...', text: 'Error refining content.' });
                });
        });
    }

    // Copy Logic
    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(ideaText.textContent).then(() => {
                const originalText = copyBtn.innerHTML;
                copyBtn.innerHTML = '<span class="icon"><i class="fa-solid fa-check"></i></span> Copied!';
                setTimeout(() => {
                    copyBtn.innerHTML = originalText;
                }, 2000);
            });
        });
    }

});
