"""
视频抽帧工具
将视频转换为多张帧图片，供给Doubao-Seed-2.0-Code处理
"""
import base64
from io import BytesIO
from typing import List
from PIL import Image


def extract_frames_from_video(
    video_bytes: bytes,
    fps: float = 1.0,
    max_frames: int = 30
) -> List[str]:
    """
    从视频中提取帧，并转换为base64编码的图片URL
    
    Args:
        video_bytes: 视频二进制数据
        fps: 每秒提取多少帧，默认1帧/秒
        max_frames: 最大提取帧数，避免过大
    
    Returns:
        List[str]: base64编码的图片URL列表，格式为 data:image/png;base64,...
    """
    try:
        import tempfile
        import os
        from moviepy import VideoFileClip

        # 写入临时文件
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_file.write(video_bytes)
            tmp_path = tmp_file.name

        try:
            clip = VideoFileClip(tmp_path)
            duration = clip.duration
            total_frames = int(duration * fps)
            
            # 限制最大帧数
            total_frames = min(total_frames, max_frames)
            
            # 如果视频很短，至少提取1帧
            if total_frames < 1:
                total_frames = 1
            
            frame_urls: List[str] = []
            
            for i in range(total_frames):
                # 计算时间点，均匀分布
                if total_frames == 1:
                    t = duration / 2  # 取中间帧
                else:
                    t = (i / (total_frames - 1)) * duration
                
                # 获取帧
                frame = clip.get_frame(t)
                
                # PIL转换
                pil_image = Image.fromarray(frame)
                
                # 保存到内存并转换为base64
                buffer = BytesIO()
                pil_image.save(buffer, format="PNG")
                buffer.seek(0)
                base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
                
                # 构建data URL
                data_url = f"data:image/png;base64,{base64_data}"
                frame_urls.append(data_url)
            
            clip.close()
            return frame_urls
            
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        print(f"Error extracting frames from video: {e}")
        import traceback
        traceback.print_exc()
        return []
