// ===== ELEMENT REFERENCES (Sab ek jagah) =====
const topicInput = document.getElementById('topicInput');
const startBtn = document.getElementById('startBtn');
const languageSelect = document.getElementById('languageSelect');
const status = document.getElementById('status');
const customAvatarSelect = document.getElementById('customAvatarSelect');
const customSideSelect = document.getElementById('customSideSelect');
const themeToggle = document.getElementById('themeToggle');

// Custom avatar creator elements
const photoInput = document.getElementById('photoInput');
const photoPreview = document.getElementById('photoPreview');
const avatarName = document.getElementById('avatarName');
const avatarPersonality = document.getElementById('avatarPersonality');
const avatarLanguage = document.getElementById('avatarLanguage');
const saveAvatarBtn = document.getElementById('saveAvatarBtn');
const savedAvatarsDiv = document.getElementById('savedAvatars');

// ===== STATE =====
const agents = ['pro', 'con', 'judge'];
let eventSource = null;
let currentPhotoBase64 = null;
let customAvatarImages = {};  // side -> {silent, half, open}

const RTL_LANGUAGES = ['ur', 'ar'];

// ===== DEFAULT AVATAR IMAGES =====
const avatarImages = {
    pro: {
        silent: 'avatars/pro.jpg',
        half:   'avatars/pro-mouth-half.jpg',
        open:   'avatars/pro-mouth-open.jpg',
    },
    con: {
        silent: 'avatars/conn.jpg',
        half:   'avatars/conn-mouth-half.jpg',
        open:   'avatars/conn-mouth-open.jpg',
    },
    judge: {
        silent: 'avatars/judge.jpg',
        half:   'avatars/judge-mouth-half.jpg',
        open:   'avatars/judge-mouth-open.jpg',
    },
};

// ===== DEBATE STATE MANAGEMENT =====
function clearAll() {
    agents.forEach(a => {
        const el = document.getElementById(`text-${a}`);
        el.textContent = '';
        el.classList.remove('rtl');
        document.getElementById(`card-${a}`).classList.remove('active');

        if (customAvatarImages[a]) {
            delete customAvatarImages[a];
        }
        document.getElementById(`avatar-${a}`).src = avatarImages[a].silent;
    });

    document.querySelector('#card-pro h3').innerHTML = 'Alex <span class="role">Pro</span>';
    document.querySelector('#card-con h3').innerHTML = 'Maya <span class="role">Con</span>';
}

function setActive(agent) {
    agents.forEach(a => {
        document.getElementById(`card-${a}`).classList.remove('active');
        // Only reset if NOT the active one
        if (a !== agent) {
            const imgs = customAvatarImages[a] || avatarImages[a];
            document.getElementById(`avatar-${a}`).src = imgs.silent;
        }
    });
    document.getElementById(`card-${agent}`).classList.add('active');
}

// ===== TTS + MOUTH ANIMATION =====
async function speakWithAudio(agent, text, language = 'en', images = null) {
    const imgs = images || avatarImages[agent];
    return new Promise(async (resolve) => {
        try {
            const resp = await fetch('/api/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, agent, language }),
            });

            if (!resp.ok) throw new Error(`TTS failed: ${resp.status}`);

            const audioBlob = await resp.blob();
            console.log(`Audio ${agent} (${language}): ${audioBlob.size} bytes`);

            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);

            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const source = audioCtx.createMediaElementSource(audio);
            const analyser = audioCtx.createAnalyser();
            analyser.fftSize = 256;
            source.connect(analyser);
            analyser.connect(audioCtx.destination);

            const dataArray = new Uint8Array(analyser.frequencyBinCount);
            const avatarEl = document.getElementById(`avatar-${agent}`);
            let animFrame;
            let lastState = 'silent';
            let lastSwitchTime = 0;
            let lastAvg = 0;
            const SWITCH_INTERVAL = 1500;
            const SMOOTHING = 0.7;

            const animate = (timestamp) => {
                analyser.getByteFrequencyData(dataArray);
                let sum = 0;
                for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
                let avg = sum / dataArray.length;
                avg = lastAvg * SMOOTHING + avg * (1 - SMOOTHING);
                lastAvg = avg;

                let state;
                if (avg < 10)       state = 'silent';
                else if (avg < 50)  state = 'half';
                else                state = 'open';

                if (state !== lastState && timestamp - lastSwitchTime > SWITCH_INTERVAL) {
                    avatarEl.src = imgs[state];
                    lastState = state;
                    lastSwitchTime = timestamp;
                }

                animFrame = requestAnimationFrame(animate);
            };

            audio.onplay = () => {
                avatarEl.src = imgs.silent;
                lastState = 'silent';
                lastSwitchTime = 0;
                document.getElementById(`card-${agent}`).classList.add('speaking');
                animFrame = requestAnimationFrame(animate);
            };

            audio.onended = () => {
                cancelAnimationFrame(animFrame);
                avatarEl.src = imgs.silent;
                document.getElementById(`card-${agent}`).classList.remove('speaking');
                URL.revokeObjectURL(audioUrl);
                audioCtx.close();
                resolve();
            };

            audio.onerror = () => {
                cancelAnimationFrame(animFrame);
                avatarEl.src = imgs.silent;
                document.getElementById(`card-${agent}`).classList.remove('speaking');
                URL.revokeObjectURL(audioUrl);
                resolve();
            };

            await audio.play();
        } catch (e) {
            console.error('TTS error:', e);
            resolve();
        }
    });
}

// ===== START DEBATE =====
async function startDebate() {
    const topic = topicInput.value.trim();
    const language = languageSelect.value;
    const customId = customAvatarSelect.value;
    const customSide = customSideSelect.value;

    if (!topic) {
        status.textContent = 'Please enter a topic.';
        return;
    }

    startBtn.disabled = true;
    clearAll();
    customAvatarImages = {};

    status.textContent = `Debate in progress (${language})...`;

    if (eventSource) eventSource.close();

    const turnQueue = [];
    let processing = false;
    let currentLanguage = language;

    async function processQueue() {
        if (processing) return;
        processing = true;
        while (turnQueue.length > 0) {
            const turn = turnQueue.shift();
            setActive(turn.agent);
            status.textContent = `${turn.agent.toUpperCase()} is speaking...`;

            const textEl = document.getElementById(`text-${turn.agent}`);
            textEl.textContent = turn.text;
            if (RTL_LANGUAGES.includes(turn.language)) {
                textEl.classList.add('rtl');
            } else {
                textEl.classList.remove('rtl');
            }

            const images = customAvatarImages[turn.agent] || avatarImages[turn.agent];
            document.getElementById(`avatar-${turn.agent}`).src = images.silent;

            await speakWithAudio(turn.agent, turn.text, turn.language, images);
            await new Promise(r => setTimeout(r, 400));
        }
        processing = false;
    }

    const params = new URLSearchParams({ topic, language });
    if (customId) {
        params.append('custom_avatar', customId);
        params.append('custom_side', customSide);
    }
    eventSource = new EventSource(`/api/debate?${params}`);

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'language') {
            currentLanguage = data.language;
        }

        if (data.type === 'custom_avatar') {
            const side = data.side;
            const photo = data.avatar.photo;

            document.querySelector(`#card-${side} h3`).innerHTML =
                `${data.avatar.name} <span class="role">${side === 'pro' ? 'Pro' : 'Con'}</span>`;

            customAvatarImages[side] = {
                silent: photo,
                half: photo,
                open: photo,
            };

            document.getElementById(`avatar-${side}`).src = photo;
        }

        if (data.type === 'text') {
            turnQueue.push({
                agent: data.agent,
                text: data.text,
                language: data.language || currentLanguage,
            });
            processQueue();
        }

        if (data.type === 'done') {
            status.textContent = 'Debate complete.';
            startBtn.disabled = false;
            eventSource.close();
        }
    };

    eventSource.onerror = () => {
        status.textContent = 'Connection error. Try again.';
        startBtn.disabled = false;
        eventSource.close();
    };
}

// ===== CUSTOM AVATAR CREATOR =====
photoPreview.addEventListener('click', function(e) {
    e.preventDefault();
    e.stopPropagation();
    photoInput.click();
});

photoInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
        alert('Photo 5MB se choti honi chahiye');
        return;
    }

    const reader = new FileReader();
    reader.onload = (ev) => {
        currentPhotoBase64 = ev.target.result;
        photoPreview.innerHTML = `<img src="${currentPhotoBase64}" alt="Avatar">`;
    };
    reader.readAsDataURL(file);
});

saveAvatarBtn.addEventListener('click', async () => {
    if (!currentPhotoBase64) {
        alert('Pehle photo upload karo');
        return;
    }
    if (!avatarName.value.trim()) {
        alert('Naam daalo');
        return;
    }

    saveAvatarBtn.disabled = true;
    saveAvatarBtn.textContent = 'Saving...';

    try {
        const resp = await fetch('/api/avatar/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: avatarName.value.trim(),
                personality: avatarPersonality.value,
                language: avatarLanguage.value,
                photo_base64: currentPhotoBase64,
            }),
        });

        const data = await resp.json();
        if (data.id) {
            alert(`✅ Avatar "${avatarName.value}" save ho gaya!`);
            currentPhotoBase64 = null;
            photoPreview.innerHTML = '<span>+ Upload Photo</span>';
            avatarName.value = '';
            loadSavedAvatars();
        }
    } catch (e) {
        console.error(e);
        alert('Save nahi hua, dobara try karo');
    } finally {
        saveAvatarBtn.disabled = false;
        saveAvatarBtn.textContent = 'Save Avatar';
    }
});

async function loadSavedAvatars() {
    try {
        const resp = await fetch('/api/avatar/list');
        const avatars = await resp.json();

        savedAvatarsDiv.innerHTML = avatars.map(a => `
            <div class="saved-avatar">
                <div class="saved-avatar-wrapper">
                    <img src="${a.photo}" alt="${a.name}">
                    <button class="delete-avatar-btn" data-id="${a.id}" title="Delete">✕</button>
                </div>
                <div>${a.name}</div>
            </div>
        `).join('');

        customAvatarSelect.innerHTML = '<option value="">👥 Default Avatars</option>' +
            avatars.map(a => `<option value="${a.id}">🎭 ${a.name}</option>`).join('');

        // ⭐ Delete buttons ke liye event listeners
        document.querySelectorAll('.delete-avatar-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const id = btn.dataset.id;
                const name = btn.parentElement.nextElementSibling.textContent;
                
                if (!confirm(`Delete avatar "${name}"?`)) return;

                try {
                    const delResp = await fetch(`/api/avatar/${id}`, {
                        method: 'DELETE',
                    });
                    const delData = await delResp.json();
                    if (delData.status === 'deleted') {
                        console.log('Deleted avatar:', id);
                        loadSavedAvatars();  // refresh list
                    }
                } catch (err) {
                    console.error('Delete failed:', err);
                    alert('Delete nahi hua, dobara try karo');
                }
            });
        });
    } catch (e) {
        console.error(e);
    }
}

// ===== THEME TOGGLE =====
const savedTheme = localStorage.getItem('theme') || 'dark';
if (savedTheme === 'light') {
    document.body.classList.add('light');
    themeToggle.textContent = '☀️';
} else {
    themeToggle.textContent = '🌙';
}

themeToggle.addEventListener('click', () => {
    document.body.classList.toggle('light');
    const isLight = document.body.classList.contains('light');
    themeToggle.textContent = isLight ? '☀️' : '🌙';
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
});

// ===== EVENT LISTENERS =====
startBtn.addEventListener('click', startDebate);
topicInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') startDebate();
});

// ===== INIT =====
loadSavedAvatars();