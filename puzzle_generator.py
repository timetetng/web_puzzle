import random
from game_logic import Tile, Board


def generate_all_tile_types():
    """Generates all 15 unique tile connection types."""
    singles, straights, l_shapes, t_shapes, cross = [], [], [], [], []
    for i in range(1, 16):
        connections = tuple(int(bit) for bit in format(i, '04b'))
        num = sum(connections)
        if num == 1:
            singles.append(connections)
        elif num == 3:
            t_shapes.append(connections)
        elif num == 4:
            cross.append(connections)
        elif num == 2:
            if (connections[0] and connections[2]) or (connections[1] and connections[3]):
                straights.append(connections)
            else:
                l_shapes.append(connections)
    for cat in [singles, straights, l_shapes, t_shapes]:
        cat.sort()
    return singles + straights + l_shapes + t_shapes + cross


TILE_TYPES = generate_all_tile_types()


def _generate_random_shape(width, height, num_tiles):
    """
    生成一个随机的、连通的棋盘形状。
    """
    if num_tiles > width * height:
        num_tiles = width * height

    shape = [[' ' for _ in range(width)] for _ in range(height)]

    start_r, start_c = random.randint(0, height - 1), random.randint(0, width - 1)
    shape[start_r][start_c] = 'x'

    occupied_cells = [(start_r, start_c)]
    frontier = []

    for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        nr, nc = start_r + dr, start_c + dc
        if 0 <= nr < height and 0 <= nc < width:
            frontier.append((nr, nc))

    while len(occupied_cells) < num_tiles and frontier:
        r, c = random.choice(frontier)
        frontier.remove((r, c))

        if shape[r][c] == ' ':
            shape[r][c] = 'x'
            occupied_cells.append((r, c))

            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < height and 0 <= nc < width and shape[nr][nc] == ' ':
                    if (nr, nc) not in frontier:
                        frontier.append((nr, nc))

    return shape


def _generate_solved_board(width, height, shape):
    """
    在给定的形状上，构建一个满足局部和全局连通性的解。
    """
    for _ in range(500):
        grid = [[None for _ in range(width)] for _ in range(height)]
        possible = True
        for r in range(height):
            for c in range(width):
                if shape[r][c] == ' ':
                    continue

                req_n = 0 if (r == 0 or shape[r - 1][c] == ' ') else grid[r - 1][c].connections[2]
                req_w = 0 if (c == 0 or shape[r][c - 1] == ' ') else grid[r][c - 1].connections[1]

                valid_tiles = []
                for tile_type in TILE_TYPES:
                    if tile_type[0] != req_n or tile_type[3] != req_w:
                        continue

                    can_have_south = (r < height - 1 and shape[r + 1][c] == 'x')
                    if tile_type[2] == 1 and not can_have_south:
                        continue

                    can_have_east = (c < width - 1 and shape[r][c + 1] == 'x')
                    if tile_type[1] == 1 and not can_have_east:
                        continue

                    valid_tiles.append(tile_type)

                if not valid_tiles:
                    possible = False
                    break

                chosen_connections = random.choice(valid_tiles)
                grid[r][c] = Tile(chosen_connections)

            if not possible:
                break

        if possible:
            temp_board = Board(shape)
            temp_board.grid = grid
            if temp_board.is_fully_solved():
                return grid

    return None

# ## 新增函数 ##
def generate_puzzle_from_shape(shape):
    """
    在给定的形状上生成一个谜题。
    """
    if not shape or not shape[0]:
        return None, None

    height = len(shape)
    width = len(shape[0])

    solution_grid = _generate_solved_board(width, height, shape)

    if solution_grid is None:
        return None, None

    flat_tiles = [tile for row in solution_grid for tile in row if tile is not None]
    
    # 检查是否有石板可供洗牌
    if not flat_tiles:
        return None, None
        
    random.shuffle(flat_tiles)

    shuffled_grid = [[None for _ in range(width)] for _ in range(height)]
    i = 0
    for r in range(height):
        for c in range(width):
            if shape[r][c] == 'x':
                shuffled_grid[r][c] = flat_tiles[i]
                i += 1

    return shuffled_grid, solution_grid


def generate_random_puzzle(width, height):
    """
    生成一个随机的、保证有单一连通解的谜题。
    """
    max_tiles = width * height
    min_tiles = int(max_tiles * 0.6)
    num_tiles = random.randint(min_tiles, max_tiles)

    solution_grid = None
    attempt_count = 0
    while solution_grid is None and attempt_count < 10:
        shape = _generate_random_shape(width, height, num_tiles)
        solution_grid = _generate_solved_board(width, height, shape)
        attempt_count += 1

    if solution_grid is None:
        shape = [['x' for _ in range(width)] for _ in range(height)]
        solution_grid = _generate_solved_board(width, height, shape)

    if solution_grid is None:
        return None, None

    flat_tiles = [tile for row in solution_grid for tile in row if tile is not None]
    random.shuffle(flat_tiles)

    shuffled_grid = [[None for _ in range(width)] for _ in range(height)]
    i = 0
    for r in range(height):
        for c in range(width):
            if shape[r][c] == 'x':
                shuffled_grid[r][c] = flat_tiles[i]
                i += 1

    return shuffled_grid, solution_grid