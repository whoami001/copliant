# Compliance Hub 设计系统

## 品牌色彩

### 主色
| 名称 | 值 | 用途 |
|------|-----|------|
| Primary | #2563EB | 主要操作按钮、链接、选中状态 |
| Primary Hover | #1D4ED8 | 按钮悬停状态 |
| Primary Light | #DBEAFE | 浅色背景、选中项背景 |

### 状态色
| 状态 | 颜色 | 背景 | 文字 |
|------|------|------|------|
| 成功 | #16A34A | #DCFCE7 | #166534 |
| 警告 | #D97706 | #FEF3C7 | #92400E |
| 危险 | #DC2626 | #FEE2E2 | #991B1B |
| 信息 | #0891B2 | - | - |

### 中性色
| 名称 | 值 | 用途 |
|------|-----|------|
| Text Primary | #111827 | 主标题、正文 |
| Text Secondary | #6B7280 | 次要文字、标签 |
| Text Disabled | #9CA3AF | 禁用状态文字 |
| Border | #E5E7EB | 边框、分割线 |
| Background | #F9FAFB | 页面背景 |
| Surface | #FFFFFF | 卡片、容器背景 |

## 间距系统

基于 4px 网格：
- `--spacing-xs`: 4px
- `--spacing-sm`: 8px
- `--spacing-md`: 12px
- `--spacing-lg`: 16px
- `--spacing-xl`: 24px

## 圆角系统

- `--radius-sm`: 4px (小按钮、徽章)
- `--radius-md`: 6px (输入框、卡片)
- `--radius-lg`: 8px (大按钮、模态框)

## 字体

### 字体栈
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
             "Helvetica Neue", Arial, sans-serif;
```

### 字号
- Logo/大标题：20px
- 页面标题：24px
- 卡片标题：16px
- 正文：14px
- 次要文字/小字：12px

### 字重
- 正常：400
- 中等：500 (按钮、标签)
- 粗体：600 (标题、Logo)
- 特粗：700 (统计数据)

## 组件规范

### 按钮
- 主按钮：Primary 背景，白色文字
- 次按钮：白色背景，Primary 边框和文字
- 危险按钮：Danger 背景，白色文字

### 输入框
- 边框：#E5E7EB
- 焦点：Primary 边框 + #DBEAFE 外发光
- 高度：40px (标准)

### 卡片
- 背景：#FFFFFF
- 边框：#E5E7EB
- 圆角：8px
- 阴影：无（扁平设计）

### 徽章 (Badge)
- 圆角：9999px (完全圆角)
- 内边距：2px 8px
- 字号：12px

## 响应式断点

- 移动：375px
- 平板：768px
- 桌面：1024px
- 宽屏：1440px

## 可访问性要求

1. 文字对比度：WCAG AA 标准 (4.5:1 正文，3:1 大文字)
2. 焦点状态：所有交互元素必须有清晰的焦点指示器
3. 触摸目标：最小 44x44px
4. 不使用纯颜色编码（需配合文字或图标）

## 设计原则

1. **功能性优先** - 作为内部工具，清晰度高于美观
2. **一致性** - 相同组件在整个应用中保持相同样式
3. **效率** - 减少点击次数，常用操作触手可及
4. **清晰反馈** - 所有操作都有明确的状态反馈
