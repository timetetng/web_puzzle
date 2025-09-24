from flask import Flask, render_template, jsonify, request
import os
import uuid

# Import game logic modules
import puzzle_generator
import solver
import vision
from game_logic import Board, Tile


app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


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


@app.route('/')
def index():
    return render_template('index.html')


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

# ## 新增后端路由 ##
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


if __name__ == '__main__':
    # app.run(debug=True)
# 生产环境使用且对公网开放则改为：
    app.run(debug=False, host='0.0.0.0')