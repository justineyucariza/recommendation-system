const API_BASE = (() => {
    const { protocol, hostname, port } = window.location;
    const isLocalFile = protocol === "file:";
    const isLocalHost = ["localhost", "127.0.0.1", ""].includes(hostname);

    if (isLocalFile || (isLocalHost && port && port !== "5000")) {
        return "http://127.0.0.1:5000";
    }

    return "";
})();

function resolveApiUrl(path) {

    if (!path) return "";

    if (/^https?:\/\//i.test(path)) return path;

    return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;

}

function getInitials(firstName, lastName, fullName) {

    const initialText = ((firstName || "").charAt(0) + (lastName || "").charAt(0)).trim();

    if (initialText) return initialText.toUpperCase();

    return ((fullName || "").charAt(0) || "-").toUpperCase();

}

function formatDateTime(value) {

    if (!value) return "--";

    const normalized = String(value).replace(" ", "T");
    const date = new Date(normalized);

    if (Number.isNaN(date.getTime())) return value;

    return new Intl.DateTimeFormat("en-US", {
        dateStyle: "medium",
        timeStyle: "short"
    }).format(date);

}

function setAvatarDisplay(imageEl, fallbackEl, imageUrl, initials) {

    if (!imageEl || !fallbackEl) return;

    if (imageUrl) {
        imageEl.src = resolveApiUrl(imageUrl);
        imageEl.classList.remove("hidden");
        fallbackEl.classList.add("hidden");
        return;
    }

    imageEl.classList.add("hidden");
    fallbackEl.classList.remove("hidden");
    fallbackEl.textContent = initials || "--";

}

const app = {

    currentStep: 1,

    currentQuestion: 0,

    totalQuestions: 50,

    questions: [

        {
            question: "I enjoy solving computer problems.",
            category: "IT"
        },

        {
            question: "I like helping children learn.",
            category: "BEED"
        },

        {
            question: "I enjoy business and selling.",
            category: "Marketing"
        },

        {
            question: "I enjoy tourism and travel.",
            category: "Tourism"
        },

        {
            question: "I enjoy learning about law and criminal justice.",
            category: "Criminology"
        },

        {
            question: "I like teaching high school students.",
            category: "BSED"
        }

    ]

};

// ==================================================================
// SESSION — populate header from sessionStorage, redirect if not set
// ==================================================================
(function populateUserHeader() {

    const studentID   = sessionStorage.getItem("studentID");
    const studentName = sessionStorage.getItem("studentName");
    const strand      = sessionStorage.getItem("studentStrand") || "";
    const section     = sessionStorage.getItem("studentSection") || "";
    const firstName   = sessionStorage.getItem("studentFirstName") || "";
    const lastName    = sessionStorage.getItem("studentLastName")  || "";
    const profilePictureUrl = sessionStorage.getItem("studentProfilePicture") || "";

    // If nothing is in session the student isn't logged in — send them back
    if (!studentID || !studentName) {
        window.location.href = "index.html";
        return;
    }

    // Avatar initials (first letter of first + last name)
    const initials = (
        (firstName.charAt(0) || "") +
        (lastName.charAt(0)  || "")
    ).toUpperCase() || studentName.charAt(0).toUpperCase();

    const avatarEl = document.getElementById("headerAvatar");

    const initialsEl = document.getElementById("headerInitials");
    setAvatarDisplay(avatarEl, initialsEl, profilePictureUrl, initials);

    // Full name
    const nameEl = document.getElementById("headerName");
    if (nameEl) nameEl.textContent = studentName;

    // Meta line — only show parts that exist
    const metaParts = [];
    if (studentID) metaParts.push(`Student No. ${studentID}`);
    if (section)   metaParts.push(section);
    if (strand)    metaParts.push(strand);

    const metaEl = document.getElementById("headerMeta");
    if (metaEl) metaEl.textContent = metaParts.join(" • ");

})();

const quizState = {
    currentQuestion: 0,
    answers: new Array(50).fill(null)
};

// 50-question assessment bank, built by cycling through the 6 career
// categories so every category gets roughly even coverage.
const assessmentQuestions = (function () {

    const bank = [
        { q: "I enjoy solving computer or coding problems.", cat: "IT" },
        { q: "I am comfortable troubleshooting technical issues.", cat: "IT" },
        { q: "I like building or designing websites and apps.", cat: "IT" },
        { q: "I am interested in cybersecurity and data protection.", cat: "IT" },
        { q: "I enjoy logical, step-by-step thinking.", cat: "IT" },
        { q: "I like working with computer hardware and networks.", cat: "IT" },
        { q: "I enjoy helping children learn new things.", cat: "BEED" },
        { q: "I am patient when explaining ideas to others.", cat: "BEED" },
        { q: "I like planning fun and creative classroom activities.", cat: "BEED" },
        { q: "I am comfortable speaking in front of young learners.", cat: "BEED" },
        { q: "I enjoy mentoring or tutoring younger students.", cat: "BEED" },
        { q: "I like teaching specific subjects such as Math or English.", cat: "BSED" },
        { q: "I enjoy public speaking and classroom discussions.", cat: "BSED" },
        { q: "I like guiding teenagers through their studies.", cat: "BSED" },
        { q: "I enjoy creating lesson plans and learning materials.", cat: "BSED" },
        { q: "I like explaining difficult topics in a simple way.", cat: "BSED" },
        { q: "I enjoy business, sales, and marketing strategies.", cat: "Marketing" },
        { q: "I like coming up with advertising or branding ideas.", cat: "Marketing" },
        { q: "I am comfortable negotiating or persuading people.", cat: "Marketing" },
        { q: "I enjoy analyzing consumer behavior and market trends.", cat: "Marketing" },
        { q: "I like managing social media or digital campaigns.", cat: "Marketing" },
        { q: "I am interested in starting my own business someday.", cat: "Marketing" },
        { q: "I enjoy traveling and learning about new cultures.", cat: "Tourism" },
        { q: "I like planning trips, tours, or events.", cat: "Tourism" },
        { q: "I am comfortable providing hospitality and customer service.", cat: "Tourism" },
        { q: "I enjoy learning about airlines, hotels, and resorts.", cat: "Tourism" },
        { q: "I like organizing itineraries and travel packages.", cat: "Tourism" },
        { q: "I enjoy learning about law and the justice system.", cat: "Criminology" },
        { q: "I am interested in crime-solving and investigation.", cat: "Criminology" },
        { q: "I like the idea of working in law enforcement.", cat: "Criminology" },
        { q: "I am comfortable handling stressful, high-pressure situations.", cat: "Criminology" },
        { q: "I enjoy studying forensic science and evidence analysis.", cat: "Criminology" }
    ];

    const options = [
        "Strongly Disagree",
        "Disagree",
        "Neutral",
        "Agree",
        "Strongly Agree"
    ];

    const questions = [];

    for (let i = 0; i < 50; i++) {
        const base = bank[i % bank.length];
        questions.push({
            question: base.q,
            category: base.cat,
            options: options
        });
    }

    return questions;

})();

// Simple toast notification shown in the #notification element.
function showNotification(message, type) {

    const el = document.getElementById("notification");

    if (!el) return;

    el.textContent = message;
    el.className = "notification show" + (type ? " " + type : "");

    clearTimeout(showNotification._timer);

    showNotification._timer = setTimeout(() => {
        el.classList.remove("show");
    }, 3000);

}

const dom = {

    stepPanels:
        document.querySelectorAll(".form-step-panel"),

    stepNodes:
        document.querySelectorAll(".step-node"),

    resultBadge:
        document.getElementById("ai-res-badge"),

    resultTitle:
        document.getElementById("ai-res-title"),

    resultReason:
        document.getElementById("ai-res-reasoning"),

    resultPathways:
        document.getElementById("ai-res-pathways")

};

function hideAllStepPanels(){

    dom.stepPanels.forEach(panel=>{

        panel.classList.add("hidden");

    });

}

function showStep(step){

    document
        .getElementById(`step-panel-${step}`)
        ?.classList.remove("hidden");

}

function updateStepNodes(step){

    dom.stepNodes.forEach((node,index)=>{

        node.classList.toggle(

            "active",

            index < step

        );

    });

}

function switchTab(tabIndex) {

    document.querySelectorAll(".nav-item").forEach((btn, index) => {
        btn.classList.toggle("active", index === tabIndex);
    });

    const homeView        = document.getElementById("home-tab-view");
    const assessmentView  = document.getElementById("assessment-tab-view");
    const leaderboardView = document.getElementById("leaderboard-tab-view");
    const sidebar         = document.getElementById("sidebar-filters");
    const search          = document.getElementById("search-container");

    homeView.classList.add("hidden");
    assessmentView.classList.add("hidden");
    leaderboardView.classList.add("hidden");
    sidebar.classList.add("hidden");
    search.classList.add("hidden");

    switch (tabIndex) {

        case 0:
            homeView.classList.remove("hidden");
            closeCourseDetails();
            break;

        case 1:
            homeView.classList.remove("hidden");
            sidebar.classList.remove("hidden");
            search.classList.remove("hidden");
            closeCourseDetails();
            handleSearchAndFilter();
            break;

        case 2:
            assessmentView.classList.remove("hidden");
            break;

        case 3:
            leaderboardView.classList.remove("hidden");
            loadLeaderboard();
            break;

    }

}

function navigateStep(step) {

    const totalSteps = 6;

    if (step < 1 || step > totalSteps) return;

    app.currentStep = step;

    
    document.querySelectorAll(".form-step-panel")
        .forEach(panel => panel.classList.add("hidden"));

    
    document
        .getElementById(`step-panel-${step}`)
        .classList.remove("hidden");

    updateAssessmentProgress();

}

function resetAssessmentFlow(){

    navigateStep(1);

    document.getElementById("student-strand").selectedIndex = 0;

    document.getElementById("student-interests").value="";
    document.getElementById("student-skills").value="";
    document.getElementById("student-career").value="";

    document.getElementById("grade-math").value=85;
    document.getElementById("grade-english").value=85;
    document.getElementById("grade-science").value=85;

    document.querySelectorAll("input[type='radio']")
        .forEach(r=>r.checked=false);

    document.getElementById("quizQuestionContainer").innerHTML="";

    document.getElementById("ai-res-badge").textContent="0%";
    document.getElementById("ai-res-title").textContent="Assessment Reset";
    document.getElementById("ai-res-reasoning").textContent="";
    document.getElementById("ai-res-pathways").innerHTML="";

}

// Quiz timer — tracks seconds from when the quiz panel opens to submission
let _quizStartTime = null;

function buildAndDisplayQuizPanel() {

    navigateStep(5);

    _quizStartTime = Date.now();   // start the clock

    renderAllQuestions();

}

function validateQuiz(){

    // Check quizState.answers array (used by the 50-question assessment)
    for (let i = 0; i < assessmentQuestions.length; i++) {
        if (quizState.answers[i] === null || quizState.answers[i] === undefined) {
            return i;
        }
    }
    return null;

}

function buildQuizScores() {

    // Map quiz category names to the keys the backend expects
    const categoryMap = {
        "IT":          "it",
        "BEED":        "beed",
        "BSED":        "bsed",
        "Marketing":   "marketing",
        "Tourism":     "tourism",
        "Criminology": "criminology"
    };

    // Sum up raw answer values (0=Strongly Disagree … 4=Strongly Agree) per category
    const rawTotals  = {};
    const rawCounts  = {};

    assessmentQuestions.forEach(function(q, i) {
        const cat    = q.category;
        const answer = quizState.answers[i];
        if (answer === null || answer === undefined) return;
        rawTotals[cat]  = (rawTotals[cat]  || 0) + answer;
        rawCounts[cat]  = (rawCounts[cat]  || 0) + 1;
    });

    // Convert to 0–100 percentage (max per question = 4)
    const quizScores = {};
    Object.keys(categoryMap).forEach(function(cat) {
        const backendKey = categoryMap[cat];
        const total      = rawTotals[cat]  || 0;
        const count      = rawCounts[cat]  || 1;
        quizScores[backendKey] = Math.round((total / (count * 4)) * 100);
    });

    return quizScores;

}

async function submitFullAssessmentToAI() {

    const unanswered = validateQuiz();

    if (unanswered !== null) {
        showNotification(`Please answer Question ${unanswered + 1}.`);
        return;
    }

    navigateStep(6);

    const badge    = document.getElementById("ai-res-badge");
    const title    = document.getElementById("ai-res-title");
    const reason   = document.getElementById("ai-res-reasoning");
    const pathways = document.getElementById("ai-res-pathways");

    badge.textContent    = "Analyzing...";
    title.textContent    = "Generating Recommendation...";
    reason.textContent   = "";
    pathways.innerHTML   = "";

    // Collect all student inputs
    const interests  = document.getElementById("student-interests")?.value  || "";
    const skills     = document.getElementById("student-skills")?.value     || "";
    const career     = document.getElementById("student-career")?.value     || "";
    const grades = {
        math:    document.getElementById("grade-math")?.value    || 85,
        english: document.getElementById("grade-english")?.value || 85,
        science: document.getElementById("grade-science")?.value || 85
    };

    const quizScores = buildQuizScores();

    // Time taken in seconds since the quiz panel opened (0 if timer wasn't started)
    const timeTakenSeconds = _quizStartTime
        ? Math.round((Date.now() - _quizStartTime) / 1000)
        : 0;

    // Read student_id from session (set by login)
    const studentId = sessionStorage.getItem("studentID") || null;

    try {

        const response = await fetch(`${API_BASE}/api/recommend`, {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                interests:            interests,
                skills:               skills,
                career_preference:    career,
                preferences:          "",
                grades:               grades,
                quiz_scores:          quizScores,
                student_id:           studentId,
                time_taken_seconds:   timeTakenSeconds
            })
        });

        if (!response.ok) {
            throw new Error("Server returned " + response.status);
        }

        const result = await response.json();

        if (result.error) {
            badge.textContent  = "0%";
            title.textContent  = result.recommended_course_title;
            reason.textContent = result.error;
            return;
        }

        displayRecommendation(result);
        loadLeaderboard();
        loadQuizHistory();

    } catch (err) {

        badge.textContent  = "Error";
        title.textContent  = "Could not connect to the recommendation server.";
        reason.textContent = "Please make sure the Flask server (course.py) is running on port 5000 and try again.";
        console.error("Recommendation API error:", err);

    }

}

function displayRecommendation(result) {

    // FIX: uses real API result instead of hardcoded values
    document.getElementById("ai-res-badge").textContent = result.alignment_score;
    document.getElementById("ai-res-title").textContent = result.recommended_course_title;

    const altCourse = result.alternative_course_title;

    document.getElementById("ai-res-reasoning").innerHTML = `
        Based on your interests, skills, grades, and 50-question assessment:<br><br>
        ✔ Your top match is <strong>${result.recommended_course_title}</strong><br>
        ✔ Alternative recommendation: <strong>${altCourse}</strong><br>
        ✔ Your alignment score reflects how well your profile fits this course.
    `;

    const pathwayList = (result.pathways || [])
        .map(function(p) { return `<li>${p}</li>`; })
        .join("");

    document.getElementById("ai-res-pathways").innerHTML = pathwayList;

}

function viewCourseDetails(course) {

    document.getElementById("courses-main-grid")
        .classList.add("hidden");

    const panel = document.getElementById("course-details-panel");

    panel.classList.remove("hidden");

    document.querySelectorAll(".detail-content-node")
        .forEach(detail => detail.classList.add("hidden"));

    const target = document.getElementById(`details-${course}`);

    if (target) {

        target.classList.remove("hidden");

    }

}

function closeCourseDetails() {

    document.getElementById("course-details-panel")
        .classList.add("hidden");

    document.getElementById("courses-main-grid")
        .classList.remove("hidden");

}

function handleSearchAndFilter() {

    const query = document.getElementById("course-search-input")
        ?.value.toLowerCase().trim() || "";

    const activeFilter = document.querySelector(".filter-opt.active")
        ?.dataset.filter || "all";

    document.querySelectorAll("#courses-main-grid .card").forEach(card => {

        const category = card.dataset.category || "";
        const text = card.textContent.toLowerCase();

        const matchesFilter = activeFilter === "all" || category === activeFilter;
        const matchesSearch = query === "" || text.includes(query);

        card.style.display = matchesFilter && matchesSearch ? "" : "none";

    });

}

document.querySelectorAll(".filter-opt").forEach(filter => {

    filter.addEventListener("click", function () {

        document.querySelectorAll(".filter-opt")
            .forEach(item => item.classList.remove("active"));

        this.classList.add("active");

        handleSearchAndFilter();

    });

});

function updateAssessmentProgress() {

    const progress =
        ((app.currentStep - 1) / 5) * 100;

    const fill =
        document.getElementById("assessmentProgressFill");

    if (fill)
        fill.style.width = progress + "%";

    const stepText =
        document.getElementById("currentStep");

    if (stepText)
        stepText.textContent = app.currentStep;

}

function validateCurrentStep(step) {

    switch(step){

        case 1:

            return document.getElementById("student-strand").value !== "";

        case 2:

            return document.getElementById("student-interests").value.trim() !== "";

        case 3:

            return true;

        case 4:

            return document.getElementById("student-career").value.trim() !== "";

        default:

            return true;

    }

}

function nextStep() {

    if(!validateCurrentStep(app.currentStep)){

        showNotification(
            "Please complete this section first.",
            "warning"
        );

        return;

    }

    navigateStep(app.currentStep + 1);

}

function previousStep(){

    navigateStep(app.currentStep - 1);

}

// Renders ALL 50 questions at once — no Next/Previous needed per question
function renderAllQuestions() {

    const container = document.getElementById("quizQuestionContainer");

    const options = [
        "Strongly Disagree",
        "Disagree",
        "Neutral",
        "Agree",
        "Strongly Agree"
    ];

    container.innerHTML = assessmentQuestions.map(function(q, i) {

        const optionsHTML = options.map(function(label, idx) {
            const checked = quizState.answers[i] === idx ? "checked" : "";
            return `
                <label class="quiz-option">
                    <input type="radio" name="q${i}" value="${idx}" ${checked}>
                    ${label}
                </label>`;
        }).join("");

        return `
            <div class="quiz-question" id="question-block-${i}">
                <h3>${i + 1}. ${q.question}</h3>
                ${optionsHTML}
            </div>`;

    }).join("");

    // Update answered count display
    updateAnsweredCount();

}

// Update the progress counter as student answers questions
function updateAnsweredCount() {

    const answered = quizState.answers.filter(function(a) {
        return a !== null && a !== undefined;
    }).length;

    const counter = document.getElementById("quizCounter");
    if (counter) {
        counter.textContent = `Answered: ${answered} / ${assessmentQuestions.length}`;
    }

    const fill = document.getElementById("quizProgressFill");
    if (fill) {
        fill.style.width = ((answered / assessmentQuestions.length) * 100) + "%";
    }

}

// Listen for any radio change across all questions
document.addEventListener("change", function(e) {

    if (!e.target.matches("input[type='radio']")) return;

    const name  = e.target.name;           // "q0", "q14", etc.
    const index = parseInt(name.replace("q", ""), 10);
    const value = Number(e.target.value);

    quizState.answers[index] = value;

    updateAnsweredCount();

});

// ---------- Header buttons & modals ----------

function openModal(id) {
    document.getElementById(id)?.classList.remove("hidden");
}

function closeModal(id) {
    document.getElementById(id)?.classList.add("hidden");
}

// Logout
document.getElementById("logoutBtn")
    ?.addEventListener("click", () => openModal("logoutModal"));

document.getElementById("cancelLogoutBtn")
    ?.addEventListener("click", () => closeModal("logoutModal"));

document.getElementById("confirmLogoutBtn")
    ?.addEventListener("click", () => {
        closeModal("logoutModal");
        // Clear all session data
        sessionStorage.removeItem("studentID");
        sessionStorage.removeItem("studentName");
        sessionStorage.removeItem("studentFirstName");
        sessionStorage.removeItem("studentLastName");
        sessionStorage.removeItem("studentEmail");
        sessionStorage.removeItem("studentStrand");
        sessionStorage.removeItem("studentSection");
        window.location.href = "index.html";
    });

// Settings
document.getElementById("settingsBtn")
    ?.addEventListener("click", () => {
        openModal("settingsModal");
        syncSettingsProfilePicturePreview();
        loadQuizHistory();
    });

document.getElementById("chooseProfileBtn")
    ?.addEventListener("click", () => {
        document.getElementById("settingsProfileInput")?.click();
    });

document.getElementById("settingsProfileInput")
    ?.addEventListener("change", function () {
        const file = this.files && this.files[0];
        const preview = document.getElementById("settingsProfilePreview");
        const fallback = document.getElementById("settingsProfileFallback");

        if (!file || !preview || !fallback) return;

        preview.src = URL.createObjectURL(file);
        preview.classList.remove("hidden");
        fallback.classList.add("hidden");
    });

document.getElementById("cancelSettingsBtn")
    ?.addEventListener("click", () => {
        // Revert checkbox to whatever is actually saved — so it doesn't stay visually toggled
        const saved = localStorage.getItem("acadsync-dark-mode") === "true";
        const checkbox = document.getElementById("settings-darkmode");
        if (checkbox) checkbox.checked = saved;
        syncSettingsProfilePicturePreview();
        closeModal("settingsModal");
    });

document.getElementById("saveSettingsBtn")
    ?.addEventListener("click", async () => {

        const isDark = document.getElementById("settings-darkmode")?.checked || false;
        localStorage.setItem("acadsync-dark-mode", isDark);
        applyDarkMode(isDark);

        const fileInput = document.getElementById("settingsProfileInput");
        const file = fileInput && fileInput.files && fileInput.files[0];

        try {
            if (file) {
                await uploadProfilePicture(file);
                syncHeaderProfilePicture();
            }
        } catch (err) {
            showNotification(err.message || "Could not upload profile picture.", "warning");
            return;
        }

        closeModal("settingsModal");
        showNotification("Settings saved.", "success");
        loadLeaderboard();
    });

// Change Password (now launched from inside the Settings modal)
document.getElementById("openChangePwdBtn")
    ?.addEventListener("click", () => {
        closeModal("settingsModal");
        openModal("passwordModal");
    });

document.getElementById("cancelPwdBtn")
    ?.addEventListener("click", () => closeModal("passwordModal"));

document.getElementById("sendCodeBtn")
    ?.addEventListener("click", () => {
        showNotification("Verification code sent.", "success");
    });

document.getElementById("savePwdBtn")
    ?.addEventListener("click", () => {

        const newPwd = document.getElementById("pwd-new")?.value || "";
        const confirmPwd = document.getElementById("pwd-confirm")?.value || "";

        if (!newPwd || !confirmPwd) {
            showNotification("Please fill in both password fields.", "warning");
            return;
        }

        if (newPwd !== confirmPwd) {
            showNotification("Passwords do not match.", "warning");
            return;
        }

        closeModal("passwordModal");
        showNotification("Password changed successfully.", "success");

    });

function syncHeaderProfilePicture() {

    const firstName = sessionStorage.getItem("studentFirstName") || "";
    const lastName = sessionStorage.getItem("studentLastName") || "";
    const studentName = sessionStorage.getItem("studentName") || "";
    const profilePictureUrl = sessionStorage.getItem("studentProfilePicture") || "";
    const initials = getInitials(firstName, lastName, studentName);

    setAvatarDisplay(
        document.getElementById("headerAvatar"),
        document.getElementById("headerInitials"),
        profilePictureUrl,
        initials
    );

}

function syncSettingsProfilePicturePreview() {

    const firstName = sessionStorage.getItem("studentFirstName") || "";
    const lastName = sessionStorage.getItem("studentLastName") || "";
    const studentName = sessionStorage.getItem("studentName") || "";
    const profilePictureUrl = sessionStorage.getItem("studentProfilePicture") || "";
    const initials = getInitials(firstName, lastName, studentName);

    setAvatarDisplay(
        document.getElementById("settingsProfilePreview"),
        document.getElementById("settingsProfileFallback"),
        profilePictureUrl,
        initials
    );

}

async function uploadProfilePicture(file) {

    const studentId = sessionStorage.getItem("studentID");

    if (!studentId) {
        throw new Error("You must be logged in to update your profile picture.");
    }

    const formData = new FormData();
    formData.append("student_id", studentId);
    formData.append("profile_picture", file);

    const response = await fetch(`${API_BASE}/api/profile-picture`, {
        method: "POST",
        body: formData
    });

    const result = await response.json();

    if (!response.ok || !result.success) {
        throw new Error(result.message || "Could not upload profile picture.");
    }

    sessionStorage.setItem("studentProfilePicture", result.profilePictureUrl || "");
    syncHeaderProfilePicture();
    syncSettingsProfilePicturePreview();

    return result;

}

async function loadQuizHistory() {

    const container = document.getElementById("quizHistoryList");
    const studentId = sessionStorage.getItem("studentID");

    if (!container || !studentId) return;

    container.innerHTML = '<div class="quiz-history-loading">Loading quiz history…</div>';

    try {
        const response = await fetch(`${API_BASE}/api/quiz-history/${studentId}`);
        const data = await response.json();

        if (!data.success || !Array.isArray(data.history) || !data.history.length) {
            container.innerHTML = '<div class="quiz-history-empty">No quiz history yet.</div>';
            return;
        }

        container.innerHTML = data.history.map(function (entry) {
            const matchText = entry.course_match ? `${entry.course_match}` : "N/A";
            return `
                <div class="quiz-history-item">
                    <div class="quiz-history-main">
                        <div class="quiz-history-title">Attempt #${entry.attempt}</div>
                        <div class="quiz-history-meta">${formatDateTime(entry.created_at)}</div>
                        <div class="quiz-history-meta">Recommended course: ${entry.recommended_course}</div>
                    </div>
                    <div class="quiz-history-score">
                        <strong>${entry.quiz_score}%</strong>
                        <span>Match: ${matchText}</span>
                    </div>
                </div>`;
        }).join("");

    } catch (err) {
        container.innerHTML = '<div class="quiz-history-empty">Could not load quiz history.</div>';
        console.error("Quiz history error:", err);
    }

}

// ---------- Dark Mode ----------

function applyDarkMode(isDark) {
    document.body.classList.toggle("dark-mode", isDark);
}

// Restore saved preference on page load
(function initDarkMode() {

    const saved = localStorage.getItem("acadsync-dark-mode") === "true";
    const checkbox = document.getElementById("settings-darkmode");

    applyDarkMode(saved);

    if (checkbox) checkbox.checked = saved;

})();

// FIX: Dark mode only applies when Save is clicked, NOT on toggle change.
// The live-preview listener has been removed.
// cancelSettingsBtn now reverts the checkbox to the saved state so it doesn't look toggled.

// Switches the email/phone label+placeholder on the password modal
function toggleMethodInput() {

    const method = document.getElementById("pwd-method")?.value;
    const label = document.getElementById("method-label");
    const input = document.getElementById("pwd-contact-input");

    if (!label || !input) return;

    if (method === "phone") {
        label.textContent = "Enter Mobile Number";
        input.placeholder = "09XXXXXXXXX";
    } else {
        label.textContent = "Enter Email Address";
        input.placeholder = "student@email.com";
    }

}

// Click outside a modal box closes it
document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
        if (e.target === overlay) {
            overlay.classList.add("hidden");
        }
    });
});

// ---------- Quiz panel navigation buttons ----------
// Now that all 50 questions show at once:
//   Previous → goes back to Step 4 (grades)
//   Next     → validates all answered, then submits for recommendation

document.getElementById("prevQuestionBtn")
    ?.addEventListener("click", function () {
        previousStep();
    });

document.getElementById("nextQuestionBtn")
    ?.addEventListener("click", function () {

        const unanswered = validateQuiz();

        if (unanswered !== null) {
            // Scroll to the first unanswered question and highlight it
            const block = document.getElementById("question-block-" + unanswered);
            if (block) {
                block.style.outline = "2px solid #e53e3e";
                block.scrollIntoView({ behavior: "smooth", block: "center" });
                // Remove highlight after 2 seconds
                setTimeout(function () { block.style.outline = ""; }, 2000);
            }
            showNotification(
                "Please answer Question " + (unanswered + 1) + " before continuing.",
                "warning"
            );
            return;
        }

        submitFullAssessmentToAI();

    });

// Also show the finishQuizArea submit button area once all questions load
// (it's hidden by default; we re-purpose "Next" above so we can hide it)
(function hideOldFinishArea() {
    const area = document.getElementById("finishQuizArea");
    if (area) area.style.display = "none";
})();

// ==================================================================
// LEADERBOARD
// ==================================================================

async function loadLeaderboard() {

    const tbody  = document.getElementById("leaderboardBody");
    const myCard = document.getElementById("myRankCard");
    const lastUpdatedEl = document.getElementById("leaderboardUpdatedAt");

    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="5" class="lb-loading">Loading…</td></tr>';
    if (myCard) myCard.classList.add("hidden");

    const currentStudentId = sessionStorage.getItem("studentID");

    try {

        const res  = await fetch(`${API_BASE}/api/leaderboard`);
        const data = await res.json();

        if (lastUpdatedEl) {
            lastUpdatedEl.textContent = data.last_updated
                ? `Last updated: ${formatDateTime(data.last_updated)}`
                : "Last updated: No quiz results yet.";
        }

        if (!data.success || !data.leaderboard.length) {
            tbody.innerHTML =
                '<tr><td colspan="5" class="lb-loading">No quiz results yet. Complete the assessment to appear on the leaderboard!</td></tr>';
            return;
        }

        let myEntry = null;

        tbody.innerHTML = data.leaderboard.map(function (entry) {

            const isMe = String(entry.studentID) === String(currentStudentId);
            if (isMe) myEntry = entry;

            const rankCell  = `<td class="lb-rank ${entry.rank <= 3 ? `lb-top${entry.rank}` : ""}">#${entry.rank}</td>`;

            const avatarMarkup = entry.profilePictureUrl
                ? `<img src="${resolveApiUrl(entry.profilePictureUrl)}" alt="${entry.name} profile picture">`
                : `<span class="lb-student-fallback">${getInitials(entry.name.split(" ")[0], entry.name.split(" ").slice(1).join(" "), entry.name)}</span>`;

            const rowClass = isMe ? ' class="lb-row-me"' : "";

            return `
                <tr${rowClass}>
                    ${rankCell}
                    <td>
                        <div class="lb-student-cell">
                            <div class="lb-student-avatar">${avatarMarkup}</div>
                            <div class="lb-student-text">
                                <strong>${entry.name}</strong>
                                <span>${entry.strand}${entry.section && entry.section !== "—" ? ` • ${entry.section}` : ""}</span>
                            </div>
                        </div>
                    </td>
                    <td>${entry.recommended_course}</td>
                    <td class="lb-score">${entry.total_score}%</td>
                    <td class="lb-time">${entry.time_display}</td>
                </tr>`;

        }).join("");

        // Show the current student's personal card at the top
        if (myEntry && myCard) {
            document.getElementById("myRankBadge").textContent = `#${myEntry.rank}`;
            document.getElementById("myRankName").textContent  = myEntry.name;
            document.getElementById("myRankAvatarFallback").textContent = getInitials(myEntry.name.split(" ")[0], myEntry.name.split(" ").slice(1).join(" "), myEntry.name);
            setAvatarDisplay(
                document.getElementById("myRankAvatar"),
                document.getElementById("myRankAvatarFallback"),
                myEntry.profilePictureUrl,
                getInitials(myEntry.name.split(" ")[0], myEntry.name.split(" ").slice(1).join(" "), myEntry.name)
            );
            document.getElementById("myRankDetail").textContent =
                `Score: ${myEntry.total_score}%  •  Course: ${myEntry.recommended_course}  •  Time: ${myEntry.time_display}`;
            myCard.classList.remove("hidden");
        }

    } catch (err) {
        tbody.innerHTML =
            '<tr><td colspan="5" class="lb-loading">Could not load leaderboard. Make sure course.py is running.</td></tr>';
        console.error("Leaderboard error:", err);
    }

}
