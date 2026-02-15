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

    const checkStatusUrl = '/api/check_status';
    const subscribeUrl = '/api/subscribe';

    // Theme Toggle
    const themeBtn = document.getElementById('theme-btn');
    const pointsDisplay = document.getElementById('points-display');
    const pointsBadge = document.getElementById('points-badge');

    // Check local storage for theme
    if (localStorage.getItem('theme') === 'dark') {
        document.body.setAttribute('data-theme', 'dark');
        themeBtn.innerHTML = '<i class="fa-solid fa-sun"></i>';
    }

    themeBtn.addEventListener('click', () => {
        if (document.body.getAttribute('data-theme') === 'dark') {
            document.body.removeAttribute('data-theme');
            localStorage.setItem('theme', 'light');
            themeBtn.innerHTML = '<i class="fa-solid fa-moon"></i>';
        } else {
            document.body.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
            themeBtn.innerHTML = '<i class="fa-solid fa-sun"></i>';
        }
    });

    // Check subscription status on load
    fetch('/api/check_status')
        .then(res => res.json())
        .then(data => {
            if (data.subscribed) {
                pointsDisplay.textContent = "Premium Member";
                pointsBadge.style.borderColor = "gold";
                pointsBadge.style.color = "gold";
            } else if (data.trial_used) {
                pointsDisplay.textContent = "Trial Expired";
                pointsBadge.style.borderColor = "#ef4444"; // Red
                pointsBadge.style.color = "#ef4444";
            } else {
                pointsDisplay.textContent = "1 Free Idea";
                pointsBadge.style.borderColor = "#10b981"; // Green
                pointsBadge.style.color = "#10b981";
            }
        });

    // Subscription Modal Elements
    const subModal = document.getElementById('subscription-modal');
    if (subModal) {
        document.getElementById('close-sub-modal')?.addEventListener('click', () => {
            subModal.classList.add('hidden');
        });

        document.getElementById('subscribe-btn')?.addEventListener('click', () => {
            const btn = document.getElementById('subscribe-btn');
            const originalText = btn.textContent;

            // Simulate processing
            btn.textContent = "Processing...";
            btn.disabled = true;

            setTimeout(() => {
                fetch(subscribeUrl, { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        subModal.classList.add('hidden');
                        alert("Upgrade Successful! Welcome to Premium.");

                        // Update UI
                        pointsDisplay.textContent = "Premium Member";
                        pointsBadge.style.borderColor = "gold";
                        pointsBadge.style.color = "gold";

                        // Reset button
                        btn.textContent = originalText;
                        btn.disabled = false;
                    })
                    .catch(e => {
                        alert("Payment failed. Please try again.");
                        btn.textContent = originalText;
                        btn.disabled = false;
                    });
            }, 1000);
        });
    }

    // 2. Generate Logic
    generateBtn.addEventListener('click', () => {


        const business = businessInput.value.trim();
        const platform = platformInput.value;
        const mood = moodInput.value;
        const goal = goalInput.value;
        const people = peopleInput.value;
        const language = languageInput.value;

        // Show Loading Overlay
        const loadingOverlay = document.getElementById('loading-overlay');
        loadingOverlay.classList.remove('hidden');

        // Optional: Update button state (though obscure by overlay)
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
                        // Show subscription modal
                        if (subModal) subModal.classList.remove('hidden');
                        else alert(data.message);
                    } else {
                        alert(data.error);
                    }
                    return;
                }

                // Display Structured Logic
                const rawText = data.idea;

                // Simple parsing based on the prompt structure
                // Expecting: BIG IDEA ... STEP-BY-STEP ... PRO TIP

                let bigIdea = "Cool Video Idea";
                let stepsHtml = "";
                let proTip = "";
                let caption = "";
                let hashtags = "";
                let bestTime = "";

                try {
                    // Extract parts using regex or splitting
                    const parts = rawText.split(/THE BIG IDEA|STEP-BY-STEP.*?|PRO TIP.*?|CAPTION|HASHTAGS|BEST TIME TO POST/i);
                    // parts[0] might be empty or intro
                    // parts[1] = Big Idea
                    // parts[2] = Steps
                    // parts[3] = Pro Tip
                    // parts[4] = Caption
                    // parts[5] = Hashtags
                    // parts[6] = Best Time

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
                        <div class="pro-tip-box">
                            <div class="pro-tip-icon"><i class="fa-solid fa-lightbulb"></i></div>
                            <div><strong>Pro Tip:</strong> ${proTip}</div>
                        </div>
                    `;
                }

                if (caption) {
                    finalHtml += `
                        <div class="result-card">
                            <div class="result-header"><i class="fa-solid fa-comment-dots"></i> Caption</div>
                            <div class="result-body">${caption}</div>
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
                alert("Error generating content.");
            });
    });

    // 3. Copy Logic
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(ideaText.textContent).then(() => {
            const originalText = copyBtn.textContent;
            copyBtn.textContent = "Copied!";
            setTimeout(() => {
                copyBtn.textContent = originalText;
            }, 2000);
        });
    });

});
