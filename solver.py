# solver.py
# 包含回溯求解算法

from game_logic import Board


def solve_puzzle(board, tiles):
    """
    使用回溯算法求解谜题。
    它会尝试将给定的石板放置在棋盘的每个空位上，直到找到一个完整的解。
    """
    # 创建一个全新的列表副本，防止在递归过程中修改原始列表
    tiles_copy = list(tiles)

    def backtrack(slot_index, available_tiles):
        if slot_index == len(board.empty_slots):
            # 所有空位都已填充，检查是否为有效解
            return board.is_fully_solved()

        r, c = board.empty_slots[slot_index]
        # 遍历所有可用的石板
        for i in range(len(available_tiles)):
            tile = available_tiles[i]

            if board.is_valid_placement(tile, r, c):
                board.place_tile(tile, r, c)

                # 创建一个移除了当前石板的新列表
                remaining_tiles = available_tiles[:i] + available_tiles[i + 1:]

                if backtrack(slot_index + 1, remaining_tiles):
                    return True

                # 回溯：如果子问题无解，则移除当前放置的石板
                board.remove_tile(r, c)

        return False

    return backtrack(0, tiles_copy)
