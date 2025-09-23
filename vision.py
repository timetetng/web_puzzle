import cv2
import numpy as np
from game_logic import Tile


def _classify_tile_image(tile_mask_img):
    """
    根据给定的图像掩码，判断石板的连接。
    """
    th, tw = tile_mask_img.shape
    if th == 0 or tw == 0:
        return (0, 0, 0, 0)
    margin_h, margin_w = int(th * 0.20), int(tw * 0.20)
    probe_points = {
        "N": (margin_h, tw // 2),
        "E": (th // 2, tw - margin_w),
        "S": (th - margin_h, tw // 2),
        "W": (th // 2, margin_w)
    }
    connections = [0, 0, 0, 0]
    if tile_mask_img[probe_points["N"]] == 255:
        connections[0] = 1
    if tile_mask_img[probe_points["E"]] == 255:
        connections[1] = 1
    if tile_mask_img[probe_points["S"]] == 255:
        connections[2] = 1
    if tile_mask_img[probe_points["W"]] == 255:
        connections[3] = 1
    return tuple(connections)


def analyze_image(image_path):
    """
    分析给定的图像，识别其中的谜题板并返回其表示。
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError
    except (FileNotFoundError, Exception) as e:
        print(f"Error loading image '{image_path}': {e}")
        return None

    path_colors = [
        (np.array([74, 88, 86]), 50),     # Gray path (BGR)
        (np.array([238, 148, 46]), 50),   # Dark blue path (BGR)
        (np.array([244, 244, 147]), 50),  # Light blue path (BGR)
        (np.array([236, 221, 78]), 50)    # Cyan path (BGR)
    ]
    bg_color = (np.array([50, 85, 64]), 15)  # Background color (BGR)

    all_paths_mask = np.zeros(img.shape[:2], dtype=np.uint8)
    for color, tolerance in path_colors:
        lower = np.maximum(0, color - tolerance).astype(np.uint8)
        upper = np.minimum(255, color + tolerance).astype(np.uint8)
        mask = cv2.inRange(img, lower, upper)
        all_paths_mask = cv2.bitwise_or(all_paths_mask, mask)

    lower_bg = np.maximum(0, bg_color[0] - bg_color[1]).astype(np.uint8)
    upper_bg = np.minimum(255, bg_color[0] + bg_color[1]).astype(np.uint8)
    bg_mask = cv2.inRange(img, lower_bg, upper_bg)
    tiles_mask = cv2.bitwise_not(bg_mask)
    kernel = np.ones((5, 5), np.uint8)
    tiles_mask_opened = cv2.morphologyEx(tiles_mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(tiles_mask_opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    tile_boxes = []
    min_area = (img.shape[0] * img.shape[1]) / 100
    for cnt in contours:
        if cv2.contourArea(cnt) > min_area:
            x, y, w, h = cv2.boundingRect(cnt)
            if 0.8 < w / h < 1.2:
                tile_boxes.append((x, y, w, h))

    if not tile_boxes:
        return None

    avg_size = np.mean([b[2] for b in tile_boxes])
    grid_positions = {}
    for (x, y, w, h) in tile_boxes:
        center_x, center_y = x + w // 2, y + h // 2
        # 使用更稳健的四舍五入
        r, c = int(round(center_y / avg_size)), int(round(center_x / avg_size))
        grid_positions[(r, c)] = (x, y, w, h)

    if not grid_positions:
        return None
    min_r = min(pos[0] for pos in grid_positions.keys())
    min_c = min(pos[1] for pos in grid_positions.keys())

    normalized_grid = {}
    for (r, c), box in grid_positions.items():
        normalized_grid[(r - min_r, c - min_c)] = box

    max_r = max(pos[0] for pos in normalized_grid.keys())
    max_c = max(pos[1] for pos in normalized_grid.keys())

    initial_board = [[None for _ in range(max_c + 1)] for _ in range(max_r + 1)]
    for (r, c), (x, y, w, h) in normalized_grid.items():
        tile_path_img = all_paths_mask[y:y + h, x:x + w]
        connections = _classify_tile_image(tile_path_img)
        if sum(connections) > 0:
            initial_board[r][c] = Tile(connections)

    return initial_board
