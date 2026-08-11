(() => {
    const shelf = document.getElementById("shelf");
    const spines = Array.from(document.querySelectorAll(".spine"));

    const emptyState = document.getElementById("emptyState");
    const loadingState = document.getElementById("loadingState");
    const loadingText = document.getElementById("loadingText");
    const errorState = document.getElementById("errorState");
    const errorText = document.getElementById("errorText");
    const resultState = document.getElementById("resultState");

    const resultGenre = document.getElementById("resultGenre");
    const resultTitle = document.getElementById("resultTitle");
    const resultMeta = document.getElementById("resultMeta");
    const resultTiming = document.getElementById("resultTiming");
    const openLink = document.getElementById("openLink");
    const anotherBtn = document.getElementById("anotherBtn");
    const retryBtn = document.getElementById("retryBtn");
    const learnToggleBtn = document.getElementById("learnToggleBtn");
    const readLaterBtn = document.getElementById("readLaterBtn");
    const learnForm = document.getElementById("learnForm");
    const saveStatus = document.getElementById("saveStatus");

    let currentGenre = null;
    let currentArticle = null;
    let loadingTimer = null;

    function showOnly(el) {
        [emptyState, loadingState, errorState, resultState].forEach(s => s.classList.add("is-hidden"));
        el.classList.remove("is-hidden");
    }

    function setSpinesDisabled(disabled) {
        spines.forEach(s => { s.disabled = disabled; });
    }

    function startLoading(genre) {
        currentGenre = genre;
        setSpinesDisabled(true);
        learnForm.classList.add("is-hidden");
        showOnly(loadingState);

        const startedAt = performance.now();
        loadingText.textContent = "searching the stacks\u2026";
        loadingTimer = setInterval(() => {
            const elapsed = ((performance.now() - startedAt) / 1000).toFixed(1);
            loadingText.textContent = `searching the stacks\u2026 (${elapsed}s)`;
        }, 300);

        return startedAt;
    }

    function stopLoading() {
        clearInterval(loadingTimer);
        setSpinesDisabled(false);
    }

    async function findArticle(genre) {
        const startedAt = startLoading(genre);

        try {
            const response = await fetch("/api/find", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ genre }),
            });
            const data = await response.json();
            stopLoading();

            if (!response.ok) {
                errorText.textContent = data.error || "something went wrong.";
                showOnly(errorState);
                return;
            }

            const elapsed = ((performance.now() - startedAt) / 1000).toFixed(1);
            renderResult(data, elapsed);
        } catch (err) {
            stopLoading();
            errorText.textContent = "couldn't reach the server. is the app still running?";
            showOnly(errorState);
        }
    }

    function renderResult(article, elapsedSeconds) {
        currentArticle = article;

        resultGenre.textContent = `shelf: ${article.genre} \u00b7 search: ${article.search_term}`;
        resultTitle.textContent = article.title;
        const minutes = Math.max(1, Math.round(article.words / 200));
        resultMeta.textContent = `${article.words} words \u00b7 ~${minutes} min read`;
        resultTiming.textContent = `found in ${elapsedSeconds}s`;
        openLink.href = article.url;

        learnForm.classList.add("is-hidden");
        learnForm.reset();
        saveStatus.textContent = "";
        learnToggleBtn.disabled = false;
        learnToggleBtn.textContent = "mark as learned";
        readLaterBtn.disabled = false;
        readLaterBtn.textContent = "save for later";

        showOnly(resultState);

    }

    spines.forEach(spine => {
        spine.addEventListener("click", () => findArticle(spine.dataset.genre));
    });

    anotherBtn.addEventListener("click", () => {
        if (currentGenre) findArticle(currentGenre);
    });

    retryBtn.addEventListener("click", () => {
        if (currentGenre) findArticle(currentGenre);
    });

    learnToggleBtn.addEventListener("click", () => {
        learnForm.classList.toggle("is-hidden");
    });

    learnForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!currentArticle) return;

        const rating = document.getElementById("ratingInput").value;
        const keywords = document.getElementById("keywordsInput").value;
        const reflection = document.getElementById("reflectionInput").value;

        saveStatus.textContent = "saving\u2026";

        try {
            const response = await fetch("/api/learn", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: currentArticle.title,
                    url: currentArticle.url,
                    genre: currentArticle.genre,
                    words: currentArticle.words,
                    rating: rating,
                    keywords: keywords,
                    reflection: reflection,
                }),
            });
            const data = await response.json();

            if (!response.ok) {
                saveStatus.textContent = data.error || "couldn't save that.";
                return;
            }

            saveStatus.textContent = "saved to my shelf.";
            learnToggleBtn.disabled = true;
            learnToggleBtn.textContent = "saved";
        } catch (err) {
            saveStatus.textContent = "couldn't reach the server.";
        }
    });

    readLaterBtn.addEventListener("click", async () => {
        if (!currentArticle) return;

        readLaterBtn.disabled = true;
        readLaterBtn.textContent = "saving\u2026";

        try {
            const response = await fetch("/api/read-later", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: currentArticle.title,
                    url: currentArticle.url,
                    genre: currentArticle.genre,
                    words: currentArticle.words,
                }),
            });
            const data = await response.json();

            if (!response.ok) {
                readLaterBtn.disabled = false;
                readLaterBtn.textContent = "save for later";
                alert(data.error || "couldn't save that.");
                return;
            }

            readLaterBtn.textContent = "saved";
        } catch (err) {
            readLaterBtn.disabled = false;
            readLaterBtn.textContent = "save for later";
            alert("couldn't reach the server.");
        }
    });
    
})();
