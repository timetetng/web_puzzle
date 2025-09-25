from flask import Flask, render_template, jsonify, request
import os
import uuid
import json
import sqlite3

# Import game logic modules
import puzzle_generator
import solver
import vision
from game_logic import Board, Tile


app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
DATABASE_FILE = 'leaderboard.db'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- 数据库初始化 ---
def init_db():
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scores (
                difficulty TEXT NOT NULL,
                username TEXT NOT NULL,
                best_single_time REAL,
                best_average_time REAL,
                PRIMARY KEY (difficulty, username)
            )
        ''')
        conn.commit()

# --- 【核心修正】在应用加载时就调用数据库初始化 ---
init_db()

# (The rest of your code remains exactly the same)
# ... (all your functions like get_leaderboard, calculate_swaps, all @app.route decorators) ...

# (保留 calculate_swaps 和 serialize_grid 函数)
def get_leaderboard():
    """读取排行榜数据"""
    # This function is no longer used but we keep it for reference
    if not os.path.exists('leaderboard.json'):
        return {}
    with open('leaderboard.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_leaderboard(data):
    """保存排行榜数据"""
    # This function is no longer used
    with open('leaderboard.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def calculate_swaps(initial_grid, final_grid):
    """Calculates the sequence of swaps to transform initial_grid to final_grid."""
    rows, cols = len(initial_grid), len(initial_grid[0])
    current_grid_state = [row[:] for row in initial_grid]
    swaps = []
    for r_target in range(rows):
        for c_target in range(cols):
            correct_tile = final_grid[r_target][c_target]
            current_tile = current_grid_state[r_target][c_target]
            if current_tile != correct_tile:
                found_at = None
                for r_search in range(r_target, rows):
                    c_start = c_target + 1 if r_search == r_target else 0
                    for c_search in range(c_start, cols):
                        if current_grid_state[r_search][c_search] == correct_tile:
                            found_at = (r_search, c_search)
                            break
                    if found_at:
                        break
                if found_at:
                    r_source, c_source = found_at
                    swaps.append([(r_target, c_target), (r_source, c_source)])
                    current_grid_state[r_target][c_target], current_grid_state[r_source][c_source] = \
                        current_grid_state[r_source][c_source], current_grid_state[r_target][c_target]
    return swaps


def serialize_grid(grid):
    """Serializes a grid of Tile objects to a list of connection dictionaries."""
    if not grid:
        return None
    return [[tile.connections if tile else None for tile in row] for row in grid]
# --- 路由 ---

@app.route('/')
def index():
    return render_template('index.html')

# (保留 /api/new_puzzle, /api/new_custom_puzzle, /api/solve, /api/upload_image)
@app.route('/api/new_puzzle', methods=['GET'])
def get_new_puzzle():
    try:
        width = int(request.args.get('width', 5))
        height = int(request.args.get('height', 5))
    except ValueError:
        width, height = 5, 5
    shuffled_grid, solution_grid = puzzle_generator.generate_random_puzzle(width, height)
    if shuffled_grid is None:
        return jsonify({"error": "Failed to generate puzzle"}), 500
    return jsonify({
        "shuffled_grid": serialize_grid(shuffled_grid),
        "solution_grid": serialize_grid(solution_grid)
    })

@app.route('/api/new_custom_puzzle', methods=['POST'])
def get_new_custom_puzzle():
    """根据用户提供的形状生成新谜题"""
    data = request.json
    shape = data.get('shape')

    if not shape or not isinstance(shape, list) or not all(isinstance(row, list) for row in shape):
        return jsonify({"error": "无效的形状数据"}), 400

    if not any('x' in row for row in shape):
        return jsonify({"error": "自定义形状必须至少包含一个石板"}), 400
        
    shuffled_grid, solution_grid = puzzle_generator.generate_puzzle_from_shape(shape)

    if shuffled_grid is None:
        return jsonify({"error": "无法为给定形状生成可解的谜题。请尝试其他形状。"}), 500

    return jsonify({
        "shuffled_grid": serialize_grid(shuffled_grid),
        "solution_grid": serialize_grid(solution_grid)
    })
    
@app.route('/api/solve', methods=['POST'])
def solve_current_puzzle():
    data = request.json
    current_grid_data, solution_grid_data = data.get('current_grid'), data.get('solution_grid')
    if not current_grid_data or not solution_grid_data:
        return jsonify({"error": "Invalid data provided"}), 400
    swaps = calculate_swaps(current_grid_data, solution_grid_data)
    return jsonify({"swaps": swaps})

@app.route('/api/upload_image', methods=['POST'])
def upload_image():
    if 'puzzle_image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files['puzzle_image']
    if file.filename == '':
        return jsonify({"error": "No image file selected"}), 400

    if file:
        filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)

        recognized_grid_obj = vision.analyze_image(temp_path)

        os.remove(temp_path)

        if recognized_grid_obj is None:
            return jsonify({"error": "Could not recognize a valid puzzle in the image."}), 400

        shape = [['x' if tile else ' ' for tile in row] for row in recognized_grid_obj]

        tiles = [tile for row in recognized_grid_obj for tile in row if isinstance(tile, Tile)]

        solver_board = Board(shape)
        is_solvable = solver.solve_puzzle(solver_board, tiles)

        if not is_solvable:
            return jsonify({"error": "Recognized puzzle is not solvable."}), 400

        return jsonify({
            "shuffled_grid": serialize_grid(recognized_grid_obj),
            "solution_grid": serialize_grid(solver_board.grid)
        })

    return jsonify({"error": "An unknown error occurred"}), 500
# ## 新增: 计时挑战 API ##
@app.route('/api/challenge/start', methods=['POST'])
def start_challenge():
    """为计时挑战生成一组谜题"""
    data = request.json
    width, height = data.get('width'), data.get('height')
    
    puzzles = []
    for _ in range(3):
        shuffled, solution = puzzle_generator.generate_random_puzzle(width, height)
        if shuffled is None:
            return jsonify({"error": "Failed to generate a full challenge set"}), 500
        puzzles.append({
            "shuffled_grid": serialize_grid(shuffled),
            "solution_grid": serialize_grid(solution)
        })
    return jsonify({"puzzles": puzzles})

# ## 新增: 排行榜 API ##
@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard_route():
    difficulty = request.args.get('difficulty')
    score_type = request.args.get('type') # 'single' or 'average'
    username = request.args.get('username')

    if not difficulty or not score_type:
        return jsonify({"error": "Missing parameters"}), 400

    time_column = "best_single_time" if score_type == 'single' else "best_average_time"

    with sqlite3.connect(DATABASE_FILE) as conn:
        conn.row_factory = sqlite3.Row # 让查询结果可以像字典一样访问
        cursor = conn.cursor()

        # 1. 获取前100名
        query_top_100 = f"""
            SELECT username, {time_column} as time FROM scores
            WHERE difficulty = ? AND {time_column} IS NOT NULL
            ORDER BY {time_column} ASC
            LIMIT 100
        """
        cursor.execute(query_top_100, (difficulty,))
        top_scores = [dict(row) for row in cursor.fetchall()]

        # 2. 如果提供了用户名，获取该用户的排名
        user_rank_info = None
        if username:
            # 使用窗口函数 RANK() 来计算排名
            query_user_rank = f"""
                SELECT rank, time FROM (
                    SELECT username, {time_column} as time, RANK() OVER (ORDER BY {time_column} ASC) as rank
                    FROM scores
                    WHERE difficulty = ? AND {time_column} IS NOT NULL
                )
                WHERE username = ?
            """
            cursor.execute(query_user_rank, (difficulty, username))
            rank_row = cursor.fetchone()
            if rank_row:
                user_rank_info = dict(rank_row)

    return jsonify({
        "top_scores": top_scores,
        "user_rank_info": user_rank_info
    })

@app.route('/api/leaderboard/submit', methods=['POST'])
def submit_score():
    data = request.json
    difficulty = data.get('difficulty')
    username = data.get('username', '匿名玩家').strip()
    times = data.get('times')
    avg_time = data.get('avgTime')
    
    if not username: username = '匿名玩家'
    if not all([difficulty, times, avg_time]):
        return jsonify({"error": "Missing data"}), 400

    new_single_time = min(times)
    new_avg_time = avg_time

    rank = -1

    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        
        # 检查是否已有记录
        cursor.execute("SELECT best_single_time, best_average_time FROM scores WHERE difficulty = ? AND username = ?", (difficulty, username))
        existing_record = cursor.fetchone()

        if existing_record:
            # 如果存在，只有当新成绩更好时才更新
            old_single, old_avg = existing_record
            
            # 如果之前的记录是空的，则新记录总比它好
            if old_single is None or new_single_time < old_single:
                cursor.execute("UPDATE scores SET best_single_time = ? WHERE difficulty = ? AND username = ?", (new_single_time, difficulty, username))
            
            if old_avg is None or new_avg_time < old_avg:
                cursor.execute("UPDATE scores SET best_average_time = ? WHERE difficulty = ? AND username = ?", (new_avg_time, difficulty, username))

        else:
            # 如果不存在，直接插入
            cursor.execute("INSERT INTO scores (difficulty, username, best_single_time, best_average_time) VALUES (?, ?, ?, ?)",
                           (difficulty, username, new_single_time, new_avg_time))
        
        conn.commit()

        # 查询并返回新成绩的排名
        query_rank = f"""
            SELECT rank FROM (
                SELECT username, RANK() OVER (ORDER BY best_average_time ASC) as rank
                FROM scores
                WHERE difficulty = ? AND best_average_time IS NOT NULL
            )
            WHERE username = ?
        """
        cursor.execute(query_rank, (difficulty, username))
        rank_row = cursor.fetchone()
        if rank_row:
            rank = rank_row[0]

    return jsonify({"success": True, "rank": rank})


if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')