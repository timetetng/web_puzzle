import pygame
import sys
import math
import time
import tkinter as tk
from tkinter import filedialog

# 从其他模块导入
from config import *
from game_logic import Tile, Board
from solver import solve_puzzle
from vision import analyze_image
import puzzle_generator

# --- 界面绘制与动画函数 (不变) ---
def generate_all_tile_types():
    singles, straights, l_shapes, t_shapes, cross = [], [], [], [], []
    for i in range(1, 16):
        connections = tuple(int(bit) for bit in format(i, '04b'))
        num = sum(connections)
        if num == 1: singles.append(connections)
        elif num == 3: t_shapes.append(connections)
        elif num == 4: cross.append(connections)
        elif num == 2:
            if (connections[0] and connections[2]) or (connections[1] and connections[3]): straights.append(connections)
            else: l_shapes.append(connections)
    for cat in [singles, straights, l_shapes, t_shapes]: cat.sort()
    return singles + straights + l_shapes + t_shapes + cross
TILE_TYPES = generate_all_tile_types()

def draw_tile(surface, tile_connections, rect, connected_sides, line_width=5, highlight_progress=0.0):
    center_x, center_y = rect.center
    n, e, s, w = tile_connections; cn, ce, cs, cw = connected_sides
    is_any_side_connected = any(connected_sides)
    def get_color(is_connected):
        base = COLOR_LINE if is_connected else COLOR_DARK_LINE
        if highlight_progress > 0 and is_connected:
            p = 1.0 - abs(2 * highlight_progress - 1)
            return (int(base[0] + (COLOR_HIGHLIGHT[0] - base[0]) * p),int(base[1] + (COLOR_HIGHLIGHT[1] - base[1]) * p),int(base[2] + (COLOR_HIGHLIGHT[2] - base[2]) * p))
        return base
    if n: pygame.draw.line(surface, get_color(cn), (center_x, center_y), (center_x, rect.top), line_width)
    if e: pygame.draw.line(surface, get_color(ce), (center_x, center_y), (rect.right, center_y), line_width)
    if s: pygame.draw.line(surface, get_color(cs), (center_x, center_y), (center_x, rect.bottom), line_width)
    if w: pygame.draw.line(surface, get_color(cw), (center_x, center_y), (rect.left, center_y), line_width)
    diamond_size = line_width * 2.0 
    diamond_points = [(center_x, center_y - diamond_size), (center_x + diamond_size, center_y), (center_x, center_y + diamond_size), (center_x - diamond_size, center_y)]
    pygame.draw.polygon(surface, get_color(is_any_side_connected), diamond_points)

def draw_board_state(surface, board_grid, grid_rects, dragged_pos=None):
    rows, cols = len(board_grid), len(board_grid[0])
    for r in range(rows):
        for c in range(cols):
            if dragged_pos == (r,c): continue
            cell_content = board_grid[r][c]
            if isinstance(cell_content, Tile):
                rect = grid_rects[r][c]
                connected_sides = [False] * 4; t_conn = cell_content.connections
                if t_conn[0] and r > 0 and isinstance(board_grid[r-1][c], Tile) and dragged_pos !=(r-1,c): connected_sides[0] = True
                if t_conn[1] and c < cols-1 and isinstance(board_grid[r][c+1], Tile) and dragged_pos !=(r,c+1): connected_sides[1] = True
                if t_conn[2] and r < rows-1 and isinstance(board_grid[r+1][c], Tile) and dragged_pos !=(r+1,c): connected_sides[2] = True
                if t_conn[3] and c > 0 and isinstance(board_grid[r][c-1], Tile) and dragged_pos !=(r,c-1): connected_sides[3] = True
                draw_tile(surface, t_conn, rect, tuple(connected_sides))

def draw_grid_background(screen, grid_rects, final_board_grid):
    rows, cols = len(final_board_grid), len(final_board_grid[0])
    for r in range(rows):
        for c in range(cols):
            rect = grid_rects[r][c]
            if final_board_grid[r][c] is not None:
                pygame.draw.rect(screen, COLOR_ACTIVE, rect)
            else:
                pygame.draw.rect(screen, COLOR_INACTIVE, rect)
            pygame.draw.rect(screen, COLOR_GRID, rect, 1)

def run_swap_animation(screen, clock, initial_board, final_board_grid, grid_rects):
    rows, cols = len(initial_board), len(initial_board[0])
    swaps, current_board = [], [row[:] for row in initial_board]
    initial_tiles = {}
    for r, row in enumerate(current_board):
        for c, t in enumerate(row):
            if isinstance(t, Tile): initial_tiles[(r, c)] = t
    pos_to_tile_id = {pos: t.id for pos, t in initial_tiles.items()}
    tile_id_to_pos = {t_id: pos for pos, t_id in pos_to_tile_id.items()}
    final_tiles = {}
    for r, row in enumerate(final_board_grid):
        for c, t in enumerate(row):
            if isinstance(t, Tile): final_tiles[(r, c)] = t
    for (r,c), correct_tile in final_tiles.items():
        current_tile = current_board[r][c]
        if not current_tile or correct_tile.id != current_tile.id:
            pos_of_correct_tile = tile_id_to_pos[correct_tile.id]
            swaps.append(((r,c), pos_of_correct_tile))
            tile_at_swap_pos = current_board[pos_of_correct_tile[0]][pos_of_correct_tile[1]]
            current_board[r][c], current_board[pos_of_correct_tile[0]][pos_of_correct_tile[1]] = tile_at_swap_pos, current_tile
            if current_tile: tile_id_to_pos[current_tile.id] = pos_of_correct_tile
            tile_id_to_pos[correct_tile.id] = (r,c)
    
    board_for_anim = [row[:] for row in initial_board]
    for pos1, pos2 in swaps:
        start_time = time.time(); tile1, tile2 = board_for_anim[pos1[0]][pos1[1]], board_for_anim[pos2[0]][pos2[1]]
        anim_running = True
        while anim_running:
            progress = min((time.time() - start_time) / SWAP_DURATION, 1.0)
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN: return
            screen.fill(COLOR_INACTIVE)
            draw_grid_background(screen, grid_rects, final_board_grid)
            temp_board = [row[:] for row in board_for_anim]
            if tile1: temp_board[pos1[0]][pos1[1]] = None
            if tile2: temp_board[pos2[0]][pos2[1]] = None
            draw_board_state(screen, temp_board, grid_rects)
            if tile1:
                start_px1, end_px1 = grid_rects[pos1[0]][pos1[1]].topleft, grid_rects[pos2[0]][pos2[1]].topleft
                curr_x = start_px1[0] + (end_px1[0] - start_px1[0]) * progress; curr_y = start_px1[1] + (end_px1[1] - start_px1[1]) * progress
                draw_tile(screen, tile1.connections, pygame.Rect(curr_x, curr_y, CELL_SIZE, CELL_SIZE), (False,)*4)
            if tile2:
                start_px2, end_px2 = grid_rects[pos2[0]][pos2[1]].topleft, grid_rects[pos1[0]][pos1[1]].topleft
                curr_x = start_px2[0] + (end_px2[0] - start_px2[0]) * progress; curr_y = start_px2[1] + (end_px2[1] - start_px2[1]) * progress
                draw_tile(screen, tile2.connections, pygame.Rect(curr_x, curr_y, CELL_SIZE, CELL_SIZE), (False,)*4)
            pygame.display.flip(); clock.tick(60)
            if progress >= 1.0: anim_running = False
        board_for_anim[pos1[0]][pos1[1]], board_for_anim[pos2[0]][pos2[1]] = tile2, tile1
        screen.fill(COLOR_INACTIVE); 
        draw_grid_background(screen, grid_rects, final_board_grid)
        draw_board_state(screen, board_for_anim, grid_rects); pygame.display.flip()
        pygame.time.wait(POST_SWAP_PAUSE)
    
    start_time = time.time(); anim_running = True
    while anim_running:
        progress = min((time.time() - start_time) / HIGHLIGHT_DURATION, 1.0)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN: return
        screen.fill(COLOR_INACTIVE)
        draw_grid_background(screen, grid_rects, final_board_grid)
        draw_board_state(screen, final_board_grid, grid_rects)
        for r in range(rows):
            for c in range(cols):
                if isinstance(final_board_grid[r][c], Tile):
                    rect = grid_rects[r][c]
                    draw_tile(screen, final_board_grid[r][c].connections, rect, (True, True, True, True), highlight_progress=progress)
        pygame.display.flip(); clock.tick(60)
        if progress >= 1.0: anim_running = False

def check_player_win(current_grid, solution_grid):
    if not solution_grid: return False
    rows, cols = len(current_grid), len(current_grid[0])
    for r in range(rows):
        for c in range(cols):
            current_tile = current_grid[r][c]
            solution_tile = solution_grid[r][c]
            if current_tile is None and solution_tile is None: continue
            if (current_tile is None) != (solution_tile is None) or \
               current_tile.connections != solution_tile.connections:
                return False
    return True

def main():
    cols, rows = 0, 0
    board_shape_and_tiles = None
    solution_grid = None
    shuffled_board_start_state = None
    
    root = tk.Tk(); root.withdraw()
    mode = input("请选择模式: [1] 手动设计  [2] 从图片导入  [3] 随机谜题 (玩家挑战)\n请输入数字: ")
    
    if mode == '2':
        image_path = filedialog.askopenfilename(title="请选择一个谜题图片", filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")])
        if not image_path: print("未选择文件，程序退出。"); return
        board_shape_and_tiles = analyze_image(image_path)
        if board_shape_and_tiles:
            rows, cols = len(board_shape_and_tiles), len(board_shape_and_tiles[0])
        else:
            print("图片识别失败，程序将退出。"); return
    elif mode == '3':
        try:
            size_str = input("请输入棋盘最大尺寸 (例如: 5x5): ")
            rows, cols = map(int, size_str.lower().split('x'))
            if cols <= 2 or rows <= 2 or cols > 10 or rows > 10: raise ValueError
        except ValueError:
            print("输入无效，将使用默认尺寸 5x5。"); cols, rows = 5, 5
        
        initial_board, solution = puzzle_generator.generate_random_puzzle(cols, rows)
        if initial_board:
            board_shape_and_tiles = initial_board
            solution_grid = solution
            shuffled_board_start_state = [row[:] for row in initial_board]
        else:
            print("生成谜题失败，程序将退出。"); return
    else:
        try:
            cols = int(input("请输入棋盘宽度 (例如: 5): ")); rows = int(input("请输入棋盘高度 (例如: 5): "))
            if cols <= 0 or rows <= 0 or cols > 15 or rows > 10: raise ValueError
        except ValueError: print("输入无效，将使用默认尺寸 5x5。"); cols, rows = 5, 5
        board_shape_and_tiles = [[' ' for _ in range(cols)] for _ in range(rows)]

    pygame.init()

    if mode == '3':
        screen_width = cols * CELL_SIZE
        main_area_height = rows * CELL_SIZE
    else:
        tiles_per_row_in_palette = PALETTE_WIDTH // (CELL_SIZE + 5);
        if tiles_per_row_in_palette == 0: tiles_per_row_in_palette = 1
        num_palette_rows = math.ceil(len(TILE_TYPES) / tiles_per_row_in_palette); palette_min_height = num_palette_rows * (CELL_SIZE + 10) + 40 
        grid_height = rows * CELL_SIZE; main_area_height = max(grid_height, palette_min_height)
        screen_width = cols * CELL_SIZE + PALETTE_WIDTH
        
    screen_height = main_area_height + BUTTON_HEIGHT + INFO_HEIGHT
    screen = pygame.display.set_mode((screen_width, screen_height)); pygame.display.set_caption("益智连线游戏求解器")
    font = pygame.font.SysFont("SimHei", 32); info_font = pygame.font.SysFont("SimHei", 24)
    clock = pygame.time.Clock()
    
    if mode == '2':
        game_mode = 'tile_placement'
        active_cells_count = sum(1 for row in board_shape_and_tiles for cell in row if cell != ' ' and not isinstance(cell, Tile))
        placed_tiles_count = sum(1 for row in board_shape_and_tiles for cell in row if isinstance(cell, Tile))
    elif mode == '3':
        game_mode = 'player_solve'
    else:
        game_mode = "shape_design"
        placed_tiles_count = 0; active_cells_count = 0
    
    is_dragging = False; dragged_item = None; dragged_item_rect = None; original_pos = None

    board_rect = pygame.Rect(0, 0, cols * CELL_SIZE, rows * CELL_SIZE)
    palette_rect = pygame.Rect(cols * CELL_SIZE, 0, PALETTE_WIDTH, main_area_height)
    full_button_rect = pygame.Rect(0, main_area_height, screen_width, BUTTON_HEIGHT)
    left_button_rect = pygame.Rect(0, main_area_height, screen_width // 2, BUTTON_HEIGHT)
    right_button_rect = pygame.Rect(screen_width // 2, main_area_height, screen_width // 2, BUTTON_HEIGHT)
    info_rect = pygame.Rect(0, main_area_height + BUTTON_HEIGHT, screen_width, INFO_HEIGHT)
    grid_rects = [[pygame.Rect(c*CELL_SIZE, r*CELL_SIZE, CELL_SIZE, CELL_SIZE) for c in range(cols)] for r in range(rows)]
    palette_tile_rects = {}
    if mode != '3':
        tiles_per_row_in_palette = PALETTE_WIDTH // (CELL_SIZE + 5);
        if tiles_per_row_in_palette == 0: tiles_per_row_in_palette = 1
        for i, t_type in enumerate(TILE_TYPES):
            px = cols * CELL_SIZE + (i % tiles_per_row_in_palette) * (CELL_SIZE + 5) + 15; py = (i // tiles_per_row_in_palette) * (CELL_SIZE + 10) + 20
            palette_tile_rects[t_type] = pygame.Rect(px, py, CELL_SIZE, CELL_SIZE)
    
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        
        # --- 全新、重构后的事件处理循环 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            # --- 拖动事件处理 (独立于点击) ---
            if is_dragging:
                if event.type == pygame.MOUSEMOTION:
                    dragged_item_rect.center = mouse_pos
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    # 玩家模式下的拖动释放 (交换)
                    if game_mode == 'player_solve':
                        if board_rect.collidepoint(mouse_pos):
                            c_target, r_target = mouse_pos[0] // CELL_SIZE, mouse_pos[1] // CELL_SIZE
                            if isinstance(board_shape_and_tiles[r_target][c_target], Tile) and original_pos != (r_target, c_target):
                                r_orig, c_orig = original_pos
                                board_shape_and_tiles[r_orig][c_orig], board_shape_and_tiles[r_target][c_target] = \
                                    board_shape_and_tiles[r_target][c_target], board_shape_and_tiles[r_orig][c_orig]
                                if check_player_win(board_shape_and_tiles, solution_grid):
                                    game_mode = "player_won"
                        is_dragging = False
                    # 放置模式下的拖动释放
                    elif game_mode == 'tile_placement':
                        is_dropped=False
                        if board_rect.collidepoint(mouse_pos):
                            c,r=mouse_pos[0]//CELL_SIZE,mouse_pos[1]//CELL_SIZE
                            if board_shape_and_tiles[r][c]!=' ':
                                target_cell=board_shape_and_tiles[r][c]
                                if target_cell is None or isinstance(target_cell, Tile):
                                    tile_to_place=Tile(dragged_item) if drag_origin=='palette' else dragged_item
                                    if target_cell is None: 
                                        board_shape_and_tiles[r][c]=tile_to_place
                                        if drag_origin == 'palette': placed_tiles_count += 1
                                    elif isinstance(target_cell, Tile): 
                                        board_shape_and_tiles[r][c]=tile_to_place
                                        if drag_origin == 'board': board_shape_and_tiles[original_pos[0]][original_pos[1]] = target_cell
                                    is_dropped=True
                        if not is_dropped and drag_origin=='board': board_shape_and_tiles[original_pos[0]][original_pos[1]]=dragged_item
                        is_dragging=False
                continue # 拖动事件处理完后跳过后续点击判断

            # --- 点击事件处理 ---
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game_mode == 'player_solve':
                    if left_button_rect.collidepoint(mouse_pos): # 重试
                        board_shape_and_tiles = [row[:] for row in shuffled_board_start_state]
                    elif right_button_rect.collidepoint(mouse_pos): # 自动求解
                        game_mode = 'solving'
                        # ... 求解动画 ...
                    elif board_rect.collidepoint(mouse_pos): # 开始拖动
                        c, r = mouse_pos[0] // CELL_SIZE, mouse_pos[1] // CELL_SIZE
                        if isinstance(board_shape_and_tiles[r][c], Tile):
                            is_dragging = True; dragged_item = board_shape_and_tiles[r][c]; original_pos = (r, c); dragged_item_rect = grid_rects[r][c].copy()
                
                elif game_mode == 'player_won':
                    if left_button_rect.collidepoint(mouse_pos): # 再来一局
                        print("正在生成新一局游戏...")
                        initial_board, solution = puzzle_generator.generate_random_puzzle(cols, rows)
                        if initial_board:
                            board_shape_and_tiles = initial_board
                            solution_grid = solution
                            shuffled_board_start_state = [row[:] for row in initial_board]
                            game_mode = 'player_solve'
                        else:
                            print("生成失败！"); running = False
                    elif right_button_rect.collidepoint(mouse_pos): # 退出
                        running = False

                elif game_mode == 'shape_design':
                    if full_button_rect.collidepoint(mouse_pos) and active_cells_count > 0:
                        game_mode = "tile_placement"; placed_tiles_count = 0
                        for r_idx,c_idx in [(r,c) for r in range(rows) for c in range(cols) if board_shape_and_tiles[r][c]=='x']: board_shape_and_tiles[r_idx][c_idx]=None
                    elif board_rect.collidepoint(mouse_pos):
                        c,r=mouse_pos[0]//CELL_SIZE, mouse_pos[1]//CELL_SIZE
                        if board_shape_and_tiles[r][c] == ' ': board_shape_and_tiles[r][c] = 'x'; active_cells_count += 1
                        else: board_shape_and_tiles[r][c] = ' '; active_cells_count -= 1

                elif game_mode == 'tile_placement':
                    if full_button_rect.collidepoint(mouse_pos) and placed_tiles_count == active_cells_count and active_cells_count > 0:
                        game_mode = "solving"
                        # ... 求解动画 ...
                    elif palette_rect.collidepoint(mouse_pos):
                        for t_type, rect in palette_tile_rects.items():
                            if rect.collidepoint(mouse_pos): is_dragging=True; dragged_item=t_type; dragged_item_rect=rect.copy(); drag_origin='palette'; break
                    elif board_rect.collidepoint(mouse_pos):
                        c, r = mouse_pos[0]//CELL_SIZE, mouse_pos[1]//CELL_SIZE
                        if isinstance(board_shape_and_tiles[r][c], Tile): is_dragging=True; dragged_item=board_shape_and_tiles[r][c]; original_pos=(r,c); dragged_item_rect=grid_rects[r][c].copy(); drag_origin='board'; board_shape_and_tiles[r][c]=None

        # --- 触发求解动画的逻辑 (移出事件循环) ---
        if game_mode == 'solving':
            screen.fill(COLOR_INACTIVE); solve_text = font.render("正在为您求解...", True, COLOR_WHITE); screen.blit(solve_text, solve_text.get_rect(center=screen.get_rect().center)); pygame.display.flip()
            initial_board_state = [row[:] for row in board_shape_and_tiles]
            
            # 确定形状和当前石板
            if mode == '3': # 玩家模式
                user_shape = [['x' if tile is not None else ' ' for tile in row] for row in solution_grid]
            else: # 设计/导入模式
                user_shape = [['x' if cell is not None else ' ' for cell in row] for row in board_shape_and_tiles]

            user_tiles = [cell for row in board_shape_and_tiles for cell in row if isinstance(cell, Tile)]
            solver_board = Board(user_shape)
            
            if solve_puzzle(solver_board, user_tiles):
                final_grid = solver_board.grid
                game_mode='animating'; run_swap_animation(screen, clock, initial_board_state, final_grid, grid_rects)
                board_shape_and_tiles = final_grid
                game_mode = "player_won" if mode == '3' else "solved"
            else:
                game_mode = "player_solve" if mode == '3' else "no_solution"

        # --- 渲染 ---
        screen.fill(COLOR_INACTIVE)
        if game_mode not in ['animating', 'solving']:
            for r in range(rows):
                for c in range(cols):
                    rect = grid_rects[r][c]; cell_content = board_shape_and_tiles[r][c]
                    bg_color = COLOR_INACTIVE
                    if isinstance(cell_content, Tile) or cell_content == 'x':
                        bg_color = COLOR_HOVER if game_mode == "shape_design" and rect.collidepoint(mouse_pos) else COLOR_ACTIVE
                    pygame.draw.rect(screen, bg_color, rect)
                    pygame.draw.rect(screen, COLOR_GRID, rect, 1)

            draw_board_state(screen, board_shape_and_tiles, grid_rects, original_pos if is_dragging else None)
            
            if game_mode == "tile_placement":
                pygame.draw.rect(screen, (30,30,30), palette_rect)
                for t_type, rect in palette_tile_rects.items():
                    pygame.draw.rect(screen, COLOR_HOVER if rect.collidepoint(mouse_pos) else (30,30,30), rect.inflate(4,4), border_radius=5)
                    draw_tile(screen, t_type, rect, (False, False, False, False)) 
            
            if is_dragging:
                draw_tile(screen, dragged_item.connections, dragged_item_rect, (False, False, False, False))
            
            info_text_str = ""
            pygame.draw.rect(screen, (10,10,10), info_rect)

            if game_mode == 'player_solve':
                info_text_str = "拖动石板交换位置"
                btn1_rect, btn2_rect = left_button_rect, right_button_rect; btn1_text, btn2_text = "重试", "自动求解"
                pygame.draw.rect(screen, COLOR_BUTTON_HOVER if btn1_rect.collidepoint(mouse_pos) else COLOR_BUTTON, btn1_rect)
                pygame.draw.rect(screen, COLOR_BUTTON_HOVER if btn2_rect.collidepoint(mouse_pos) else COLOR_BUTTON, btn2_rect)
                screen.blit(font.render(btn1_text, True, COLOR_WHITE), font.render(btn1_text, True, COLOR_WHITE).get_rect(center=btn1_rect.center))
                screen.blit(font.render(btn2_text, True, COLOR_WHITE), font.render(btn2_text, True, COLOR_WHITE).get_rect(center=btn2_rect.center))
            elif game_mode == 'player_won':
                info_text_str = "你赢了! 恭喜你解开了谜题！"
                btn1_rect, btn2_rect = left_button_rect, right_button_rect; btn1_text, btn2_text = "再来一局", "退出"
                pygame.draw.rect(screen, COLOR_BUTTON_HOVER if btn1_rect.collidepoint(mouse_pos) else COLOR_BUTTON, btn1_rect)
                pygame.draw.rect(screen, COLOR_BUTTON_HOVER if btn2_rect.collidepoint(mouse_pos) else COLOR_BUTTON, btn2_rect)
                screen.blit(font.render(btn1_text, True, COLOR_WHITE), font.render(btn1_text, True, COLOR_WHITE).get_rect(center=btn1_rect.center))
                screen.blit(font.render(btn2_text, True, COLOR_WHITE), font.render(btn2_text, True, COLOR_WHITE).get_rect(center=btn2_rect.center))
            else:
                btn_text_str = ""
                if game_mode == "shape_design": btn_text_str, info_text_str = "完成形状设计", f"点击格子 ({active_cells_count}个)"
                elif game_mode == "tile_placement": btn_text_str, info_text_str = "开始求解", f"拖动石板 ({placed_tiles_count}/{active_cells_count})"
                elif game_mode == "solved": btn_text_str, info_text_str = "完成！", "成功找到解！"
                elif game_mode == "no_solution": btn_text_str, info_text_str = "无解", "此谜题无解！"
                if btn_text_str:
                    pygame.draw.rect(screen, COLOR_BUTTON_HOVER if full_button_rect.collidepoint(mouse_pos) else COLOR_BUTTON, full_button_rect)
                    screen.blit(font.render(btn_text_str, True, COLOR_WHITE), font.render(btn_text_str, True, COLOR_WHITE).get_rect(center=full_button_rect.center))

            screen.blit(info_font.render(info_text_str, True, COLOR_GRID), info_font.render(info_text_str, True, COLOR_GRID).get_rect(center=info_rect.center))
            pygame.display.flip()
        clock.tick(60)
        
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()