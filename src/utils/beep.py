"""按钮反馈音效工具"""
import threading
import winsound
from pathlib import Path

# WAV 音效文件路径（相对于本文件所在的 utils/ 向上两级到 src/assets/sounds/）
_WAV_PATH = Path(__file__).parent.parent / "assets" / "sounds" / "beep.wav"


def beep() -> None:
    """播放按钮反馈音效；WAV 使用系统异步播放，不为每次点击创建线程。"""
    if _WAV_PATH.exists():
        try:
            winsound.PlaySound(
                str(_WAV_PATH),
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
            )
            return
        except (RuntimeError, OSError):
            pass
    threading.Thread(target=_beep_impl, daemon=True).start()


def _beep_impl() -> None:
    try:
        winsound.Beep(800, 100)
    except (RuntimeError, OSError):
        pass
