"""Command-line helper to regenerate deterministic demo videos.

运行本脚本会覆盖生成 data/incoming 下的三段样本短视频，
适合教师准备课堂环境，或同学在误删样本后快速恢复。
"""

from pathlib import Path
import sys

# 脚本位于 scripts/，直接运行时 Python 默认找不到 app 包。
# 把项目根目录加入 sys.path 后，就可以复用正式后端模块，而不是复制一份逻辑。
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.demo_assets import ensure_demo_videos  # noqa: E402


def main() -> None:
    """Generate demo videos and print their paths for report screenshots."""
    videos = ensure_demo_videos(overwrite=True)
    for item in videos:
        print(f"created: {item['path']} ({item['title']})")


if __name__ == "__main__":
    main()
