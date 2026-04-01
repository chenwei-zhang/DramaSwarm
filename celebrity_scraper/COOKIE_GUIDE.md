# 微博 Cookie 获取指南

本项目的深度爬虫模式需要微博 Cookie 才能运行。

## 获取步骤

1. **打开浏览器**（推荐 Chrome），访问 https://weibo.cn（注意是 `weibo.cn`，不是 `weibo.com`）

2. **登录微博账号**（如果没有账号，注册一个即可，免费）

3. **打开开发者工具**：
   - Chrome: `F12` 或 `Ctrl+Shift+I`（Mac: `Cmd+Option+I`）
   - 切换到 **Network（网络）** 标签

4. **刷新页面**（`F5`）

5. **复制 Cookie**：
   - 点击第一个请求（通常是 `weibo.cn` 本身）
   - 在右侧 **Headers（标头）** → **Request Headers（请求标头）** 中找到 `Cookie`
   - 复制 `Cookie:` 后面的完整值（一长串字符串）

6. **保存 Cookie**（以下方式任选一种）：
   - 保存到文件 `weibo_cookie.txt`（项目根目录）
   - 设置环境变量: `export WEIBO_COOKIE="你的cookie"`
   - 运行时传入: `python update_weibo_data.py --cookie "你的cookie"`

## 注意事项

- Cookie 有效期约 **3 个月**，过期后需要重新获取
- 使用 `weibo.cn`（移动版）的 Cookie，不要用 `weibo.com` 的
- 不要将 Cookie 提交到 Git（已在 `.gitignore` 中排除）

## 使用示例

```bash
# 验证 Cookie 是否有效
python update_weibo_data.py --cookie "YOUR_COOKIE" --validate

# 从文件读取 Cookie，更新指定明星
python update_weibo_data.py --cookie-file weibo_cookie.txt --names 杨幂 赵丽颖

# 更新所有明星
python update_weibo_data.py --cookie-file weibo_cookie.txt --all
```
