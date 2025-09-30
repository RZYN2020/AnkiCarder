import ffmpeg
from typing import Optional, Dict, Any, List
import os
import re
from anki import get_temp_dir

class Subtitle:    
    def __init__(self, video: 'Video', start_time: int, end_time: int, text: str) -> None:
        self.video = video
        self.start_ms = start_time
        self.end_ms = end_time
        self.text = text
    
    def getSentenceAudio(self) -> Optional[str]:
        try:
            file_name = f"{os.path.basename(self.video.path)}_{self.start_ms}_{self.end_ms}.mp3"
            output_path = os.path.join(get_temp_dir(), file_name)
            ffmpeg.input(
                self.video.path, 
                ss=self.start_ms / 1000, 
                t=(self.end_ms - self.start_ms) / 1000
            ).output(
                output_path, 
                vn=None,                 # 1. 禁用视频流（-vn）
                acodec='libmp3lame',     # 2. 指定音频编码器为 MP3 编码器
                ab='192k',               # 3. 指定音频比特率为 192k
            ).global_args('-loglevel', 'error').run()
            return output_path
        except ffmpeg.Error as e:
            print(f"Error extracting audio: {e}")
    
    def getSentenceText(self):
        return self.text
    
    def getScreenShot(self) -> Optional[str]:
        try:
            file_name = f"{os.path.basename(self.video.path)}_{self.start_ms}.jpg"
            output_path = os.path.join(get_temp_dir(), file_name)
            ffmpeg.input(self.video.path, ss=self.start_ms / 1000).output(
                output_path,
                vframes=1,             # Only write 1 video frame
                vcodec='mjpeg',        # Explicitly use the MJPEG encoder for .jpg
                pix_fmt='yuvj420p',    # Use a standard JPEG pixel format (often necessary)
                # You may need to add a scale filter if the input is very high-res or non-standard:
                # vf='scale=1920:-2'   # Example: Scale width to 1920, maintain aspect ratio
            ).global_args('-loglevel', 'error').run()
            return output_path
        except ffmpeg.Error as e:
            print(f"Error extracting screen shot: {e}")

    def __repr__(self):
        return (f"SubTitleSentence(start_ms={self.start_ms}, end_ms={self.end_ms}, "
                f"text='{self.text[:50]}...')")



def parse_time_to_ms(time_str: str) -> int:
    """将 SRT 时间格式 (HH:MM:SS,mmm) 转换为毫秒数"""
    # 示例: 00:01:30,500
    try:
        hours, minutes, rest = time_str.split(':')
        seconds, milliseconds = rest.replace(',', '.').split('.')
        total_ms = (int(hours) * 3600 + int(minutes) * 60 + int(seconds)) * 1000 + int(milliseconds)
        return total_ms
    except ValueError as e:
        print(f"警告：时间格式解析失败 '{time_str}': {e}")
        return 0

def remove_font_tags(text: str) -> str:
    """移除文本中的 <font ... > 和 </font> 标签"""
    # 匹配 <font ... >
    text = re.sub(r'<font\s+.*?>', '', text, flags=re.IGNORECASE)
    # 匹配 </font>
    text = re.sub(r'</font>', '', text, flags=re.IGNORECASE)
    return text

# ----------------------------------------------------

def parse_srt_content(video: 'Video', content: str) -> List[Subtitle]:
    """
    使用正则表达式简化解析 SRT 文件内容。
    
    SRT 块的通用格式为:
    [可选的空行]
    <序号>
    <起始时间> --> <结束时间>
    <文本行 1>
    <文本行 2>
    ...
    [空行]
    
    :param content: 整个 SRT 文件的字符串内容。
    :return: 包含 SubTitleSentence 对象的列表。
    """
    sentences: List[Subtitle] = []
    
    # 核心简化：使用正则表达式匹配整个字幕块
    # 模式说明:
    # 1. (\d+)\n        : 匹配序号 (\d+), 后面跟一个换行符 \n
    # 2. (.*?) --> (.*?): 匹配时间戳，非贪婪地捕获起始和结束时间
    # 3. \n            : 匹配时间戳后的换行符
    # 4. ([\s\S]*?)    : 非贪婪地捕获中间所有的文本内容 (包括换行符和空格)
    # 5. \n{2,}         : 匹配块结束的两个或更多个换行符 (或文件末尾)
    SRT_BLOCK_PATTERN = re.compile(
        r'(\d+)\s*\n'                 # 序号
        r'(.*?) --> (.*?)\s*\n'       # 起始时间 --> 结束时间
        r'([\s\S]*?)'                 # 文本内容 (非贪婪匹配)
        r'(?=\n{2,}|\Z)',             # 正向预查：匹配两个以上空行或文件末尾 (\Z)
        re.MULTILINE 
    )

    for match in SRT_BLOCK_PATTERN.finditer(content):
        # index, start_time_str, end_time_str, raw_text = match.groups()
        start_time_str, end_time_str, raw_text = match.group(2), match.group(3), match.group(4)
        
        # 1. 清洗文本
        text_with_tags_removed = remove_font_tags(raw_text.strip())
        
        # 2. 移除多余空格，将所有内部空白 (包括换行) 替换为单个空格，并移除首尾空格
        clean_text = ' '.join(text_with_tags_removed.split()).strip()
        
        if clean_text:
            # 3. 解析时间并创建对象
            start_ms = parse_time_to_ms(start_time_str)
            end_ms = parse_time_to_ms(end_time_str)
            
            sentences.append(Subtitle(video, start_ms, end_ms, clean_text))

    return sentences
  

class Video:
    def __init__(self, video_path: str, subtitle_path: Optional[str] = None) -> None:
        self.path = video_path
        self.subtitles = []
        if subtitle_path:
            self._load_external_subtitle(subtitle_path)
        else:
            self._extract_subtitle()
    
    def _load_external_subtitle(self, subtitle_path: str):
        with open(subtitle_path, 'r', encoding='utf-8') as file:
            content = file.read()
            self.subtitles = parse_srt_content(self, content)
    
    def _extract_subtitle(self):
        try:
            file_name = f"{self.path.split('.')[0]}.srt"
            output_path = os.path.join(get_temp_dir(), file_name)
            ffmpeg.input(self.path).output(output_path).global_args('-loglevel', 'error').run()
        except ffmpeg.Error as e:
            print(f"Error extracting subtitle: {e}")
            return
        self._load_external_subtitle(output_path)