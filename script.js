/**
 * VORTEX LOGIC ENGINE
 * Enhanced with Fibonacci Progressive Decrement, Auto-Restore & Default Audio
 */

// --- DOM ELEMENTS ---
const ui = {
    ring: document.getElementById('progress-ring'),
    label: document.getElementById('phase-label'),
    timer: document.getElementById('timer-display'),
    btnToggle: document.getElementById('btn-toggle'),
    btnReset: document.getElementById('btn-reset'),
    inputs: [
        document.getElementById('t-inhale'),
        document.getElementById('t-hold1'),
        document.getElementById('t-exhale'),
        document.getElementById('t-hold2')
    ],
    soundCheck: document.getElementById('sound-check')
};

// --- CONSTANTS & CONFIG ---
const PHASES = ['INHALE', 'HOLD', 'EXHALE', 'HOLD'];
const CIRCUMFERENCE = 753.98; 

// --- STATE ---
let state = {
    isRunning: false,
    cycleStartTime: null, 
    pauseOffset: 0,       
    currentPhaseIndex: 0,
    durations: [13, 0, 13, 0], 
    originalDurations: null, // Snapshot of settings at session start
    animationFrame: null
};

// Initialize SVG
ui.ring.style.strokeDasharray = `${CIRCUMFERENCE} ${CIRCUMFERENCE}`;
ui.ring.style.strokeDashoffset = CIRCUMFERENCE;

// --- AUDIO ENGINE ---
let audioCtx = null;

function playTone(frequency = 440, type = 'sine', duration = 0.1) {
    if (!ui.soundCheck.checked) return;
    // Init context on user interaction
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === 'suspended') audioCtx.resume();

    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = type;
    osc.frequency.value = frequency;
    
    gain.gain.setValueAtTime(0, audioCtx.currentTime);
    gain.gain.linearRampToValueAtTime(0.1, audioCtx.currentTime + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
    
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + duration);
}

// --- FIBONACCI LOGIC ---

function generateFibSequence(max) {
    const seq = [1, 1];
    while (seq[seq.length - 1] < max) {
        seq.push(seq[seq.length - 1] + seq[seq.length - 2]);
    }
    return seq;
}

function getNextFibValue(current) {
    if (current <= 1) return 1;
    const seq = generateFibSequence(current);
    for (let i = seq.length - 1; i >= 0; i--) {
        if (seq[i] < current) return seq[i];
    }
    return 1;
}

function applyNextFibonacciCycle() {
    const nextDurations = state.durations.map(d => {
        if (d === 0) return 0; 
        return getNextFibValue(d);
    });

    state.durations = nextDurations;

    // Update DOM inputs to reflect new state
    ui.inputs.forEach((input, i) => {
        input.value = state.durations[i];
    });
}

// --- CORE FUNCTIONS ---

function updateDurationsFromInputs() {
    state.durations = ui.inputs.map(input => Math.max(0, parseFloat(input.value) || 0));
}

function formatTime(seconds) {
    return Math.abs(seconds).toFixed(1);
}

function render(phaseIdx, phaseProgress, timeLeft) {
    ui.label.textContent = PHASES[phaseIdx];
    ui.timer.textContent = formatTime(timeLeft);
    const offset = CIRCUMFERENCE - (phaseProgress * CIRCUMFERENCE);
    ui.ring.style.strokeDashoffset = offset;
}

function loop(timestamp) {
    if (!state.isRunning) return;

    let elapsedInCycle = (timestamp - state.cycleStartTime) / 1000;
    const cycleDuration = state.durations.reduce((a, b) => a + b, 0);
    
    // --- CYCLE COMPLETION CHECK ---
    if (cycleDuration > 0 && elapsedInCycle >= cycleDuration) {
        // Check if we just finished the "floor" cycle (everything is <= 1)
        const isFloorCycle = state.durations.every(d => d === 0 || d <= 1);

        if (isFloorCycle) {
            // DONE. Stop and Restore.
            playTone(220, 'sine', 0.5);
            reset(); 
            return;
        }

        // Otherwise, proceed to next level
        state.cycleStartTime += (cycleDuration * 1000);
        elapsedInCycle -= cycleDuration;
        applyNextFibonacciCycle();
    }

    // Calculate Phase
    let timeAccumulator = 0;
    let activePhaseIndex = 0;
    let timeInCurrentPhase = 0;

    for (let i = 0; i < 4; i++) {
        if (elapsedInCycle < timeAccumulator + state.durations[i]) {
            activePhaseIndex = i;
            timeInCurrentPhase = elapsedInCycle - timeAccumulator;
            break;
        }
        timeAccumulator += state.durations[i];
    }

    if (activePhaseIndex !== state.currentPhaseIndex) {
        const pitch = activePhaseIndex === 0 ? 880 : 440; 
        playTone(pitch, 'sine', 0.15);
        state.currentPhaseIndex = activePhaseIndex;
    }

    const duration = state.durations[activePhaseIndex];
    const progress = duration > 0 ? timeInCurrentPhase / duration : 1;
    const timeLeft = Math.max(0, duration - timeInCurrentPhase);

    render(activePhaseIndex, progress, timeLeft);
    state.animationFrame = requestAnimationFrame(loop);
}

// --- CONTROLS ---

function start() {
    if (state.isRunning) return;
    
    if (state.cycleStartTime === null) {
        // FRESH START
        updateDurationsFromInputs();
        // Capture snapshot of Original Settings
        state.originalDurations = [...state.durations];
        state.cycleStartTime = performance.now();
    } else {
        // RESUME
        state.cycleStartTime = performance.now() - state.pauseOffset;
    }
    
    state.isRunning = true;
    ui.btnToggle.textContent = "PAUSE";
    ui.btnToggle.style.background = "var(--accent-color)";
    
    playTone(660, 'triangle', 0.05);
    state.animationFrame = requestAnimationFrame(loop);
}

function pause() {
    if (!state.isRunning) return;
    state.isRunning = false;
    ui.btnToggle.textContent = "RESUME";
    ui.btnToggle.style.background = "";
    cancelAnimationFrame(state.animationFrame);
    state.pauseOffset = performance.now() - state.cycleStartTime;
}

function toggle() {
    if (state.isRunning) pause();
    else start();
}

function reset() {
    const isSessionActive = (state.cycleStartTime !== null);

    state.isRunning = false;
    cancelAnimationFrame(state.animationFrame);
    state.cycleStartTime = null;
    state.pauseOffset = 0;
    state.currentPhaseIndex = -1;
    
    ui.btnToggle.textContent = "START";
    ui.btnToggle.style.background = "";
    
    ui.ring.style.strokeDashoffset = CIRCUMFERENCE;
    ui.label.textContent = "READY";
    
    if (isSessionActive && state.originalDurations) {
        // Restore Original Values
        state.durations = [...state.originalDurations];
        ui.inputs.forEach((input, i) => {
            input.value = state.durations[i];
        });
        ui.timer.textContent = formatTime(state.durations[0]);
    } else {
        ui.timer.textContent = formatTime(state.durations[0]);
    }
}

// --- EVENT LISTENERS ---

ui.btnToggle.addEventListener('click', toggle);
ui.btnReset.addEventListener('click', reset);

ui.inputs.forEach(input => {
    input.addEventListener('change', () => {
        // Allow changing inputs only when stopped/idle
        if (!state.isRunning && state.cycleStartTime === null) {
            updateDurationsFromInputs();
            ui.timer.textContent = formatTime(state.durations[0]);
        }
    });
});

document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT') return;
    if (e.code === 'Space') { e.preventDefault(); toggle(); }
    if (e.code === 'KeyR') { reset(); }
});

// Initial Setup
updateDurationsFromInputs();
ui.timer.textContent = formatTime(state.durations[0]);
