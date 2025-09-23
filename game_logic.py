# game_logic.py
# 定义游戏的核心对象 Tile 和 Board

class Tile:
    """表示一个状态固定的石板。"""
    def __init__(self, connections, tile_id=None):
        self.connections = tuple(connections)
        self.id = tile_id if tile_id is not None else id(self)

    def __eq__(self, other):
        return isinstance(other, Tile) and self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"T{self.connections}"


class Board:
    """表示游戏棋盘。"""
    def __init__(self, shape):
        self.shape = [list(row) for row in shape]
        self.height = len(self.shape)
        self.width = len(self.shape[0])
        self.grid = [[None for _ in range(self.width)] for _ in range(self.height)]
        self.empty_slots = self._get_empty_slots()

    def _get_empty_slots(self):
        slots = []
        for r in range(self.height):
            for c in range(self.width):
                if self.shape[r][c] == 'x':
                    slots.append((r, c))
        return slots

    def is_valid_placement(self, tile, r, c):
        directions = [(-1, 0, 0, 2), (0, 1, 1, 3), (1, 0, 2, 0), (0, -1, 3, 1)]
        for dr, dc, my_side, neighbor_side in directions:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.height and 0 <= nc < self.width:
                neighbor = self.grid[nr][nc]
                if neighbor and tile.connections[my_side] != neighbor.connections[neighbor_side]:
                    return False
        return True

    def is_fully_solved(self):
        all_tile_coords = []

        for r in range(self.height):
            for c in range(self.width):
                tile = self.grid[r][c]
                is_in_shape = self.shape[r][c] == 'x'
                if is_in_shape and not tile:
                    return False
                if not is_in_shape and tile:
                    return False
                if tile:
                    all_tile_coords.append((r, c))

        if not all_tile_coords:
            return True

        for r, c in all_tile_coords:
            tile = self.grid[r][c]

            has_north_neighbor = r > 0 and self.shape[r - 1][c] == 'x'
            if tile.connections[0] == 1:
                if not has_north_neighbor or not self.grid[r - 1][c] or self.grid[r - 1][c].connections[2] != 1:
                    return False

            has_east_neighbor = c < self.width - 1 and self.shape[r][c + 1] == 'x'
            if tile.connections[1] == 1:
                if not has_east_neighbor or not self.grid[r][c + 1] or self.grid[r][c + 1].connections[3] != 1:
                    return False

            has_south_neighbor = r < self.height - 1 and self.shape[r + 1][c] == 'x'
            if tile.connections[2] == 1:
                if not has_south_neighbor or not self.grid[r + 1][c] or self.grid[r + 1][c].connections[0] != 1:
                    return False

            has_west_neighbor = c > 0 and self.shape[r][c - 1] == 'x'
            if tile.connections[3] == 1:
                if not has_west_neighbor or not self.grid[r][c - 1] or self.grid[r][c - 1].connections[1] != 1:
                    return False

        q = [all_tile_coords[0]]
        visited = {all_tile_coords[0]}
        while q:
            r, c = q.pop(0)
            tile = self.grid[r][c]
            if tile.connections[0] == 1 and (r - 1, c) not in visited:
                visited.add((r - 1, c))
                q.append((r - 1, c))
            if tile.connections[1] == 1 and (r, c + 1) not in visited:
                visited.add((r, c + 1))
                q.append((r, c + 1))
            if tile.connections[2] == 1 and (r + 1, c) not in visited:
                visited.add((r + 1, c))
                q.append((r + 1, c))
            if tile.connections[3] == 1 and (r, c - 1) not in visited:
                visited.add((r, c - 1))
                q.append((r, c - 1))

        return len(visited) == len(all_tile_coords)

    def place_tile(self, tile, r, c):
        self.grid[r][c] = tile

    def remove_tile(self, r, c):
        self.grid[r][c] = None
