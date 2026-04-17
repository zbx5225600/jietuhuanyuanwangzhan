import base64
from openai.types.chat import ChatCompletionContentPartParam, ChatCompletionMessageParam
from prompts.prompt_types import Stack
from prompts import system_prompt
from prompts.policies import build_selected_stack_policy, build_user_image_policy
from video.utils import get_video_bytes_and_mime_type
from video.frame_extractor import extract_frames_from_video


def build_video_prompt_messages(
    video_data_url: str,
    stack: Stack,
    text_prompt: str,
    image_generation_enabled: bool,
    fps: float = 1.0,
    max_frames: int = 30,
) -> list[ChatCompletionMessageParam]:
    image_policy = build_user_image_policy(image_generation_enabled)
    selected_stack = build_selected_stack_policy(stack)
    
    user_text = f"""
    You have been given a video of a user interacting with a web app. You need to re-create the same app exactly such that the same user interactions will produce the same results in the app you build.

    - Watch the entire video carefully and understand all the user interactions and UI state changes.
    - The video has been split into multiple key frames, one frame per second.
    - Study all frames carefully to understand how the UI evolves.
    - Make sure the app looks exactly like what you see in the video frames.
    - Pay close attention to background color, text color, font size, font family,
    padding, margin, border, etc. Match the colors and sizes exactly.
    - {image_policy}
    - If some functionality requires a backend call, just mock the data instead.
    - MAKE THE APP FUNCTIONAL using JavaScript. Allow the user to interact with the app and get the same behavior as shown in the video.
    - Use SVGs and interactive 3D elements if needed to match the functionality shown in the video.

    Analyze these video frames and generate the code.
    
    {selected_stack}
    """
    if text_prompt.strip():
        user_text = user_text + "\n\nAdditional instructions: " + text_prompt

    # 提取视频帧
    video_bytes, _ = get_video_bytes_and_mime_type(video_data_url)
    frame_urls = extract_frames_from_video(video_bytes, fps, max_frames)
    
    # 构建用户内容：所有帧 + 文本提示
    user_content: list[ChatCompletionContentPartParam] = []
    
    # 添加所有帧作为图片
    for frame_url in frame_urls:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": frame_url, "detail": "high"},
        })
    
    # 添加文本提示
    user_content.append({
        "type": "text",
        "text": user_text,
    })

    return [
        {
            "role": "system",
            "content": system_prompt.SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]
