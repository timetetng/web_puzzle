document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');
    const difficultyBtns = document.querySelectorAll('.difficulty-btn');
    const retryBtn = document.getElementById('retryBtn');
    const solveBtn = document.getElementById('solveBtn');
    const infoPanel = document.getElementById('infoPanel');
    const uploadBtn = document.getElementById('uploadBtn');
    const imageUploader = document.getElementById('imageUploader');
    // ## 新增DOM元素引用 ##
    const customBtn = document.getElementById('customBtn');
    const customizationUI = document.getElementById('customization-ui');
    const customWidthInput = document.getElementById('customWidth');
    const customHeightInput = document.getElementById('customHeight');
    const createGridBtn = document.getElementById('createGridBtn');
    const customActions = customizationUI.querySelector('.custom-actions');
    const generateCustomBtn = document.getElementById('generateCustomBtn');
    const cancelCustomBtn = document.getElementById('cancelCustomBtn');
    const playAgainBtn = document.getElementById('playAgainBtn');

    const sleep = ms => new Promise(res => setTimeout(res, ms));
    const ANIMATION_SWAP_SPEED_MS = 150;
    const CELL_SIZE = 80;

    const COLORS = {
        BACKGROUND: '#323232',
        GRID: '#555555',
        ACTIVE_BG: '#464646',
        INACTIVE_BG: '#3a3a3a',
        LINE_CONNECTED: '#65e065',
        LINE_DISCONNECTED: '#808080'
    };

    let boardState = null;
    let solutionState = null;
    let initialBoardState = null;
    let boardSize = { width: 0, height: 0 };
    let isAnimating = false;
    let isDragging = false;
    let draggedTile = null;
    let dragStartPos = { x: 0, y: 0 };
    let originalGridPos = { r: 0, c: 0 };
    // ## 新增状态变量 ##
    let isCustomizing = false;
    let customShape = [];
    let lastCustomShape = null; // 用于 "再来一次" 功能

    function drawTile(connections, x, y, connectedSides) {
        const centerX = x + CELL_SIZE / 2;
        const centerY = y + CELL_SIZE / 2;
        ctx.lineWidth = 4;
        ctx.lineCap = 'round';
        const diamondSize = 12;
        const sides = [
            { conn: connections[0], side: connectedSides[0], x2: centerX, y2: y },
            { conn: connections[1], side: connectedSides[1], x2: x + CELL_SIZE, y2: centerY },
            { conn: connections[2], side: connectedSides[2], x2: centerX, y2: y + CELL_SIZE },
            { conn: connections[3], side: connectedSides[3], x2: x, y2: centerY },
        ];
        sides.forEach(s => {
            if (s.conn) {
                ctx.beginPath();
                ctx.moveTo(centerX, centerY);
                ctx.lineTo(s.x2, s.y2);
                ctx.strokeStyle = s.side ? COLORS.LINE_CONNECTED : COLORS.LINE_DISCONNECTED;
                ctx.stroke();
            }
        });
        const diamondColor = connectedSides.some(side => side) ? COLORS.LINE_CONNECTED : COLORS.LINE_DISCONNECTED;
        ctx.beginPath();
        ctx.moveTo(centerX, centerY - diamondSize / 2);
        ctx.lineTo(centerX + diamondSize / 2, centerY);
        ctx.lineTo(centerX, centerY + diamondSize / 2);
        ctx.lineTo(centerX - diamondSize / 2, centerY);
        ctx.closePath();
        ctx.fillStyle = diamondColor;
        ctx.fill();
    }
    
    // ## 新增函数：绘制自定义形状的网格 ##
    function drawCustomizationGrid() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const width = customShape[0].length;
        const height = customShape.length;
        for (let r = 0; r < height; r++) {
            for (let c = 0; c < width; c++) {
                const isSelected = customShape[r][c] === 'x';
                ctx.fillStyle = isSelected ? COLORS.ACTIVE_BG : COLORS.INACTIVE_BG;
                ctx.fillRect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE);
                ctx.strokeStyle = COLORS.GRID;
                ctx.lineWidth = 1;
                ctx.strokeRect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE);
            }
        }
    }

    function drawBoard() {
        if (!boardState) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        for (let r = 0; r < boardSize.height; r++) {
            for (let c = 0; c < boardSize.width; c++) {
                const tile = boardState[r][c];
                ctx.fillStyle = tile ? COLORS.ACTIVE_BG : COLORS.INACTIVE_BG;
                ctx.fillRect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE);
                ctx.strokeStyle = COLORS.GRID;
                ctx.lineWidth = 1;
                ctx.strokeRect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE);
            }
        }
        for (let r = 0; r < boardSize.height; r++) {
            for (let c = 0; c < boardSize.width; c++) {
                const tileConns = boardState[r][c];
                if (tileConns && !(isDragging && originalGridPos.r === r && originalGridPos.c === c)) {
                    const connectedSides = [false, false, false, false];
                    if (tileConns[0] === 1) {
                        if (r > 0 && boardState[r - 1][c] && boardState[r - 1][c][2] === 1) connectedSides[0] = true;
                    }
                    if (tileConns[1] === 1) {
                        if (c < boardSize.width - 1 && boardState[r][c + 1] && boardState[r][c + 1][3] === 1) connectedSides[1] = true;
                    }
                    if (tileConns[2] === 1) {
                        if (r < boardSize.height - 1 && boardState[r + 1][c] && boardState[r + 1][c][0] === 1) connectedSides[2] = true;
                    }
                    if (tileConns[3] === 1) {
                        if (c > 0 && boardState[r][c - 1] && boardState[r][c - 1][1] === 1) connectedSides[3] = true;
                    }
                    drawTile(tileConns, c * CELL_SIZE, r * CELL_SIZE, connectedSides);
                }
            }
        }
        if (isDragging && draggedTile) {
            const connectedSides = [false, false, false, false];
            drawTile(draggedTile, dragStartPos.x - CELL_SIZE / 2, dragStartPos.y - CELL_SIZE / 2, connectedSides);
        }
    }

    async function runSolveAnimation(swaps) {
        isAnimating = true;
        infoPanel.textContent = '正在播放解法...';
        for (const swap of swaps) {
            const [pos1, pos2] = swap;
            [boardState[pos1[0]][pos1[1]], boardState[pos2[0]][pos2[1]]] = [boardState[pos2[0]][pos2[1]], boardState[pos1[0]][pos1[1]]];
            drawBoard();
            await sleep(ANIMATION_SWAP_SPEED_MS);
        }
        infoPanel.textContent = '求解完成！';
        isAnimating = false;
        drawBoard();
    }
    
    function hideCustomizationUI() {
        customizationUI.style.display = 'none';
        customActions.style.display = 'none';
        customizationUI.querySelector('.custom-inputs').style.display = 'flex';
        isCustomizing = false;
    }
    
    // ## 新增函数：获取自定义谜题 ##
    async function fetchCustomPuzzle(shape) {
        infoPanel.textContent = '正在根据自定义形状生成谜题...';
        isAnimating = true;
        hideCustomizationUI();
        playAgainBtn.style.display = 'none';

        try {
            const response = await fetch('/api/new_custom_puzzle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ shape })
            });
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || `Server error: ${response.statusText}`);
            }
            const data = await response.json();
            boardState = data.shuffled_grid;
            solutionState = data.solution_grid;
            initialBoardState = JSON.parse(JSON.stringify(data.shuffled_grid));
            boardSize = {
                width: boardState[0].length,
                height: boardState.length
            };
            canvas.width = boardSize.width * CELL_SIZE;
            canvas.height = boardSize.height * CELL_SIZE;
            infoPanel.textContent = '自定义谜题生成成功！';
            lastCustomShape = JSON.parse(JSON.stringify(shape)); // 保存形状以便“再来一次”
            playAgainBtn.style.display = 'inline-block';
            drawBoard();
        } catch (error) {
            console.error("Failed to fetch custom puzzle:", error);
            infoPanel.textContent = `加载失败: ${error.message}`;
            await fetchNewPuzzle(); // 如果失败，加载一个默认谜题
        } finally {
            isAnimating = false;
        }
    }

    async function fetchNewPuzzle(width = 5, height = 5) {
        infoPanel.textContent = '正在生成新谜题...';
        isAnimating = true;
        hideCustomizationUI();
        playAgainBtn.style.display = 'none'; // 随机谜题隐藏"再来一次"按钮
        lastCustomShape = null; // 清除上次的自定义形状
        try {
            const response = await fetch(`/api/new_puzzle?width=${width}&height=${height}`);
            if (!response.ok) throw new Error(`Server error: ${response.statusText}`);
            const data = await response.json();
            boardState = data.shuffled_grid;
            solutionState = data.solution_grid;
            initialBoardState = JSON.parse(JSON.stringify(data.shuffled_grid));
            boardSize = {
                width: boardState[0].length,
                height: boardState.length
            };
            canvas.width = boardSize.width * CELL_SIZE;
            canvas.height = boardSize.height * CELL_SIZE;
            infoPanel.textContent = '拖动石板，完成连线！';
            drawBoard();
        } catch (error) {
            console.error("Failed to fetch puzzle:", error);
            infoPanel.textContent = '加载失败，请刷新重试！';
        } finally {
            isAnimating = false;
        }
    }

    function getEventPos(event) {
        const rect = canvas.getBoundingClientRect();
        let clientX, clientY;
        if (event.touches && event.touches.length > 0) {
            clientX = event.touches[0].clientX;
            clientY = event.touches[0].clientY;
        } else if (event.changedTouches && event.changedTouches.length > 0) {
            clientX = event.changedTouches[0].clientX;
            clientY = event.changedTouches[0].clientY;
        } else {
            clientX = event.clientX;
            clientY = event.clientY;
        }
        return {
            x: clientX - rect.left,
            y: clientY - rect.top
        };
    }

    // ## 重构事件处理 ##
    // 将点击和拖拽开始逻辑合并到一个函数中，根据 isCustomizing 状态分发
    function handleInteractionStart(event) {
        if (isAnimating) return;

        // 如果是自定义模式，处理形状点击
        if (isCustomizing) {
            if (event.type === 'touchstart') event.preventDefault();
            const pos = getEventPos(event);
            const c = Math.floor(pos.x / CELL_SIZE);
            const r = Math.floor(pos.y / CELL_SIZE);
            if (customShape[r] && typeof customShape[r][c] !== 'undefined') {
                customShape[r][c] = customShape[r][c] === 'x' ? ' ' : 'x';
                drawCustomizationGrid();
            }
            return;
        }

        // 如果是游戏模式，处理拖拽开始
        if (!boardState || isDragging) return;
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
        if (isDragging) {
            const pos = getEventPos(event);
            const c = Math.floor(pos.x / CELL_SIZE);
            const r = Math.floor(pos.y / CELL_SIZE);
            if (boardState[r] && boardState[r][c] && (r !== originalGridPos.r || c !== originalGridPos.c)) {
                [boardState[originalGridPos.r][originalGridPos.c], boardState[r][c]] = [boardState[r][c], boardState[originalGridPos.r][originalGridPos.c]];
            }
            isDragging = false;
            draggedTile = null;
            drawBoard();
        }
    }

    // ## 绑定事件 ##
    canvas.addEventListener('mousedown', handleInteractionStart);
    canvas.addEventListener('mousemove', handleDragMove);
    canvas.addEventListener('mouseup', handleDragEnd);
    canvas.addEventListener('mouseleave', handleDragEnd);
    canvas.addEventListener('touchstart', handleInteractionStart, { passive: false });
    canvas.addEventListener('touchmove', handleDragMove, { passive: false });
    canvas.addEventListener('touchend', handleDragEnd);
    canvas.addEventListener('touchcancel', handleDragEnd);

    // ## 新增自定义UI的事件监听器 ##
    customBtn.addEventListener('click', () => {
        if (isAnimating) return;
        customizationUI.style.display = 'block';
        infoPanel.textContent = '请设置棋盘尺寸并创建画布。';
    });

    createGridBtn.addEventListener('click', () => {
        const width = parseInt(customWidthInput.value, 10);
        const height = parseInt(customHeightInput.value, 10);
        if (isNaN(width) || isNaN(height) || width < 2 || height < 2 || width > 15 || height > 15) {
            infoPanel.textContent = '错误：宽高必须在 2 到 15 之间。';
            return;
        }
        isCustomizing = true;
        customShape = Array(height).fill(null).map(() => Array(width).fill(' '));
        boardSize = { width, height };
        canvas.width = boardSize.width * CELL_SIZE;
        canvas.height = boardSize.height * CELL_SIZE;
        drawCustomizationGrid();
        customizationUI.querySelector('.custom-inputs').style.display = 'none';
        customActions.style.display = 'flex';
        infoPanel.textContent = '请在画布上点击，设计谜题的形状。';
    });

    generateCustomBtn.addEventListener('click', () => {
        if (isAnimating) return;
        const hasTiles = customShape.some(row => row.includes('x'));
        if (!hasTiles) {
            infoPanel.textContent = '错误：自定义形状中至少要包含一个石板。';
            return;
        }
        fetchCustomPuzzle(customShape);
    });

    cancelCustomBtn.addEventListener('click', () => {
        if (isAnimating) return;
        hideCustomizationUI();
        fetchNewPuzzle(); // 取消后加载一个默认谜题
    });

    playAgainBtn.addEventListener('click', () => {
        if (isAnimating || !lastCustomShape) return;
        fetchCustomPuzzle(lastCustomShape);
    });

    difficultyBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (isAnimating) return;
            const size = btn.dataset.size.split('x');
            fetchNewPuzzle(parseInt(size[0], 10), parseInt(size[1], 10));
        });
    });

    retryBtn.addEventListener('click', () => {
        if (initialBoardState && !isAnimating) {
            boardState = JSON.parse(JSON.stringify(initialBoardState));
            infoPanel.textContent = '已重试，请继续！';
            drawBoard();
        }
    });

    solveBtn.addEventListener('click', async () => {
        if (!boardState || !solutionState || isAnimating) return;
        infoPanel.textContent = '正在向服务器请求解法...';
        const response = await fetch('/api/solve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_grid: boardState,
                solution_grid: solutionState
            })
        });
        const data = await response.json();
        if (data.swaps && data.swaps.length > 0) {
            await runSolveAnimation(data.swaps);
        } else {
            infoPanel.textContent = '已经是正确答案了！';
        }
    });

    uploadBtn.addEventListener('click', () => {
        if (isAnimating) return;
        imageUploader.click();
    });

    imageUploader.addEventListener('change', async (event) => {
        const file = event.target.files[0];
        if (!file || isAnimating) return;
        infoPanel.textContent = '正在上传和识别图片...';
        isAnimating = true;
        const formData = new FormData();
        formData.append('puzzle_image', file);
        try {
            const response = await fetch('/api/upload_image', {
                method: 'POST',
                body: formData
            });
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || '识别失败');
            }
            const data = await response.json();
            boardState = data.shuffled_grid;
            solutionState = data.solution_grid;
            initialBoardState = JSON.parse(JSON.stringify(data.shuffled_grid));
            boardSize = {
                width: boardState[0].length,
                height: boardState.length
            };
            canvas.width = boardSize.width * CELL_SIZE;
            canvas.height = boardSize.height * CELL_SIZE;
            lastCustomShape = null; // 清除自定义形状状态
            playAgainBtn.style.display = 'none'; // 隐藏"再来一次"按钮
            infoPanel.textContent = '图片识别成功，开始游戏！';
            drawBoard();
        } catch (error) {
            console.error("Image upload failed:", error);
            infoPanel.textContent = `错误: ${error.message}`;
        } finally {
            isAnimating = false;
            imageUploader.value = '';
        }
    });

    fetchNewPuzzle(5, 5); // 初始加载
});