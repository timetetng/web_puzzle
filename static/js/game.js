document.addEventListener('DOMContentLoaded', () => {
    // --- 常量定义 ---
    const sleep = ms => new Promise(res => setTimeout(res, ms));
    const ANIMATION_SWAP_SPEED_MS = 150;
    const CELL_SIZE = 80;
    const COLORS = {
        BACKGROUND: '#323232', GRID: '#555555', ACTIVE_BG: '#464646',
        INACTIVE_BG: '#3a3a3a', LINE_CONNECTED: '#65e065', LINE_DISCONNECTED: '#808080',
        DIAMOND_LIT: '#c0ffc0', LINE_LIT: '#a0fffa', COMPLETION_HIGHLIGHT: '#65e065'
    };
    const ANIMATION_LIT_DURATION = 600;
    const ANIMATION_COMPLETION_DURATION = 700;
    const ANIMATION_COMPLETION_RADIUS_START = 0;
    const ANIMATION_COMPLETION_RADIUS_END_FACTOR = 1.2;

    // --- DOM 元素引用 ---
    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');
    const modeSelection = document.getElementById('mode-selection');
    const classicModeBtn = document.getElementById('classic-mode-btn');
    const timedModeBtn = document.getElementById('timed-mode-btn');
    const leaderboardBtn = document.getElementById('leaderboard-btn');
    const gameArea = document.getElementById('game-area');
    const infoPanel = document.getElementById('infoPanel');
    const exitGameBtn = document.getElementById('exit-game-btn');
    const classicControls = document.getElementById('classic-controls');
    const timedControls = document.getElementById('timed-controls');
    const difficultyBtns = document.querySelectorAll('.difficulty-btn');
    const retryBtnClassic = document.getElementById('retryBtnClassic');
    const retryBtnTimed = document.getElementById('retryBtnTimed');
    const solveBtn = document.getElementById('solveBtn');
    const uploadBtn = document.getElementById('uploadBtn');
    const imageUploader = document.getElementById('imageUploader');
    const customBtn = document.getElementById('customBtn');
    const customizationUI = document.getElementById('customization-ui');
    const customWidthInput = document.getElementById('customWidth');
    const customHeightInput = document.getElementById('customHeight');
    const createGridBtn = document.getElementById('createGridBtn');
    const customActions = customizationUI.querySelector('.custom-actions');
    const generateCustomBtn = document.getElementById('generateCustomBtn');
    const cancelCustomBtn = document.getElementById('cancelCustomBtn');
    const playAgainBtn = document.getElementById('playAgainBtn');
    const timedInfo = document.getElementById('timed-info');
    const puzzleCounterEl = document.getElementById('puzzle-counter');
    const timerEl = document.getElementById('timer');
    const resultsModal = document.getElementById('results-modal');
    const resultsPlayAgainBtn = document.getElementById('results-play-again-btn');
    const resultsExitBtn = document.getElementById('results-exit-btn');
    const submitScoreBtn = document.getElementById('submit-score-btn');
    const usernameInput = document.getElementById('username-input');
    const leaderboardModal = document.getElementById('leaderboard-modal');
    const closeLeaderboardBtn = document.getElementById('close-leaderboard-btn');
    const leaderboardDifficultySelect = document.getElementById('leaderboard-difficulty-select');
    const leaderboardTypeSelect = document.getElementById('leaderboard-type-select');
    const leaderboardDisplay = document.getElementById('leaderboard-display');

    // --- 游戏状态变量 ---
    let gameMode = null, boardState = null, solutionState = null, initialBoardState = null, countdownInterval = null;
    let boardSize = { width: 0, height: 0 };
    let isAnimating = false, isDragging = false, isCustomizing = false, isCountingDown = false;
    let draggedTile = null, lastCustomShape = null, timerInterval = null;
    let dragStartPos = { x: 0, y: 0 }, originalGridPos = { r: 0, c: 0 };
    let customShape = [], challengeState = {};
    let activeAnimations = [], animationFrameId = null, puzzleJustSolved = false;
    let isConfettiRunning = false;
    function interpolateColor(c1, c2, f) {
        const r1 = parseInt(c1.slice(1, 3), 16), g1 = parseInt(c1.slice(3, 5), 16), b1 = parseInt(c1.slice(5, 7), 16);
        const r2 = parseInt(c2.slice(1, 3), 16), g2 = parseInt(c2.slice(3, 5), 16), b2 = parseInt(c2.slice(5, 7), 16);
        const r = Math.round(r1 + f * (r2 - r1)), g = Math.round(g1 + f * (g2 - g1)), b = Math.round(b1 + f * (b2 - b1));
        return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
    }

    function gameLoop(timestamp) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        drawBoardBase();
        const vs = calculateVisualState(timestamp);
        drawAllTiles(vs);
        activeAnimations.forEach(a => { if (a.type === 'completion-diffuse') { const p = Math.max(0, Math.min((timestamp - a.startTime) / a.duration, 1)); if (p < 1) drawCompletionDiffuse(p); } });
        activeAnimations = activeAnimations.filter(a => { const p = (timestamp - a.startTime) / a.duration; if (p >= 1 && a.onComplete) a.onComplete(); return p < 1; });
        if (activeAnimations.length > 0) { animationFrameId = requestAnimationFrame(gameLoop); } else { animationFrameId = null; drawBoard(); }
    }
    function startAnimationLoop() { if (!animationFrameId) animationFrameId = requestAnimationFrame(gameLoop); }
    function calculateVisualState(timestamp) {
        const s = { diamondColors: {}, pipeColors: {} };
        activeAnimations.forEach(a => {
            if (a.type === 'light-up') {
                const p = Math.min((timestamp - a.startTime) / a.duration, 1), dp = Math.min(p * 2, 1), pp = Math.max(0, (p - .5) * 2);
                const dc = interpolateColor(COLORS.DIAMOND_LIT, COLORS.LINE_CONNECTED, 1 - dp), pc = interpolateColor(COLORS.LINE_DISCONNECTED, COLORS.LINE_LIT, pp);
                s.diamondColors[`${a.r1},${a.c1}`] = dc; s.diamondColors[`${a.r2},${a.c2}`] = dc; s.pipeColors[`${a.r1},${a.c1},${a.side1}`] = pc; s.pipeColors[`${a.r2},${a.c2},${a.side2}`] = pc;
            }
        });
        return s;
    }

    function drawBoardBase() {
        if (!boardState) return; for (let r = 0; r < boardSize.height; r++) for (let c = 0; c < boardSize.width; c++) {
            ctx.fillStyle = boardState[r][c] ? COLORS.ACTIVE_BG : COLORS.INACTIVE_BG; ctx.fillRect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE);
            ctx.strokeStyle = COLORS.GRID; ctx.lineWidth = 1; ctx.strokeRect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE);
        }
    }
    function drawAllTiles(vs) {
        if (!boardState) return; for (let r = 0; r < boardSize.height; r++) for (let c = 0; c < boardSize.width; c++)
            if (boardState[r][c] && !(isDragging && originalGridPos.r === r && originalGridPos.c === c))
                drawTile(boardState[r][c], c * CELL_SIZE, r * CELL_SIZE, getConnectedSides(r, c), vs, r, c);
        if (isDragging && draggedTile) drawTile(draggedTile, dragStartPos.x - CELL_SIZE / 2, dragStartPos.y - CELL_SIZE / 2, [!1, !1, !1, !1], {}, -1, -1);
    }
    function getConnectedSides(r, c) {
        const t = boardState[r][c], s = [!1, !1, !1, !1]; if (!t) return s;
        if (t[0] === 1 && r > 0 && boardState[r - 1][c]?.[2] === 1) s[0] = !0; if (t[1] === 1 && c < boardSize.width - 1 && boardState[r][c + 1]?.[3] === 1) s[1] = !0;
        if (t[2] === 1 && r < boardSize.height - 1 && boardState[r + 1][c]?.[0] === 1) s[2] = !0; if (t[3] === 1 && c > 0 && boardState[r][c - 1]?.[1] === 1) s[3] = !0;
        return s;
    }
    function drawTile(conn, x, y, cs, vs, r, c) {
        const cx = x + CELL_SIZE / 2, cy = y + CELL_SIZE / 2, ds = 12; ctx.lineWidth = 4; ctx.lineCap = 'round';
        const sides = [{ c: conn[0], s: cs[0], x2: cx, y2: y, id: 0 }, { c: conn[1], s: cs[1], x2: x + CELL_SIZE, y2: cy, id: 1 }, { c: conn[2], s: cs[2], x2: cx, y2: y + CELL_SIZE, id: 2 }, { c: conn[3], s: cs[3], x2: x, y2: cy, id: 3 }];
        sides.forEach(s => {
            if (s.c) {
                let pc = vs.pipeColors && vs.pipeColors[`${r},${c},${s.id}`]; if (!pc) pc = s.s ? COLORS.LINE_CONNECTED : COLORS.LINE_DISCONNECTED;
                ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(s.x2, s.y2); ctx.strokeStyle = pc; ctx.stroke();
            }
        });
        let dc = vs.diamondColors && vs.diamondColors[`${r},${c}`]; if (!dc) dc = cs.some(s => s) ? COLORS.LINE_CONNECTED : COLORS.LINE_DISCONNECTED;
        ctx.beginPath(); ctx.moveTo(cx, cy - ds / 2); ctx.lineTo(cx + ds / 2, cy); ctx.lineTo(cx, cy + ds / 2); ctx.lineTo(cx - ds / 2, cy); ctx.closePath(); ctx.fillStyle = dc; ctx.fill();
    }
    function drawBoard() { if (!boardState) { ctx.clearRect(0, 0, canvas.width, canvas.height); return } if (animationFrameId) return; drawBoardBase(); drawAllTiles({}); }
    function drawCustomizationGrid() {
        if (!customShape || customShape.length === 0) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const h = boardSize.height;
        const w = boardSize.width;
        for (let r = 0; r < h; r++) {
            for (let c = 0; c < w; c++) {
                ctx.fillStyle = customShape[r][c] === 'x' ? COLORS.ACTIVE_BG : COLORS.INACTIVE_BG;
                ctx.fillRect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE);
                ctx.strokeStyle = COLORS.GRID;
                ctx.lineWidth = 1;
                ctx.strokeRect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE);
            }
        }
    }

    function drawCompletionDiffuse(p) {
        const w = canvas.width, h = canvas.height; if (w <= 0 || h <= 0) return; const cx = w / 2, cy = h / 2;
        const mr = Math.sqrt(w * w + h * h) * ANIMATION_COMPLETION_RADIUS_END_FACTOR, cr = ANIMATION_COMPLETION_RADIUS_START + p * (mr - ANIMATION_COMPLETION_RADIUS_START);
        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.max(0, cr)), sc = COLORS.COMPLETION_HIGHLIGHT + 'ff', ec = COLORS.COMPLETION_HIGHLIGHT + '00'; g.addColorStop(0, sc); g.addColorStop(Math.min(.5, p * 2), sc); g.addColorStop(1, ec);
        ctx.save(); ctx.globalAlpha = 1 - p; ctx.fillStyle = g; ctx.fillRect(0, 0, w, h); ctx.restore();
    }

    function isPuzzleSolved(grid) {
        if (!grid || grid.length === 0) return !0; const h = grid.length, w = grid[0].length, a = [], s = [];
        for (let r = 0; r < h; r++) { s.push([]); for (let c = 0; c < w; c++) grid[r][c] ? (s[r].push('x'), a.push({ r, c })) : s[r].push(' ') }
        if (a.length === 0) return !0;
        for (const { r, c } of a) {
            const t = grid[r][c];
            if (t[0] === 1 && (!(r > 0 && s[r - 1][c] === 'x' && grid[r - 1][c]?.[2] === 1))) return !1;
            if (t[1] === 1 && (!(c < w - 1 && s[r][c + 1] === 'x' && grid[r][c + 1]?.[3] === 1))) return !1;
            if (t[2] === 1 && (!(r < h - 1 && s[r + 1][c] === 'x' && grid[r + 1][c]?.[0] === 1))) return !1;
            if (t[3] === 1 && (!(c > 0 && s[r][c - 1] === 'x' && grid[r][c - 1]?.[1] === 1))) return !1
        }
        const q = [a[0]], v = new Set([`${a[0].r},${a[0].c}`]);
        while (q.length > 0) {
            const { r, c } = q.shift(), t = grid[r][c];
            if (t[0] === 1) { const k = `${r - 1},${c}`; if (!v.has(k)) { v.add(k); q.push({ r: r - 1, c }) } }
            if (t[1] === 1) { const k = `${r},${c + 1}`; if (!v.has(k)) { v.add(k); q.push({ r, c: c + 1 }) } }
            if (t[2] === 1) { const k = `${r + 1},${c}`; if (!v.has(k)) { v.add(k); q.push({ r: r + 1, c }) } }
            if (t[3] === 1) { const k = `${r},${c - 1}`; if (!v.has(k)) { v.add(k); q.push({ r, c: c - 1 }) } }
        }
        return v.size === a.length
    }
    
    // --- 核心修改 1: 函数签名增加 isManualSolve 参数，默认为 true ---
    function checkPuzzleCompletion(isManualSolve = true) {
        if (!boardState || puzzleJustSolved) return !1;
        if (isPuzzleSolved(boardState)) {
            puzzleJustSolved = !0;
            const onC = () => {
                if (gameMode === 'timed' && !isCountingDown) {
                    onTimedPuzzleSolved();
                } else if (gameMode === 'classic') {
                    // --- 核心修改 2: 只有在手动解题时才显示文本和播放烟花 ---
                    if (isManualSolve) {
                        infoPanel.textContent = '恭喜你，解谜成功！';
                        isConfettiRunning = true;
                        confetti({ particleCount: 150, spread: 90, origin: { y: .6 } })
                            .then(() => {
                                isConfettiRunning = false;
                            });
                    }
                }
            };
            activeAnimations.push({ type: 'completion-diffuse', startTime: performance.now(), duration: ANIMATION_COMPLETION_DURATION, onComplete: onC });
            startAnimationLoop();
            return !0
        }
        return !1
    }
    function onTimedPuzzleSolved() {
        if (timerInterval) clearInterval(timerInterval); const timeTaken = Date.now() - challengeState.puzzleStartTime;
        challengeState.times.push(timeTaken); challengeState.currentPuzzleIndex++;
        setTimeout(() => {
            try {
                if (challengeState.currentPuzzleIndex < 3) {
                    loadTimedPuzzle(challengeState.currentPuzzleIndex, !1);
                    const nextPuzzle = challengeState.puzzles[challengeState.currentPuzzleIndex];
                    if (!nextPuzzle || !nextPuzzle.shuffled_grid || !nextPuzzle.shuffled_grid[0]) throw new Error("加载下一关谜题数据失败。");
                    const nextWidth = nextPuzzle.shuffled_grid[0].length, countdownDuration = { '3': 3, '4': 4, '5': 5, '7': 7 }[nextWidth] || 3, pauseStartTime = Date.now();
                    runCountdown(countdownDuration).then(() => {
                        challengeState.totalPausedTime += Date.now() - pauseStartTime; challengeState.puzzleStartTime = Date.now();
                        timerInterval = setInterval(() => {
                            const elapsedTime = (Date.now() - challengeState.startTime) - challengeState.totalPausedTime;
                            timerEl.textContent = formatTime(elapsedTime)
                        }, 41)
                    })
                }
                else { challengeState.totalTime = (Date.now() - challengeState.startTime) - challengeState.totalPausedTime; showResults() }
            }
            catch (error) { console.error("在 onTimedPuzzleSolved 的延迟执行中发生错误:", error); infoPanel.textContent = "加载下一关时出错，请刷新页面重试。" }
        }, 50)
    }

    function loadTimedPuzzle(i, sT = !0) {
        resetPuzzleState(); const p = challengeState.puzzles[i]; boardState = p.shuffled_grid; solutionState = p.solution_grid;
        initialBoardState = JSON.parse(JSON.stringify(p.shuffled_grid)); boardSize = { width: boardState[0].length, height: boardState.length };
        canvas.width = boardSize.width * CELL_SIZE; canvas.height = boardSize.height * CELL_SIZE;
        puzzleCounterEl.textContent = `第 ${i + 1} / 3 关`; drawBoard(); if (sT) challengeState.puzzleStartTime = Date.now()
    }
    function handleCustomizationClick(event) {
        if (!isCustomizing) return;
        const pos = getEventPos(event);
        const c = Math.floor(pos.x / CELL_SIZE);
        const r = Math.floor(pos.y / CELL_SIZE);

        if (customShape[r] && typeof customShape[r][c] !== 'undefined') {
            customShape[r][c] = customShape[r][c] === 'x' ? ' ' : 'x';
            drawCustomizationGrid();
        }
    }

    function handleInteractionStart(event) {
        if (isConfettiRunning) {
            if (typeof confetti === 'function') confetti.reset();
            isConfettiRunning = false;
            return;
        }

        if (isAnimating || isCountingDown || isDragging) return;

        if (isCustomizing) {
            handleCustomizationClick(event);
            return; // 处理完自定义点击后，必须立即返回
        }

        if (!boardState) return;
        if (event.type === 'touchstart') event.preventDefault();
        const pos = getEventPos(event);
        const c = Math.floor(pos.x / CELL_SIZE);
        const r = Math.floor(pos.y / CELL_SIZE);
        if (boardState[r] && boardState[r][c]) {
            isDragging = true;
            draggedTile = boardState[r][c];
            originalGridPos = { r, c };
            dragStartPos = pos;
        }
    }
    function handleDragMove(event) {
        if (isDragging) {
            if (event.type === 'touchmove') event.preventDefault();
            dragStartPos = getEventPos(event);
            drawBoard();
        }
    }

    function handleDragEnd(event) {
        if (!isDragging) return; const p = getEventPos(event), cn = Math.floor(p.x / CELL_SIZE), rn = Math.floor(p.y / CELL_SIZE),
            ro = originalGridPos.r, co = originalGridPos.c; let s = !1; isDragging = !1; draggedTile = null;
        if (boardState[rn] && typeof boardState[rn][cn] !== 'undefined' && (rn !== ro || cn !== co)) {
            if (boardState[rn][cn]) {
                [boardState[ro][co], boardState[rn][cn]] = [boardState[rn][cn], boardState[ro][co]]; s = !0
            }
        }
        if (s) { drawBoardBase(); drawAllTiles({}); const iS = checkPuzzleCompletion(); if (!iS) triggerConnectionAnimations({ r: ro, c: co }, { r: rn, c: cn }) } else { drawBoard() }
    }

    async function runSolveAnimation(swaps) {
        isAnimating = !0; infoPanel.textContent = '正在播放解法...'; for (const s of swaps) {
            const [p1, p2] = s;
            [boardState[p1[0]][p1[1]], boardState[p2[0]][p2[1]]] = [boardState[p2[0]][p2[1]], boardState[p1[0]][p1[1]]];
            triggerConnectionAnimations(p1, p2); drawBoard(); await sleep(ANIMATION_SWAP_SPEED_MS)
        }
        infoPanel.textContent = '求解完成！'; isAnimating = !1;
        // --- 核心修改 3: 自动求解完成后，调用 checkPuzzleCompletion 并传入 false ---
        checkPuzzleCompletion(false);
    }
    function formatTime(ms) {
        const m = Math.floor(ms / 6e4), s = Math.floor(ms % 6e4 / 1e3), mils = Math.floor(ms % 1e3);
        return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(mils).padStart(3, '0')}`
    }
    function triggerConnectionAnimations(p1, p2) {
        const ps = [p1, p2], dirs = [[-1, 0, 0, 2], [0, 1, 1, 3], [1, 0, 2, 0], [0, -1, 3, 1]]; let aT = !1;
        ps.forEach(p => {
            if (!p) return; const r1 = p.r, c1 = p.c, t1 = boardState[r1] ? boardState[r1][c1] : null; if (!t1) return;
            dirs.forEach(([dr, dc, s1, s2]) => {
                if (t1[s1] === 1) {
                    const r2 = r1 + dr, c2 = c1 + dc; if (r2 >= 0 && r2 < boardSize.height && c2 >= 0 && c2 < boardSize.width) {
                        const t2 = boardState[r2][c2]; if (t2 && t2[s2] === 1) {
                            activeAnimations.push({
                                type: 'light-up', startTime: performance.now(),
                                duration: ANIMATION_LIT_DURATION, r1, c1, side1: s1, r2, c2, side2: s2
                            }); aT = !0
                        }
                    }
                }
            })
        }); if (aT) startAnimationLoop()
    }
    function getEventPos(e) {
        const rect = canvas.getBoundingClientRect(); let cx, cy; if (e.touches && e.touches.length > 0) { cx = e.touches[0].clientX; cy = e.touches[0].clientY }
        else if (e.changedTouches && e.changedTouches.length > 0) { cx = e.changedTouches[0].clientX; cy = e.changedTouches[0].clientY } else { cx = e.clientX; cy = e.clientY }
        return { x: cx - rect.left, y: cy - rect.top }
    }
    function hideCustomizationUI() {
        customizationUI.style.display = 'none'; customActions.style.display = 'none';
        customizationUI.querySelector('.custom-inputs').style.display = 'flex'; isCustomizing = !1
    }
    function showModeSelection() {
        gameArea.style.display = 'none'; modeSelection.style.display = 'block'; gameMode = null; if (timerInterval) clearInterval(timerInterval);
        boardState = null; drawBoard()
    }
    function resetPuzzleState() { if (animationFrameId) { cancelAnimationFrame(animationFrameId); animationFrameId = null } activeAnimations = []; puzzleJustSolved = !1 }
    function setupGameUIForMode(mode) {
        gameMode = mode;
        modeSelection.style.display = 'none';
        gameArea.style.display = 'flex';
        const iT = mode === 'timed';
        classicControls.style.display = iT ? 'none' : 'flex';
        timedControls.style.display = iT ? 'flex' : 'none';
        timedInfo.style.display = iT ? 'block' : 'none';
        hideCustomizationUI();
        playAgainBtn.style.display = 'none';
        resetPuzzleState();

        if (mode === 'classic') {
            infoPanel.textContent = '经典模式：正在为您生成默认3x3谜题...';
            fetchNewPuzzle(3, 3);
        } else { // 'timed' 模式
            infoPanel.textContent = '计时挑战：请选择难度，准备倒计时！';
            boardState = null;
            drawBoard();

            if (timerInterval) clearInterval(timerInterval);
            challengeState = {};
            timerEl.textContent = formatTime(0);
            puzzleCounterEl.textContent = '';
        }
    }
    async function fetchCustomPuzzle(shape) {
        infoPanel.textContent = '正在根据自定义形状生成谜题...'; isAnimating = !0; hideCustomizationUI();
        playAgainBtn.style.display = 'none'; resetPuzzleState(); try {
            const r = await fetch('/api/new_custom_puzzle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ shape })
            }); if (!r.ok) { const eD = await r.json(); throw new Error(eD.error || `Server error: ${r.statusText}`) }
            const d = await r.json(); boardState = d.shuffled_grid; solutionState = d.solution_grid; initialBoardState = JSON.parse(JSON.stringify(d.shuffled_grid));
            boardSize = { width: boardState[0].length, height: boardState.length }; canvas.width = boardSize.width * CELL_SIZE; canvas.height = boardSize.height * CELL_SIZE;
            infoPanel.textContent = '自定义谜题生成成功！'; lastCustomShape = JSON.parse(JSON.stringify(shape)); playAgainBtn.style.display = 'inline-block';
            drawBoard()
        } catch (e) { console.error("Failed to fetch custom puzzle:", e); infoPanel.textContent = `加载失败: ${e.message}` } finally { isAnimating = !1 }
    }
    function runCountdown(dur) {
        if (countdownInterval) clearInterval(countdownInterval);

        return new Promise(res => {
            isCountingDown = !0;
            let rem = dur;
            const endC = () => {
                if (!isCountingDown) return;
                isCountingDown = !1;
                clearInterval(countdownInterval);
                countdownInterval = null;
                canvas.removeEventListener('mousedown', endC);
                canvas.removeEventListener('touchstart', endC);
                infoPanel.textContent = "开始!";
                res()
            };
            canvas.addEventListener('mousedown', endC, { once: !0 });
            canvas.addEventListener('touchstart', endC, { once: !0 });
            infoPanel.textContent = `准备... ${rem}`;
            countdownInterval = setInterval(() => {
                rem--;
                if (rem > 0) infoPanel.textContent = `准备... ${rem}`;
                else endC()
            }, 1e3)
        })
    }
    async function fetchNewPuzzle(w = 5, h = 5) {
        infoPanel.textContent = '正在生成新谜题...'; isAnimating = !0; hideCustomizationUI(); playAgainBtn.style.display = 'none';
        lastCustomShape = null; resetPuzzleState(); try {
            const r = await fetch(`/api/new_puzzle?width=${w}&height=${h}`); if (!r.ok) throw new Error(`Server error: ${r.statusText}`);
            const d = await r.json(); boardState = d.shuffled_grid; solutionState = d.solution_grid; initialBoardState = JSON.parse(JSON.stringify(d.shuffled_grid));
            boardSize = { width: boardState[0].length, height: boardState.length }; canvas.width = boardSize.width * CELL_SIZE; canvas.height = boardSize.height * CELL_SIZE;
            infoPanel.textContent = '拖动石板，完成连线！'; drawBoard()
        } catch (e) { console.error("Failed to fetch puzzle:", e); infoPanel.textContent = `加载失败: ${e.message}` }
        finally { isAnimating = !1 }
    }
    async function startTimedChallenge(w, h) {
        if (timerInterval) clearInterval(timerInterval);
        isAnimating = !0;
        infoPanel.textContent = '准备中，正在生成谜题...';
        resetPuzzleState();
        try {
            const r = await fetch('/api/challenge/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ width: w, height: h })
            });
            if (!r.ok) throw new Error(`服务器错误: ${r.statusText}`);
            const d = await r.json();
            if (!d.puzzles || d.puzzles.length < 3) throw new Error('未能从服务器获取到完整的谜题。');
            challengeState = {
                puzzles: d.puzzles,
                currentPuzzleIndex: 0,
                times: [],
                totalPausedTime: 0,
                difficulty: `${w}x${h}`
            };
            const dur = { '3': 3, '4': 4, '5': 5, '7': 7 }[w] || 3;
            loadTimedPuzzle(0, !1);
            isAnimating = !1;
            await runCountdown(dur);
            challengeState.startTime = Date.now();
            challengeState.puzzleStartTime = Date.now();
            timerInterval = setInterval(() => {
                const e = (Date.now() - challengeState.startTime) - challengeState.totalPausedTime;
                timerEl.textContent = formatTime(e)
            }, 41)
        }
        catch (e) {
            console.error("无法开始计时挑战:", e);
            infoPanel.textContent = `开始挑战失败: ${e.message}`;
            isAnimating = !1
        }
    }
    function showResults() {
        const [t1, t2, t3] = challengeState.times, avg = (t1 + t2 + t3) / 3; challengeState.avgTime = avg;
        document.getElementById('time-1').textContent = formatTime(t1); document.getElementById('time-2').textContent = formatTime(t2);
        document.getElementById('time-3').textContent = formatTime(t3); document.getElementById('time-avg').textContent = formatTime(avg);
        document.getElementById('time-total').textContent = formatTime(challengeState.totalTime);
        usernameInput.value = localStorage.getItem('puzzleUsername') || ''; submitScoreBtn.textContent = '提交成绩'; submitScoreBtn.disabled = !1;
        resultsModal.style.display = 'flex'; confetti({ particleCount: 200, spread: 120, origin: { y: .6 } })
    }
    async function showLeaderboard() { leaderboardModal.style.display = 'flex'; await updateLeaderboardView() }
    async function updateLeaderboardView() {
        const d = leaderboardDifficultySelect.value, t = leaderboardTypeSelect.value, u = localStorage.getItem('puzzleUsername');
        leaderboardDisplay.innerHTML = '<p>加载中...</p>'; try {
            const r = await fetch(`/api/leaderboard?difficulty=${d}&type=${t}&username=${u || ''}`);
            if (!r.ok) throw new Error("无法获取排行榜数据"); const data = await r.json(), ts = data.top_scores || [], ui = data.user_rank_info;
            if (ts.length === 0) leaderboardDisplay.innerHTML = '<p>暂无记录</p>'; else {
                let h = '<ol>'; ts.forEach((s, i) => {
                    let rd = `${i + 1}.`;
                    if (i === 0) rd = '🥇'; if (i === 1) rd = '🥈'; if (i === 2) rd = '🥉'; h += `<li><span>${rd} ${s.username}</span><span>${formatTime(s.time)}</span></li>`
                });
                h += '</ol>'; leaderboardDisplay.innerHTML = h
            } const urd = document.createElement('div'); urd.className = 'user-rank-info';
            if (ui) {
                if (ui.rank > 100) urd.innerHTML = `<p>您的当前排名: <b>第 ${ui.rank} 名</b> (成绩: ${formatTime(ui.time)})</p>`;
                else urd.innerHTML = `<p>您的当前排名: <b>第 ${ui.rank} 名</b></p>`
            } else if (u) urd.innerHTML = '<p>您在此模式下暂未上榜</p>';
            leaderboardDisplay.appendChild(urd)
        } catch (e) { leaderboardDisplay.innerHTML = `<p style="color: #ff6b6b;">${e.message}</p>` }
    }

    // Event Listeners
    canvas.addEventListener('mousedown', handleInteractionStart); canvas.addEventListener('mousemove', handleDragMove);
    canvas.addEventListener('mouseup', handleDragEnd); canvas.addEventListener('mouseleave', handleDragEnd);
    canvas.addEventListener('touchstart', handleInteractionStart, { passive: !1 }); canvas.addEventListener('touchmove', handleDragMove, { passive: !1 });
    canvas.addEventListener('touchend', handleDragEnd); canvas.addEventListener('touchcancel', handleDragEnd);
    classicModeBtn.addEventListener('click', () => setupGameUIForMode('classic')); timedModeBtn.addEventListener('click', () => setupGameUIForMode('timed'));
    exitGameBtn.addEventListener('click', showModeSelection); difficultyBtns.forEach(b => {
        b.addEventListener('click', () => {
            if (isAnimating) return;
            const s = b.dataset.size.split('x'), w = parseInt(s[0], 10), h = parseInt(s[1], 10); if (gameMode === 'timed') startTimedChallenge(w, h);
            else if (gameMode === 'classic') fetchNewPuzzle(w, h)
        })
    }); const retryLogic = () => {
        if (initialBoardState && !isAnimating) {
            resetPuzzleState();
            boardState = JSON.parse(JSON.stringify(initialBoardState)); infoPanel.textContent = '已重试，请继续！'; drawBoard()
        }
    };
    retryBtnClassic.addEventListener('click', retryLogic); retryBtnTimed.addEventListener('click', retryLogic);
    solveBtn.addEventListener('click', async () => {
        if (!boardState || !solutionState || isAnimating) return; infoPanel.textContent = '正在向服务器请求解法...';
        try {
            const r = await fetch('/api/solve', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
                    current_grid: boardState,
                    solution_grid: solutionState
                })
            }); if (!r.ok) throw new Error("求解失败"); const d = await r.json(); if (d.swaps && d.swaps.length > 0) await runSolveAnimation(d.swaps);
            else {
                infoPanel.textContent = '已经是正确答案了！'; 
                // --- 核心修改 4: 如果点击求解时已完成，同样调用 checkPuzzleCompletion 并传入 false ---
                checkPuzzleCompletion(false)
            }
        } catch (e) { infoPanel.textContent = e.message }
    });
    uploadBtn.addEventListener('click', () => { if (isAnimating) return; imageUploader.click() });
    imageUploader.addEventListener('change', async e => {
        const f = e.target.files[0]; if (!f || isAnimating) return; infoPanel.textContent = '正在上传和识别图片...';
        isAnimating = !0; resetPuzzleState(); const fd = new FormData(); fd.append('puzzle_image', f); try {
            const r = await fetch('/api/upload_image', { method: 'POST', body: fd });
            if (!r.ok) { const eD = await r.json(); throw new Error(eD.error || '识别失败') } const d = await r.json(); boardState = d.shuffled_grid; solutionState = d.solution_grid;
            initialBoardState = JSON.parse(JSON.stringify(d.shuffled_grid)); boardSize = { width: boardState[0].length, height: boardState.length };
            canvas.width = boardSize.width * CELL_SIZE; canvas.height = boardSize.height * CELL_SIZE; lastCustomShape = null; playAgainBtn.style.display = 'none';
            infoPanel.textContent = '图片识别成功，开始游戏！'; drawBoard()
        } catch (e) { console.error("Image upload failed:", e); infoPanel.textContent = `错误: ${e.message}` }
        finally { isAnimating = !1; imageUploader.value = '' }
    });
    customBtn.addEventListener('click', () => {
        if (isAnimating) return; resetPuzzleState(); boardState = null; drawBoard(); customizationUI.style.display = 'flex';
        infoPanel.textContent = '请设置棋盘尺寸并创建画布。'
    });
    createGridBtn.addEventListener('click', () => {
        const w = parseInt(customWidthInput.value, 10), h = parseInt(customHeightInput.value, 10);
        if (isNaN(w) || isNaN(h) || w < 2 || h < 2 || w > 7 || h > 7) { infoPanel.textContent = '错误：宽高必须在 2 到 7 之间。'; return } isCustomizing = !0;
        customShape = Array(h).fill(null).map(() => Array(w).fill(' ')); boardSize = { width: w, height: h }; canvas.width = boardSize.width * CELL_SIZE;
        canvas.height = boardSize.height * CELL_SIZE; drawCustomizationGrid(); customizationUI.querySelector('.custom-inputs').style.display = 'none';
        customActions.style.display = 'flex'; infoPanel.textContent = '请在画布上点击，设计谜题的形状。'
    });
    generateCustomBtn.addEventListener('click', () => {
        if (isAnimating) return; const hT = customShape.some(r => r.includes('x'));
        if (!hT) { infoPanel.textContent = '错误：自定义形状中至少要包含一个石板。'; return } fetchCustomPuzzle(customShape)
    });
    cancelCustomBtn.addEventListener('click', () => { if (isAnimating) return; hideCustomizationUI(); fetchNewPuzzle(3, 3) });
    playAgainBtn.addEventListener('click', () => { if (isAnimating || !lastCustomShape) return; fetchCustomPuzzle(lastCustomShape) });
    resultsPlayAgainBtn.addEventListener('click', () => {
        confetti.reset();
        resultsModal.style.display = 'none';
        const [w, h] = challengeState.difficulty.split('x').map(Number);
        startTimedChallenge(w, h);
    });
    resultsExitBtn.addEventListener('click', () => {
        confetti.reset();
        resultsModal.style.display = 'none';
        setupGameUIForMode('timed');
    });
    submitScoreBtn.addEventListener('click', async () => {
        const u = usernameInput.value.trim() || '匿名玩家'; localStorage.setItem('puzzleUsername', u);
        submitScoreBtn.disabled = !0; submitScoreBtn.textContent = '提交中...'; try {
            const r = await fetch('/api/leaderboard/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
                    difficulty: challengeState.difficulty, username: u, times: challengeState.times,
                    avgTime: challengeState.avgTime
                })
            }); if (!r.ok) throw new Error("提交失败"); const d = await r.json(); if (d.success) submitScoreBtn.textContent = `提交成功! 您的排名: 第 ${d.rank} 名`;
            else submitScoreBtn.textContent = '提交失败'
        } catch (e) { submitScoreBtn.textContent = e.message }
        setTimeout(() => { submitScoreBtn.textContent = '提交成绩'; submitScoreBtn.disabled = !1 }, 3e3)
    });
    leaderboardBtn.addEventListener('click', showLeaderboard); closeLeaderboardBtn.addEventListener('click', () => leaderboardModal.style.display = 'none');
    leaderboardDifficultySelect.addEventListener('change', updateLeaderboardView); leaderboardTypeSelect.addEventListener('change', updateLeaderboardView);

    // Game Init
    showModeSelection();
});