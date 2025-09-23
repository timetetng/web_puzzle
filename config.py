# config.py
# 存储所有配置和常量

import pygame

# --- 尺寸与布局 ---
CELL_SIZE = 80
PALETTE_WIDTH = 280
BUTTON_HEIGHT = 65
INFO_HEIGHT = 50

# --- 动画参数 ---
SWAP_DURATION = 0.1       # 单次交换动画时间（秒）
HIGHLIGHT_DURATION = 1.0  # 最终高亮动画时间（秒）
POST_SWAP_PAUSE = 100     # 每次交换后暂停毫秒数

# --- 颜色定义 ---
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GRID = (200, 200, 200)
COLOR_INACTIVE = (50, 50, 50)
COLOR_ACTIVE = (163, 173, 147)
COLOR_HOVER = (150, 170, 200)
COLOR_BUTTON = (0, 150, 136)
COLOR_BUTTON_HOVER = (38, 166, 154)
COLOR_LINE = (46, 148, 239)        # 蓝色，表示已连接
COLOR_DARK_LINE = (86, 88, 74)     # 灰色，表示未连接
COLOR_HIGHLIGHT = (157, 250, 254)  # 高亮颜色
COLOR_SELECTED = (255, 255, 0)     # 黄色，用于玩家选中石板